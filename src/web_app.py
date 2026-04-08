from __future__ import annotations

import os
import socket
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, send_from_directory

from ai_chat import generate_chat_reply
from sidance_local import generate_sidance_video, get_sidance_status
from video_composer import process_multimodal_video


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = Path(__file__).resolve().parent
STATIC_DIR = SRC_DIR / "static"
OUTPUT_DIR = ROOT_DIR / "output"
UPLOADS_DIR = ROOT_DIR / "input" / "web_uploads"


app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")


def _load_dotenv() -> None:
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _ensure_folders() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _allowed_file(filename: str, valid_exts: set[str]) -> bool:
    lower = filename.lower()
    return any(lower.endswith(ext) for ext in valid_exts)


def _is_runway_configured() -> bool:
    return bool(
        os.getenv("RUNWAY_API_KEY", "").strip()
        or os.getenv("RUNWAYML_API_SECRET", "").strip()
    )


def _find_free_port(start_port: int = 7860, max_tries: int = 40) -> int:
    for step in range(max_tries):
        port = start_port + step
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


@app.route("/")
def index() -> object:
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/media/<path:subpath>")
def media(subpath: str) -> object:
    return send_from_directory(OUTPUT_DIR, subpath, as_attachment=False)


@app.get("/api/system-status")
def api_system_status() -> object:
    _load_dotenv()
    backend = os.getenv("VIDEO_GEN_BACKEND", "auto").strip().lower() or "auto"
    if backend not in {"auto", "runway", "local"}:
        backend = "auto"

    runway_ok = _is_runway_configured()
    effective = "runway" if (backend in {"auto", "runway"} and runway_ok) else "local"
    sidance_status = get_sidance_status()

    return jsonify(
        {
            "ok": True,
            "backend_config": backend,
            "runway_configured": runway_ok,
            "effective_backend": effective,
            "output_format": "9:16 1080x1920",
            "sidance": sidance_status,
        }
    )


@app.post("/api/generate")
def api_generate() -> object:
    _load_dotenv()
    _ensure_folders()

    video = request.files.get("video")
    image = request.files.get("image")
    audio = request.files.get("audio")
    prompt = str(request.form.get("prompt", "")).strip()
    overlay_text = str(request.form.get("overlay_text", "")).strip()
    text_position = str(request.form.get("text_position", "abajo")).strip()
    text_color = str(request.form.get("text_color", "blanco")).strip()

    text_size_raw = str(request.form.get("text_size", "")).strip()
    image_seconds_raw = str(request.form.get("image_duration_seconds", "")).strip()

    try:
        text_size = int(text_size_raw) if text_size_raw else None
    except ValueError:
        text_size = None

    try:
        image_duration_seconds = (
            float(image_seconds_raw) if image_seconds_raw else None
        )
    except ValueError:
        image_duration_seconds = None

    if (not video or not video.filename) and (not image or not image.filename):
        return jsonify({"ok": False, "message": "Debes subir un vídeo o una imagen."}), 400
    if not prompt:
        return jsonify({"ok": False, "message": "Falta el texto de instrucción."}), 400

    if video and video.filename and not _allowed_file(
        video.filename, {".mp4", ".mov", ".mkv", ".avi", ".webm"}
    ):
        return jsonify({"ok": False, "message": "Formato de vídeo no soportado."}), 400

    if image and image.filename and not _allowed_file(
        image.filename, {".png", ".jpg", ".jpeg", ".webp"}
    ):
        return jsonify({"ok": False, "message": "Formato de imagen no admitido."}), 400

    if audio and audio.filename and not _allowed_file(
        audio.filename, {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
    ):
        return jsonify({"ok": False, "message": "Formato de audio no admitido."}), 400

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_id = f"upload_{stamp}_{uuid4().hex[:6]}"
    upload_dir = UPLOADS_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    video_path: Path | None = None
    image_path: Path | None = None
    audio_path: Path | None = None

    if video and video.filename:
        video_ext = Path(video.filename).suffix.lower() or ".mp4"
        video_path = upload_dir / f"input_video{video_ext}"
        video.save(video_path)

    if image and image.filename:
        image_ext = Path(image.filename).suffix.lower() or ".png"
        image_path = upload_dir / f"input_image{image_ext}"
        image.save(image_path)

    if audio and audio.filename:
        audio_ext = Path(audio.filename).suffix.lower() or ".mp3"
        audio_path = upload_dir / f"input_audio{audio_ext}"
        audio.save(audio_path)

    result = process_multimodal_video(
        video_path=str(video_path) if video_path else None,
        image_path=str(image_path) if image_path else None,
        prompt=prompt,
        output_root=str(OUTPUT_DIR),
        audio_path=str(audio_path) if audio_path else None,
        overlay_text=overlay_text,
        text_position=text_position,
        text_size=text_size,
        text_color=text_color,
        image_duration_seconds=image_duration_seconds,
    )

    output_url = ""
    if result.output_video.is_file():
        if result.output_video.is_relative_to(OUTPUT_DIR):
            rel_path = result.output_video.relative_to(OUTPUT_DIR).as_posix()
        else:
            rel_path = result.output_video.name

        output_url = f"/media/{rel_path}"

    status_code = 200 if result.ok else 400
    return (
        jsonify(
            {
                "ok": result.ok,
                "message": result.message,
                "effects_applied": result.effects_applied,
                "backend": result.backend,
                "output_video_url": output_url,
                "output_video_path": str(result.output_video) if result.output_video.is_file() else "",
                "job_dir": str(result.job_dir),
            }
        ),
        status_code,
    )


@app.post("/api/chat")
def api_chat() -> object:
    _load_dotenv()
    payload = request.get_json(silent=True) or {}

    user_message = str(payload.get("message", "")).strip()
    markers = payload.get("markers", [])
    current_time = payload.get("current_time", 0.0)
    chat_history = payload.get("chat_history", [])

    if not user_message:
        return jsonify({"ok": False, "message": "Mensaje vacío."}), 400

    if not isinstance(markers, list):
        markers = []
    if not isinstance(chat_history, list):
        chat_history = []

    try:
        current_time_value = float(current_time)
    except (TypeError, ValueError):
        current_time_value = 0.0

    reply = generate_chat_reply(
        user_message=user_message,
        markers=markers,
        current_time=current_time_value,
        chat_history=chat_history,
    )
    return jsonify({"ok": True, "reply": reply})


@app.post("/api/generate-sidance")
def api_generate_sidance() -> object:
    _load_dotenv()
    _ensure_folders()

    payload = request.get_json(silent=True) or {}

    prompt = str(payload.get("prompt", "")).strip()
    size_label = str(payload.get("size_label", "")).strip() or None

    steps_raw = payload.get("num_inference_steps")
    guidance_raw = payload.get("guidance_scale")
    seed_raw = payload.get("seed")

    try:
        num_inference_steps = int(steps_raw) if steps_raw is not None else None
    except (TypeError, ValueError):
        num_inference_steps = None

    try:
        guidance_scale = float(guidance_raw) if guidance_raw is not None else None
    except (TypeError, ValueError):
        guidance_scale = None

    try:
        seed = int(seed_raw) if seed_raw is not None else None
    except (TypeError, ValueError):
        seed = None

    result = generate_sidance_video(
        prompt=prompt,
        output_root=OUTPUT_DIR,
        size_label=size_label,
        num_inference_steps=num_inference_steps,
        guidance_scale=guidance_scale,
        seed=seed,
    )

    output_url = ""
    if result.output_video.is_file():
        if result.output_video.is_relative_to(OUTPUT_DIR):
            rel_path = result.output_video.relative_to(OUTPUT_DIR).as_posix()
        else:
            rel_path = result.output_video.name
        output_url = f"/media/{rel_path}"

    status_code = 200 if result.ok else 400
    return (
        jsonify(
            {
                "ok": result.ok,
                "message": result.message,
                "backend": result.backend,
                "model_id": result.model_id,
                "output_video_url": output_url,
                "output_video_path": str(result.output_video) if result.output_video.is_file() else "",
                "job_dir": str(result.job_dir),
            }
        ),
        status_code,
    )


def run_server() -> None:
    _load_dotenv()
    _ensure_folders()
    port = _find_free_port()
    url = f"http://127.0.0.1:{port}"

    def _open_browser() -> None:
        webbrowser.open(url)

    print(f"SEEDANCE RUBEN COTON local en {url}")
    print("Cierra esta ventana para detener la aplicación.")
    threading.Timer(1.0, _open_browser).start()
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    run_server()
