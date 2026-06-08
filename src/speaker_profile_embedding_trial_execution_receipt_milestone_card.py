from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


MILESTONE_COLUMNS = [
    "next_milestone",
    "unlocks",
    "remaining_gate_count",
    "milestone_note",
]


def load_phase_checkpoint_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_bridge_rows() -> list[dict[str, str]]:
    path = (
        PROJECT_ROOT
        / "results"
        / "tables"
        / "speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_bridge_checklist.json"
    )
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_milestone_card_row(
    checkpoint: dict[str, str],
    bridge_rows: list[dict[str, str]],
) -> dict[str, str]:
    if not checkpoint:
        return {}
    checkpoint_case = str(checkpoint.get("checkpoint_case", "NoOverlap"))
    receipt_target = ""
    if bridge_rows:
        receipt_target = str(bridge_rows[0].get("receipt_target", ""))
    return {
        "next_milestone": "speaker_profile_receipt_readiness_reopen_ready",
        "unlocks": f"Reopen {receipt_target} for {checkpoint_case} after the current checkpoint gate closes.",
        "remaining_gate_count": str(max(len(bridge_rows) - 1, 0)),
        "milestone_note": (
            f"Closing the current speaker-profile checkpoint for {checkpoint_case} completes the visible receipt-phase milestone. "
            "This remains coordination-only and does not fill the receipt or claim voiceprint success."
        ),
    }


def build_milestone_card_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Embedding Trial Execution Receipt Milestone Card",
        "",
        "This generated milestone card shows the immediate unlock boundary after the current speaker-profile receipt checkpoint closes. "
        "It remains experimental/frontier coordination only and does not fill receipts or claim voiceprint success.",
        "",
        f"- Next milestone: `{row['next_milestone']}`",
        f"- Unlocks: {row['unlocks']}",
        f"- Remaining gate count after milestone: `{row['remaining_gate_count']}`",
        f"- Milestone note: {row['milestone_note']}",
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_milestone_card.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_milestone_card.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_receipt_milestone_card.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=MILESTONE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_milestone_card_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_milestone_card_row(load_phase_checkpoint_card(), load_bridge_rows())
    if not row:
        print("Speaker-profile receipt phase checkpoint card not found; milestone card not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote speaker profile embedding trial execution receipt milestone card CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt milestone card JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt milestone card note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
