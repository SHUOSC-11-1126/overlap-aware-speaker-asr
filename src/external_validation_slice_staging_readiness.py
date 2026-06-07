from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


READINESS_COLUMNS = [
    "dataset_name",
    "slice_id",
    "label",
    "license_status",
    "staging_status",
    "readiness_status",
    "blocker",
    "readiness_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "readiness_scope",
    "dataset_name",
    "readiness_status",
    "writeback_note",
]


def load_slice_manifest() -> dict[str, Any]:
    manifest_path = PROJECT_ROOT / "results" / "tables" / "external_validation_slice_manifest.json"
    if not manifest_path.exists():
        return {}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_readiness_row(manifest: dict[str, Any]) -> dict[str, str]:
    license_status = str(manifest.get("license_status", "pending_confirmation"))
    staging_status = str(manifest.get("staging_status", "blocked_by_license_gate"))
    readiness_status = "not_ready" if license_status == "pending_confirmation" else "ready_for_staging_review"
    blocker = (
        "license_confirmation_pending"
        if license_status == "pending_confirmation"
        else "none_documented"
    )
    return {
        "dataset_name": str(manifest.get("dataset_name", "AISHELL-4")),
        "slice_id": str(manifest.get("slice_id", "")),
        "label": str(manifest.get("label", "external/sanity-check")),
        "license_status": license_status,
        "staging_status": staging_status,
        "readiness_status": readiness_status,
        "blocker": blocker,
        "readiness_note": (
            "Staging readiness audit for the first external slice. "
            "No external audio has been downloaded or evaluated."
        ),
    }


def build_readiness_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Readiness",
        "",
        "This generated note audits whether the first external slice is ready to move beyond manifest-only planning. "
        "It does not claim benchmark execution.",
        "",
        "| dataset_name | slice_id | label | license_status | staging_status | readiness_status | blocker | readiness_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['dataset_name']} | {row['slice_id']} | {row['label']} | {row['license_status']} | "
            f"{row['staging_status']} | {row['readiness_status']} | {row['blocker']} | {row['readiness_note']} |"
        ),
    ]
    return lines


def build_readiness_receipt_rows(readiness_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "readiness_documented",
            "readiness_scope": "single_short_meeting_excerpt",
            "dataset_name": str(readiness_row.get("dataset_name", "")),
            "readiness_status": str(readiness_row.get("readiness_status", "")),
            "writeback_note": (
                "Staging readiness documented; external audio staging remains blocked until license confirmation is recorded."
            ),
        }
    ]


def build_readiness_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Readiness Receipt",
        "",
        "This receipt records the staging readiness writeback. It does not claim external benchmark execution.",
        "",
        "| execution_status | readiness_scope | dataset_name | readiness_status | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['readiness_scope']} | {row['dataset_name']} | "
            f"{row['readiness_status']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    readiness_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "external_validation_slice_staging_readiness.csv"
    json_path = tables_dir / "external_validation_slice_staging_readiness.json"
    md_path = figures_dir / "external_validation_slice_staging_readiness.md"
    receipt_json_path = tables_dir / "external_validation_slice_staging_readiness_receipt.json"
    receipt_md_path = figures_dir / "external_validation_slice_staging_readiness_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=READINESS_COLUMNS)
        writer.writeheader()
        writer.writerow(readiness_row)
    json_path.write_text(json.dumps(readiness_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_readiness_lines(readiness_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_readiness_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    manifest = load_slice_manifest()
    readiness_row = build_readiness_row(manifest)
    receipt_rows = build_readiness_receipt_rows(readiness_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        readiness_row,
        receipt_rows,
    )
    print(f"Wrote external slice staging readiness CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice staging readiness JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external slice staging readiness note: {md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote external slice staging readiness receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external slice staging readiness receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
