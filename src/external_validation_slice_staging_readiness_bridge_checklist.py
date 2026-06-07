from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "readiness_status",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_readiness_row() -> dict[str, str]:
    readiness_path = PROJECT_ROOT / "results" / "tables" / "external_validation_slice_staging_readiness.json"
    if not readiness_path.exists():
        return {}
    payload = json.loads(readiness_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(readiness_row: dict[str, str]) -> list[dict[str, str]]:
    readiness_status = str(readiness_row.get("readiness_status", "not_ready"))
    blocker = str(readiness_row.get("blocker", "license_confirmation_pending"))
    return [
        {
            "checklist_order": "1",
            "readiness_status": readiness_status,
            "prerequisite_artifact": "results/figures/external_validation_slice_staging_readiness.md",
            "receipt_target": "results/figures/external_validation_slice_manifest_bridge_checklist.md",
            "checklist_goal": (
                "Verify the staging readiness bridge before advancing the slice manifest bridge checklist."
            ),
            "bridge_note": (
                f"Readiness remains {readiness_status} with blocker={blocker}; confirm license gate context first."
            ),
            "next_gate": "Confirm this bridge before opening the slice manifest bridge checklist target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Readiness Bridge Checklist",
        "",
        "This generated checklist turns the staging readiness audit into a row-by-row bridge verification path. "
        "It remains external/sanity-check coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | readiness_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['readiness_status']} | {row['prerequisite_artifact']} | "
            f"{row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "external_validation_slice_staging_readiness_bridge_checklist.csv"
    json_path = tables_dir / "external_validation_slice_staging_readiness_bridge_checklist.json"
    md_path = figures_dir / "external_validation_slice_staging_readiness_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    readiness_row = load_readiness_row()
    rows = build_bridge_checklist_rows(readiness_row)
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote external slice staging readiness bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external slice staging readiness bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external slice staging readiness bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
