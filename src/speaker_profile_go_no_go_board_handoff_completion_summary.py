from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


COMPLETION_COLUMNS = [
    "scope",
    "handoff_status",
    "overall_state",
    "go_count",
    "checkpoint_count",
    "case_scope",
    "queue_status",
    "observation",
]


def load_handoff() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_go_no_go_board_handoff.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_completion_row(handoff: dict[str, str]) -> dict[str, str]:
    handoff_status = str(handoff.get("handoff_status", "speaker_profile_go_handoff_pending"))
    overall_state = str(handoff.get("overall_state", "execution_not_ready"))
    go_count = str(handoff.get("go_count", "0"))
    checkpoint_count = str(handoff.get("checkpoint_count", "0"))
    case_scope = str(handoff.get("case_scope", "NoOverlap"))
    queue_status = "queue_complete" if handoff_status == "speaker_profile_go_handoff_ready" else "queue_in_progress"
    return {
        "scope": "speaker_profile_go_no_go_board_handoff",
        "handoff_status": handoff_status,
        "overall_state": overall_state,
        "go_count": go_count,
        "checkpoint_count": checkpoint_count,
        "case_scope": case_scope,
        "queue_status": queue_status,
        "observation": (
            "Experimental/frontier speaker-profile go-no-go handoff completion rollup; "
            "embedding trial execution scaffold readiness remains the next coordination step."
        ),
    }


def build_completion_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Go-No-Go Board Handoff Completion Summary",
        "",
        "This generated note summarizes speaker-profile go-no-go handoff completion. "
        "It does not claim speaker identification success.",
        "",
        "| scope | handoff_status | overall_state | go_count | checkpoint_count | case_scope | queue_status | observation |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['handoff_status']} | {row['overall_state']} | {row['go_count']} | "
            f"{row['checkpoint_count']} | {row['case_scope']} | {row['queue_status']} | {row['observation']} |"
        ),
    ]


def write_outputs(completion_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_go_no_go_board_handoff_completion_summary.csv"
    json_path = tables_dir / "speaker_profile_go_no_go_board_handoff_completion_summary.json"
    md_path = figures_dir / "speaker_profile_go_no_go_board_handoff_completion_summary.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COMPLETION_COLUMNS)
        writer.writeheader()
        writer.writerow(completion_row)
    json_path.write_text(json.dumps(completion_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_completion_lines(completion_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    handoff = load_handoff()
    if not handoff:
        print("Speaker profile go-no-go handoff not found; completion summary not written.")
        return
    completion_row = build_completion_row(handoff)
    csv_path, json_path, md_path = write_outputs(completion_row)
    print(f"Wrote speaker profile go-no-go handoff completion summary CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile go-no-go handoff completion summary JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile go-no-go handoff completion summary note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Queue status: {completion_row['queue_status']}")


if __name__ == "__main__":
    main()
