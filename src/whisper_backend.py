from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=4)
def _faster_model(model_size: str) -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(model_size, device="cpu", compute_type="int8")


@lru_cache(maxsize=4)
def _openai_model(model_size: str) -> Any:
    import whisper

    return whisper.load_model(model_size)


def _transcribe_faster(wav_path: str, model_size: str, language: str) -> dict[str, Any]:
    model = _faster_model(model_size)
    segments_iter, info = model.transcribe(wav_path, language=language, vad_filter=False)
    segments = []
    text_parts = []
    for segment in segments_iter:
        item = {"start": float(segment.start), "end": float(segment.end), "text": segment.text}
        segments.append(item)
        text_parts.append(segment.text)
    return {
        "backend": "faster-whisper",
        "model_size": model_size,
        "language": getattr(info, "language", language),
        "text": "".join(text_parts).strip(),
        "segments": segments,
        "status": "ok",
    }


def _transcribe_openai(wav_path: str, model_size: str, language: str) -> dict[str, Any]:
    model = _openai_model(model_size)
    result = model.transcribe(wav_path, language=language)
    segments = [
        {"start": float(seg.get("start", 0.0)), "end": float(seg.get("end", 0.0)), "text": str(seg.get("text", ""))}
        for seg in result.get("segments", [])
    ]
    return {
        "backend": "openai-whisper",
        "model_size": model_size,
        "language": result.get("language", language),
        "text": str(result.get("text", "")).strip(),
        "segments": segments,
        "status": "ok",
    }


def transcribe_audio(wav_path: str, model_size: str = "small", backend: str = "auto", language: str = "zh") -> dict[str, Any]:
    started = time.perf_counter()
    path = Path(wav_path)
    if not path.exists():
        return {
            "backend": backend,
            "model_size": model_size,
            "language": language,
            "text": "",
            "segments": [],
            "runtime_sec": 0.0,
            "status": "failed",
            "error": f"missing wav: {wav_path}",
        }
    candidates = ["faster-whisper", "openai-whisper"] if backend == "auto" else [backend]
    errors = []
    for candidate in candidates:
        try:
            if candidate in {"faster-whisper", "faster_whisper"}:
                output = _transcribe_faster(str(path), model_size, language)
            elif candidate in {"openai-whisper", "openai_whisper", "whisper"}:
                output = _transcribe_openai(str(path), model_size, language)
            else:
                raise ValueError(f"unknown backend: {candidate}")
            output["runtime_sec"] = round(time.perf_counter() - started, 4)
            return output
        except Exception as exc:  # pragma: no cover - depends on optional backend/model download
            errors.append(f"{candidate}: {exc}")
    return {
        "backend": backend,
        "model_size": model_size,
        "language": language,
        "text": "",
        "segments": [],
        "runtime_sec": round(time.perf_counter() - started, 4),
        "status": "failed",
        "error": " | ".join(errors),
    }
