from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "queue_status",
    "handoff_status",
    "case_scope",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_go_no_go_board_handoff_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(summary: dict[str, str]) -> list[dict[str, str]]:
    if not summary:
        return []
    queue_status = str(summary.get("queue_status", "queue_in_progress"))
    handoff_status = str(summary.get("handoff_status", "speaker_profile_go_handoff_pending"))
    case_scope = str(summary.get("case_scope", "NoOverlap"))
    return [
        {
            "checklist_order": "1",
            "queue_status": queue_status,
            "handoff_status": handoff_status,
            "case_scope": case_scope,
            "prerequisite_artifact": "results/figures/speaker_profile_go_no_go_board_handoff_completion_summary.md",
            "receipt_target": "results/figures/speaker_profile_embedding_trial_execution_scaffold_readiness.md",
            "checklist_goal": (
                "Verify go-no-go handoff completion before reopening the embedding trial execution scaffold readiness."
            ),
            "bridge_note": (
                f"Go-no-go handoff completion reports queue_status={queue_status} with handoff_status="
                f"{handoff_status} for {case_scope}; attribution claims remain blocked."
            ),
            "next_gate": (
                "Confirm this bridge before opening the speaker profile embedding trial execution scaffold readiness."
            ),
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Go-No-Go Board Handoff Completion Summary Bridge Checklist",
        "",
        "This generated checklist connects go-no-go handoff completion to the embedding trial execution scaffold readiness. "
        "It does not claim speaker identification success.",
        "",
        "| checklist_order | queue_status | handoff_status | case_scope | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['queue_status']} | {row['handoff_status']} | "
            f"{row['case_scope']} | {row['prerequisite_artifact']} | {row['receipt_target']} | "
            f"{row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_go_no_go_board_handoff_completion_summary_bridge_checklist.csv"
    json_path = tables_dir / "speaker_profile_go_no_go_board_handoff_completion_summary_bridge_checklist.json"
    md_path = figures_dir / "speaker_profile_go_no_go_board_handoff_completion_summary_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_completion_summary())
    if not rows:
        print("Speaker profile go-no-go handoff completion summary not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote speaker profile go-no-go handoff completion bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile go-no-go handoff completion bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile go-no-go handoff completion bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
