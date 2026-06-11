from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .external_validation_slice_scaffold import MAPPING_COLUMNS, build_mapping_row


AISHELL4_LICENSE_ID = "CC BY-SA 4.0"
AISHELL4_SOURCE_URL = "https://www.openslr.org/111/"
AISHELL4_PAPER_URL = "https://arxiv.org/abs/2104.03603"
CONFIRMED_LICENSE_STATUS = "confirmed_research_cc_by_sa_4_0"

CONFIRMATION_COLUMNS = [
    "dataset_name",
    "label",
    "license_id",
    "license_status",
    "confirmation_status",
    "usage_scope",
    "source_url",
    "paper_url",
    "attribution_note",
    "result_label",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "confirmation_scope",
    "dataset_name",
    "license_status",
    "writeback_note",
]


def load_slice_mapping() -> dict[str, Any]:
    mapping_path = PROJECT_ROOT / "results" / "tables" / "external_validation_slice_mapping.json"
    if not mapping_path.exists():
        return {}
    payload = json.loads(mapping_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_confirmation_row(mapping: dict[str, Any]) -> dict[str, str]:
    dataset_name = str(mapping.get("dataset_name", "AISHELL-4"))
    return {
        "dataset_name": dataset_name,
        "label": str(mapping.get("label", "external/sanity-check")),
        "license_id": AISHELL4_LICENSE_ID,
        "license_status": CONFIRMED_LICENSE_STATUS,
        "confirmation_status": "confirmed",
        "usage_scope": "research_only_sanity_check_slice",
        "source_url": AISHELL4_SOURCE_URL,
        "paper_url": AISHELL4_PAPER_URL,
        "attribution_note": (
            f"{dataset_name} is used only for a tiny external/sanity-check slice under {AISHELL4_LICENSE_ID}. "
            "Research use only; no commercial redistribution of audio in this repository."
        ),
        "result_label": "external/sanity-check",
    }


def apply_confirmation_to_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    updated = dict(mapping)
    updated["license_status"] = CONFIRMED_LICENSE_STATUS
    updated["license_id"] = AISHELL4_LICENSE_ID
    updated["license_source_url"] = AISHELL4_SOURCE_URL
    updated["license_paper_url"] = AISHELL4_PAPER_URL
    updated["license_confirmation_status"] = "confirmed"
    updated["scaffold_note"] = (
        "AISHELL-4 license confirmed for research-only sanity-check mapping. "
        "No external audio has been downloaded or evaluated yet."
    )
    return updated


def write_mapping_artifacts(mapping: dict[str, Any]) -> tuple[Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    json_path = tables_dir / "external_validation_slice_mapping.json"
    csv_path = tables_dir / "external_validation_slice_mapping.csv"
    json_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    row = build_mapping_row(mapping)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAPPING_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    return csv_path, json_path


def build_receipt_rows(confirmation_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "license_confirmed",
            "confirmation_scope": "single_dataset_license_decision",
            "dataset_name": confirmation_row["dataset_name"],
            "license_status": confirmation_row["license_status"],
            "writeback_note": (
                "License confirmation recorded with source attribution. "
                "Audio staging remains optional; no gold benchmark claim."
            ),
        }
    ]


def build_summary_lines(confirmation_row: dict[str, str]) -> list[str]:
    return [
        "# External Validation License Confirmation (external/sanity-check)",
        "",
        "Label: `external/sanity-check` — documents a research-only license confirmation "
        f"for {confirmation_row['dataset_name']}. Does not claim benchmark execution.",
        "",
        "| dataset | license | status | scope | source |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| {confirmation_row['dataset_name']} | {confirmation_row['license_id']} | "
            f"{confirmation_row['confirmation_status']} | {confirmation_row['usage_scope']} | "
            f"{confirmation_row['source_url']} |"
        ),
        "",
        f"- Attribution: {confirmation_row['attribution_note']}",
        f"- Paper: {confirmation_row['paper_url']}",
    ]


def write_outputs(
    confirmation_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "external_validation_license_confirmation.csv"
    json_path = tables_dir / "external_validation_license_confirmation.json"
    md_path = figures_dir / "external_validation_license_confirmation.md"
    receipt_json_path = tables_dir / "external_validation_license_confirmation_receipt.json"
    receipt_md_path = figures_dir / "external_validation_license_confirmation_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONFIRMATION_COLUMNS)
        writer.writeheader()
        writer.writerow(confirmation_row)
    json_path.write_text(json.dumps(confirmation_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(build_summary_lines(confirmation_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt_md_path.write_text(
        "# External Validation License Confirmation Receipt\n\n"
        + json.dumps(receipt_rows, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def confirm_license() -> tuple[dict[str, str], dict[str, Any]]:
    mapping = load_slice_mapping()
    if not mapping:
        raise FileNotFoundError("external_validation_slice_mapping.json is missing")
    confirmation_row = build_confirmation_row(mapping)
    updated_mapping = apply_confirmation_to_mapping(mapping)
    write_mapping_artifacts(updated_mapping)
    receipt_rows = build_receipt_rows(confirmation_row)
    write_outputs(confirmation_row, receipt_rows)
    return confirmation_row, updated_mapping


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record AISHELL-4 research-only license confirmation for external sanity-check."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    confirmation_row, _ = confirm_license()
    print(f"Confirmed license for {confirmation_row['dataset_name']}: {confirmation_row['license_status']}")


if __name__ == "__main__":
    main()
