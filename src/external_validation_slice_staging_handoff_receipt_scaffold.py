from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


SCAFFOLD_COLUMNS = [
    "dataset_name",
    "handoff_status",
    "blocker",
    "scaffold_status",
    "expected_inputs",
    "expected_outputs",
    "scaffold_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "scaffold_scope",
    "dataset_name",
    "blocker",
    "writeback_note",
]


def load_staging_handoff() -> dict[str, Any]:
    handoff_path = PROJECT_ROOT / "results" / "tables" / "external_validation_slice_staging_readiness_handoff.json"
    if not handoff_path.exists():
        return {}
    payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_scaffold_row(handoff: dict[str, Any]) -> dict[str, str]:
    dataset_name = str(handoff.get("dataset_name", "AISHELL-4"))
    handoff_status = str(handoff.get("handoff_status", "staging_handoff_ready"))
    blocker = str(handoff.get("blocker", "license_confirmation_pending"))
    return {
        "dataset_name": dataset_name,
        "handoff_status": handoff_status,
        "blocker": blocker,
        "scaffold_status": "receipt_scaffold_only",
        "expected_inputs": "License confirmation note plus AISHELL-4 slice manifest and mapping artifact.",
        "expected_outputs": "External slice staging receipt documenting the first narrow sanity-check excerpt.",
        "scaffold_note": (
            f"Template-only external slice staging receipt scaffold for {dataset_name} while blocker={blocker}. "
            "External audio staging and benchmark evaluation remain pending."
        ),
    }


def build_scaffold_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Handoff Receipt Scaffold",
        "",
        "This generated note records a template-only external slice staging receipt scaffold. "
        "It does not claim external audio download or benchmark execution.",
        "",
        "| dataset_name | handoff_status | blocker | scaffold_status | expected_inputs | expected_outputs | scaffold_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['dataset_name']} | {row['handoff_status']} | {row['blocker']} | {row['scaffold_status']} | "
            f"{row['expected_inputs']} | {row['expected_outputs']} | {row['scaffold_note']} |"
        ),
    ]
    return lines


def build_scaffold_receipt_rows(scaffold_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "receipt_scaffold_complete",
            "scaffold_scope": "single_external_slice_staging",
            "dataset_name": str(scaffold_row.get("dataset_name", "")),
            "blocker": str(scaffold_row.get("blocker", "")),
            "writeback_note": (
                "External slice staging receipt scaffold documented; "
                "external audio staging and benchmark evaluation remain pending."
            ),
        }
    ]


def build_scaffold_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Handoff Receipt Scaffold Receipt",
        "",
        "This receipt records the staging receipt scaffold writeback. It does not claim benchmark execution.",
        "",
        "| execution_status | scaffold_scope | dataset_name | blocker | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['scaffold_scope']} | {row['dataset_name']} | "
            f"{row['blocker']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    scaffold_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "external_validation_slice_staging_handoff_receipt_scaffold.csv"
    json_path = tables_dir / "external_validation_slice_staging_handoff_receipt_scaffold.json"
    md_path = figures_dir / "external_validation_slice_staging_handoff_receipt_scaffold.md"
    receipt_template_path = tables_dir / "external_validation_slice_staging_handoff_receipt.json"
    receipt_json_path = tables_dir / "external_validation_slice_staging_handoff_receipt_scaffold_receipt.json"
    receipt_md_path = figures_dir / "external_validation_slice_staging_handoff_receipt_scaffold_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SCAFFOLD_COLUMNS)
        writer.writeheader()
        writer.writerow(scaffold_row)
    json_path.write_text(json.dumps(scaffold_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_scaffold_lines(scaffold_row)) + "\n", encoding="utf-8")

    receipt_template = [
        {
            "execution_status": "template_only",
            "run_scope": "single_external_slice_staging",
            "dataset_name": scaffold_row.get("dataset_name", ""),
            "blocker": scaffold_row.get("blocker", ""),
            "expected_inputs": scaffold_row.get("expected_inputs", ""),
            "expected_outputs": "External slice staging note and mapping confirmation.",
            "writeback_note": (
                "External audio staging has not happened yet; "
                "fill this receipt only after license confirmation and slice staging."
            ),
        }
    ]
    receipt_template_path.write_text(json.dumps(receipt_template, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_scaffold_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_template_path, receipt_json_path, receipt_md_path


def main() -> None:
    handoff = load_staging_handoff()
    scaffold_row = build_scaffold_row(handoff)
    receipt_rows = build_scaffold_receipt_rows(scaffold_row)
    csv_path, json_path, md_path, receipt_template_path, receipt_json_path, receipt_md_path = write_outputs(
        scaffold_row,
        receipt_rows,
    )
    print(f"Wrote external validation slice staging handoff receipt scaffold CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external validation slice staging handoff receipt scaffold JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external validation slice staging handoff receipt scaffold note: {md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote external validation slice staging handoff receipt template JSON: "
        f"{receipt_template_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external validation slice staging handoff receipt scaffold receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external validation slice staging handoff receipt scaffold receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
