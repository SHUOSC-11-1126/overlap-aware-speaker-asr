from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_status",
    "case_id",
    "alignment_gap",
    "drift_severity",
    "handoff_goal",
    "primary_limitation",
    "expected_evidence",
    "handoff_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "handoff_scope",
    "case_id",
    "expected_inputs",
    "writeback_note",
]


def load_drift_diagnostic_rows() -> list[dict[str, Any]]:
    diagnostic_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_alignment_drift_diagnostic.json"
    if not diagnostic_path.exists():
        return []
    payload = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    return list(payload) if isinstance(payload, list) else []


def build_handoff_row(diagnostic_row: dict[str, Any]) -> dict[str, str]:
    case_id = str(diagnostic_row.get("case_id", "HeavyOverlap"))
    alignment_gap = str(diagnostic_row.get("alignment_gap", ""))
    drift_severity = str(diagnostic_row.get("drift_severity", "moderate"))
    return {
        "handoff_status": "drift_handoff_ready",
        "case_id": case_id,
        "alignment_gap": alignment_gap,
        "drift_severity": drift_severity,
        "handoff_goal": (
            f"Inspect {case_id} cleaned separated segments before advancing any cpWER bridge handoff claim."
        ),
        "primary_limitation": (
            "Cross-metric drift is documented but not yet reconciled against segment-level export paths."
        ),
        "expected_evidence": "results/figures/meeteval_cpwer_alignment_drift_diagnostic.md",
        "handoff_note": (
            "experimental/frontier drift handoff only; full MeetEval evaluation and cpWER execution remain pending."
        ),
    }


def build_handoff_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Handoff",
        "",
        "This generated handoff turns the drift diagnostic into the next narrow MeetEval frontier step. "
        "It does not claim cpWER execution.",
        "",
        "| handoff_status | case_id | alignment_gap | drift_severity | handoff_goal | primary_limitation | expected_evidence | handoff_note |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['handoff_status']} | {row['case_id']} | {row['alignment_gap']} | {row['drift_severity']} | "
            f"{row['handoff_goal']} | {row['primary_limitation']} | {row['expected_evidence']} | {row['handoff_note']} |"
        )
    return lines


def build_handoff_receipt_rows(handoff_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "handoff_documented",
            "handoff_scope": "single_drift_case",
            "case_id": str(handoff_row.get("case_id", "")),
            "expected_inputs": "MeetEval cpWER alignment drift diagnostic table.",
            "writeback_note": (
                "Drift handoff documented for coordination; segment-level reconciliation remains pending."
            ),
        }
    ]


def build_handoff_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Handoff Receipt",
        "",
        "This receipt records the drift handoff writeback. It does not claim cpWER execution.",
        "",
        "| execution_status | handoff_scope | case_id | expected_inputs | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['handoff_scope']} | {row['case_id']} | "
            f"{row['expected_inputs']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    handoff_rows: list[dict[str, str]],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    handoff_csv_path = tables_dir / "meeteval_cpwer_alignment_drift_handoff.csv"
    handoff_json_path = tables_dir / "meeteval_cpwer_alignment_drift_handoff.json"
    handoff_md_path = figures_dir / "meeteval_cpwer_alignment_drift_handoff.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_alignment_drift_handoff_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_alignment_drift_handoff_receipt.md"

    with handoff_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerows(handoff_rows)
    handoff_json_path.write_text(json.dumps(handoff_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    handoff_md_path.write_text("\n".join(build_handoff_lines(handoff_rows)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_handoff_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return handoff_csv_path, handoff_json_path, handoff_md_path, receipt_json_path, receipt_md_path


def main() -> None:
    diagnostic_rows = load_drift_diagnostic_rows()
    handoff_rows = [build_handoff_row(row) for row in diagnostic_rows]
    receipt_rows = build_handoff_receipt_rows(handoff_rows[0]) if handoff_rows else []
    handoff_csv_path, handoff_json_path, handoff_md_path, receipt_json_path, receipt_md_path = write_outputs(
        handoff_rows,
        receipt_rows,
    )
    print(f"Wrote MeetEval cpWER alignment drift handoff CSV: {handoff_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER alignment drift handoff JSON: {handoff_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER alignment drift handoff note: {handoff_md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote MeetEval cpWER alignment drift handoff receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift handoff receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
