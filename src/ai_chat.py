from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def _format_seconds(seconds: float) -> str:
    total = max(0, int(seconds))
    mins = total // 60
    secs = total % 60
    return f"{mins:02d}:{secs:02d}"


def _marker_brief(markers: list[dict[str, Any]]) -> str:
    if not markers:
        return "No hay marcas aun."

    rows: list[str] = []
    for marker in markers[-12:]:
        marker_id = marker.get("id", "?")
        marker_type = marker.get("type", "point")
        time_sec = float(marker.get("time", 0.0))
        x = float(marker.get("x", 0.0))
        y = float(marker.get("y", 0.0))
        note = str(marker.get("note", "")).strip()

        line = (
            f"#{marker_id} | t={_format_seconds(time_sec)} "
            f"| x={x:.1f}% y={y:.1f}% | tipo={marker_type}"
        )
        if note:
            line += f" | nota={note}"
        rows.append(line)
    return "\n".join(rows)


def _extract_output_text(body: dict[str, Any]) -> str:
    out_text = str(body.get("output_text", "")).strip()
    if out_text:
        return out_text

    output = body.get("output", [])
    if not isinstance(output, list):
        return ""

    chunks: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content", [])
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "output_text":
                text = str(part.get("text", "")).strip()
                if text:
                    chunks.append(text)

    return "\n".join(chunks).strip()


def _build_local_fallback(
    user_message: str,
    markers: list[dict[str, Any]],
    current_time: float,
) -> str:
    msg = user_message.lower()
    lines: list[str] = []

    lines.append("Perfecto. Te ayudo a editar por partes.")
    lines.append(f"Tiempo actual del preview: {_format_seconds(current_time)}.")

    if markers:
        last = markers[-1]
        lines.append(
            (
                f"Ultima marca: #{last.get('id', '?')} "
                f"en {_format_seconds(float(last.get('time', 0.0)))} "
                f"(x={float(last.get('x', 0.0)):.1f}%, y={float(last.get('y', 0.0)):.1f}%)."
            )
        )
    else:
        lines.append("Aun no hay marcas. Haz click o arrastra sobre el video para crear la primera.")

    if "cara" in msg or "rostro" in msg:
        lines.append("Si quieres cambiar una cara, marca primero esa zona y dime el estilo exacto.")
    if "fondo" in msg:
        lines.append("Para cambiar fondo, marca una zona grande y dime el fondo nuevo.")
    if "texto" in msg or "titulo" in msg:
        lines.append("Para texto en pantalla, marca posicion y dime frase + segundos de inicio/fin.")

    lines.append("Dime el siguiente cambio y lo hacemos paso a paso.")
    return "\n".join(lines)


def _call_openai_responses(
    api_key: str,
    model: str,
    system_prompt: str,
    user_message: str,
    markers: list[dict[str, Any]],
    current_time: float,
    chat_history: list[dict[str, str]],
) -> str | None:
    safe_history = []
    for turn in chat_history[-12:]:
        role = str(turn.get("role", "")).strip()
        content = str(turn.get("content", "")).strip()
        if role in {"user", "assistant"} and content:
            safe_history.append(
                {
                    "role": role,
                    "content": [{"type": "text", "text": content}],
                }
            )

    marker_text = _marker_brief(markers)
    user_payload = (
        f"Mensaje del usuario:\n{user_message}\n\n"
        f"Tiempo actual del preview: {_format_seconds(current_time)} ({current_time:.2f}s)\n\n"
        f"Marcas activas:\n{marker_text}"
    )

    input_payload: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": [{"type": "text", "text": system_prompt}],
        }
    ]
    input_payload.extend(safe_history)
    input_payload.append(
        {
            "role": "user",
            "content": [{"type": "text", "text": user_payload}],
        }
    )

    body = {
        "model": model,
        "input": input_payload,
        "temperature": 0.2,
    }

    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=50) as response:
            text = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(text)
            extracted = _extract_output_text(parsed)
            return extracted or None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None


def generate_chat_reply(
    user_message: str,
    markers: list[dict[str, Any]],
    current_time: float,
    chat_history: list[dict[str, str]],
) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"

    system_prompt = (
        "Eres un asistente de edicion de video para una app local.\n"
        "Hablas en espanol simple.\n"
        "Responde con frases cortas y directas.\n"
        "Si hay marcas de tiempo/posicion, usalas para dar instrucciones concretas.\n"
        "Evita jerga tecnica.\n"
        "No inventes datos.\n"
        "Si falta una marca, pide al usuario que la cree en el preview."
    )

    if api_key:
        online_reply = _call_openai_responses(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_message=user_message,
            markers=markers,
            current_time=current_time,
            chat_history=chat_history,
        )
        if online_reply:
            return online_reply

    return _build_local_fallback(
        user_message=user_message,
        markers=markers,
        current_time=current_time,
    )
