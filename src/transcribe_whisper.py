from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, get_audio_cases, load_config
from .io_helpers import read_json


ALLOWED_LIGHTWEIGHT_MODELS = {"tiny", "base", "small"}
MIXED_BENCHMARK_COLUMNS = [
    "case_id",
    "overlap_level",
    "audio_path",
    "model",
    "runtime_sec",
    "segments_count",
    "text_length",
    "text_preview",
    "transcript_path",
]
SEPARATED_BENCHMARK_COLUMNS = [
    "case_id",
    "overlap_level",
    "model",
    "spk1_audio_path",
    "spk2_audio_path",
    "spk1_runtime_sec",
    "spk2_runtime_sec",
    "runtime_sec_total",
    "spk1_segments_count",
    "spk2_segments_count",
    "merged_segments_count",
    "spk1_text_length",
    "spk2_text_length",
    "full_text_length",
    "speaker_transcript_path",
]


def find_case(config: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in get_audio_cases(config):
        if case["id"] == case_id:
            return case
    raise ValueError(f"Unknown audio case: {case_id}")


def select_cases(config: dict[str, Any], case_id: str) -> list[dict[str, Any]]:
    if case_id == "all":
        return get_audio_cases(config)
    return [find_case(config, case_id)]


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
    raise ValueError(f"Unsupported mode: {mode}")


def resolve_separated_audio_paths(config: dict[str, Any], case: dict[str, Any]) -> list[tuple[str, Path]]:
    separated_dir = PROJECT_ROOT / config["paths"]["separated_audio_dir"]
    return [
        ("separated_spk1", separated_dir / case["separated"]["spk1"]),
        ("separated_spk2", separated_dir / case["separated"]["spk2"]),
    ]


def transcribe_audio(model: Any, audio_path: Path, language: str) -> dict[str, Any]:
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
    output_mode = mode.replace("separated_", "")
    output_path = output_dir / f"{case_id}_{output_mode}_whisper.json"
    payload = {
        "case_id": case_id,
        "audio_path": audio_path.relative_to(PROJECT_ROOT).as_posix(),
        "mode": mode,
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


def transcript_path_for(case_id: str, mode: str) -> Path:
    output_mode = mode.replace("separated_", "")
    return PROJECT_ROOT / "results" / "transcripts_raw" / f"{case_id}_{output_mode}_whisper.json"


def preview(text: str, limit: int = 120) -> str:
    return " ".join(text.split())[:limit]


def load_whisper_model(model_name: str) -> Any:
    import whisper

    return whisper.load_model(model_name)


def get_transcript_text_length(transcript: dict[str, Any], key: str = "text") -> int:
    return len(transcript.get(key, ""))


def build_mixed_benchmark_rows(config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in get_audio_cases(config):
        path = transcript_path_for(case["id"], "mixed")
        transcript = read_json(path)
        text = transcript.get("text", "")
        rows.append(
            {
                "case_id": case["id"],
                "overlap_level": case["overlap_level"],
                "audio_path": transcript.get("audio_path", ""),
                "model": transcript.get("model", ""),
                "runtime_sec": transcript.get("runtime_sec", 0.0),
                "segments_count": len(transcript.get("segments", [])),
                "text_length": len(text),
                "text_preview": preview(text),
                "transcript_path": path.relative_to(PROJECT_ROOT).as_posix(),
            }
        )
    return rows


def write_mixed_benchmark(config: dict[str, Any]) -> None:
    rows = build_mixed_benchmark_rows(config)
    output_dir = PROJECT_ROOT / "results" / "tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "mixed_asr_benchmark.csv"
    json_path = output_dir / "mixed_asr_benchmark.json"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MIXED_BENCHMARK_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote mixed ASR benchmark CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote mixed ASR benchmark JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Benchmark rows: {len(rows)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lightweight Whisper transcription.")
    parser.add_argument("--case", required=True, help="Audio case id, e.g. NoOverlap")
    parser.add_argument("--mode", choices=["mixed", "separated"], required=True)
    parser.add_argument("--model", choices=sorted(ALLOWED_LIGHTWEIGHT_MODELS), default=None)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing transcripts.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    cases = select_cases(config, args.case)
    model_name = get_model_name(config, args.model)
    language = config.get("asr", {}).get("language", "zh")
    model = None

    for case in cases:
        if args.mode == "mixed":
            audio_jobs = [("mixed", resolve_audio_path(config, case, args.mode))]
        else:
            audio_jobs = resolve_separated_audio_paths(config, case)

        for mode, audio_path in audio_jobs:
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file does not exist: {audio_path}")
            output_path = transcript_path_for(case["id"], mode)
            if output_path.exists() and not args.overwrite:
                print(f"skip existing transcript: {output_path.relative_to(PROJECT_ROOT)}")
                continue
            if model is None:
                model = load_whisper_model(model_name)
            result = transcribe_audio(model, audio_path, language)
            output_path = write_transcript(
                case_id=case["id"],
                audio_path=audio_path,
                model_name=model_name,
                language=language,
                result=result,
                mode=mode,
            )
            print(f"Wrote transcript: {output_path.relative_to(PROJECT_ROOT)}")
            print(f"{case['id']} {mode} runtime: {result['runtime_sec']}s")

    if args.mode == "mixed":
        write_mixed_benchmark(config)


if __name__ == "__main__":
    main()
