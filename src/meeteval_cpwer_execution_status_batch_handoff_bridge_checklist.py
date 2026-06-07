from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "handoff_ready_count",
    "handoff_total_count",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_handoff_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_status_batch_handoff.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_bridge_checklist_rows(handoff_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not handoff_rows:
        return []
    ready_count = sum(1 for row in handoff_rows if row.get("handoff_status") == "execution_handoff_ready")
    total_count = len(handoff_rows)
    first_case = next(
        (row.get("case_id", "NoOverlap") for row in handoff_rows if row.get("handoff_status") == "execution_handoff_ready"),
        handoff_rows[0].get("case_id", "NoOverlap"),
    )
    return [
        {
            "checklist_order": "1",
            "handoff_ready_count": str(ready_count),
            "handoff_total_count": str(total_count),
            "prerequisite_artifact": "results/figures/meeteval_cpwer_execution_status_batch_handoff.md",
            "receipt_target": "results/tables/meeteval_cpwer_official_execution.json",
            "checklist_goal": (
                f"Verify the batch execution handoff before running official MeetEval cpWER for {first_case}."
            ),
            "bridge_note": (
                f"Batch handoff reports {ready_count}/{total_count} ready actions with first target {first_case}; "
                "confirm handoff alignment before official cpWER narrow dry run."
            ),
            "next_gate": "Confirm this bridge before running meeteval_cpwer_official_execution.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Status Batch Handoff Bridge Checklist",
        "",
        "This generated checklist connects the batch execution handoff to the official cpWER execution target. "
        "It does not claim cpWER execution.",
        "",
        "| checklist_order | handoff_ready_count | handoff_total_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['handoff_ready_count']} | {row['handoff_total_count']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_status_batch_handoff_bridge_checklist.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_status_batch_handoff_bridge_checklist.json"
    md_path = figures_dir / "meeteval_cpwer_execution_status_batch_handoff_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_handoff_rows())
    if not rows:
        print("Batch handoff not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote MeetEval cpWER execution status batch handoff bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch handoff bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution status batch handoff bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
