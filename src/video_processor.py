from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import subprocess
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List


TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_RATIO_LABEL = "9:16 (1080x1920)"

RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"
RUNWAY_API_VERSION = "2024-11-06"


@dataclass
class ProcessResult:
    ok: bool
    output_video: Path
    job_dir: Path
    message: str
    effects_applied: List[str]
    backend: str = "local"


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


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
        (["mas brillo", "brillo"], "eq=brightness=0.06", "Mas brillo"),
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


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _probe_duration_seconds(media_path: Path, ffmpeg_path: str) -> float | None:
    proc = _run_command([ffmpeg_path, "-i", str(media_path)])
    text = (proc.stderr or "") + "\n" + (proc.stdout or "")
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


def _choose_backend() -> str:
    requested = os.getenv("VIDEO_GEN_BACKEND", "auto").strip().lower()
    if requested not in {"auto", "runway", "local"}:
        requested = "auto"

    runway_key = (
        os.getenv("RUNWAY_API_KEY", "").strip()
        or os.getenv("RUNWAYML_API_SECRET", "").strip()
    )

    if requested == "local":
        return "local"
    if requested == "runway":
        return "runway" if runway_key else "local"
    if runway_key:
        return "runway"
    return "local"


def _ensure_reels_video(source_video: Path, reels_video: Path, ffmpeg_path: str) -> None:
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(source_video),
        "-vf",
        (
            f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}"
        ),
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
        str(reels_video),
    ]
    proc = _run_command(command)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "Error desconocido preparando reels.")


def _remux_audio(
    video_source: Path,
    audio_source: Path,
    output_path: Path,
    ffmpeg_path: str,
) -> bool:
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(video_source),
        "-i",
        str(audio_source),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_path),
    ]
    proc = _run_command(command)
    return proc.returncode == 0


def _build_summary(
    backend: str,
    prompt: str,
    input_video: Path,
    input_image: Path | None,
    input_audio: Path | None,
    output_video: Path,
    effects_applied: List[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "backend": backend,
        "prompt": prompt,
        "effects_applied": effects_applied,
        "input_video": str(input_video),
        "input_image": str(input_image) if input_image else None,
        "input_audio": str(input_audio) if input_audio else None,
        "output_video": str(output_video),
        "output_ratio": TARGET_RATIO_LABEL,
        "output_resolution": f"{TARGET_WIDTH}x{TARGET_HEIGHT}",
    }
    if extra:
        summary.update(extra)
    return summary


def _json_request(
    url: str,
    method: str,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read().decode("utf-8", errors="replace")
            if not raw.strip():
                return {}
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Error de red: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Respuesta JSON invalida del proveedor.") from exc


def _multipart_upload(upload_url: str, fields: dict[str, Any], file_path: Path) -> None:
    boundary = f"----VideoIAFormBoundary{int(time.time() * 1000)}"
    file_bytes = file_path.read_bytes()
    file_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    body_parts: list[bytes] = []
    for key, value in fields.items():
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(
            f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8")
        )
        body_parts.append(f"{value}\r\n".encode("utf-8"))

    body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
    body_parts.append(
        (
            f'Content-Disposition: form-data; name="file"; '
            f'filename="{file_path.name}"\r\n'
        ).encode("utf-8")
    )
    body_parts.append(f"Content-Type: {file_type}\r\n\r\n".encode("utf-8"))
    body_parts.append(file_bytes)
    body_parts.append(b"\r\n")
    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(body_parts)

    request = urllib.request.Request(
        upload_url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180):
            return
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Fallo subiendo archivo al proveedor: HTTP {exc.code} {body_text}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Fallo de red subiendo archivo al proveedor: {exc}") from exc


def _runway_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Runway-Version": RUNWAY_API_VERSION,
    }


def _runway_upload_file(api_key: str, file_path: Path) -> str:
    response = _json_request(
        f"{RUNWAY_API_BASE}/uploads",
        "POST",
        _runway_headers(api_key),
        {"filename": file_path.name, "type": "ephemeral"},
    )

    upload_url = str(response.get("uploadUrl", "")).strip()
    runway_uri = str(response.get("uri", "") or response.get("runwayUri", "")).strip()
    fields = response.get("fields", {})

    if not upload_url or not runway_uri or not isinstance(fields, dict):
        raise RuntimeError("Respuesta invalida al crear upload en Runway.")

    _multipart_upload(upload_url, fields, file_path)
    return runway_uri


def _collect_http_urls(value: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("http://") or text.startswith("https://"):
            urls.append(text)
        return urls
    if isinstance(value, dict):
        for v in value.values():
            urls.extend(_collect_http_urls(v))
        return urls
    if isinstance(value, list):
        for item in value:
            urls.extend(_collect_http_urls(item))
        return urls
    return urls


def _pick_best_video_url(task_data: dict[str, Any]) -> str | None:
    urls = _collect_http_urls(task_data.get("output", task_data))
    if not urls:
        urls = _collect_http_urls(task_data)
    if not urls:
        return None

    mp4_urls = [url for url in urls if ".mp4" in url.lower()]
    if mp4_urls:
        return mp4_urls[0]
    return urls[0]


def _download_file(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            data = response.read()
            destination.write_bytes(data)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Error descargando video generado: HTTP {exc.code} {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Error de red descargando video generado: {exc}") from exc


def _runway_wait_for_task(api_key: str, task_id: str) -> dict[str, Any]:
    timeout_seconds = int(os.getenv("RUNWAY_MAX_WAIT_SECONDS", "900"))
    poll_seconds = max(5, int(os.getenv("RUNWAY_POLL_SECONDS", "6")))
    started = time.time()

    while True:
        task = _json_request(
            f"{RUNWAY_API_BASE}/tasks/{task_id}",
            "GET",
            _runway_headers(api_key),
            None,
        )
        status = str(task.get("status", "")).strip().upper()

        if status in {"SUCCEEDED", "SUCCESS", "COMPLETED"}:
            return task
        if status in {"FAILED", "ERROR", "CANCELED", "CANCELLED"}:
            failure = task.get("failure") or task.get("failureCode") or "Sin detalle"
            raise RuntimeError(f"Runway devolvio estado {status}: {failure}")

        if time.time() - started > timeout_seconds:
            raise RuntimeError("Timeout esperando el resultado de Runway.")

        time.sleep(poll_seconds)


def _process_with_local_backend(
    prepared_video: Path,
    reference_image: Path | None,
    external_audio: Path | None,
    prompt: str,
    job_dir: Path,
    ffmpeg_path: str,
    source_video: Path,
    effects: List[str],
    labels: List[str],
) -> ProcessResult:
    visual_output = job_dir / "video_visual_local.mp4"
    final_output = job_dir / "video_resultado.mp4"

    base_transform = (
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_WIDTH}:{TARGET_HEIGHT}"
    )
    video_chain = ",".join(effects + [base_transform]) if effects else base_transform

    if reference_image:
        filter_complex = (
            f"[0:v]{video_chain}[base];"
            "[1:v]scale=280:-1[ref];"
            "[base][ref]overlay=W-w-24:24[outv]"
        )
        command = [
            ffmpeg_path,
            "-y",
            "-i",
            str(prepared_video),
            "-loop",
            "1",
            "-i",
            str(reference_image),
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
            str(visual_output),
        ]
    else:
        command = [
            ffmpeg_path,
            "-y",
            "-i",
            str(prepared_video),
            "-vf",
            video_chain,
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
            "-movflags",
            "+faststart",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(visual_output),
        ]

    proc = _run_command(command)
    if proc.returncode != 0:
        fallback_video = job_dir / "video_resultado_sin_procesar.mp4"
        try:
            shutil.copy2(prepared_video, fallback_video)
        except Exception:
            fallback_video = prepared_video
        (job_dir / "ffmpeg_error.log").write_text(proc.stderr, encoding="utf-8")
        return ProcessResult(
            ok=False,
            output_video=fallback_video,
            job_dir=job_dir,
            message=(
                "Error aplicando cambios locales. "
                "Se guardo copia del video base preparado."
            ),
            effects_applied=[],
            backend="local",
        )

    audio_source = external_audio if external_audio and external_audio.exists() else None
    if audio_source:
        if not _remux_audio(visual_output, audio_source, final_output, ffmpeg_path):
            shutil.copy2(visual_output, final_output)
    else:
        shutil.copy2(visual_output, final_output)

    summary = _build_summary(
        backend="local",
        prompt=prompt,
        input_video=source_video,
        input_image=reference_image,
        input_audio=audio_source,
        output_video=final_output,
        effects_applied=labels,
    )
    (job_dir / "resumen.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if labels:
        status_msg = (
            "Video generado en formato Reels 9:16 (1080x1920) con backend local. "
            "Efectos: " + ", ".join(labels)
        )
    else:
        status_msg = (
            "Video generado en formato Reels 9:16 (1080x1920) con backend local."
        )

    return ProcessResult(
        ok=True,
        output_video=final_output,
        job_dir=job_dir,
        message=status_msg,
        effects_applied=labels,
        backend="local",
    )


def _process_with_runway_backend(
    prepared_video: Path,
    reference_image: Path | None,
    external_audio: Path | None,
    prompt: str,
    job_dir: Path,
    ffmpeg_path: str,
    source_video: Path,
) -> ProcessResult:
    api_key = (
        os.getenv("RUNWAY_API_KEY", "").strip()
        or os.getenv("RUNWAYML_API_SECRET", "").strip()
    )
    if not api_key:
        return ProcessResult(
            ok=False,
            output_video=Path(),
            job_dir=job_dir,
            message="Falta RUNWAY_API_KEY para usar backend Runway.",
            effects_applied=[],
            backend="runway",
        )

    try:
        runway_video_uri = _runway_upload_file(api_key, prepared_video)
        runway_image_uri = _runway_upload_file(api_key, reference_image) if reference_image else None

        payload: dict[str, Any] = {
            "model": "gen4_aleph",
            "videoUri": runway_video_uri,
            "promptText": prompt[:1000],
        }
        if runway_image_uri:
            payload["references"] = [{"type": "image", "uri": runway_image_uri}]

        created_task = _json_request(
            f"{RUNWAY_API_BASE}/video_to_video",
            "POST",
            _runway_headers(api_key),
            payload,
        )
        task_id = str(created_task.get("id", "")).strip()
        if not task_id:
            raise RuntimeError("Runway no devolvio id de tarea.")

        final_task = _runway_wait_for_task(api_key, task_id)
        generated_url = _pick_best_video_url(final_task)
        if not generated_url:
            raise RuntimeError("No se encontro URL de video en la respuesta de Runway.")

        raw_runway_video = job_dir / "video_runway_raw.mp4"
        _download_file(generated_url, raw_runway_video)

        reels_visual = job_dir / "video_runway_reels.mp4"
        _ensure_reels_video(raw_runway_video, reels_visual, ffmpeg_path)

        final_output = job_dir / "video_resultado.mp4"
        audio_source = external_audio if external_audio and external_audio.exists() else prepared_video
        if not _remux_audio(reels_visual, audio_source, final_output, ffmpeg_path):
            shutil.copy2(reels_visual, final_output)

        duration = _probe_duration_seconds(prepared_video, ffmpeg_path)
        cost_hint = ""
        if duration:
            # Runway gen4_aleph: 15 credits/s -> $0.15/s
            cost_hint = f" Coste estimado aprox: ${duration * 0.15:.2f}."

        summary = _build_summary(
            backend="runway",
            prompt=prompt,
            input_video=source_video,
            input_image=reference_image,
            input_audio=audio_source,
            output_video=final_output,
            effects_applied=[],
            extra={"runway_task_id": task_id, "generated_url": generated_url},
        )
        (job_dir / "resumen.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return ProcessResult(
            ok=True,
            output_video=final_output,
            job_dir=job_dir,
            message=(
                "Video generado con Runway (gen4_aleph) en formato Reels 9:16 "
                "(1080x1920)." + cost_hint
            ),
            effects_applied=[],
            backend="runway",
        )
    except Exception as exc:
        return ProcessResult(
            ok=False,
            output_video=prepared_video,
            job_dir=job_dir,
            message=f"Fallo backend Runway: {exc}",
            effects_applied=[],
            backend="runway",
        )


def process_video(
    video_path: str,
    image_path: str | None,
    prompt: str,
    output_root: str,
    audio_path: str | None = None,
) -> ProcessResult:
    src_video = Path(video_path).resolve()
    src_image = Path(image_path).resolve() if image_path else None
    src_audio = Path(audio_path).resolve() if audio_path else None
    output_root_path = Path(output_root).resolve()

    if not src_video.exists():
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

    ffmpeg_path = _resolve_ffmpeg()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir = output_root_path / f"job_{timestamp}"
    job_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = job_dir / "prompt.txt"
    prompt_file.write_text(prompt.strip(), encoding="utf-8")

    input_copy_video = job_dir / f"input_video{src_video.suffix.lower() or '.mp4'}"
    shutil.copy2(src_video, input_copy_video)

    input_copy_image: Path | None = None
    if src_image:
        input_copy_image = job_dir / f"input_image{src_image.suffix.lower() or '.png'}"
        shutil.copy2(src_image, input_copy_image)

    input_copy_audio: Path | None = None
    if src_audio:
        input_copy_audio = job_dir / f"input_audio{src_audio.suffix.lower() or '.mp3'}"
        shutil.copy2(src_audio, input_copy_audio)

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
            backend="local",
        )

    prepared_video = job_dir / "input_video_reels.mp4"
    try:
        _ensure_reels_video(input_copy_video, prepared_video, ffmpeg_path)
    except Exception as exc:
        fallback_video = job_dir / "video_resultado_sin_procesar.mp4"
        shutil.copy2(input_copy_video, fallback_video)
        (job_dir / "ffmpeg_error.log").write_text(str(exc), encoding="utf-8")
        return ProcessResult(
            ok=False,
            output_video=fallback_video,
            job_dir=job_dir,
            message=f"No se pudo preparar el video en formato Reels: {exc}",
            effects_applied=[],
            backend="local",
        )

    backend = _choose_backend()
    effects, labels = _detect_effects(prompt)

    if backend == "runway":
        runway_result = _process_with_runway_backend(
            prepared_video=prepared_video,
            reference_image=input_copy_image,
            external_audio=input_copy_audio,
            prompt=prompt,
            job_dir=job_dir,
            ffmpeg_path=ffmpeg_path,
            source_video=src_video,
        )
        if runway_result.ok or os.getenv("VIDEO_GEN_BACKEND", "auto").strip().lower() == "runway":
            return runway_result

        local_result = _process_with_local_backend(
            prepared_video=prepared_video,
            reference_image=input_copy_image,
            external_audio=input_copy_audio,
            prompt=prompt,
            job_dir=job_dir,
            ffmpeg_path=ffmpeg_path,
            source_video=src_video,
            effects=effects,
            labels=labels,
        )
        if local_result.ok:
            local_result.message = (
                runway_result.message
                + " Se uso backend local como respaldo. "
                + local_result.message
            )
        return local_result

    return _process_with_local_backend(
        prepared_video=prepared_video,
        reference_image=input_copy_image,
        external_audio=input_copy_audio,
        prompt=prompt,
        job_dir=job_dir,
        ffmpeg_path=ffmpeg_path,
        source_video=src_video,
        effects=effects,
        labels=labels,
    )
