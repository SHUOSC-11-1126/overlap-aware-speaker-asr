from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "preflight_pass_count",
    "preflight_total_count",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_batch_receipt() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_preflight_batch_receipt.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        return payload[0] if isinstance(payload[0], dict) else {}
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(receipt: dict[str, str]) -> list[dict[str, str]]:
    if not receipt:
        return []
    pass_count = str(receipt.get("preflight_pass_count", "0"))
    total_count = str(receipt.get("preflight_total_count", "0"))
    return [
        {
            "checklist_order": "1",
            "preflight_pass_count": pass_count,
            "preflight_total_count": total_count,
            "prerequisite_artifact": "results/figures/meeteval_cpwer_execution_preflight_batch.md",
            "receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
            "checklist_goal": (
                "Verify the batch execution preflight before opening the official cpWER execution receipt."
            ),
            "bridge_note": (
                f"Batch preflight reports {pass_count}/{total_count} cases passed; "
                "confirm segment-export readiness before official cpWER execution."
            ),
            "next_gate": "Confirm this bridge before opening the official MeetEval cpWER execution receipt.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Preflight Batch Bridge Checklist",
        "",
        "This generated checklist connects the batch preflight to the official execution receipt target. "
        "It does not claim cpWER execution.",
        "",
        "| checklist_order | preflight_pass_count | preflight_total_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['preflight_pass_count']} | {row['preflight_total_count']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_preflight_batch_bridge_checklist.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_preflight_batch_bridge_checklist.json"
    md_path = figures_dir / "meeteval_cpwer_execution_preflight_batch_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_batch_receipt())
    if not rows:
        print("Batch preflight receipt not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote MeetEval cpWER execution preflight batch bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution preflight batch bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution preflight batch bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
