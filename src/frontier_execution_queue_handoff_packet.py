from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


PACKET_COLUMNS = [
    "packet_order",
    "section_name",
    "artifact_path",
    "section_role",
    "packet_note",
]


PACKET_SECTIONS = [
    (
        "1",
        "execution_queue_status",
        "results/figures/frontier_execution_queue_status.md",
        "Unified frontier execution-chain status rollup across MeetEval, speaker profile, and external staging.",
    ),
    (
        "2",
        "execution_queue_status_bridge_checklist",
        "results/figures/frontier_execution_queue_status_bridge_checklist.md",
        "Verify the unified execution-chain rollup before opening per-frontier execution receipt paths.",
    ),
    (
        "3",
        "execution_queue_completion_summary",
        "results/figures/frontier_execution_queue_completion_summary.md",
        "Queue-level ready/pending count rollup for the unified execution coordination chain.",
    ),
    (
        "4",
        "execution_queue_completion_summary_bridge_checklist",
        "results/figures/frontier_execution_queue_completion_summary_bridge_checklist.md",
        "Verify queue-level completion state before opening the unified execution handoff.",
    ),
    (
        "5",
        "execution_queue_handoff",
        "results/figures/frontier_execution_queue_handoff.md",
        "Per-frontier execution handoff actions for MeetEval, speaker profile, and external validation.",
    ),
    (
        "6",
        "execution_queue_operator_brief",
        "results/figures/frontier_execution_queue_operator_brief.md",
        "Plain-language operator summary for the current first execution-queue target.",
    ),
    (
        "7",
        "execution_queue_runbook_card",
        "results/figures/frontier_execution_queue_runbook_card.md",
        "One-page first-action execution card for the current first execution-queue target.",
    ),
    (
        "8",
        "execution_queue_runbook_bridge_checklist",
        "results/figures/frontier_execution_queue_runbook_bridge_checklist.md",
        "Verify the runbook card before opening the current execution queue receipt target.",
    ),
    (
        "9",
        "execution_queue_phase_checkpoint_card",
        "results/figures/frontier_execution_queue_phase_checkpoint_card.md",
        "Narrow completion checkpoint for the current first execution-queue action.",
    ),
    (
        "10",
        "execution_queue_phase_checkpoint_bridge_checklist",
        "results/figures/frontier_execution_queue_phase_checkpoint_bridge_checklist.md",
        "Verify the phase checkpoint card before reopening the current execution queue milestone card.",
    ),
    (
        "11",
        "execution_queue_milestone_card",
        "results/figures/frontier_execution_queue_milestone_card.md",
        "Immediate milestone boundary and next unlock for the current first execution-queue action.",
    ),
    (
        "12",
        "execution_queue_milestone_bridge_checklist",
        "results/figures/frontier_execution_queue_milestone_bridge_checklist.md",
        "Verify the milestone card before reopening the current execution queue completion dashboard.",
    ),
    (
        "13",
        "execution_queue_completion_dashboard",
        "results/figures/frontier_execution_queue_completion_dashboard.md",
        "One-glance operator-facing dashboard for the current execution queue state.",
    ),
    (
        "14",
        "execution_queue_completion_dashboard_bridge_checklist",
        "results/figures/frontier_execution_queue_completion_dashboard_bridge_checklist.md",
        "Verify the completion dashboard before reopening the current execution queue runbook card.",
    ),
    (
        "15",
        "execution_queue_status_preflight_bridge_checklist",
        "results/figures/frontier_execution_queue_status_preflight_bridge_checklist.md",
        "Verify the completion-dashboard bridge before reopening the execution queue status rollup.",
    ),
    (
        "16",
        "execution_queue_handoff_bridge_checklist",
        "results/figures/frontier_execution_queue_handoff_bridge_checklist.md",
        "Verify each execution handoff before opening the receipt target for that frontier.",
    ),
]


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_packet_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    ready_count = str(summary.get("ready_chain_count", "0"))
    pending_count = str(summary.get("pending_chain_count", "0"))
    rows: list[dict[str, str]] = []
    for order, section_name, artifact_path, section_role in PACKET_SECTIONS:
        rows.append(
            {
                "packet_order": order,
                "section_name": section_name,
                "artifact_path": artifact_path,
                "section_role": section_role,
                "packet_note": (
                    f"Execution queue packet section while queue_status={queue_status}, "
                    f"ready_chain_count={ready_count}, pending_chain_count={pending_count}; "
                    "no benchmark execution or external audio staging is claimed."
                ),
            }
        )
    return rows


def build_packet_lines(rows: list[dict[str, str]], summary: dict[str, str]) -> list[str]:
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    return [
        "# Frontier Execution Queue Handoff Packet",
        "",
        "This generated note provides a single entrypoint for the frontier execution queue stack. "
        "It remains experimental/frontier coordination only and does not claim benchmark completion.",
        "",
        f"Current rollup: `queue_status = {queue_status}`.",
        "",
        "| packet_order | section_name | artifact_path | section_role | packet_note |",
        "| --- | --- | --- | --- | --- |",
        *[
            f"| {row['packet_order']} | {row['section_name']} | {row['artifact_path']} | "
            f"{row['section_role']} | {row['packet_note']} |"
            for row in rows
        ],
    ]


def write_outputs(rows: list[dict[str, str]], summary: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_handoff_packet.csv"
    json_path = tables_dir / "frontier_execution_queue_handoff_packet.json"
    md_path = figures_dir / "frontier_execution_queue_handoff_packet.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PACKET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_packet_lines(rows, summary)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    summary = load_completion_summary()
    rows = build_packet_rows(summary)
    csv_path, json_path, md_path = write_outputs(rows, summary)
    print(f"Wrote frontier execution queue handoff packet CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue handoff packet JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue handoff packet note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
