from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


EXECUTION_RECEIPT_BRIDGE_COLUMNS = [
    "recommended_frontier",
    "prerequisite_artifact",
    "execution_receipt_target",
    "bridge_note",
]


def load_runbook_bridge_rows() -> list[dict[str, str]]:
    path = (
        PROJECT_ROOT
        / "results"
        / "tables"
        / "meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist.json"
    )
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_execution_receipt_bridge_row(bridge_row: dict[str, str]) -> dict[str, str]:
    if not bridge_row:
        return {}
    frontier = str(bridge_row.get("recommended_frontier", "meeteval_compatibility"))
    receipt_target = str(
        bridge_row.get("execution_receipt_target", "results/tables/meeteval_cpwer_execution_receipt.json")
    )
    runbook_status = str(bridge_row.get("runbook_status", "tokenization_gain_frontier_fill_runbook_pending"))
    return {
        "recommended_frontier": frontier,
        "prerequisite_artifact": (
            "results/figures/meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist.md"
        ),
        "execution_receipt_target": receipt_target,
        "bridge_note": (
            f"After verifying runbook_status={runbook_status} for {frontier}, update execution_status in "
            f"{receipt_target}. No full MeetEval benchmark completion is claimed by this bridge alone."
        ),
    }


def build_execution_receipt_bridge_lines(row: dict[str, str]) -> list[str]:
    return [
        "# MeetEval Tokenization Gain Frontier Fill Execution Receipt Bridge",
        "",
        "This generated bridge connects the tokenization gain frontier fill runbook bridge checklist to the "
        "MeetEval execution receipt JSON target. It remains experimental/frontier coordination only.",
        "",
        "| recommended_frontier | prerequisite_artifact | execution_receipt_target | bridge_note |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['recommended_frontier']} | {row['prerequisite_artifact']} | "
            f"{row['execution_receipt_target']} | {row['bridge_note']} |"
        ),
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge.csv"
    json_path = tables_dir / "meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge.json"
    md_path = figures_dir / "meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXECUTION_RECEIPT_BRIDGE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_execution_receipt_bridge_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    bridge_rows = load_runbook_bridge_rows()
    row = build_execution_receipt_bridge_row(bridge_rows[0] if bridge_rows else {})
    if not row:
        print("Tokenization gain frontier fill runbook bridge checklist not found; execution receipt bridge not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote MeetEval tokenization gain frontier fill execution receipt bridge CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval tokenization gain frontier fill execution receipt bridge JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval tokenization gain frontier fill execution receipt bridge note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
