from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_status",
    "dataset_name",
    "readiness_status",
    "blocker",
    "staging_handoff_target",
    "handoff_goal",
    "expected_evidence",
    "handoff_note",
]


def load_staging_readiness() -> dict[str, Any]:
    readiness_path = PROJECT_ROOT / "results" / "tables" / "external_validation_slice_staging_readiness.json"
    if not readiness_path.exists():
        return {}
    payload = json.loads(readiness_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_handoff_row(readiness: dict[str, Any]) -> dict[str, str]:
    dataset_name = str(readiness.get("dataset_name", "AISHELL-4"))
    readiness_status = str(readiness.get("readiness_status", "not_ready"))
    blocker = str(readiness.get("blocker", "license_confirmation_pending"))
    return {
        "handoff_status": "staging_handoff_ready",
        "dataset_name": dataset_name,
        "readiness_status": readiness_status,
        "blocker": blocker,
        "staging_handoff_target": "results/figures/external_validation_slice_staging_handoff.md",
        "handoff_goal": (
            f"Resolve the {blocker} blocker for {dataset_name} before any external audio staging attempt."
        ),
        "expected_evidence": "results/tables/external_validation_slice_staging_handoff_receipt.json",
        "handoff_note": (
            "external/sanity-check staging handoff only; no external audio download or benchmark evaluation is claimed."
        ),
    }


def build_handoff_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Readiness Handoff",
        "",
        "This generated handoff turns the staging readiness audit into the next narrow external-validation frontier step. "
        "It does not claim benchmark execution or external audio download.",
        "",
        "| handoff_status | dataset_name | readiness_status | blocker | staging_handoff_target | handoff_goal | expected_evidence | handoff_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['handoff_status']} | {row['dataset_name']} | {row['readiness_status']} | {row['blocker']} | "
            f"{row['staging_handoff_target']} | {row['handoff_goal']} | {row['expected_evidence']} | {row['handoff_note']} |"
        ),
    ]
    return lines


def build_handoff_receipt_rows(handoff_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "handoff_documented",
            "handoff_scope": "single_external_slice_staging",
            "dataset_name": str(handoff_row.get("dataset_name", "")),
            "writeback_note": (
                "Staging readiness handoff documented for coordination; "
                "external audio staging and benchmark evaluation remain pending."
            ),
        }
    ]


def build_handoff_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Readiness Handoff Receipt",
        "",
        "This receipt records the staging readiness handoff writeback. It does not claim benchmark execution.",
        "",
        "| execution_status | handoff_scope | dataset_name | writeback_note |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['handoff_scope']} | {row['dataset_name']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    handoff_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "external_validation_slice_staging_readiness_handoff.csv"
    json_path = tables_dir / "external_validation_slice_staging_readiness_handoff.json"
    md_path = figures_dir / "external_validation_slice_staging_readiness_handoff.md"
    receipt_json_path = tables_dir / "external_validation_slice_staging_readiness_handoff_receipt.json"
    receipt_md_path = figures_dir / "external_validation_slice_staging_readiness_handoff_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerow(handoff_row)
    json_path.write_text(json.dumps(handoff_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(handoff_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_handoff_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    readiness = load_staging_readiness()
    handoff_row = build_handoff_row(readiness)
    receipt_rows = build_handoff_receipt_rows(handoff_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        handoff_row,
        receipt_rows,
    )
    print(f"Wrote external slice staging readiness handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice staging readiness handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice staging readiness handoff note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice staging readiness handoff receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice staging readiness handoff receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
