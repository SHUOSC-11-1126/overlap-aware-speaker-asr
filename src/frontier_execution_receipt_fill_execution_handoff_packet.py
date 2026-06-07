from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


HANDOFF_PACKET_COLUMNS = [
    "packet_section",
    "artifact_path",
    "section_role",
]


PACKET_SECTIONS = [
    ("dashboard", "results/figures/frontier_execution_receipt_fill_execution_completion_dashboard.md", "Top-level fill execution queue snapshot"),
    ("dashboard_bridge_checklist", "results/figures/frontier_execution_receipt_fill_execution_dashboard_bridge_checklist.md", "Dashboard to runbook verification"),
    ("meeteval_preflight_batch", "results/figures/meeteval_cpwer_execution_preflight_batch.md", "All-gold MeetEval cpWER execution preflight rollup"),
    ("meeteval_preflight_batch_bridge_checklist", "results/figures/meeteval_cpwer_execution_preflight_batch_bridge_checklist.md", "Batch preflight to official execution receipt verification"),
    ("meeteval_receipt_batch_scaffold", "results/figures/meeteval_cpwer_execution_receipt_batch_scaffold.md", "All-gold official cpWER execution receipt scaffold rollup"),
    ("meeteval_receipt_batch_scaffold_bridge_checklist", "results/figures/meeteval_cpwer_execution_receipt_batch_scaffold_bridge_checklist.md", "Batch receipt scaffold to official execution receipt verification"),
    ("meeteval_execution_status_batch", "results/figures/meeteval_cpwer_execution_status_batch.md", "All-gold MeetEval cpWER execution chain status rollup"),
    ("meeteval_execution_status_batch_bridge_checklist", "results/figures/meeteval_cpwer_execution_status_batch_bridge_checklist.md", "Batch execution status to official execution receipt verification"),
    ("frontier_bridge", "results/figures/frontier_execution_receipt_fill_execution_frontier_bridge.md", "Fill execution to breadth-first frontier queue bridge"),
    ("frontier_bridge_checklist", "results/figures/frontier_execution_receipt_fill_execution_frontier_bridge_checklist.md", "Frontier bridge verification path"),
    ("runbook", "results/figures/frontier_execution_receipt_fill_execution_runbook_card.md", "One-page first action execution card"),
    ("milestone", "results/figures/frontier_execution_receipt_fill_execution_milestone_card.md", "Immediate completion boundary"),
    ("entry", "results/figures/frontier_execution_receipt_fill_execution_completion_summary.md", "Queue completion status rollup"),
    ("handoff", "results/figures/frontier_execution_receipt_fill_execution_handoff.md", "Per-frontier fill execution actions"),
    ("operator", "results/figures/frontier_execution_receipt_fill_execution_operator_brief.md", "Plain-language operator next step"),
    ("receipt_bridge", "results/figures/frontier_execution_receipt_fill_execution_receipt_bridge.md", "Bridge to execution receipt target"),
    ("receipt_bridge_checklist", "results/figures/frontier_execution_receipt_fill_execution_receipt_bridge_checklist.md", "Ordered receipt writeback verification"),
    ("evidence_receipt", "results/figures/frontier_execution_receipt_fill_execution_evidence_receipt.md", "Fill execution writeback closeout card"),
    ("evidence_receipt_bridge_checklist", "results/figures/frontier_execution_receipt_fill_execution_evidence_receipt_bridge_checklist.md", "Handoff packet to evidence receipt verification"),
    ("runbook_bridge_checklist", "results/figures/frontier_execution_receipt_fill_execution_runbook_bridge_checklist.md", "Runbook card to evidence receipt verification"),
    ("phase_checkpoint", "results/figures/frontier_execution_receipt_fill_execution_phase_checkpoint_card.md", "Per-phase completion signal check"),
    ("execution_receipt_bridge", "results/figures/frontier_execution_receipt_fill_execution_execution_receipt_bridge.md", "Evidence receipt to JSON execution receipt bridge"),
    ("execution_receipt_bridge_checklist", "results/figures/frontier_execution_receipt_fill_execution_execution_receipt_bridge_checklist.md", "Ordered JSON receipt writeback verification"),
    ("status", "results/figures/frontier_execution_receipt_fill_execution_status.md", "Unified fill execution status rollup"),
    ("packet", "results/figures/frontier_execution_receipt_fill_execution_packet.md", "Earlier fill execution packet entrypoint"),
]


def build_handoff_packet_rows() -> list[dict[str, str]]:
    return [
        {
            "packet_section": section,
            "artifact_path": path,
            "section_role": role,
        }
        for section, path, role in PACKET_SECTIONS
    ]


def build_handoff_packet_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Handoff Packet",
        "",
        "This generated packet consolidates the fill execution coordination stack into one entrypoint. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| packet_section | artifact_path | section_role |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['packet_section']} | {row['artifact_path']} | {row['section_role']} |"
        )
    lines.extend(
        [
            "",
            "## Recommended first action",
            "",
            "1. Confirm the MeetEval preflight batch and its bridge checklist before any cpWER run.",
            "2. Open the runbook card for the current first frontier (`meeteval_compatibility`).",
            "3. Follow the execution receipt bridge checklist before updating the JSON receipt.",
            "4. Fill `results/tables/meeteval_cpwer_execution_receipt.json` only after a real frontier run.",
            "",
            "No benchmark execution or external audio staging is claimed until receipts are filled.",
        ]
    )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_handoff_packet.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_handoff_packet.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_handoff_packet.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_PACKET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_packet_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_handoff_packet_rows()
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote frontier execution receipt fill execution handoff packet CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution handoff packet JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution handoff packet note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
