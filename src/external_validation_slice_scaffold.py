from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


MAPPING_COLUMNS = [
    "dataset_name",
    "label",
    "slice_id",
    "license_status",
    "audio_path",
    "reference_path",
    "speaker_schema",
    "mapping_status",
    "scaffold_note",
]

SCAFFOLD_RECEIPT_COLUMNS = [
    "execution_status",
    "slice_scope",
    "dataset_name",
    "mapping_artifact",
    "license_status",
    "expected_outputs",
    "writeback_note",
]


def build_aishell4_mapping_stub() -> dict[str, Any]:
    return {
        "dataset_name": "AISHELL-4",
        "label": "external/sanity-check",
        "slice_id": "aishell4_meeting_excerpt_stub_001",
        "license_status": "pending_confirmation",
        "audio_path": "resources/external_sanity_check/aishell4/meeting_excerpt_stub_001.wav",
        "reference_path": "resources/external_sanity_check/aishell4/meeting_excerpt_stub_001_reference.json",
        "speaker_schema": {
            "speaker_field": "speaker",
            "start_field": "start",
            "end_field": "end",
            "text_field": "text",
        },
        "segments": [],
        "mapping_status": "scaffold_only",
        "scaffold_note": (
            "Template-only mapping stub for the first AISHELL-4 slice. "
            "No external audio or reference has been staged yet."
        ),
    }


def build_mapping_row(stub: dict[str, Any]) -> dict[str, str]:
    return {
        "dataset_name": str(stub.get("dataset_name", "")),
        "label": str(stub.get("label", "")),
        "slice_id": str(stub.get("slice_id", "")),
        "license_status": str(stub.get("license_status", "")),
        "audio_path": str(stub.get("audio_path", "")),
        "reference_path": str(stub.get("reference_path", "")),
        "speaker_schema": json.dumps(stub.get("speaker_schema", {}), ensure_ascii=False),
        "mapping_status": str(stub.get("mapping_status", "")),
        "scaffold_note": str(stub.get("scaffold_note", "")),
    }


def build_scaffold_summary_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# External Validation Slice Scaffold",
        "",
        "This generated note records a template-only mapping stub for the first external sanity-check slice. "
        "It does not claim that any external benchmark has been executed.",
        "",
        "| dataset_name | label | slice_id | license_status | audio_path | reference_path | mapping_status | scaffold_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['dataset_name']} | {row['label']} | {row['slice_id']} | {row['license_status']} | "
            f"{row['audio_path']} | {row['reference_path']} | {row['mapping_status']} | {row['scaffold_note']} |"
        ),
    ]
    return lines


def build_scaffold_receipt_rows(mapping_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "scaffold_complete",
            "slice_scope": "single_short_meeting_excerpt",
            "dataset_name": str(mapping_row.get("dataset_name", "")),
            "mapping_artifact": "results/tables/external_validation_slice_mapping.json",
            "license_status": str(mapping_row.get("license_status", "")),
            "expected_outputs": "Repo mapping stub and license gate note for the first external slice.",
            "writeback_note": "External slice scaffold complete; no external benchmark audio or evaluation has been run yet.",
        }
    ]


def build_scaffold_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Slice Receipt",
        "",
        "This receipt records the first external slice scaffold writeback. It does not claim that any external benchmark has been executed.",
        "",
        "| execution_status | slice_scope | dataset_name | mapping_artifact | license_status | expected_outputs | writeback_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['slice_scope']} | {row['dataset_name']} | {row['mapping_artifact']} | "
            f"{row['license_status']} | {row['expected_outputs']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    stub: dict[str, Any],
    mapping_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    resources_dir = PROJECT_ROOT / "resources" / "external_sanity_check" / "aishell4"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    mapping_json_path = tables_dir / "external_validation_slice_mapping.json"
    mapping_csv_path = tables_dir / "external_validation_slice_mapping.csv"
    scaffold_md_path = figures_dir / "external_validation_slice_scaffold.md"
    receipt_json_path = tables_dir / "external_validation_slice_receipt.json"
    receipt_md_path = figures_dir / "external_validation_slice_receipt.md"
    placeholder_path = resources_dir / ".gitkeep"

    mapping_json_path.write_text(json.dumps(stub, ensure_ascii=False, indent=2), encoding="utf-8")
    with mapping_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=MAPPING_COLUMNS)
        writer.writeheader()
        writer.writerow(mapping_row)
    scaffold_md_path.write_text("\n".join(build_scaffold_summary_lines(mapping_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_scaffold_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    if not placeholder_path.exists():
        placeholder_path.write_text("", encoding="utf-8")
    return (
        mapping_json_path,
        mapping_csv_path,
        scaffold_md_path,
        receipt_json_path,
        receipt_md_path,
        placeholder_path,
    )


def main() -> None:
    stub = build_aishell4_mapping_stub()
    mapping_row = build_mapping_row(stub)
    receipt_rows = build_scaffold_receipt_rows(mapping_row)
    (
        mapping_json_path,
        mapping_csv_path,
        scaffold_md_path,
        receipt_json_path,
        receipt_md_path,
        placeholder_path,
    ) = write_outputs(stub, mapping_row, receipt_rows)
    print(f"Wrote external slice mapping JSON: {mapping_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice mapping CSV: {mapping_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice scaffold note: {scaffold_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Ensured external sanity-check placeholder: {placeholder_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
