from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


GATE_COLUMNS = [
    "dataset_name",
    "label",
    "license_status",
    "gate_step",
    "gate_order",
    "gate_note",
    "next_gate",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "slice_scope",
    "dataset_name",
    "license_status",
    "expected_inputs",
    "writeback_note",
]


def load_slice_mapping() -> dict[str, Any]:
    mapping_path = PROJECT_ROOT / "results" / "tables" / "external_validation_slice_mapping.json"
    if not mapping_path.exists():
        return {}
    return json.loads(mapping_path.read_text(encoding="utf-8"))


def build_license_gate_rows(mapping: dict[str, Any]) -> list[dict[str, str]]:
    dataset_name = str(mapping.get("dataset_name", "AISHELL-4"))
    label = str(mapping.get("label", "external/sanity-check"))
    license_status = str(mapping.get("license_status", "pending_confirmation"))
    return [
        {
            "dataset_name": dataset_name,
            "label": label,
            "license_status": license_status,
            "gate_step": "Confirm official AISHELL-4 license terms before staging any local audio.",
            "gate_order": "1",
            "gate_note": "Read the official release page and record whether local reuse is permitted for a tiny sanity-check slice.",
            "next_gate": "Document the license decision in the slice receipt before downloading audio.",
        },
        {
            "dataset_name": dataset_name,
            "label": label,
            "license_status": license_status,
            "gate_step": "Verify attribution and redistribution constraints for any excerpt used in the repo.",
            "gate_order": "2",
            "gate_note": "Keep the external slice explicitly labeled external/sanity-check and separate from gold benchmark claims.",
            "next_gate": "Only after the license gate is documented should any audio staging begin.",
        },
    ]


def build_license_gate_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation License Gate",
        "",
        "This generated checklist records the license gate for the first external sanity-check slice. "
        "It does not claim that any external audio has been downloaded or evaluated.",
        "",
        "| dataset_name | label | license_status | gate_order | gate_step | gate_note | next_gate |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['dataset_name']} | {row['label']} | {row['license_status']} | {row['gate_order']} | "
            f"{row['gate_step']} | {row['gate_note']} | {row['next_gate']} |"
        )
    return lines


def build_license_gate_receipt_rows(mapping: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "license_gate_documented",
            "slice_scope": "single_short_meeting_excerpt",
            "dataset_name": str(mapping.get("dataset_name", "AISHELL-4")),
            "license_status": str(mapping.get("license_status", "pending_confirmation")),
            "expected_inputs": "Official AISHELL-4 license terms plus the existing slice mapping stub.",
            "writeback_note": "License gate checklist documented; external audio staging remains blocked until license confirmation is recorded.",
        }
    ]


def build_license_gate_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation License Gate Receipt",
        "",
        "This receipt records the license-gate documentation pass. It does not claim that any external benchmark has been executed.",
        "",
        "| execution_status | slice_scope | dataset_name | license_status | expected_inputs | writeback_note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['slice_scope']} | {row['dataset_name']} | {row['license_status']} | "
            f"{row['expected_inputs']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    gate_rows: list[dict[str, str]],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    gate_csv_path = tables_dir / "external_validation_license_gate.csv"
    gate_json_path = tables_dir / "external_validation_license_gate.json"
    gate_md_path = figures_dir / "external_validation_license_gate.md"
    receipt_json_path = tables_dir / "external_validation_license_gate_receipt.json"
    receipt_md_path = figures_dir / "external_validation_license_gate_receipt.md"

    with gate_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=GATE_COLUMNS)
        writer.writeheader()
        writer.writerows(gate_rows)
    gate_json_path.write_text(json.dumps(gate_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    gate_md_path.write_text("\n".join(build_license_gate_lines(gate_rows)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_license_gate_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return gate_csv_path, gate_json_path, gate_md_path, receipt_json_path, receipt_md_path


def main() -> None:
    mapping = load_slice_mapping()
    gate_rows = build_license_gate_rows(mapping)
    receipt_rows = build_license_gate_receipt_rows(mapping)
    gate_csv_path, gate_json_path, gate_md_path, receipt_json_path, receipt_md_path = write_outputs(
        gate_rows,
        receipt_rows,
    )
    print(f"Wrote external license gate CSV: {gate_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external license gate JSON: {gate_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external license gate note: {gate_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external license gate receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external license gate receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
