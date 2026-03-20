from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
INPUT_DIR = PROJECT_ROOT / "input" / "audit_temp"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dirs() -> None:
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "reports").mkdir(parents=True, exist_ok=True)


def load_env_from_file() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def resolve_ffmpeg() -> str:
    ffmpeg = shutil_which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("No se encontro ffmpeg ni imageio-ffmpeg.") from exc


def shutil_which(command: str) -> str | None:
    from shutil import which

    return which(command)


def run_cmd(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def create_sample_media(ffmpeg_path: str) -> tuple[Path, Path, Path]:
    video_path = INPUT_DIR / "audit_video.mp4"
    image_path = INPUT_DIR / "audit_image.png"
    audio_path = INPUT_DIR / "audit_audio.wav"

    run_cmd(
        [
            ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=24",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100",
            "-t",
            "2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(video_path),
        ]
    )
    run_cmd(
        [
            ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=yellow:s=320x320",
            "-frames:v",
            "1",
            str(image_path),
        ]
    )
    run_cmd(
        [
            ffmpeg_path,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=44100",
            "-t",
            "2",
            str(audio_path),
        ]
    )
    return video_path, image_path, audio_path


def probe_resolution(ffmpeg_path: str, video_path: Path) -> str:
    probe = run_cmd([ffmpeg_path, "-i", str(video_path)])
    text = (probe.stderr or "") + "\n" + (probe.stdout or "")
    match = re.search(r"(\d{2,5})x(\d{2,5})", text)
    if not match:
        return "no-detectado"
    return f"{match.group(1)}x{match.group(2)}"


@dataclass
class AuditRecord:
    timestamp: str
    cycle: int
    check: str
    ok: bool
    detail: str
    elapsed_ms: int = 0


class Auditor:
    def __init__(
        self,
        duration_minutes: int,
        interval_seconds: int,
        report_path: Path,
        jsonl_path: Path,
        force_local_for_endurance: bool,
    ) -> None:
        self.duration_minutes = max(1, duration_minutes)
        self.interval_seconds = max(10, interval_seconds)
        self.report_path = report_path
        self.jsonl_path = jsonl_path
        self.force_local_for_endurance = force_local_for_endurance
        self.records: list[AuditRecord] = []

        sys.path.insert(0, str(SRC_DIR))
        from web_app import app  # noqa: WPS433

        self.app = app
        self.client = app.test_client()
        self.ffmpeg_path = resolve_ffmpeg()
        self.video_path, self.image_path, self.audio_path = create_sample_media(self.ffmpeg_path)

    def log(self, record: AuditRecord) -> None:
        self.records.append(record)
        with self.jsonl_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def check(self, cycle: int, name: str, fn: Any) -> None:
        started = time.perf_counter()
        try:
            ok, detail = fn()
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            self.log(
                AuditRecord(
                    timestamp=utc_now_iso(),
                    cycle=cycle,
                    check=name,
                    ok=bool(ok),
                    detail=str(detail),
                    elapsed_ms=elapsed_ms,
                )
            )
        except Exception as exc:  # pragma: no cover
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            self.log(
                AuditRecord(
                    timestamp=utc_now_iso(),
                    cycle=cycle,
                    check=name,
                    ok=False,
                    detail=f"Excepcion: {exc}",
                    elapsed_ms=elapsed_ms,
                )
            )

    def _check_system_status(self) -> tuple[bool, str]:
        res = self.client.get("/api/system-status")
        if res.status_code != 200:
            return False, f"/api/system-status {res.status_code}"
        payload = res.get_json(silent=True) or {}
        return True, f"backend={payload.get('effective_backend')} format={payload.get('output_format')}"

    def _check_chat(self) -> tuple[bool, str]:
        body = {
            "message": "auditoria de chat",
            "markers": [],
            "current_time": 1.23,
            "chat_history": [],
        }
        res = self.client.post("/api/chat", json=body)
        if res.status_code != 200:
            return False, f"/api/chat {res.status_code}"
        payload = res.get_json(silent=True) or {}
        ok = bool(payload.get("ok"))
        reply = str(payload.get("reply", ""))
        return ok, f"reply_len={len(reply)}"

    def _check_generate_video_only(self) -> tuple[bool, str]:
        with self.video_path.open("rb") as vf:
            res = self.client.post(
                "/api/generate",
                data={
                    "prompt": "auditoria video only",
                    "video": (io.BytesIO(vf.read()), self.video_path.name),
                },
                content_type="multipart/form-data",
            )

        if res.status_code != 200:
            return False, f"/api/generate {res.status_code}"

        payload = res.get_json(silent=True) or {}
        if not payload.get("ok"):
            return False, f"ok=false msg={payload.get('message')}"

        out_path = Path(str(payload.get("output_video_path", "")))
        if not out_path.exists():
            return False, "salida no existe"

        resolution = probe_resolution(self.ffmpeg_path, out_path)
        if resolution != "1080x1920":
            return False, f"resolucion inesperada: {resolution}"

        return True, f"backend={payload.get('backend')} resolution={resolution}"

    def _check_generate_video_image_audio(self) -> tuple[bool, str]:
        with self.video_path.open("rb") as vf, self.image_path.open("rb") as imf, self.audio_path.open(
            "rb"
        ) as af:
            res = self.client.post(
                "/api/generate",
                data={
                    "prompt": "auditoria con imagen y audio",
                    "video": (io.BytesIO(vf.read()), self.video_path.name),
                    "image": (io.BytesIO(imf.read()), self.image_path.name),
                    "audio": (io.BytesIO(af.read()), self.audio_path.name),
                },
                content_type="multipart/form-data",
            )

        if res.status_code != 200:
            return False, f"/api/generate {res.status_code}"

        payload = res.get_json(silent=True) or {}
        if not payload.get("ok"):
            return False, f"ok=false msg={payload.get('message')}"

        out_path = Path(str(payload.get("output_video_path", "")))
        if not out_path.exists():
            return False, "salida no existe"

        resolution = probe_resolution(self.ffmpeg_path, out_path)
        if resolution != "1080x1920":
            return False, f"resolucion inesperada: {resolution}"

        return True, f"backend={payload.get('backend')} resolution={resolution}"

    def _check_invalid_video_extension(self) -> tuple[bool, str]:
        fake = io.BytesIO(b"not-a-real-video")
        res = self.client.post(
            "/api/generate",
            data={
                "prompt": "invalido",
                "video": (fake, "archivo.txt"),
            },
            content_type="multipart/form-data",
        )
        if res.status_code != 400:
            return False, f"esperado 400 y fue {res.status_code}"
        return True, "rechazo de formato invalido OK"

    def run(self) -> None:
        start = time.time()
        deadline = start + (self.duration_minutes * 60)

        if self.force_local_for_endurance:
            os.environ["VIDEO_GEN_BACKEND"] = "local"
            self.log(
                AuditRecord(
                    timestamp=utc_now_iso(),
                    cycle=0,
                    check="config_backend",
                    ok=True,
                    detail="VIDEO_GEN_BACKEND forzado a local (solo proceso de auditoria)",
                    elapsed_ms=0,
                )
            )

        cycle = 1
        while time.time() < deadline:
            cycle_start = time.time()

            self.check(cycle, "system_status", self._check_system_status)
            self.check(cycle, "chat_api", self._check_chat)
            self.check(cycle, "generate_video_only", self._check_generate_video_only)
            self.check(cycle, "generate_video_image_audio", self._check_generate_video_image_audio)
            self.check(cycle, "invalid_video_extension", self._check_invalid_video_extension)

            cycle += 1

            elapsed_cycle = time.time() - cycle_start
            sleep_for = self.interval_seconds - elapsed_cycle
            if sleep_for > 0 and time.time() + sleep_for < deadline:
                time.sleep(sleep_for)

        self._write_report(start, deadline)

    def _write_report(self, start: float, deadline: float) -> None:
        total = len(self.records)
        passed = sum(1 for record in self.records if record.ok)
        failed = total - passed

        by_check: dict[str, dict[str, int]] = {}
        for record in self.records:
            bucket = by_check.setdefault(record.check, {"ok": 0, "fail": 0})
            if record.ok:
                bucket["ok"] += 1
            else:
                bucket["fail"] += 1

        failed_rows = [record for record in self.records if not record.ok]
        lines: list[str] = []
        lines.append("# AUDITORIA FUNCIONAL VIDEO IA")
        lines.append("")
        lines.append(f"- Inicio UTC: {datetime.fromtimestamp(start, tz=timezone.utc).isoformat()}")
        lines.append(f"- Fin UTC: {datetime.fromtimestamp(min(time.time(), deadline), tz=timezone.utc).isoformat()}")
        lines.append(f"- Duracion objetivo: {self.duration_minutes} min")
        lines.append(f"- Total checks: {total}")
        lines.append(f"- OK: {passed}")
        lines.append(f"- FAIL: {failed}")
        lines.append("")
        lines.append("## Resumen por check")
        for check_name in sorted(by_check):
            bucket = by_check[check_name]
            lines.append(f"- {check_name}: OK={bucket['ok']} FAIL={bucket['fail']}")
        lines.append("")
        lines.append("## Fallos")
        if not failed_rows:
            lines.append("- Sin fallos detectados.")
        else:
            for row in failed_rows[:100]:
                lines.append(
                    f"- [{row.timestamp}] ciclo={row.cycle} check={row.check} detalle={row.detail}"
                )
        lines.append("")
        lines.append(f"JSONL detallado: {self.jsonl_path}")

        self.report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Auditoria funcional de VIDEO IA")
    parser.add_argument("--duration-minutes", type=int, default=120)
    parser.add_argument("--interval-seconds", type=int, default=300)
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "reports" / "audit_2h_report.md",
    )
    parser.add_argument(
        "--jsonl",
        type=Path,
        default=PROJECT_ROOT / "reports" / "audit_2h_events.jsonl",
    )
    parser.add_argument(
        "--force-local",
        action="store_true",
        help="Forzar backend local en .env para evitar dependencia de nube durante auditoria",
    )
    return parser.parse_args()


def main() -> None:
    ensure_dirs()
    load_env_from_file()

    args = parse_args()
    audit = Auditor(
        duration_minutes=args.duration_minutes,
        interval_seconds=args.interval_seconds,
        report_path=args.report,
        jsonl_path=args.jsonl,
        force_local_for_endurance=args.force_local,
    )
    audit.run()
    print(f"Audit report: {args.report}")
    print(f"Audit log: {args.jsonl}")


if __name__ == "__main__":
    main()
