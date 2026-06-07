from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


EXECUTION_RECEIPT_BRIDGE_COLUMNS = [
    "receipt_frontier",
    "prerequisite_artifact",
    "execution_receipt_target",
    "bridge_note",
]


def load_evidence_receipt() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_evidence_receipt.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_execution_receipt_bridge_row(
    evidence_receipt: dict[str, str],
    operator_brief: dict[str, str],
) -> dict[str, str]:
    if not evidence_receipt:
        return {}
    frontier = str(evidence_receipt.get("receipt_frontier", "unknown"))
    execution_target = str(operator_brief.get("operator_receipt", ""))
    return {
        "receipt_frontier": frontier,
        "prerequisite_artifact": "results/figures/frontier_execution_receipt_fill_execution_evidence_receipt.md",
        "execution_receipt_target": execution_target,
        "bridge_note": (
            f"After verifying the evidence receipt for {frontier}, update execution_status in {execution_target}. "
            "No benchmark execution is claimed until the JSON receipt is filled."
        ),
    }


def build_execution_receipt_bridge_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Execution Receipt Bridge",
        "",
        "This generated bridge connects the evidence receipt to the per-frontier execution receipt JSON target. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| receipt_frontier | prerequisite_artifact | execution_receipt_target | bridge_note |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['receipt_frontier']} | {row['prerequisite_artifact']} | "
            f"{row['execution_receipt_target']} | {row['bridge_note']} |"
        ),
    ]
    return lines


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_execution_receipt_bridge.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_execution_receipt_bridge.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_execution_receipt_bridge.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXECUTION_RECEIPT_BRIDGE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_execution_receipt_bridge_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_execution_receipt_bridge_row(load_evidence_receipt(), load_operator_brief())
    if not row:
        print("Evidence receipt not found; execution receipt bridge not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier execution receipt fill execution execution receipt bridge CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution execution receipt bridge JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution execution receipt bridge note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
