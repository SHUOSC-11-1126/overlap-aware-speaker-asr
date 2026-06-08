from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "queue_status",
    "ready_receipt_count",
    "pending_receipt_count",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_queue_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    ready_count = str(summary.get("ready_receipt_count", "0"))
    pending_count = str(summary.get("pending_receipt_count", "0"))
    return [
        {
            "checklist_order": "1",
            "queue_status": queue_status,
            "ready_receipt_count": ready_count,
            "pending_receipt_count": pending_count,
            "prerequisite_artifact": "results/figures/frontier_execution_receipt_queue_writeback_packet.md",
            "receipt_target": "results/figures/frontier_execution_receipt_queue_operator_brief.md",
            "checklist_goal": (
                "Verify the receipt queue writeback packet before opening the current operator brief."
            ),
            "bridge_note": (
                f"Receipt queue summary reports queue_status={queue_status}, ready_receipt_count={ready_count}, "
                f"pending_receipt_count={pending_count}; confirm writeback packet context before reopening the operator brief."
            ),
            "next_gate": "Confirm this bridge before opening the frontier execution receipt queue operator brief target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Queue Writeback Packet Bridge Checklist",
        "",
        "This generated checklist turns the receipt queue writeback packet into a bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | queue_status | ready_receipt_count | pending_receipt_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['queue_status']} | {row['ready_receipt_count']} | "
            f"{row['pending_receipt_count']} | {row['prerequisite_artifact']} | {row['receipt_target']} | "
            f"{row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_queue_writeback_packet_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_receipt_queue_writeback_packet_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_receipt_queue_writeback_packet_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_completion_summary())
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote frontier execution receipt queue writeback packet bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue writeback packet bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue writeback packet bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
