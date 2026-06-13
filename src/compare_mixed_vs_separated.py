from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, get_audio_cases, load_config
from .io_helpers import read_json


CSV_COLUMNS = [
    "case_id",
    "overlap_level",
    "model",
    "mixed_audio_path",
    "separated_method",
    "mixed_runtime_sec",
    "separated_runtime_sec",
    "mixed_segments_count",
    "separated_segments_count",
    "mixed_text_length",
    "separated_text_length",
    "mixed_text_preview",
    "separated_text_preview",
    "mixed_transcript_path",
    "separated_transcript_path",
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


def preview(text: str, limit: int = 120) -> str:
    return " ".join(text.split())[:limit]


def build_row(case: dict[str, Any]) -> dict[str, Any]:
    case_id = case["id"]
    mixed_path = PROJECT_ROOT / "results" / "transcripts_raw" / f"{case_id}_mixed_whisper.json"
    separated_path = (
        PROJECT_ROOT
        / "results"
        / "transcripts_speaker"
        / f"{case_id}_separated_speaker_transcript.json"
    )
    mixed = read_json(mixed_path)
    separated = read_json(separated_path)
    mixed_text = mixed.get("text", "")
    separated_text = separated.get("full_text", "")

    return {
        "case_id": case_id,
        "overlap_level": case["overlap_level"],
        "model": mixed.get("model", separated.get("model", "")),
        "mixed_audio_path": mixed.get("audio_path", ""),
        "separated_method": separated.get("method", ""),
        "mixed_runtime_sec": mixed.get("runtime_sec", 0.0),
        "separated_runtime_sec": separated.get("runtime_sec_total", 0.0),
        "mixed_segments_count": len(mixed.get("segments", [])),
        "separated_segments_count": len(separated.get("segments", [])),
        "mixed_text_length": len(mixed_text),
        "separated_text_length": len(separated_text),
        "mixed_text_preview": preview(mixed_text),
        "separated_text_preview": preview(separated_text),
        "mixed_transcript_path": mixed_path.relative_to(PROJECT_ROOT).as_posix(),
        "separated_transcript_path": separated_path.relative_to(PROJECT_ROOT).as_posix(),
    }


def read_existing_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_json(rows: list[dict[str, Any]], path: Path) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_row(rows: list[dict[str, Any]], row: dict[str, Any]) -> list[dict[str, Any]]:
    key = (str(row["case_id"]), str(row["model"]))
    filtered = [
        existing
        for existing in rows
        if (str(existing.get("case_id")), str(existing.get("model"))) != key
    ]
    filtered.append(row)
    return sorted(filtered, key=lambda item: (str(item["case_id"]), str(item["model"])))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare mixed and separated transcripts.")
    parser.add_argument("--case", required=True, help="Audio case id, e.g. NoOverlap")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    cases = select_cases(config, args.case)

    csv_path = PROJECT_ROOT / "results" / "tables" / "mixed_vs_separated_comparison.csv"
    json_path = PROJECT_ROOT / "results" / "tables" / "mixed_vs_separated_comparison.json"
    rows = read_existing_rows(csv_path)
    for case in cases:
        rows = upsert_row(rows, build_row(case))
    write_csv(rows, csv_path)
    write_json(rows, json_path)

    print(f"Wrote comparison CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote comparison JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
