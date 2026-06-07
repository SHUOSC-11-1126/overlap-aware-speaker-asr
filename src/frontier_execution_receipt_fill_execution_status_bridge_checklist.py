from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "combined_fill_execution_status",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_status_row() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_status.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(status_row: dict[str, str]) -> list[dict[str, str]]:
    combined = str(status_row.get("combined_fill_execution_status", "fill_execution_in_progress"))
    return [
        {
            "checklist_order": "1",
            "combined_fill_execution_status": combined,
            "prerequisite_artifact": "results/figures/frontier_execution_receipt_fill_execution_status.md",
            "receipt_target": "results/figures/frontier_execution_receipt_fill_execution_handoff.md",
            "checklist_goal": (
                "Verify the unified fill execution status rollup before opening the fill execution handoff."
            ),
            "bridge_note": (
                f"Status rollup reports combined_fill_execution_status={combined}; "
                "confirm fill execution readiness before advancing the fill execution handoff."
            ),
            "next_gate": "Confirm this bridge before opening the frontier execution receipt fill execution handoff target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Status Bridge Checklist",
        "",
        "This generated checklist turns the fill execution status rollup into a bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | combined_fill_execution_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['combined_fill_execution_status']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_status_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_status_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_status_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_status_row())
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote frontier execution receipt fill execution status bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution status bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution status bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
