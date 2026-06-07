from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


DIAGNOSTIC_COLUMNS = [
    "case_id",
    "hypothesis_source",
    "cpwer_bridge_lite",
    "speaker_macro_cer",
    "alignment_gap",
    "drift_severity",
    "likely_cause",
    "recommended_action",
    "diagnostic_status",
    "observation",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "diagnostic_scope",
    "drift_case_count",
    "expected_inputs",
    "writeback_note",
]


def load_alignment_rows() -> list[dict[str, Any]]:
    alignment_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_alignment.json"
    if not alignment_path.exists():
        return []
    payload = json.loads(alignment_path.read_text(encoding="utf-8"))
    return list(payload) if isinstance(payload, list) else []


def select_drift_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if str(row.get("alignment_status", "")) == "drift"]


def classify_drift_severity(gap: float) -> str:
    if gap >= 0.015:
        return "moderate"
    if gap > 0.001:
        return "minor"
    return "negligible"


def build_drift_diagnostic_row(row: dict[str, Any]) -> dict[str, str]:
    case_id = str(row.get("case_id", ""))
    hypothesis_source = str(row.get("hypothesis_source", ""))
    gap = float(row.get("alignment_gap", 0.0) or 0.0)
    likely_cause = (
        f"{case_id} uses {hypothesis_source}; the cleaned separated export path and speaker_macro_cer "
        "recomputation diverge under heavy overlap, producing a non-zero cross-metric gap."
    )
    return {
        "case_id": case_id,
        "hypothesis_source": hypothesis_source,
        "cpwer_bridge_lite": str(row.get("cpwer_bridge_lite", "")),
        "speaker_macro_cer": str(row.get("speaker_macro_cer", "")),
        "alignment_gap": str(gap),
        "drift_severity": classify_drift_severity(gap),
        "likely_cause": likely_cause,
        "recommended_action": (
            f"Inspect {case_id} cleaned separated segments before treating cpWER bridge-lite as aligned "
            "with speaker_macro_cer."
        ),
        "diagnostic_status": "drift_documented",
        "observation": (
            "experimental/frontier drift diagnostic only; this does not claim a finished MeetEval evaluation."
        ),
    }


def build_drift_diagnostic_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Diagnostic",
        "",
        "This generated note documents cross-metric drift cases from the alignment audit. "
        "It does not claim a finished MeetEval evaluation.",
        "",
        "| case_id | hypothesis_source | cpwer_bridge_lite | speaker_macro_cer | alignment_gap | drift_severity | likely_cause | recommended_action | diagnostic_status | observation |",
        "| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['hypothesis_source']} | {row['cpwer_bridge_lite']} | "
            f"{row['speaker_macro_cer']} | {row['alignment_gap']} | {row['drift_severity']} | "
            f"{row['likely_cause']} | {row['recommended_action']} | {row['diagnostic_status']} | {row['observation']} |"
        )
    return lines


def build_drift_diagnostic_receipt_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "diagnostic_complete",
            "diagnostic_scope": "alignment_drift_cases",
            "drift_case_count": str(len(rows)),
            "expected_inputs": "MeetEval cpWER alignment table with drift status rows.",
            "writeback_note": (
                "Drift cases documented for coordination; full MeetEval evaluation and cpWER execution remain pending."
            ),
        }
    ]


def build_drift_diagnostic_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Diagnostic Receipt",
        "",
        "This receipt records the drift diagnostic writeback. It does not claim cpWER execution.",
        "",
        "| execution_status | diagnostic_scope | drift_case_count | expected_inputs | writeback_note |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['diagnostic_scope']} | {row['drift_case_count']} | "
            f"{row['expected_inputs']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    diagnostic_rows: list[dict[str, str]],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_alignment_drift_diagnostic.csv"
    json_path = tables_dir / "meeteval_cpwer_alignment_drift_diagnostic.json"
    md_path = figures_dir / "meeteval_cpwer_alignment_drift_diagnostic.md"
    receipt_json_path = tables_dir / "meeteval_cpwer_alignment_drift_diagnostic_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_alignment_drift_diagnostic_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DIAGNOSTIC_COLUMNS)
        writer.writeheader()
        writer.writerows(diagnostic_rows)
    json_path.write_text(json.dumps(diagnostic_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_drift_diagnostic_lines(diagnostic_rows)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text(
        "\n".join(build_drift_diagnostic_receipt_lines(receipt_rows)) + "\n",
        encoding="utf-8",
    )
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    alignment_rows = load_alignment_rows()
    drift_rows = select_drift_rows(alignment_rows)
    diagnostic_rows = [build_drift_diagnostic_row(row) for row in drift_rows]
    receipt_rows = build_drift_diagnostic_receipt_rows(diagnostic_rows)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        diagnostic_rows,
        receipt_rows,
    )
    print(f"Wrote MeetEval cpWER alignment drift diagnostic CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER alignment drift diagnostic JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER alignment drift diagnostic note: {md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote MeetEval cpWER alignment drift diagnostic receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift diagnostic receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Drift diagnostic summary: drift_case_count={len(diagnostic_rows)}")


if __name__ == "__main__":
    main()
