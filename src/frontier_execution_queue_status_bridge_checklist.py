from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "combined_chain_status",
    "meeteval_chain_status",
    "speaker_profile_chain_status",
    "external_staging_chain_status",
    "llm_critic_chain_status",
    "demo_excellence_chain_status",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_status_row() -> dict[str, str]:
    status_path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_status.json"
    if not status_path.exists():
        return {}
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(status_row: dict[str, str]) -> list[dict[str, str]]:
    combined_status = str(status_row.get("combined_chain_status", "execution_chain_in_progress"))
    meeteval_status = str(status_row.get("meeteval_chain_status", "execution_chain_in_progress"))
    speaker_status = str(status_row.get("speaker_profile_chain_status", "execution_chain_in_progress"))
    external_status = str(status_row.get("external_staging_chain_status", "execution_chain_in_progress"))
    llm_status = str(status_row.get("llm_critic_chain_status", "execution_chain_in_progress"))
    demo_status = str(status_row.get("demo_excellence_chain_status", "execution_chain_in_progress"))
    return [
        {
            "checklist_order": "1",
            "combined_chain_status": combined_status,
            "meeteval_chain_status": meeteval_status,
            "speaker_profile_chain_status": speaker_status,
            "external_staging_chain_status": external_status,
            "llm_critic_chain_status": llm_status,
            "demo_excellence_chain_status": demo_status,
            "prerequisite_artifact": "results/figures/frontier_execution_queue_status.md",
            "receipt_target": "results/figures/meeteval_cpwer_execution_status_bridge_checklist.md",
            "checklist_goal": (
                "Verify the unified frontier execution-chain rollup before opening any per-frontier execution receipt."
            ),
            "bridge_note": (
                f"Combined rollup reports combined_chain_status={combined_status}; "
                f"meeteval={meeteval_status}, speaker_profile={speaker_status}, external_staging={external_status}, "
                f"llm_critic={llm_status}, demo_excellence={demo_status}."
            ),
            "next_gate": "Confirm this bridge before claiming any frontier benchmark execution.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Queue Status Bridge Checklist",
        "",
        "This generated checklist turns the unified frontier execution-chain rollup into a row-by-row bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim benchmark completion.",
        "",
        "| checklist_order | combined_chain_status | meeteval_chain_status | speaker_profile_chain_status | external_staging_chain_status | llm_critic_chain_status | demo_excellence_chain_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['combined_chain_status']} | {row['meeteval_chain_status']} | "
            f"{row['speaker_profile_chain_status']} | {row['external_staging_chain_status']} | "
            f"{row['llm_critic_chain_status']} | {row['demo_excellence_chain_status']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_status_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_queue_status_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_queue_status_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    status_row = load_status_row()
    rows = build_bridge_checklist_rows(status_row)
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote frontier execution queue status bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue status bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue status bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
