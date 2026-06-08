from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "recommended_frontier",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_runbook_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_queue_runbook_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def extract_receipt_target(completion_signal: str) -> str:
    match = re.search(r"(results/tables/[A-Za-z0-9_./-]+\.json)", completion_signal)
    return match.group(1) if match else ""


def build_bridge_checklist_rows(runbook: dict[str, str]) -> list[dict[str, str]]:
    if not runbook:
        return []
    frontier = str(runbook.get("recommended_frontier", "unknown"))
    receipt_target = extract_receipt_target(str(runbook.get("completion_signal", "")))
    return [
        {
            "checklist_order": "1",
            "recommended_frontier": frontier,
            "prerequisite_artifact": "results/figures/frontier_execution_receipt_queue_runbook_card.md",
            "receipt_target": receipt_target or "results/tables/execution_receipt.json",
            "checklist_goal": (
                f"Verify the receipt queue runbook card for {frontier} before opening the receipt target."
            ),
            "bridge_note": str(runbook.get("runbook_note", "")),
            "next_gate": "Confirm this bridge before opening the receipt queue receipt target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    return [
        "# Frontier Execution Receipt Queue Runbook Bridge Checklist",
        "",
        "This generated checklist connects the receipt queue runbook card to the receipt target. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | recommended_frontier | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        *[
            f"| {row['checklist_order']} | {row['recommended_frontier']} | {row['prerequisite_artifact']} | "
            f"{row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
            for row in rows
        ],
    ]


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_queue_runbook_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_receipt_queue_runbook_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_receipt_queue_runbook_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_runbook_card())
    if not rows:
        print("Receipt queue runbook card not found; runbook bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote frontier execution receipt queue runbook bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue runbook bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue runbook bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
