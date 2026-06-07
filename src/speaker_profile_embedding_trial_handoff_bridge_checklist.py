from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "case_id",
    "trial_status",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_embedding_trial() -> dict[str, str]:
    trial_path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial.json"
    if not trial_path.exists():
        return {}
    payload = json.loads(trial_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(trial_row: dict[str, str]) -> list[dict[str, str]]:
    case_id = str(trial_row.get("case_id", "NoOverlap"))
    trial_status = str(trial_row.get("trial_status", "scaffold_only"))
    profile_confidence_gap = str(trial_row.get("profile_confidence_gap", "0.0"))
    return [
        {
            "checklist_order": "1",
            "case_id": case_id,
            "trial_status": trial_status,
            "prerequisite_artifact": "results/figures/speaker_profile_embedding_trial.md",
            "receipt_target": "results/figures/speaker_profile_embedding_trial_handoff.md",
            "checklist_goal": (
                f"Verify the embedding trial scaffold bridge for {case_id} before reopening stronger-method execution."
            ),
            "bridge_note": (
                f"Embedding trial remains {trial_status} with profile_confidence_gap={profile_confidence_gap}; "
                "confirm scaffold context before advancing to voiceprint execution."
            ),
            "next_gate": "Confirm this bridge before opening a stronger speaker-profile method execution target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Handoff Bridge Checklist",
        "",
        "This generated checklist turns the embedding trial scaffold into a row-by-row bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim voiceprint success.",
        "",
        "| checklist_order | case_id | trial_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['case_id']} | {row['trial_status']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_handoff_bridge_checklist.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_handoff_bridge_checklist.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_handoff_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    trial_row = load_embedding_trial()
    rows = build_bridge_checklist_rows(trial_row)
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote speaker profile embedding trial handoff bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial handoff bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial handoff bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
