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
        "receipt_queue_operator_brief",
        "results/figures/frontier_execution_receipt_queue_operator_brief.md",
        "Plain-language operator summary for the current first receipt-queue target.",
    ),
    (
        "2",
        "receipt_queue_receipt_bridge",
        "results/figures/frontier_execution_receipt_queue_receipt_bridge.md",
        "Connects the operator brief to the current execution receipt target.",
    ),
    (
        "3",
        "receipt_queue_receipt_bridge_checklist",
        "results/figures/frontier_execution_receipt_queue_receipt_bridge_checklist.md",
        "Verifies the receipt bridge before the current execution receipt path is reopened.",
    ),
    (
        "4",
        "receipt_queue_evidence_receipt",
        "results/figures/frontier_execution_receipt_queue_evidence_receipt.md",
        "Records what evidence should be written back before the receipt stops being template-only.",
    ),
    (
        "5",
        "receipt_queue_evidence_receipt_bridge_checklist",
        "results/figures/frontier_execution_receipt_queue_evidence_receipt_bridge_checklist.md",
        "Verifies the evidence receipt before any execution receipt JSON is reopened.",
    ),
    (
        "6",
        "receipt_queue_execution_receipt_bridge",
        "results/figures/frontier_execution_receipt_queue_execution_receipt_bridge.md",
        "Connects the evidence receipt to the per-frontier execution receipt JSON target.",
    ),
    (
        "7",
        "receipt_queue_execution_receipt_bridge_checklist",
        "results/figures/frontier_execution_receipt_queue_execution_receipt_bridge_checklist.md",
        "Verifies the execution receipt bridge before the current JSON receipt is reopened.",
    ),
]


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_queue_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_packet_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    ready_count = str(summary.get("ready_receipt_count", "0"))
    pending_count = str(summary.get("pending_receipt_count", "0"))
    rows: list[dict[str, str]] = []
    for order, section_name, artifact_path, section_role in PACKET_SECTIONS:
        rows.append(
            {
                "packet_order": order,
                "section_name": section_name,
                "artifact_path": artifact_path,
                "section_role": section_role,
                "packet_note": (
                    f"Receipt queue writeback packet section while queue_status={queue_status}, "
                    f"ready_receipt_count={ready_count}, pending_receipt_count={pending_count}; "
                    "no benchmark execution is claimed until the JSON receipt is filled."
                ),
            }
        )
    return rows


def build_packet_lines(rows: list[dict[str, str]], summary: dict[str, str]) -> list[str]:
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    return [
        "# Frontier Execution Receipt Queue Writeback Packet",
        "",
        "This generated note provides a single entrypoint for the receipt-queue writeback stack. "
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

    csv_path = tables_dir / "frontier_execution_receipt_queue_writeback_packet.csv"
    json_path = tables_dir / "frontier_execution_receipt_queue_writeback_packet.json"
    md_path = figures_dir / "frontier_execution_receipt_queue_writeback_packet.md"

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
    print(f"Wrote frontier execution receipt queue writeback packet CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt queue writeback packet JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt queue writeback packet note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
