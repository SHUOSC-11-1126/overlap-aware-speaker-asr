from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


RECEIPT_BRIDGE_COLUMNS = [
    "operator_frontier",
    "prerequisite_artifact",
    "receipt_target",
    "bridge_note",
]


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_receipt_bridge_row(operator_brief: dict[str, str]) -> dict[str, str]:
    if not operator_brief:
        return {}
    frontier = str(operator_brief.get("operator_frontier", "unknown"))
    receipt_target = str(operator_brief.get("operator_receipt", ""))
    return {
        "operator_frontier": frontier,
        "prerequisite_artifact": "results/figures/frontier_execution_receipt_fill_execution_operator_brief.md",
        "receipt_target": receipt_target,
        "bridge_note": (
            f"Open the operator brief first, then write back through {receipt_target} "
            f"after the real {frontier} frontier run. No benchmark execution is claimed by this bridge alone."
        ),
    }


def build_receipt_bridge_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Receipt Bridge",
        "",
        "This generated bridge connects the fill execution operator brief to the current execution receipt target. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| operator_frontier | prerequisite_artifact | receipt_target | bridge_note |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['operator_frontier']} | {row['prerequisite_artifact']} | {row['receipt_target']} | "
            f"{row['bridge_note']} |"
        ),
    ]
    return lines


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_receipt_bridge.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_receipt_bridge.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_receipt_bridge.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RECEIPT_BRIDGE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_receipt_bridge_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_receipt_bridge_row(load_operator_brief())
    if not row:
        print("Operator brief not found; receipt bridge not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier execution receipt fill execution receipt bridge CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution receipt bridge JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution receipt bridge note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
