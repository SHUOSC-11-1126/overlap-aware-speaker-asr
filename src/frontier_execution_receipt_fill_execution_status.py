from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT
from .frontier_execution_receipt_fill_queue_status import (
    TEMPLATE_STATUSES,
    load_receipt_execution_status,
)


STATUS_COLUMNS = [
    "scope",
    "meeteval_fill_execution_status",
    "speaker_profile_fill_execution_status",
    "external_staging_fill_execution_status",
    "combined_fill_execution_status",
    "status_note",
]

RECEIPT_PATHS = {
    "meeteval_fill_execution_status": "results/tables/meeteval_cpwer_execution_receipt.json",
    "speaker_profile_fill_execution_status": "results/tables/speaker_profile_embedding_trial_execution_receipt.json",
    "external_staging_fill_execution_status": "results/tables/external_validation_slice_staging_handoff_receipt.json",
}


def derive_fill_execution_status(execution_status: str) -> str:
    if execution_status == "missing":
        return "receipt_missing"
    if execution_status in TEMPLATE_STATUSES:
        return "awaiting_fill"
    return "fill_complete"


def build_status_row() -> dict[str, str]:
    per_frontier = {
        key: derive_fill_execution_status(load_receipt_execution_status(path))
        for key, path in RECEIPT_PATHS.items()
    }
    statuses = list(per_frontier.values())
    if all(status == "awaiting_fill" for status in statuses):
        combined = "fill_execution_ready"
    elif all(status == "fill_complete" for status in statuses):
        combined = "fill_execution_complete"
    else:
        combined = "fill_execution_in_progress"
    return {
        "scope": "frontier_execution_receipt_fill_execution",
        "meeteval_fill_execution_status": per_frontier["meeteval_fill_execution_status"],
        "speaker_profile_fill_execution_status": per_frontier["speaker_profile_fill_execution_status"],
        "external_staging_fill_execution_status": per_frontier["external_staging_fill_execution_status"],
        "combined_fill_execution_status": combined,
        "status_note": (
            "Unified experimental/frontier receipt-fill execution rollup across MeetEval, speaker profile, "
            "and external staging; template-only receipts remain unfilled and no benchmark execution is claimed."
        ),
    }


def build_status_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Status",
        "",
        "This generated note records the unified frontier receipt-fill execution rollup. "
        "It remains coordination support only and does not claim benchmark completion.",
        "",
        "| scope | meeteval_fill_execution_status | speaker_profile_fill_execution_status | "
        "external_staging_fill_execution_status | combined_fill_execution_status | status_note |",
        "| --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['meeteval_fill_execution_status']} | "
            f"{row['speaker_profile_fill_execution_status']} | {row['external_staging_fill_execution_status']} | "
            f"{row['combined_fill_execution_status']} | {row['status_note']} |"
        ),
    ]
    return lines


def write_outputs(status_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_status.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_status.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_status.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STATUS_COLUMNS)
        writer.writeheader()
        writer.writerow(status_row)
    json_path.write_text(json.dumps(status_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_status_lines(status_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    status_row = build_status_row()
    csv_path, json_path, md_path = write_outputs(status_row)
    print(f"Wrote frontier execution receipt fill execution status CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt fill execution status JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt fill execution status note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Combined fill execution status: {status_row['combined_fill_execution_status']}")


if __name__ == "__main__":
    main()
