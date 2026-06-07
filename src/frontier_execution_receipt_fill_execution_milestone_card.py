from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


MILESTONE_COLUMNS = [
    "next_milestone",
    "unlocks",
    "remaining_frontier_count",
    "milestone_note",
]


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_handoff_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_handoff.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_milestone_card_row(
    completion_summary: dict[str, str],
    handoff_rows: list[dict[str, str]],
) -> dict[str, str]:
    if not completion_summary:
        return {}
    awaiting = int(completion_summary.get("awaiting_fill_execution_count", "0") or "0")
    total = int(completion_summary.get("total_frontier_count", "0") or "0")
    second_frontier = ""
    if len(handoff_rows) > 1:
        second_frontier = str(handoff_rows[1].get("frontier_name", "speaker_profile"))
    unlocks = (
        f"Advance to {second_frontier} fill execution after the first receipt is filled"
        if second_frontier
        else "Advance to the next frontier receipt after the first receipt is filled"
    )
    return {
        "next_milestone": "first_execution_receipt_filled",
        "unlocks": unlocks,
        "remaining_frontier_count": str(max(awaiting - 1, 0)),
        "milestone_note": (
            f"Filling the first execution receipt closes milestone 1 of {total}; "
            "no benchmark execution is claimed until a real frontier run happens."
        ),
    }


def build_milestone_card_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Milestone Card",
        "",
        "This generated milestone card shows the immediate completion boundary for the fill execution queue. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        f"- Next milestone: `{row['next_milestone']}`",
        f"- Unlocks: {row['unlocks']}",
        f"- Remaining frontier count after milestone: `{row['remaining_frontier_count']}`",
        f"- Milestone note: {row['milestone_note']}",
    ]
    return lines


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_milestone_card.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_milestone_card.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_milestone_card.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=MILESTONE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_milestone_card_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_milestone_card_row(load_completion_summary(), load_handoff_rows())
    if not row:
        print("Completion summary not found; milestone card not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier execution receipt fill execution milestone card CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution milestone card JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution milestone card note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
