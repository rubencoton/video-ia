from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from video_processor import ProcessResult, process_video


DEFAULT_IMAGE_SECONDS = 8.0


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _resolve_ffmpeg() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _probe_duration_seconds(media_path: Path, ffmpeg_path: str) -> float | None:
    proc = _run_command([ffmpeg_path, "-i", str(media_path)])
    text = (proc.stderr or "") + "\n" + (proc.stdout or "")
    import re

    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


def _escape_drawtext_text(value: str) -> str:
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace(":", "\\:")
    escaped = escaped.replace("'", "\\'")
    escaped = escaped.replace("%", "\\%")
    escaped = escaped.replace("\n", "\\n")
    return escaped


def _sanitize_position(value: str | None) -> str:
    key = str(value or "").strip().lower()
    if key in {"arriba", "top"}:
        return "arriba"
    if key in {"centro", "center", "middle"}:
        return "centro"
    return "abajo"


def _sanitize_color(value: str | None) -> str:
    key = str(value or "").strip().lower()
    mapping = {
        "blanco": "white",
        "negro": "black",
        "amarillo": "yellow",
        "cian": "cyan",
        "rojo": "red",
    }
    return mapping.get(key, "white")


def _drawtext_filter(
    overlay_text: str,
    position: str | None,
    size: int | None,
    color: str | None,
) -> str | None:
    text = str(overlay_text or "").strip()
    if not text:
        return None

    text = text[:220]
    text_escaped = _escape_drawtext_text(text)
    pos = _sanitize_position(position)
    y_expr = "h-th-70"
    if pos == "arriba":
        y_expr = "70"
    elif pos == "centro":
        y_expr = "(h-text_h)/2"

    size_value = size if isinstance(size, int) else 46
    size_value = max(18, min(110, size_value))
    color_value = _sanitize_color(color)

    return (
        "drawtext="
        f"text='{text_escaped}':"
        f"fontcolor={color_value}:"
        f"fontsize={size_value}:"
        "line_spacing=8:"
        "box=1:"
        "boxcolor=black@0.40:"
        "boxborderw=18:"
        "borderw=2:"
        "bordercolor=black@0.80:"
        "x=(w-text_w)/2:"
        f"y={y_expr}"
    )


def _create_video_from_image(
    image_path: Path,
    output_path: Path,
    ffmpeg_path: str,
    duration_seconds: float,
) -> None:
    duration = max(1.0, min(600.0, float(duration_seconds)))
    command = [
        ffmpeg_path,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_path),
        "-t",
        f"{duration:.2f}",
        "-r",
        "24",
        "-vf",
        "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    proc = _run_command(command)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "No se pudo crear video desde imagen.")


def _apply_text_overlay(
    base_video: Path,
    output_path: Path,
    ffmpeg_path: str,
    overlay_text: str,
    text_position: str | None,
    text_size: int | None,
    text_color: str | None,
) -> None:
    text_filter = _drawtext_filter(
        overlay_text=overlay_text,
        position=text_position,
        size=text_size,
        color=text_color,
    )
    if not text_filter:
        raise RuntimeError("No hay texto para superponer.")

    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(base_video),
        "-vf",
        text_filter,
        "-map",
        "0:v:0",
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
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        "-shortest",
        str(output_path),
    ]
    proc = _run_command(command)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "No se pudo aplicar el texto al video.")


def process_multimodal_video(
    video_path: str | None,
    image_path: str | None,
    prompt: str,
    output_root: str,
    audio_path: str | None = None,
    overlay_text: str | None = None,
    text_position: str | None = None,
    text_size: int | None = None,
    text_color: str | None = None,
    image_duration_seconds: float | None = None,
) -> ProcessResult:
    src_video = Path(video_path).resolve() if video_path else None
    src_image = Path(image_path).resolve() if image_path else None
    src_audio = Path(audio_path).resolve() if audio_path else None
    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)

    if not src_video and not src_image:
        return ProcessResult(
            ok=False,
            output_video=Path(),
            job_dir=Path(),
            message="Debes subir un video o una imagen.",
            effects_applied=[],
            backend="local",
        )

    if src_video and not src_video.exists():
        return ProcessResult(
            ok=False,
            output_video=Path(),
            job_dir=Path(),
            message="No existe el video indicado.",
            effects_applied=[],
            backend="local",
        )
    if src_image and not src_image.exists():
        return ProcessResult(
            ok=False,
            output_video=Path(),
            job_dir=Path(),
            message="No existe la imagen indicada.",
            effects_applied=[],
            backend="local",
        )
    if src_audio and not src_audio.exists():
        return ProcessResult(
            ok=False,
            output_video=Path(),
            job_dir=Path(),
            message="No existe el audio indicado.",
            effects_applied=[],
            backend="local",
        )

    resolved_video = src_video
    image_for_overlay = src_image

    if resolved_video is None and src_image is not None:
        ffmpeg_path = _resolve_ffmpeg()
        if not ffmpeg_path:
            return ProcessResult(
                ok=False,
                output_video=Path(),
                job_dir=Path(),
                message="No se encontro ffmpeg para crear video desde imagen.",
                effects_applied=[],
                backend="local",
            )

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = output_root_path / f"_tmp_composer_{stamp}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_video = temp_dir / "video_base_desde_imagen.mp4"

        duration = image_duration_seconds if isinstance(image_duration_seconds, (int, float)) else None
        if duration is None and src_audio:
            duration = _probe_duration_seconds(src_audio, ffmpeg_path)
        if duration is None:
            duration = DEFAULT_IMAGE_SECONDS

        try:
            _create_video_from_image(
                image_path=src_image,
                output_path=temp_video,
                ffmpeg_path=ffmpeg_path,
                duration_seconds=float(duration),
            )
        except Exception as exc:
            return ProcessResult(
                ok=False,
                output_video=Path(),
                job_dir=temp_dir,
                message=f"No se pudo crear video base desde imagen: {exc}",
                effects_applied=[],
                backend="local",
            )

        resolved_video = temp_video
        # Cuando la imagen crea el video base, no la duplicamos como overlay de esquina.
        image_for_overlay = None

    assert resolved_video is not None

    result = process_video(
        video_path=str(resolved_video),
        image_path=str(image_for_overlay) if image_for_overlay else None,
        prompt=prompt,
        output_root=str(output_root_path),
        audio_path=str(src_audio) if src_audio else None,
    )
    if not result.ok:
        return result

    if not str(overlay_text or "").strip():
        return result

    ffmpeg_path = _resolve_ffmpeg()
    if not ffmpeg_path:
        result.message += " No se aplico el texto porque no hay ffmpeg."
        return result

    text_output = result.job_dir / "video_resultado_texto.mp4"
    try:
        _apply_text_overlay(
            base_video=result.output_video,
            output_path=text_output,
            ffmpeg_path=ffmpeg_path,
            overlay_text=str(overlay_text),
            text_position=text_position,
            text_size=text_size,
            text_color=text_color,
        )
    except Exception as exc:
        result.message += f" No se aplico el texto: {exc}"
        return result

    result.output_video = text_output
    result.effects_applied = list(result.effects_applied) + ["Texto superpuesto"]
    result.message += " Texto aplicado correctamente."
    return result
