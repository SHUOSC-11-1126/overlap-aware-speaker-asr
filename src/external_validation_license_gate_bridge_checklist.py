from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "dataset_name",
    "license_status",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_license_gate_row() -> dict[str, str]:
    gate_path = PROJECT_ROOT / "results" / "tables" / "external_validation_license_gate.csv"
    if not gate_path.exists():
        return {}
    with gate_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return row
    return {}


def build_bridge_checklist_rows(gate_row: dict[str, str]) -> list[dict[str, str]]:
    dataset_name = str(gate_row.get("dataset_name", "AISHELL-4"))
    license_status = str(gate_row.get("license_status", "pending_confirmation"))
    return [
        {
            "checklist_order": "1",
            "dataset_name": dataset_name,
            "license_status": license_status,
            "prerequisite_artifact": "results/figures/external_validation_license_gate.md",
            "receipt_target": "results/figures/external_validation_slice_manifest.md",
            "checklist_goal": (
                f"Verify the license gate bridge for {dataset_name} before advancing slice manifest staging."
            ),
            "bridge_note": (
                f"License status remains {license_status}; confirm gate steps before opening the slice manifest target."
            ),
            "next_gate": "Confirm this bridge before opening the external slice manifest target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation License Gate Bridge Checklist",
        "",
        "This generated checklist turns the license gate into a row-by-row bridge verification path. "
        "It remains external/sanity-check coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | dataset_name | license_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['dataset_name']} | {row['license_status']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "external_validation_license_gate_bridge_checklist.csv"
    json_path = tables_dir / "external_validation_license_gate_bridge_checklist.json"
    md_path = figures_dir / "external_validation_license_gate_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    gate_row = load_license_gate_row()
    rows = build_bridge_checklist_rows(gate_row)
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote external validation license gate bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external validation license gate bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external validation license gate bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
