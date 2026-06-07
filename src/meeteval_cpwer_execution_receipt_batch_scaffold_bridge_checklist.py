from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "preflight_pass_count",
    "scaffold_case_count",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_batch_scaffold_receipt() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_receipt_batch_scaffold_receipt.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        return payload[0] if isinstance(payload[0], dict) else {}
    return payload if isinstance(payload, dict) else {}


def load_batch_scaffold_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_receipt_batch_scaffold.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_bridge_checklist_rows(
    receipt: dict[str, str],
    scaffold_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not receipt:
        return []
    pass_count = sum(1 for row in scaffold_rows if row.get("preflight_pass") == "True")
    scaffold_count = str(len(scaffold_rows))
    return [
        {
            "checklist_order": "1",
            "preflight_pass_count": str(pass_count),
            "scaffold_case_count": scaffold_count,
            "prerequisite_artifact": "results/figures/meeteval_cpwer_execution_receipt_batch_scaffold.md",
            "receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
            "checklist_goal": (
                "Verify the batch execution receipt scaffold before opening the official cpWER execution receipt."
            ),
            "bridge_note": (
                f"Batch scaffold reports {pass_count}/{scaffold_count} cases with preflight_pass=True; "
                "confirm segment-export readiness before official cpWER execution."
            ),
            "next_gate": "Confirm this bridge before opening the official MeetEval cpWER execution receipt.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Receipt Batch Scaffold Bridge Checklist",
        "",
        "This generated checklist connects the batch execution receipt scaffold to the official execution receipt target. "
        "It does not claim cpWER execution.",
        "",
        "| checklist_order | preflight_pass_count | scaffold_case_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | ---: | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['preflight_pass_count']} | {row['scaffold_case_count']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_receipt_batch_scaffold_bridge_checklist.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_receipt_batch_scaffold_bridge_checklist.json"
    md_path = figures_dir / "meeteval_cpwer_execution_receipt_batch_scaffold_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(
        load_batch_scaffold_receipt(),
        load_batch_scaffold_rows(),
    )
    if not rows:
        print("Batch scaffold receipt not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote MeetEval cpWER execution receipt batch scaffold bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution receipt batch scaffold bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution receipt batch scaffold bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
