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
    ("entry", "results/figures/frontier_execution_receipt_fill_execution_completion_summary.md", "Start here for queue completion status"),
    ("handoff", "results/figures/frontier_execution_receipt_fill_execution_handoff.md", "Per-frontier fill execution actions"),
    ("operator", "results/figures/frontier_execution_receipt_fill_execution_operator_brief.md", "Plain-language operator next step"),
    ("receipt_bridge", "results/figures/frontier_execution_receipt_fill_execution_receipt_bridge.md", "Bridge to execution receipt target"),
    ("receipt_bridge_checklist", "results/figures/frontier_execution_receipt_fill_execution_receipt_bridge_checklist.md", "Ordered receipt writeback verification"),
    ("status", "results/figures/frontier_execution_receipt_fill_execution_status.md", "Unified fill execution status rollup"),
    ("packet", "results/figures/frontier_execution_receipt_fill_execution_packet.md", "Single-entry fill execution packet"),
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
            "1. Read the operator brief for the current first frontier (`meeteval_compatibility`).",
            "2. Follow the receipt bridge checklist before updating the execution receipt.",
            "3. Fill `results/tables/meeteval_cpwer_execution_receipt.json` only after a real frontier run.",
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
