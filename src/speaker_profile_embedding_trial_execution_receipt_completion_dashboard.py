from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


DASHBOARD_COLUMNS = [
    "current_case",
    "next_milestone",
    "remaining_gate_count",
    "dominant_blocker",
    "dashboard_note",
]


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial_execution_receipt_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_milestone_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial_execution_receipt_milestone_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_dashboard_row(
    operator_brief: dict[str, str],
    milestone_card: dict[str, str],
) -> dict[str, str]:
    if not operator_brief or not milestone_card:
        return {}
    current_case = str(operator_brief.get("operator_case", ""))
    next_milestone = str(milestone_card.get("next_milestone", ""))
    remaining_gate_count = str(milestone_card.get("remaining_gate_count", "0"))
    operator_status = str(operator_brief.get("operator_status", "receipt_not_ready"))
    return {
        "current_case": current_case,
        "next_milestone": next_milestone,
        "remaining_gate_count": remaining_gate_count,
        "dominant_blocker": "receipt_template_fill_pending",
        "dashboard_note": (
            f"{current_case or 'The current case'} remains in {operator_status} while template-only execution "
            "receipts remain the dominant coordination blocker. This remains coordination-only and does not "
            "fill the receipt or claim voiceprint success."
        ),
    }


def build_dashboard_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Embedding Trial Execution Receipt Completion Dashboard",
        "",
        "This generated dashboard summarizes the current speaker-profile receipt state at a glance. "
        "It remains experimental/frontier coordination only and does not fill receipts or claim voiceprint success.",
        "",
        f"- Current case: `{row['current_case']}`",
        f"- Next milestone: `{row['next_milestone']}`",
        f"- Remaining gate count after milestone: `{row['remaining_gate_count']}`",
        f"- Dominant blocker: `{row['dominant_blocker']}`",
        f"- Dashboard note: {row['dashboard_note']}",
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_completion_dashboard.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_completion_dashboard.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_receipt_completion_dashboard.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DASHBOARD_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_dashboard_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_dashboard_row(load_operator_brief(), load_milestone_card())
    if not row:
        print("Speaker-profile receipt operator brief or milestone card not found; completion dashboard not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote speaker profile embedding trial execution receipt completion dashboard CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt completion dashboard JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt completion dashboard note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
