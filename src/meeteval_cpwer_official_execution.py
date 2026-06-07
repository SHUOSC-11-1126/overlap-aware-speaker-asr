from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .meeteval_cpwer_bridge import aggregate_speaker_text
from .meeteval_dry_run import load_jsonl_segments, select_preferred_case


EXECUTION_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "execution_status",
    "official_cpwer",
    "cpwer_tool",
    "speaker_count",
    "result_label",
    "execution_note",
]

RECEIPT_UPDATE_COLUMNS = [
    "execution_status",
    "run_scope",
    "case_id",
    "hypothesis_source",
    "preflight_pass",
    "official_cpwer",
    "cpwer_tool",
    "cpwer_bridge_lite",
    "expected_inputs",
    "expected_outputs",
    "writeback_note",
]


def try_import_meeteval() -> Any | None:
    try:
        from meeteval.wer.wer.cp import cp_word_error_rate

        return cp_word_error_rate
    except ImportError:
        return None


def extract_speakers(segments: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            str(segment.get("speaker", "")).strip()
            for segment in segments
            if str(segment.get("speaker", "")).strip()
        }
    )


def build_speaker_text_lists(
    reference_segments: list[dict[str, Any]],
    hypothesis_segments: list[dict[str, Any]],
    speakers: list[str],
) -> tuple[list[str], list[str]]:
    reference_texts = [aggregate_speaker_text(reference_segments, speaker) for speaker in speakers]
    hypothesis_texts = [aggregate_speaker_text(hypothesis_segments, speaker) for speaker in speakers]
    return reference_texts, hypothesis_texts


def compute_official_cpwer(
    cp_word_error_rate: Any,
    reference_texts: list[str],
    hypothesis_texts: list[str],
) -> float:
    result = cp_word_error_rate(reference=reference_texts, hypothesis=hypothesis_texts)
    error_rate = getattr(result, "error_rate", result)
    return round(float(error_rate), 6)


def load_bridge_lite_score(case_id: str) -> str:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_bridge.csv"
    if not path.exists():
        return ""
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("case_id", "")) == case_id:
                return str(row.get("cpwer_bridge_lite", ""))
    return ""


def load_hypothesis_source(case_id: str) -> str:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_preflight_batch.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            for row in payload:
                if str(row.get("case_id", "")) == case_id:
                    return str(row.get("hypothesis_source", ""))
    return ""


def build_execution_row(
    case_id: str,
    hypothesis_source: str,
    official_cpwer: float | None,
    speaker_count: int,
    tool_available: bool,
) -> dict[str, str]:
    if official_cpwer is not None:
        execution_status = "official_cpwer_narrow_dry_run_complete"
        execution_note = (
            f"Official MeetEval cpWER narrow dry run completed for {case_id}; "
            "this remains experimental/frontier and is not a full benchmark claim."
        )
    elif not tool_available:
        execution_status = "official_cpwer_tool_unavailable"
        execution_note = (
            "MeetEval package not installed; run `pip install meeteval` before official cpWER execution."
        )
    else:
        execution_status = "official_cpwer_execution_failed"
        execution_note = f"Official MeetEval cpWER execution failed for {case_id}."

    return {
        "case_id": case_id,
        "hypothesis_source": hypothesis_source,
        "execution_status": execution_status,
        "official_cpwer": "" if official_cpwer is None else str(official_cpwer),
        "cpwer_tool": "meeteval" if tool_available else "unavailable",
        "speaker_count": str(speaker_count),
        "result_label": "experimental/frontier",
        "execution_note": execution_note,
    }


def run_official_execution(case_id: str) -> dict[str, str]:
    cp_word_error_rate = try_import_meeteval()
    tool_available = cp_word_error_rate is not None
    reference_path = PROJECT_ROOT / "results" / "tables" / "meeteval_reference_segments.jsonl"
    hypothesis_path = PROJECT_ROOT / "results" / "tables" / "meeteval_hypothesis_segments.jsonl"
    reference_segments = load_jsonl_segments(reference_path, case_id)
    hypothesis_segments = load_jsonl_segments(hypothesis_path, case_id)
    speakers = extract_speakers(reference_segments)
    hypothesis_source = load_hypothesis_source(case_id)

    official_cpwer: float | None = None
    if tool_available and len(speakers) >= 2 and reference_segments and hypothesis_segments:
        reference_texts, hypothesis_texts = build_speaker_text_lists(
            reference_segments,
            hypothesis_segments,
            speakers,
        )
        if all(reference_texts) and all(hypothesis_texts):
            official_cpwer = compute_official_cpwer(cp_word_error_rate, reference_texts, hypothesis_texts)

    return build_execution_row(case_id, hypothesis_source, official_cpwer, len(speakers), tool_available)


def build_execution_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Official Execution",
        "",
        "This generated note records official MeetEval cpWER narrow dry-run execution. "
        "Results remain experimental/frontier and do not constitute a full benchmark claim.",
        "",
        "| case_id | hypothesis_source | execution_status | official_cpwer | cpwer_tool | speaker_count | result_label | execution_note |",
        "| --- | --- | --- | ---: | --- | ---: | --- | --- |",
    ]
    for row in rows:
        cpwer_display = row["official_cpwer"] if row["official_cpwer"] else "—"
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['execution_status']} | "
            f"{cpwer_display} | {row['cpwer_tool']} | {row['speaker_count']} | "
            f"{row['result_label']} | {row['execution_note']} |"
        )
    return lines


def merge_receipt_entry(
    existing: dict[str, Any],
    execution_row: dict[str, str],
) -> dict[str, Any]:
    case_id = str(execution_row.get("case_id", ""))
    bridge_lite = load_bridge_lite_score(case_id)
    merged = dict(existing)
    merged.update(
        {
            "execution_status": execution_row.get("execution_status", merged.get("execution_status", "")),
            "official_cpwer": execution_row.get("official_cpwer", ""),
            "cpwer_tool": execution_row.get("cpwer_tool", ""),
            "cpwer_bridge_lite": bridge_lite,
            "result_label": execution_row.get("result_label", "experimental/frontier"),
            "writeback_note": execution_row.get(
                "execution_note",
                str(merged.get("writeback_note", "")),
            ),
        }
    )
    return merged


def update_execution_receipt(execution_row: dict[str, str]) -> list[dict[str, Any]]:
    receipt_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_receipt.json"
    if receipt_path.exists():
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    else:
        payload = []

    if not isinstance(payload, list):
        payload = []

    case_id = str(execution_row.get("case_id", ""))
    updated = False
    merged_payload: list[dict[str, Any]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("case_id", "")) == case_id:
            merged_payload.append(merge_receipt_entry(entry, execution_row))
            updated = True
        else:
            merged_payload.append(entry)

    if not updated:
        merged_payload.append(
            merge_receipt_entry(
                {
                    "execution_status": "template_only",
                    "run_scope": "narrow_cpwer_dry_run",
                    "case_id": case_id,
                    "hypothesis_source": execution_row.get("hypothesis_source", ""),
                    "preflight_pass": "True",
                    "expected_inputs": (
                        "results/tables/meeteval_reference_segments.jsonl; "
                        "results/tables/meeteval_hypothesis_segments.jsonl; MeetEval cpWER tooling."
                    ),
                    "expected_outputs": "Official cpWER score and evaluation note.",
                    "writeback_note": "",
                },
                execution_row,
            )
        )

    receipt_path.write_text(json.dumps(merged_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return merged_payload


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_official_execution.csv"
    json_path = tables_dir / "meeteval_cpwer_official_execution.json"
    md_path = figures_dir / "meeteval_cpwer_official_execution.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXECUTION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_execution_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run official MeetEval cpWER narrow dry run.")
    parser.add_argument(
        "--case",
        default="preferred",
        help="Verified case id or 'preferred' (default uses dry-run checklist priority).",
    )
    return parser.parse_args()


def resolve_case_id(case_arg: str) -> str:
    if case_arg == "preferred":
        checklist_path = PROJECT_ROOT / "results" / "tables" / "meeteval_dry_run_checklist.csv"
        return select_preferred_case(checklist_path)
    return case_arg


def main() -> None:
    args = parse_args()
    case_id = resolve_case_id(args.case)
    execution_row = run_official_execution(case_id)
    csv_path, json_path, md_path = write_outputs([execution_row])

    if execution_row.get("execution_status") == "official_cpwer_narrow_dry_run_complete":
        update_execution_receipt(execution_row)

    print(f"Wrote MeetEval cpWER official execution CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER official execution JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER official execution note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Execution status: {execution_row['execution_status']}")
    if execution_row.get("official_cpwer"):
        print(f"Official cpWER: {execution_row['official_cpwer']}")


if __name__ == "__main__":
    main()
