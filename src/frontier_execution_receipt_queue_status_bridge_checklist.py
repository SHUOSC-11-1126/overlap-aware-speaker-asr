from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "combined_readiness_status",
    "meeteval_readiness_status",
    "speaker_profile_readiness_status",
    "external_staging_readiness_status",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_status_row() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_queue_status.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(status_row: dict[str, str]) -> list[dict[str, str]]:
    combined = str(status_row.get("combined_readiness_status", "receipt_not_ready"))
    meeteval = str(status_row.get("meeteval_readiness_status", "receipt_not_ready"))
    speaker = str(status_row.get("speaker_profile_readiness_status", "receipt_not_ready"))
    external = str(status_row.get("external_staging_readiness_status", "receipt_not_ready"))
    return [
        {
            "checklist_order": "1",
            "combined_readiness_status": combined,
            "meeteval_readiness_status": meeteval,
            "speaker_profile_readiness_status": speaker,
            "external_staging_readiness_status": external,
            "prerequisite_artifact": "results/figures/frontier_execution_receipt_queue_status.md",
            "receipt_target": "results/figures/frontier_execution_receipt_queue_completion_summary.md",
            "checklist_goal": (
                "Verify the unified frontier receipt readiness rollup before opening the completion summary."
            ),
            "bridge_note": (
                f"Receipt rollup reports combined_readiness_status={combined}; "
                f"meeteval={meeteval}, speaker_profile={speaker}, external_staging={external}."
            ),
            "next_gate": "Confirm this bridge before opening the frontier execution receipt completion summary.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Queue Status Bridge Checklist",
        "",
        "This generated checklist turns the unified frontier receipt readiness rollup into a bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | combined_readiness_status | meeteval_readiness_status | speaker_profile_readiness_status | external_staging_readiness_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['combined_readiness_status']} | {row['meeteval_readiness_status']} | "
            f"{row['speaker_profile_readiness_status']} | {row['external_staging_readiness_status']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_queue_status_bridge_checklist.csv"
    json_path = tables_dir / "frontier_execution_receipt_queue_status_bridge_checklist.json"
    md_path = figures_dir / "frontier_execution_receipt_queue_status_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_status_row())
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote frontier execution receipt queue status bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt queue status bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt queue status bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
