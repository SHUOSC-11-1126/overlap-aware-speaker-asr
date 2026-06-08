from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "frontier_name",
    "writeback_status",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_open_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_queue_writeback_open_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(open_card: dict[str, str]) -> list[dict[str, str]]:
    if not open_card:
        return []
    frontier_name = str(open_card.get("frontier_name", "unknown"))
    writeback_status = str(open_card.get("writeback_status", "receipt_missing"))
    receipt_target = str(open_card.get("receipt_target", ""))
    return [
        {
            "checklist_order": "1",
            "frontier_name": frontier_name,
            "writeback_status": writeback_status,
            "prerequisite_artifact": "results/figures/frontier_execution_receipt_queue_writeback_open_card.md",
            "receipt_target": receipt_target,
            "checklist_goal": (
                f"Verify the writeback open card for {frontier_name} before opening the execution receipt."
            ),
            "bridge_note": (
                f"Open card reports writeback_status={writeback_status} for {frontier_name}; "
                "confirm open-card context before reopening the execution receipt."
            ),
            "next_gate": f"Confirm this bridge before opening {receipt_target}.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Queue Writeback Open Card Bridge Checklist",
        "",
        "This generated checklist turns the receipt queue writeback open card into an ordered verification path. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | frontier_name | writeback_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['frontier_name']} | {row['writeback_status']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_queue_writeback_open_card_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_receipt_queue_writeback_open_card_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_receipt_queue_writeback_open_card_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_open_card())
    if not rows:
        print("Writeback open card not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote frontier execution receipt queue writeback open card bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue writeback open card bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue writeback open card bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
