from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


FRONTIER_BRIDGE_COLUMNS = [
    "receipt_queue_frontier",
    "frontier_queue_head",
    "bridge_reason",
    "bridge_note",
]


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_queue_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_frontier_queue_head() -> str:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue.json"
    if not path.exists():
        return "meeteval_compatibility"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        return str(payload[0].get("frontier_id", "meeteval_compatibility"))
    return "meeteval_compatibility"


def build_frontier_bridge_row(operator_brief: dict[str, str], queue_head: str) -> dict[str, str]:
    if not operator_brief:
        return {}
    frontier = str(operator_brief.get("operator_frontier", "unknown"))
    return {
        "receipt_queue_frontier": frontier,
        "frontier_queue_head": queue_head,
        "bridge_reason": (
            "The receipt queue head aligns with the breadth-first frontier queue head for the current first frontier."
        ),
        "bridge_note": (
            f"Receipt queue recommends {frontier} while the frontier queue head is {queue_head}; "
            "no benchmark execution is claimed until receipts are updated after real runs."
        ),
    }


def build_frontier_bridge_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Execution Receipt Queue Frontier Bridge",
        "",
        "This generated bridge connects the receipt queue coordination stack to the broader breadth-first frontier queue. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| receipt_queue_frontier | frontier_queue_head | bridge_reason | bridge_note |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['receipt_queue_frontier']} | {row['frontier_queue_head']} | "
            f"{row['bridge_reason']} | {row['bridge_note']} |"
        ),
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_queue_frontier_bridge.csv"
    json_path = tables_dir / "frontier_execution_receipt_queue_frontier_bridge.json"
    md_path = figures_dir / "frontier_execution_receipt_queue_frontier_bridge.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FRONTIER_BRIDGE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_frontier_bridge_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_frontier_bridge_row(load_operator_brief(), load_frontier_queue_head())
    if not row:
        print("Receipt queue operator brief not found; frontier bridge not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier execution receipt queue frontier bridge CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue frontier bridge JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue frontier bridge note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
