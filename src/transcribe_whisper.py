from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, get_audio_cases, load_config


ALLOWED_LIGHTWEIGHT_MODELS = {"tiny", "base", "small"}


def find_case(config: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in get_audio_cases(config):
        if case["id"] == case_id:
            return case
    raise ValueError(f"Unknown audio case: {case_id}")


def get_model_name(config: dict[str, Any], override: str | None = None) -> str:
    model_name = override or config.get("asr", {}).get("whisper_model", "small")
    if model_name not in ALLOWED_LIGHTWEIGHT_MODELS:
        raise ValueError(
            f"Refusing to run non-lightweight Whisper model '{model_name}'. "
            f"Allowed models: {', '.join(sorted(ALLOWED_LIGHTWEIGHT_MODELS))}"
        )
    return model_name


def resolve_audio_path(config: dict[str, Any], case: dict[str, Any], mode: str) -> Path:
    paths = config["paths"]
    if mode == "mixed":
        return PROJECT_ROOT / paths["mixed_audio_dir"] / case["mixed"]
    if mode == "separated":
        raise NotImplementedError("Separated transcription is intentionally deferred.")
    raise ValueError(f"Unsupported mode: {mode}")


def transcribe_audio(audio_path: Path, model_name: str, language: str) -> dict[str, Any]:
    import whisper

    model = whisper.load_model(model_name)
    start_time = time.perf_counter()
    result = model.transcribe(
        str(audio_path),
        language=language,
        verbose=False,
        temperature=0.0,
        condition_on_previous_text=False,
    )
    runtime_sec = round(time.perf_counter() - start_time, 3)
    segments = [
        {
            "start": round(float(segment["start"]), 3),
            "end": round(float(segment["end"]), 3),
            "text": segment["text"].strip(),
        }
        for segment in result.get("segments", [])
    ]
    return {
        "text": result.get("text", "").strip(),
        "segments": segments,
        "runtime_sec": runtime_sec,
    }


def write_transcript(
    case_id: str,
    audio_path: Path,
    model_name: str,
    language: str,
    result: dict[str, Any],
    mode: str,
) -> Path:
    output_dir = PROJECT_ROOT / "results" / "transcripts_raw"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{case_id}_{mode}_whisper.json"
    payload = {
        "case_id": case_id,
        "audio_path": audio_path.relative_to(PROJECT_ROOT).as_posix(),
        "model": f"whisper-{model_name}",
        "language": language,
        "text": result["text"],
        "segments": result["segments"],
        "runtime_sec": result["runtime_sec"],
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lightweight Whisper transcription.")
    parser.add_argument("--case", required=True, help="Audio case id, e.g. NoOverlap")
    parser.add_argument("--mode", choices=["mixed", "separated"], required=True)
    parser.add_argument("--model", choices=sorted(ALLOWED_LIGHTWEIGHT_MODELS), default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    case = find_case(config, args.case)
    model_name = get_model_name(config, args.model)
    language = config.get("asr", {}).get("language", "zh")
    audio_path = resolve_audio_path(config, case, args.mode)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file does not exist: {audio_path}")

    result = transcribe_audio(audio_path, model_name, language)
    output_path = write_transcript(
        case_id=case["id"],
        audio_path=audio_path,
        model_name=model_name,
        language=language,
        result=result,
        mode=args.mode,
    )
    print(f"Wrote transcript: {output_path.relative_to(PROJECT_ROOT)}")
    print(f"Runtime: {result['runtime_sec']}s")


if __name__ == "__main__":
    main()
