from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


_IMPORT_ERROR: str | None = None
_PIPE = None
_PIPE_MODEL_ID: str | None = None

try:
    import torch
    from diffusers import CogVideoXDPMScheduler, CogVideoXPipeline
    from diffusers.utils import export_to_video
except Exception as exc:  # pragma: no cover - depends on local environment
    torch = None
    CogVideoXDPMScheduler = None
    CogVideoXPipeline = None
    export_to_video = None
    _IMPORT_ERROR = str(exc)


DEFAULT_MODEL_ID = "THUDM/CogVideoX1.5-5B"
DEFAULT_SIZE_LABEL = "720x480 (mas rapido)"


@dataclass
class SidanceResult:
    ok: bool
    output_video: Path
    job_dir: Path
    message: str
    backend: str = "sidance_local"
    model_id: str = DEFAULT_MODEL_ID


def _get_model_id() -> str:
    model_id = (
        os.getenv("SIDANCE_LOCAL_MODEL", "").strip()
        or os.getenv("SEEDANCE_LOCAL_MODEL", "").strip()
        or DEFAULT_MODEL_ID
    )
    return model_id or DEFAULT_MODEL_ID


def _get_default_steps() -> int:
    raw = (
        os.getenv("SIDANCE_LOCAL_STEPS", "").strip()
        or os.getenv("SEEDANCE_LOCAL_STEPS", "").strip()
        or "28"
    )
    try:
        value = int(raw)
    except ValueError:
        value = 28
    return max(16, min(60, value))


def _get_default_guidance() -> float:
    raw = (
        os.getenv("SIDANCE_LOCAL_GUIDANCE", "").strip()
        or os.getenv("SEEDANCE_LOCAL_GUIDANCE", "").strip()
        or "6.0"
    )
    try:
        value = float(raw)
    except ValueError:
        value = 6.0
    return max(3.0, min(12.0, value))


def _get_default_num_frames() -> int:
    raw = (
        os.getenv("SIDANCE_LOCAL_NUM_FRAMES", "").strip()
        or os.getenv("SEEDANCE_LOCAL_NUM_FRAMES", "").strip()
        or "49"
    )
    try:
        value = int(raw)
    except ValueError:
        value = 49
    return max(16, min(81, value))


def _get_default_fps() -> int:
    raw = (
        os.getenv("SIDANCE_LOCAL_FPS", "").strip()
        or os.getenv("SEEDANCE_LOCAL_FPS", "").strip()
        or "16"
    )
    try:
        value = int(raw)
    except ValueError:
        value = 16
    return max(8, min(30, value))


def _expand_prompt(user_prompt: str) -> str:
    base = user_prompt.strip()
    if not base:
        return ""
    return (
        "Vídeo cinematográfico, movimiento coherente, escena detallada, "
        "iluminación natural, alta calidad visual, movimiento de cámara suave. "
        + base
    )


def _size_to_hw(size_label: str | None) -> tuple[int, int, str]:
    mapping = {
        "1360x768 (mejor calidad)": (768, 1360),
        "720x480 (mas rapido)": (480, 720),
    }

    if size_label in mapping:
        height, width = mapping[size_label]
        return height, width, size_label

    candidate = (size_label or "").strip().lower()
    if "x" in candidate:
        parts = candidate.split("x", 1)
        try:
            width = int(parts[0])
            height = int(parts[1].split(" ")[0])
            if 320 <= width <= 1920 and 240 <= height <= 1920:
                return height, width, f"{width}x{height}"
        except ValueError:
            pass

    fallback_h, fallback_w = mapping[DEFAULT_SIZE_LABEL]
    return fallback_h, fallback_w, DEFAULT_SIZE_LABEL


def get_sidance_status() -> dict[str, Any]:
    model_id = _get_model_id()

    if _IMPORT_ERROR:
        return {
            "available": False,
            "dependencies_ready": False,
            "cuda_available": False,
            "model_id": model_id,
            "default_steps": _get_default_steps(),
            "default_guidance": _get_default_guidance(),
            "message": (
                "Faltan dependencias de SIDANCE local. "
                "Instala requirements_sidance_local.txt."
            ),
            "detail": _IMPORT_ERROR,
        }

    assert torch is not None  # for type checkers
    cuda_ok = bool(torch.cuda.is_available())
    if not cuda_ok:
        return {
            "available": False,
            "dependencies_ready": True,
            "cuda_available": False,
            "model_id": model_id,
            "default_steps": _get_default_steps(),
            "default_guidance": _get_default_guidance(),
            "message": "No se detectó GPU CUDA. SIDANCE local necesita NVIDIA CUDA.",
        }

    return {
        "available": True,
        "dependencies_ready": True,
        "cuda_available": True,
        "model_id": model_id,
        "default_steps": _get_default_steps(),
        "default_guidance": _get_default_guidance(),
        "message": "SIDANCE local listo.",
    }


def _load_pipe(model_id: str):
    global _PIPE, _PIPE_MODEL_ID

    status = get_sidance_status()
    if not status["available"]:
        raise RuntimeError(str(status["message"]))

    if _PIPE is not None and _PIPE_MODEL_ID == model_id:
        return _PIPE

    assert CogVideoXPipeline is not None
    assert CogVideoXDPMScheduler is not None
    assert torch is not None

    dtype = torch.bfloat16
    pipe = CogVideoXPipeline.from_pretrained(model_id, torch_dtype=dtype)
    pipe.scheduler = CogVideoXDPMScheduler.from_config(
        pipe.scheduler.config,
        timestep_spacing="trailing",
    )

    pipe.enable_sequential_cpu_offload()
    pipe.vae.enable_slicing()
    pipe.vae.enable_tiling()

    _PIPE = pipe
    _PIPE_MODEL_ID = model_id
    return _PIPE


def _new_job_dir(output_root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_dir = output_root / f"sidance_job_{stamp}"
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def generate_sidance_video(
    prompt: str,
    output_root: str | Path,
    size_label: str | None = None,
    num_inference_steps: int | None = None,
    guidance_scale: float | None = None,
    seed: int | None = None,
) -> SidanceResult:
    output_root_path = Path(output_root).resolve()
    output_root_path.mkdir(parents=True, exist_ok=True)
    job_dir = _new_job_dir(output_root_path)
    model_id = _get_model_id()

    expanded_prompt = _expand_prompt(prompt)
    if not expanded_prompt:
        return SidanceResult(
            ok=False,
            output_video=Path(),
            job_dir=job_dir,
            message="Error: escribe un texto de instrucción para SIDANCE local.",
            model_id=model_id,
        )

    status = get_sidance_status()
    if not status["available"]:
        detail = str(status.get("detail", "")).strip()
        suffix = f" Detalle: {detail}" if detail else ""
        return SidanceResult(
            ok=False,
            output_video=Path(),
            job_dir=job_dir,
            message=f"{status['message']}{suffix}",
            model_id=model_id,
        )

    height, width, final_size_label = _size_to_hw(size_label)
    steps = num_inference_steps if isinstance(num_inference_steps, int) else _get_default_steps()
    steps = max(16, min(60, steps))
    guidance = (
        guidance_scale
        if isinstance(guidance_scale, (float, int))
        else _get_default_guidance()
    )
    guidance = max(3.0, min(12.0, float(guidance)))

    if not isinstance(seed, int):
        seed = -1
    if seed < 0:
        seed = int(datetime.utcnow().timestamp()) % 1000000007

    try:
        pipe = _load_pipe(model_id)
        assert torch is not None
        assert export_to_video is not None

        generator = torch.Generator(device="cpu").manual_seed(seed)
        frames = pipe(
            prompt=expanded_prompt,
            height=height,
            width=width,
            num_videos_per_prompt=1,
            num_inference_steps=steps,
            num_frames=_get_default_num_frames(),
            use_dynamic_cfg=True,
            guidance_scale=guidance,
            generator=generator,
        ).frames[0]

        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        out_video = job_dir / f"sidance_local_{stamp}.mp4"
        export_to_video(frames, str(out_video), fps=_get_default_fps())

        summary = {
            "backend": "sidance_local",
            "model_id": model_id,
            "prompt": prompt,
            "prompt_expanded": expanded_prompt,
            "output_video": str(out_video),
            "width": width,
            "height": height,
            "size_label": final_size_label,
            "steps": steps,
            "guidance_scale": guidance,
            "seed": seed,
            "timestamp_utc": stamp,
        }
        (job_dir / "resumen_sidance.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return SidanceResult(
            ok=True,
            output_video=out_video,
            job_dir=job_dir,
            message=(
                "Listo: vídeo generado con SIDANCE local. "
                f"Resolución: {width}x{height}. Modelo: {model_id}."
            ),
            model_id=model_id,
        )
    except Exception as exc:  # pragma: no cover - depends on local environment
        (job_dir / "sidance_error.log").write_text(str(exc), encoding="utf-8")
        return SidanceResult(
            ok=False,
            output_video=Path(),
            job_dir=job_dir,
            message=f"Fallo SIDANCE local: {exc}",
            model_id=model_id,
        )
