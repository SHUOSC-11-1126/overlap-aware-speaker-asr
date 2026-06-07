from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "case_id",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_advance_row() -> dict[str, str]:
    advance_path = PROJECT_ROOT / "results" / "tables" / "llm_critic_review_pass_advance.json"
    if not advance_path.exists():
        return {}
    payload = json.loads(advance_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(advance_row: dict[str, str]) -> list[dict[str, str]]:
    case_id = str(advance_row.get("case_id", "LightOverlap"))
    prior_pass_status = str(advance_row.get("prior_pass_status", "HeavyOverlap review_complete"))
    return [
        {
            "checklist_order": "1",
            "case_id": case_id,
            "prerequisite_artifact": "results/figures/llm_critic_review_pass_advance.md",
            "receipt_target": "results/figures/llm_critic_review_pass_advance_receipt.md",
            "checklist_goal": (
                f"Verify the second qualitative pass bridge for {case_id} before any repair claim is advanced."
            ),
            "bridge_note": (
                f"Queue advanced with prior_pass_status={prior_pass_status}; confirm the second pass note "
                "before opening the advance receipt target."
            ),
            "next_gate": "Confirm this bridge before opening the critic review pass advance receipt target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# LLM Critic Review Pass Advance Bridge Checklist",
        "",
        "This generated checklist turns the second qualitative pass into a row-by-row bridge verification path. "
        "It remains qualitative/demo only and does not claim verified transcript repair.",
        "",
        "| checklist_order | case_id | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['case_id']} | {row['prerequisite_artifact']} | "
            f"{row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "llm_critic_review_pass_advance_bridge_checklist.csv"
    json_path = tables_dir / "llm_critic_review_pass_advance_bridge_checklist.json"
    md_path = figures_dir / "llm_critic_review_pass_advance_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    advance_row = load_advance_row()
    rows = build_bridge_checklist_rows(advance_row)
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote LLM critic review pass advance bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote LLM critic review pass advance bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote LLM critic review pass advance bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
