from __future__ import annotations

import argparse
import csv
import json
import wave
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .external_validation_go_no_go_board import execution_receipt_filled, mini_check_audio_ready
from .transcribe_whisper import get_model_name, load_whisper_model, preview, transcribe_audio


EVAL_COLUMNS = [
    "dataset_name",
    "slice_id",
    "label",
    "audio_path",
    "model",
    "audio_duration_sec",
    "runtime_sec",
    "segments_count",
    "text_length",
    "text_preview",
    "eval_status",
    "result_label",
    "transcript_path",
    "observation",
]

SUMMARY_COLUMNS = [
    "metric",
    "value",
    "label",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_mini_check() -> dict[str, Any]:
    return load_json_dict("results/tables/external_validation_mini_sanity_check.json")


def load_slice_mapping() -> dict[str, Any]:
    return load_json_dict("results/tables/external_validation_slice_mapping.json")


def transcript_path(slice_id: str) -> Path:
    return PROJECT_ROOT / "results" / "external_sanity_check" / "transcripts" / f"{slice_id}_whisper.json"


def audio_duration_sec(audio_path: Path) -> float:
    with wave.open(str(audio_path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate()
        if rate <= 0:
            return 0.0
        return round(frames / float(rate), 3)


def assert_prerequisites(mini_check: dict[str, Any]) -> None:
    if not mini_check_audio_ready(mini_check):
        raise RuntimeError("Mini sanity check must confirm staged audio and reference before narrow eval")
    if not execution_receipt_filled():
        raise RuntimeError("Staging execution receipt must be filled before narrow eval")


def write_transcript_payload(
    slice_id: str,
    audio_path: Path,
    model_name: str,
    language: str,
    result: dict[str, Any],
) -> Path:
    output_path = transcript_path(slice_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "slice_id": slice_id,
        "audio_path": audio_path.relative_to(PROJECT_ROOT).as_posix(),
        "model": f"whisper-{model_name}",
        "language": language,
        "label": "external/sanity-check",
        "text": result["text"],
        "segments": result["segments"],
        "runtime_sec": result["runtime_sec"],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def build_eval_row(
    mapping: dict[str, Any],
    mini_check: dict[str, Any],
    transcript: dict[str, Any],
    transcript_file: Path,
) -> dict[str, str]:
    audio_rel = str(mapping.get("audio_path", ""))
    audio_path = PROJECT_ROOT / audio_rel
    text = str(transcript.get("text", ""))
    return {
        "dataset_name": str(mini_check.get("dataset_name", mapping.get("dataset_name", "AISHELL-4"))),
        "slice_id": str(mini_check.get("slice_id", mapping.get("slice_id", ""))),
        "label": str(mini_check.get("label", "external/sanity-check")),
        "audio_path": audio_rel,
        "model": str(transcript.get("model", "")),
        "audio_duration_sec": str(audio_duration_sec(audio_path) if audio_path.exists() else ""),
        "runtime_sec": str(transcript.get("runtime_sec", "")),
        "segments_count": str(len(transcript.get("segments", []))),
        "text_length": str(len(text)),
        "text_preview": preview(text),
        "eval_status": "narrow_asr_complete",
        "result_label": "external/sanity-check",
        "transcript_path": transcript_file.relative_to(PROJECT_ROOT).as_posix(),
        "observation": (
            "Qualitative narrow ASR on one AISHELL-4 excerpt; no gold CER claimed because reference transcript "
            "alignment remains pending."
        ),
    }


def build_summary_rows(eval_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {"metric": "eval_status", "value": eval_row["eval_status"], "label": "external/sanity-check"},
        {"metric": "model", "value": eval_row["model"], "label": "external/sanity-check"},
        {"metric": "text_length", "value": eval_row["text_length"], "label": "external/sanity-check"},
    ]


def build_summary_lines(eval_row: dict[str, str], summary_rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Narrow Audio Eval (external/sanity-check)",
        "",
        "Label: `external/sanity-check` — qualitative ASR on one staged AISHELL-4 excerpt. "
        "Does not claim gold benchmark CER.",
        "",
        "| metric | value | label |",
        "| --- | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['metric']} | {row['value']} | {row['label']} |")
    lines.extend(
        [
            "",
            f"- Preview: {eval_row['text_preview']}",
            f"- Observation: {eval_row['observation']}",
        ]
    )
    return lines


def write_outputs(
    eval_row: dict[str, str],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "external_validation_narrow_audio_eval.csv"
    json_path = table_dir / "external_validation_narrow_audio_eval.json"
    summary_csv_path = table_dir / "external_validation_narrow_audio_eval_summary.csv"
    summary_json_path = table_dir / "external_validation_narrow_audio_eval_summary.json"
    md_path = figure_dir / "external_validation_narrow_audio_eval.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=EVAL_COLUMNS)
        writer.writeheader()
        writer.writerow(eval_row)
    json_path.write_text(json.dumps(eval_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(json.dumps(summary_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(build_summary_lines(eval_row, summary_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def run_narrow_eval(model_override: str | None = None, overwrite: bool = False) -> dict[str, str]:
    config = load_config()
    mini_check = load_mini_check()
    mapping = load_slice_mapping()
    assert_prerequisites(mini_check)

    slice_id = str(mini_check.get("slice_id", mapping.get("slice_id", "")))
    audio_path = PROJECT_ROOT / str(mapping.get("audio_path", ""))
    if not audio_path.exists():
        raise FileNotFoundError(f"Staged audio missing: {audio_path.relative_to(PROJECT_ROOT)}")

    transcript_file = transcript_path(slice_id)
    if transcript_file.exists() and not overwrite:
        transcript = json.loads(transcript_file.read_text(encoding="utf-8"))
    else:
        model_name = get_model_name(config, override=model_override or "tiny")
        language = str(config.get("asr", {}).get("language", "zh"))
        model = load_whisper_model(model_name)
        result = transcribe_audio(model, audio_path, language)
        transcript_file = write_transcript_payload(slice_id, audio_path, model_name, language, result)
        transcript = json.loads(transcript_file.read_text(encoding="utf-8"))

    eval_row = build_eval_row(mapping, mini_check, transcript, transcript_file)
    summary_rows = build_summary_rows(eval_row)
    write_outputs(eval_row, summary_rows)
    return {
        "eval_status": eval_row["eval_status"],
        "model": eval_row["model"],
        "text_length": eval_row["text_length"],
        "transcript_path": eval_row["transcript_path"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run narrow external/sanity-check ASR on staged AISHELL-4 excerpt.")
    parser.add_argument("--model", choices=["tiny", "base", "small"], default=None)
    parser.add_argument("--overwrite", action="store_true", help="Re-transcribe even if transcript exists.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_narrow_eval(model_override=args.model, overwrite=args.overwrite)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
