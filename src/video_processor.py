from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List


TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_RATIO_LABEL = "9:16 (1080x1920)"


@dataclass
class ProcessResult:
    ok: bool
    output_video: Path
    job_dir: Path
    message: str
    effects_applied: List[str]


def _normalize(text: str) -> str:
    table = str.maketrans(
        {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ä": "a",
            "ë": "e",
            "ï": "i",
            "ö": "o",
            "ü": "u",
            "ñ": "n",
        }
    )
    return text.lower().translate(table)


def _detect_effects(prompt: str) -> tuple[List[str], List[str]]:
    normalized = _normalize(prompt)
    filters: List[str] = []
    labels: List[str] = []

    rules = [
        (["blanco y negro", "black and white", "bn"], "hue=s=0", "Blanco y negro"),
        (
            ["sepia", "vintage"],
            "colorchannelmixer=.393:.769:.189:.349:.686:.168:.272:.534:.131",
            "Sepia/Vintage",
        ),
        (["mas brillo", "más brillo", "brillo"], "eq=brightness=0.06", "Mas brillo"),
        (
            ["alto contraste", "contraste"],
            "eq=contrast=1.20:saturation=1.05",
            "Contraste",
        ),
        (
            ["cinematic", "cinematografico", "cinematografica"],
            "eq=contrast=1.12:saturation=1.20",
            "Cinematic",
        ),
    ]

    for keywords, ff_filter, label in rules:
        if any(keyword in normalized for keyword in keywords):
            filters.append(ff_filter)
            labels.append(label)

    return filters, labels


def _resolve_ffmpeg() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def process_video(
    video_path: str,
    image_path: str,
    prompt: str,
    output_root: str,
) -> ProcessResult:
    src_video = Path(video_path).resolve()
    src_image = Path(image_path).resolve()
    output_root_path = Path(output_root).resolve()

    if not src_video.exists():
        return ProcessResult(
            ok=False,
            output_video=Path(),
            job_dir=Path(),
            message="No existe el video indicado.",
            effects_applied=[],
        )

    if not src_image.exists():
        return ProcessResult(
            ok=False,
            output_video=Path(),
            job_dir=Path(),
            message="No existe la imagen indicada.",
            effects_applied=[],
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"job_{timestamp}"
    job_dir = output_root_path / safe_name
    job_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = job_dir / "prompt.txt"
    prompt_file.write_text(prompt.strip(), encoding="utf-8")

    input_copy_video = job_dir / f"input_video{src_video.suffix.lower()}"
    input_copy_image = job_dir / f"input_image{src_image.suffix.lower()}"
    shutil.copy2(src_video, input_copy_video)
    shutil.copy2(src_image, input_copy_image)

    ffmpeg_path = _resolve_ffmpeg()
    output_video = job_dir / "video_resultado.mp4"
    filters, labels = _detect_effects(prompt)

    if not ffmpeg_path:
        fallback_video = job_dir / "video_resultado_sin_procesar.mp4"
        shutil.copy2(src_video, fallback_video)
        (job_dir / "resultado.txt").write_text(
            (
                "No se encontro ffmpeg.\n"
                "Se ha dejado una copia del video original.\n"
                "No se puede garantizar formato fijo 1080x1920 sin ffmpeg.\n"
                "Instala ffmpeg o imageio-ffmpeg para activar edicion automatica.\n"
            ),
            encoding="utf-8",
        )
        return ProcessResult(
            ok=False,
            output_video=fallback_video,
            job_dir=job_dir,
            message=(
                "No se encontro ffmpeg. "
                "No se pudo forzar formato Reels 9:16 (1080x1920)."
            ),
            effects_applied=[],
        )

    base_transform = (
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}"
    )
    video_chain = ",".join(filters + [base_transform]) if filters else base_transform
    filter_complex = (
        f"[0:v]{video_chain}[base];"
        "[1:v]scale=280:-1[ref];"
        "[base][ref]overlay=W-w-24:24[outv]"
    )

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(input_copy_video),
        "-loop",
        "1",
        "-i",
        str(input_copy_image),
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "21",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_video),
    ]

    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if proc.returncode != 0:
        fallback_video = job_dir / "video_resultado_sin_procesar.mp4"
        try:
            shutil.copy2(input_copy_video, fallback_video)
        except Exception:
            fallback_video = input_copy_video
        (job_dir / "ffmpeg_error.log").write_text(proc.stderr, encoding="utf-8")
        return ProcessResult(
            ok=False,
            output_video=fallback_video,
            job_dir=job_dir,
            message=(
                "Hubo un error aplicando filtros. "
                "Se guardo copia del video original y log del error."
            ),
            effects_applied=[],
        )

    summary = {
        "prompt": prompt,
        "effects_applied": labels,
        "input_video": str(src_video),
        "input_image": str(src_image),
        "output_video": str(output_video),
        "output_ratio": TARGET_RATIO_LABEL,
        "output_resolution": f"{TARGET_WIDTH}x{TARGET_HEIGHT}",
    }
    (job_dir / "resumen.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if labels:
        status_msg = (
            "Video generado en formato Reels 9:16 (1080x1920) con efectos: "
            + ", ".join(labels)
        )
    else:
        status_msg = (
            "Video generado en formato Reels 9:16 (1080x1920) "
            "(sin efecto detectado en prompt, con imagen aplicada)."
        )

    return ProcessResult(
        ok=True,
        output_video=output_video,
        job_dir=job_dir,
        message=status_msg,
        effects_applied=labels,
    )
