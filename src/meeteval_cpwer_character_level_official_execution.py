from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .meeteval_cpwer_bridge import aggregate_speaker_text
from .meeteval_cpwer_execution_preflight_batch import GOLD_CASES
from .meeteval_cpwer_official_execution import (
    build_execution_row,
    load_hypothesis_source,
    try_import_meeteval,
)
from .meeteval_dry_run import load_jsonl_segments, select_preferred_case
from .meeteval_tokenization import tokenize_chinese_for_meeteval


EXECUTION_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "execution_status",
    "official_cpwer",
    "official_cpwer_raw",
    "cpwer_tool",
    "speaker_count",
    "tokenization_mode",
    "result_label",
    "execution_note",
]


def extract_speakers(segments: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(segment.get("speaker", "")).strip()
            for segment in segments
            if str(segment.get("speaker", "")).strip()
        }
    )


def build_tokenized_speaker_text_lists(
    reference_segments: list[dict[str, Any]],
    hypothesis_segments: list[dict[str, Any]],
    speakers: list[str],
) -> tuple[list[str], list[str]]:
    reference_texts = [
        tokenize_chinese_for_meeteval(aggregate_speaker_text(reference_segments, speaker))
        for speaker in speakers
    ]
    hypothesis_texts = [
        tokenize_chinese_for_meeteval(aggregate_speaker_text(hypothesis_segments, speaker))
        for speaker in speakers
    ]
    return reference_texts, hypothesis_texts


def run_character_level_execution(case_id: str) -> dict[str, str]:
    cp_word_error_rate = try_import_meeteval()
    tool_available = cp_word_error_rate is not None
    reference_path = PROJECT_ROOT / "results" / "tables" / "meeteval_reference_segments.jsonl"
    hypothesis_path = PROJECT_ROOT / "results" / "tables" / "meeteval_hypothesis_segments.jsonl"
    reference_segments = load_jsonl_segments(reference_path, case_id)
    hypothesis_segments = load_jsonl_segments(hypothesis_path, case_id)
    speakers = extract_speakers(reference_segments)
    hypothesis_source = load_hypothesis_source(case_id)

    official_cpwer: float | None = None
    raw_cpwer: float | None = None
    scored_length: int | None = None
    if tool_available and len(speakers) >= 2 and reference_segments and hypothesis_segments:
        reference_texts, hypothesis_texts = build_tokenized_speaker_text_lists(
            reference_segments,
            hypothesis_segments,
            speakers,
        )
        if all(reference_texts) and all(hypothesis_texts):
            result = cp_word_error_rate(reference=reference_texts, hypothesis=hypothesis_texts)
            official_cpwer = round(float(getattr(result, "error_rate", result)), 6)
            scored_length = int(getattr(result, "length", 0) or 0)

        raw_reference = [aggregate_speaker_text(reference_segments, s) for s in speakers]
        raw_hypothesis = [aggregate_speaker_text(hypothesis_segments, s) for s in speakers]
        if all(raw_reference) and all(raw_hypothesis):
            raw_result = cp_word_error_rate(reference=raw_reference, hypothesis=raw_hypothesis)
            raw_cpwer = round(float(getattr(raw_result, "error_rate", raw_result)), 6)

    row = build_execution_row(
        case_id,
        hypothesis_source,
        official_cpwer,
        len(speakers),
        tool_available,
        scored_length=scored_length,
    )
    row["tokenization_mode"] = "character_spaced"
    row["official_cpwer_raw"] = "" if raw_cpwer is None else str(raw_cpwer)
    if official_cpwer is not None:
        row["execution_status"] = "character_level_cpwer_narrow_dry_run_complete"
        row["execution_note"] = (
            f"Character-spaced MeetEval cpWER narrow dry run completed for {case_id}; "
            "this remains experimental/frontier and uses space-separated CJK characters "
            "to align with bridge-lite character-level scoring."
        )
    return row


def build_execution_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Character-Level Official Execution",
        "",
        "This generated note records character-spaced MeetEval cpWER narrow dry-run execution. "
        "Results remain experimental/frontier and do not constitute a full benchmark claim.",
        "",
        "| case_id | hypothesis_source | execution_status | official_cpwer | official_cpwer_raw | cpwer_tool | speaker_count | tokenization_mode | result_label | execution_note |",
        "| --- | --- | --- | ---: | ---: | --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        cpwer_display = row["official_cpwer"] if row["official_cpwer"] else "—"
        raw_display = row.get("official_cpwer_raw", "") or "—"
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['execution_status']} | "
            f"{cpwer_display} | {raw_display} | {row['cpwer_tool']} | {row['speaker_count']} | "
            f"{row['tokenization_mode']} | {row['result_label']} | {row['execution_note']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_character_level_official_execution.csv"
    json_path = tables_dir / "meeteval_cpwer_character_level_official_execution.json"
    md_path = figures_dir / "meeteval_cpwer_character_level_official_execution.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXECUTION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_execution_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run character-spaced MeetEval cpWER narrow dry run.")
    parser.add_argument(
        "--case",
        default="all",
        help="Verified case id, 'preferred', or 'all' (default all gold cases).",
    )
    parser.add_argument("--all", action="store_true", help="Run all five verified gold cases.")
    return parser.parse_args()


def resolve_case_ids(case_arg: str, run_all: bool) -> list[str]:
    if run_all or case_arg == "all":
        return list(GOLD_CASES)
    if case_arg == "preferred":
        checklist_path = PROJECT_ROOT / "results" / "tables" / "meeteval_dry_run_checklist.csv"
        return [select_preferred_case(checklist_path)]
    return [case_arg]


def main() -> None:
    args = parse_args()
    case_ids = resolve_case_ids(args.case, args.all)
    execution_rows = [run_character_level_execution(case_id) for case_id in case_ids]
    csv_path, json_path, md_path = write_outputs(execution_rows)

    complete_count = sum(
        1
        for row in execution_rows
        if row.get("execution_status") == "character_level_cpwer_narrow_dry_run_complete"
    )
    print(f"Wrote character-level official execution CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote character-level official execution JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote character-level official execution note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Execution complete: {complete_count}/{len(execution_rows)} cases")
    for row in execution_rows:
        if row.get("official_cpwer"):
            print(f"  {row['case_id']}: char_cpWER={row['official_cpwer']} raw_cpWER={row.get('official_cpwer_raw', '—')}")


if __name__ == "__main__":
    main()
