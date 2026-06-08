from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


PHASE_CHECKPOINT_COLUMNS = [
    "checkpoint_frontier",
    "checkpoint_action",
    "completion_signal",
    "checkpoint_note",
]


def load_runbook_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_operator_next_action_status_handoff_runbook_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_phase_checkpoint_row(runbook: dict[str, str]) -> dict[str, str]:
    if not runbook:
        return {}
    frontier = str(runbook.get("recommended_frontier", "unknown"))
    return {
        "checkpoint_frontier": frontier,
        "checkpoint_action": str(runbook.get("recommended_action", "")),
        "completion_signal": str(runbook.get("completion_signal", "")),
        "checkpoint_note": (
            f"Phase checkpoint for {frontier}: complete this action and confirm the completion signal "
            "before advancing the status/handoff stack. No frontier execution is claimed."
        ),
    }


def build_phase_checkpoint_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Operator Next-Action Status Handoff Phase Checkpoint Card",
        "",
        "This generated checkpoint card shows the per-phase completion signal for the current status/handoff step. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        f"- Checkpoint frontier: `{row['checkpoint_frontier']}`",
        f"- Checkpoint action: `{row['checkpoint_action']}`",
        f"- Completion signal: `{row['completion_signal']}`",
        f"- Checkpoint note: {row['checkpoint_note']}",
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_status_handoff_phase_checkpoint_card.csv"
    json_path = tables_dir / "frontier_operator_next_action_status_handoff_phase_checkpoint_card.json"
    md_path = figures_dir / "frontier_operator_next_action_status_handoff_phase_checkpoint_card.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PHASE_CHECKPOINT_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_phase_checkpoint_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_phase_checkpoint_row(load_runbook_card())
    if not row:
        print("Status handoff runbook card not found; phase checkpoint card not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier operator next-action status handoff phase checkpoint card CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff phase checkpoint card JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier operator next-action status handoff phase checkpoint card note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
