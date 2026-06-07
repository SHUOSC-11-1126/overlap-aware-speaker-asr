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


def load_review_pass_row() -> dict[str, str]:
    pass_path = PROJECT_ROOT / "results" / "tables" / "llm_critic_review_pass.json"
    if not pass_path.exists():
        return {}
    payload = json.loads(pass_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(pass_row: dict[str, str]) -> list[dict[str, str]]:
    case_id = str(pass_row.get("case_id", "HeavyOverlap"))
    review_priority = str(pass_row.get("review_priority", "high"))
    return [
        {
            "checklist_order": "1",
            "case_id": case_id,
            "prerequisite_artifact": "results/figures/llm_critic_review_pass.md",
            "receipt_target": "results/figures/llm_critic_review_receipt.md",
            "checklist_goal": (
                f"Verify the critic review pass bridge for {case_id} before any repair claim is advanced."
            ),
            "bridge_note": (
                f"Open the review pass note first, then write back through the receipt target for the "
                f"{review_priority} qualitative pass."
            ),
            "next_gate": "Confirm this bridge before opening the critic review receipt target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# LLM Critic Review Pass Bridge Checklist",
        "",
        "This generated checklist turns the first qualitative review pass into a row-by-row bridge verification path. "
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

    csv_path = tables_dir / "llm_critic_review_pass_bridge_checklist.csv"
    json_path = tables_dir / "llm_critic_review_pass_bridge_checklist.json"
    md_path = figures_dir / "llm_critic_review_pass_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    pass_row = load_review_pass_row()
    rows = build_bridge_checklist_rows(pass_row)
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote LLM critic review pass bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote LLM critic review pass bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
