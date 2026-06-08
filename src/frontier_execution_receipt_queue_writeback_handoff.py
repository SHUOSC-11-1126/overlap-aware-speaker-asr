from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_order",
    "frontier_name",
    "writeback_status",
    "recommended_action",
    "expected_inputs",
    "expected_outputs",
    "handoff_note",
]

FRONTIER_HANDOFFS = [
    (
        "meeteval_compatibility",
        "meeteval_cpwer_execution_receipt.json",
        "results/tables/meeteval_cpwer_execution_receipt.json",
    ),
    (
        "speaker_profile",
        "speaker_profile_embedding_trial_execution_receipt.json",
        "results/tables/speaker_profile_embedding_trial_execution_receipt.json",
    ),
    (
        "external_validation",
        "external_validation_slice_staging_handoff_receipt.json",
        "results/tables/external_validation_slice_staging_handoff_receipt.json",
    ),
]


def load_status_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_queue_writeback_status.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_handoff_rows(status_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_frontier = {str(row.get("frontier_name", "")): row for row in status_rows}
    rows: list[dict[str, str]] = []
    for order, (frontier_name, receipt_name, receipt_path) in enumerate(FRONTIER_HANDOFFS, start=1):
        status_row = by_frontier.get(frontier_name, {})
        writeback_status = str(status_row.get("writeback_status", "receipt_missing"))
        if writeback_status == "awaiting_writeback":
            action = (
                f"Execute the real {frontier_name} writeback path, then update execution_status in {receipt_path} "
                "and attach the current evidence note."
            )
        elif writeback_status == "writeback_complete":
            action = f"Review the written-back receipt at {receipt_path} and archive the current evidence note."
        else:
            action = "Resolve receipt blockers before attempting writeback."
        rows.append(
            {
                "handoff_order": str(order),
                "frontier_name": frontier_name,
                "writeback_status": writeback_status,
                "recommended_action": action,
                "expected_inputs": (
                    "results/figures/frontier_execution_receipt_queue_writeback_status.md; "
                    "writeback packet and execution receipt bridge checklist."
                ),
                "expected_outputs": receipt_path,
                "handoff_note": (
                    f"Writeback handoff for {frontier_name} while writeback_status={writeback_status}; "
                    f"{receipt_name} remains explicitly labeled and no benchmark execution is claimed beyond the receipt contents."
                ),
            }
        )
    return rows


def build_handoff_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Queue Writeback Handoff",
        "",
        "This generated note turns the unified receipt-queue writeback status rollup into per-frontier writeback actions. "
        "It remains experimental/frontier coordination only and does not claim benchmark completion.",
        "",
        "| handoff_order | frontier_name | writeback_status | recommended_action | expected_inputs | expected_outputs | handoff_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['handoff_order']} | {row['frontier_name']} | {row['writeback_status']} | "
            f"{row['recommended_action']} | {row['expected_inputs']} | {row['expected_outputs']} | {row['handoff_note']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_queue_writeback_handoff.csv"
    json_path = tables_dir / "frontier_execution_receipt_queue_writeback_handoff.json"
    md_path = figures_dir / "frontier_execution_receipt_queue_writeback_handoff.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_handoff_rows(load_status_rows())
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote frontier execution receipt queue writeback handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt queue writeback handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt queue writeback handoff note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
