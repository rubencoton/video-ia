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
from video_processor import process_video


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


@app.post("/api/generate")
def api_generate() -> object:
    _ensure_folders()

    video = request.files.get("video")
    image = request.files.get("image")
    prompt = str(request.form.get("prompt", "")).strip()

    if not video or not video.filename:
        return jsonify({"ok": False, "message": "Falta el archivo de video."}), 400
    if not image or not image.filename:
        return jsonify({"ok": False, "message": "Falta la imagen de referencia."}), 400
    if not prompt:
        return jsonify({"ok": False, "message": "Falta el prompt."}), 400

    if not _allowed_file(video.filename, {".mp4", ".mov", ".mkv", ".avi", ".webm"}):
        return jsonify({"ok": False, "message": "Formato de video no soportado."}), 400
    if not _allowed_file(image.filename, {".png", ".jpg", ".jpeg", ".webp"}):
        return jsonify({"ok": False, "message": "Formato de imagen no soportado."}), 400

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_id = f"upload_{stamp}_{uuid4().hex[:6]}"
    upload_dir = UPLOADS_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    video_ext = Path(video.filename).suffix.lower() or ".mp4"
    image_ext = Path(image.filename).suffix.lower() or ".png"

    video_path = upload_dir / f"input_video{video_ext}"
    image_path = upload_dir / f"input_image{image_ext}"

    video.save(video_path)
    image.save(image_path)

    result = process_video(
        video_path=str(video_path),
        image_path=str(image_path),
        prompt=prompt,
        output_root=str(OUTPUT_DIR),
    )

    if result.output_video.is_relative_to(OUTPUT_DIR):
        rel_path = result.output_video.relative_to(OUTPUT_DIR).as_posix()
    else:
        rel_path = result.output_video.name

    output_url = f"/media/{rel_path}"

    return jsonify(
        {
            "ok": result.ok,
            "message": result.message,
            "effects_applied": result.effects_applied,
            "output_video_url": output_url,
            "output_video_path": str(result.output_video),
            "job_dir": str(result.job_dir),
        }
    )


@app.post("/api/chat")
def api_chat() -> object:
    payload = request.get_json(silent=True) or {}

    user_message = str(payload.get("message", "")).strip()
    markers = payload.get("markers", [])
    current_time = payload.get("current_time", 0.0)
    chat_history = payload.get("chat_history", [])

    if not user_message:
        return jsonify({"ok": False, "message": "Mensaje vacio."}), 400

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


def run_server() -> None:
    _load_dotenv()
    _ensure_folders()
    port = _find_free_port()
    url = f"http://127.0.0.1:{port}"

    def _open_browser() -> None:
        webbrowser.open(url)

    print(f"VIDEO IA local en {url}")
    print("Cierra esta ventana para detener la app.")
    threading.Timer(1.0, _open_browser).start()
    app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    run_server()
