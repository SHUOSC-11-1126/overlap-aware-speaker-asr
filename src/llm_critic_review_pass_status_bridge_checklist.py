from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "next_case_id",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_status_summary() -> dict[str, str]:
    summary_path = PROJECT_ROOT / "results" / "tables" / "llm_critic_review_pass_status_summary.json"
    if not summary_path.exists():
        return {}
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    next_case_id = str(summary.get("next_case_id", "MidOverlap"))
    completed_count = str(summary.get("completed_count", "0"))
    pending_count = str(summary.get("pending_count", "0"))
    return [
        {
            "checklist_order": "1",
            "next_case_id": next_case_id,
            "prerequisite_artifact": "results/figures/llm_critic_review_pass_status.md",
            "receipt_target": "results/figures/llm_critic_review_pass_next_receipt.md",
            "checklist_goal": (
                f"Verify the review pass status bridge before advancing the next qualitative pass for {next_case_id}."
            ),
            "bridge_note": (
                f"Status rollup reports completed={completed_count}, pending={pending_count}; "
                f"confirm queue state before opening the next pass receipt target."
            ),
            "next_gate": "Confirm this bridge before opening the critic review pass next receipt target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# LLM Critic Review Pass Status Bridge Checklist",
        "",
        "This generated checklist turns the pass status rollup into a row-by-row bridge verification path. "
        "It remains qualitative/demo only and does not claim verified transcript repair.",
        "",
        "| checklist_order | next_case_id | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['next_case_id']} | {row['prerequisite_artifact']} | "
            f"{row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "llm_critic_review_pass_status_bridge_checklist.csv"
    json_path = tables_dir / "llm_critic_review_pass_status_bridge_checklist.json"
    md_path = figures_dir / "llm_critic_review_pass_status_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    summary = load_status_summary()
    rows = build_bridge_checklist_rows(summary)
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote LLM critic review pass status bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote LLM critic review pass status bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote LLM critic review pass status bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
