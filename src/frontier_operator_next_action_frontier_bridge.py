from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


FRONTIER_BRIDGE_COLUMNS = [
    "runbook_frontier",
    "frontier_queue_head",
    "bridge_reason",
    "bridge_note",
]


def load_runbook_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_operator_next_action_runbook_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_go_no_go_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_go_no_go_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_frontier_bridge_row(
    runbook_card: dict[str, str],
    go_no_go_summary: dict[str, str],
) -> dict[str, str]:
    if not runbook_card:
        return {}
    runbook_frontier = str(runbook_card.get("recommended_frontier", ""))
    queue_head = str(go_no_go_summary.get("highest_priority_ready_frontier", ""))
    aligned = runbook_frontier == queue_head and bool(runbook_frontier)
    return {
        "runbook_frontier": runbook_frontier,
        "frontier_queue_head": queue_head,
        "bridge_reason": (
            "The top-level operator runbook frontier aligns with the broader frontier ready queue head."
            if aligned
            else "The top-level operator runbook frontier does not align with the broader frontier ready queue head."
        ),
        "bridge_note": (
            f"Runbook recommends {runbook_frontier} while the broader frontier ready queue head is {queue_head}; "
            "this remains coordination-only and does not claim frontier execution."
        ),
    }


def build_frontier_bridge_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Operator Next-Action Frontier Bridge",
        "",
        "This generated bridge connects the top-level operator runbook card back to the broader frontier board. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        "| runbook_frontier | frontier_queue_head | bridge_reason | bridge_note |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['runbook_frontier']} | {row['frontier_queue_head']} | "
            f"{row['bridge_reason']} | {row['bridge_note']} |"
        ),
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_frontier_bridge.csv"
    json_path = tables_dir / "frontier_operator_next_action_frontier_bridge.json"
    md_path = figures_dir / "frontier_operator_next_action_frontier_bridge.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_BRIDGE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_bridge_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_frontier_bridge_row(load_runbook_card(), load_go_no_go_summary())
    if not row:
        print("Runbook card not found; frontier bridge not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(f"Wrote frontier operator next-action frontier bridge CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action frontier bridge JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action frontier bridge note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
