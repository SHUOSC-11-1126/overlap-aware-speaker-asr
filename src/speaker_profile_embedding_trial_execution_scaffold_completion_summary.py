from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


COMPLETION_COLUMNS = [
    "scope",
    "readiness_status",
    "case_id",
    "queue_status",
    "observation",
]


def load_readiness() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial_execution_scaffold_readiness.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_completion_row(readiness: dict[str, str]) -> dict[str, str]:
    readiness_status = str(readiness.get("readiness_status", "scaffold_not_ready"))
    case_id = str(readiness.get("case_id", "NoOverlap"))
    queue_status = "queue_complete" if readiness_status == "scaffold_ready" else "queue_in_progress"
    return {
        "scope": "speaker_profile_embedding_trial_execution_scaffold",
        "readiness_status": readiness_status,
        "case_id": case_id,
        "queue_status": queue_status,
        "observation": (
            "Experimental/frontier execution scaffold completion rollup; "
            "execution preflight remains the next narrow step without voiceprint claims."
        ),
    }


def build_completion_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Embedding Trial Execution Scaffold Completion Summary",
        "",
        "This generated note summarizes execution scaffold completion readiness. "
        "It does not claim voiceprint success or improved speaker attribution.",
        "",
        "| scope | readiness_status | case_id | queue_status | observation |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['readiness_status']} | {row['case_id']} | "
            f"{row['queue_status']} | {row['observation']} |"
        ),
    ]


def write_outputs(completion_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_scaffold_completion_summary.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_scaffold_completion_summary.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_scaffold_completion_summary.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=COMPLETION_COLUMNS)
        writer.writeheader()
        writer.writerow(completion_row)
    json_path.write_text(json.dumps(completion_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_completion_lines(completion_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    readiness = load_readiness()
    if not readiness:
        print("Execution scaffold readiness not found; completion summary not written.")
        return
    completion_row = build_completion_row(readiness)
    csv_path, json_path, md_path = write_outputs(completion_row)
    print(
        "Wrote speaker profile embedding trial execution scaffold completion summary CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution scaffold completion summary JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution scaffold completion summary note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Queue status: {completion_row['queue_status']}")


if __name__ == "__main__":
    main()
