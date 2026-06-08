from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "current_case",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_dashboard_bridge_rows() -> list[dict[str, str]]:
    path = (
        PROJECT_ROOT
        / "results"
        / "tables"
        / "speaker_profile_embedding_trial_execution_receipt_completion_dashboard_bridge_checklist.json"
    )
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_bridge_checklist_rows(dashboard_bridge_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not dashboard_bridge_rows:
        return []
    dashboard_bridge = dashboard_bridge_rows[0]
    current_case = str(dashboard_bridge.get("current_case", "unknown"))
    prior_gate = str(dashboard_bridge.get("next_gate", ""))
    return [
        {
            "checklist_order": "1",
            "current_case": current_case,
            "prerequisite_artifact": "results/figures/speaker_profile_embedding_trial_execution_receipt_completion_dashboard_bridge_checklist.md",
            "receipt_target": "results/figures/speaker_profile_embedding_trial_execution_status.md",
            "checklist_goal": (
                f"Verify the speaker-profile completion-dashboard bridge for {current_case} before opening the status rollup."
            ),
            "bridge_note": (
                f"Dashboard bridge remains aligned to {current_case}; prior gate was: {prior_gate} "
                "Confirm that bridge context before opening the machine-readable speaker-profile status rollup."
            ),
            "next_gate": "Confirm this bridge before opening the speaker-profile status rollup target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    return [
        "# Speaker Profile Embedding Trial Execution Receipt Status Preflight Bridge Checklist",
        "",
        "This generated checklist connects the completion-dashboard bridge layer to the speaker-profile status rollup. "
        "It remains experimental/frontier coordination only and does not fill receipts or claim voiceprint success.",
        "",
        "| checklist_order | current_case | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        *[
            f"| {row['checklist_order']} | {row['current_case']} | {row['prerequisite_artifact']} | "
            f"{row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
            for row in rows
        ],
    ]


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_status_preflight_bridge_checklist.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_status_preflight_bridge_checklist.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_receipt_status_preflight_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_dashboard_bridge_rows())
    if not rows:
        print("Speaker-profile receipt completion dashboard bridge checklist not found; status preflight not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote speaker profile embedding trial execution receipt status preflight bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt status preflight bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt status preflight bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
