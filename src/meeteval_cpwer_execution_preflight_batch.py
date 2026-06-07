from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .meeteval_cpwer_execution_preflight import (
    PREFLIGHT_COLUMNS,
    load_execution_handoff,
    run_preflight,
)

GOLD_CASES = [
    "NoOverlap",
    "LightOverlap",
    "MidOverlap",
    "HeavyOverlap",
    "OppositeOverlap",
]


def build_preflight_batch_rows(handoff: dict[str, Any]) -> list[dict[str, Any]]:
    return [run_preflight(case_id, handoff) for case_id in GOLD_CASES]


def build_batch_summary_lines(rows: list[dict[str, Any]]) -> list[str]:
    pass_count = sum(1 for row in rows if row.get("preflight_pass"))
    lines = [
        "# MeetEval cpWER Execution Preflight Batch",
        "",
        "This generated note records execution preflight across all five verified gold cases. "
        "It does not claim official cpWER evaluation or benchmark completion.",
        "",
        f"Summary: `{pass_count}/{len(rows)}` cases passed preflight.",
        "",
        "| case_id | hypothesis_source | speaker_set_match | time_range_valid | preflight_pass | preflight_note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['speaker_set_match']} | "
            f"{row['time_range_valid']} | {row['preflight_pass']} | {row['preflight_note']} |"
        )
    return lines


def build_batch_receipt_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    pass_count = sum(1 for row in rows if row.get("preflight_pass"))
    return [
        {
            "execution_status": "preflight_batch_complete",
            "run_scope": "all_gold_cpwer_execution_preflight",
            "case_id": "ALL",
            "preflight_pass_count": str(pass_count),
            "preflight_total_count": str(len(rows)),
            "expected_inputs": (
                "results/tables/meeteval_reference_segments.jsonl; "
                "results/tables/meeteval_hypothesis_segments.jsonl"
            ),
            "expected_outputs": "Official cpWER score receipt per verified gold case.",
            "writeback_note": (
                "Batch execution preflight documented; official MeetEval cpWER evaluation remains pending."
            ),
        }
    ]


def build_batch_receipt_lines(receipt_rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Preflight Batch Receipt",
        "",
        "This receipt records the batch preflight writeback. It does not claim cpWER execution.",
        "",
        "| execution_status | run_scope | case_id | preflight_pass_count | preflight_total_count | writeback_note |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]
    for row in receipt_rows:
        lines.append(
            f"| {row['execution_status']} | {row['run_scope']} | {row['case_id']} | "
            f"{row['preflight_pass_count']} | {row['preflight_total_count']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    rows: list[dict[str, Any]],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_preflight_batch.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_preflight_batch.json"
    md_path = figures_dir / "meeteval_cpwer_execution_preflight_batch.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_execution_preflight_batch_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_execution_preflight_batch_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PREFLIGHT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_batch_summary_lines(rows)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_batch_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    handoff = load_execution_handoff()
    rows = build_preflight_batch_rows(handoff)
    receipt_rows = build_batch_receipt_rows(rows)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(rows, receipt_rows)
    pass_count = sum(1 for row in rows if row.get("preflight_pass"))
    print(f"Wrote MeetEval cpWER execution preflight batch CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution preflight batch JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution preflight batch note: {md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote MeetEval cpWER execution preflight batch receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution preflight batch receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Preflight pass count: {pass_count}/{len(rows)}")


if __name__ == "__main__":
    main()
