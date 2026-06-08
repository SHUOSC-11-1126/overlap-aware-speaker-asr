from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


OPERATOR_BRIEF_COLUMNS = [
    "operator_case",
    "operator_status",
    "operator_target",
    "operator_evidence",
    "operator_action",
    "operator_note",
]


def load_handoff_bridge_rows() -> list[dict[str, str]]:
    path = (
        PROJECT_ROOT
        / "results"
        / "tables"
        / "speaker_profile_embedding_trial_execution_receipt_handoff_packet_bridge_checklist.json"
    )
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_operator_brief_row(bridge_row: dict[str, str]) -> dict[str, str]:
    if not bridge_row:
        return {}
    case_id = str(bridge_row.get("case_id", "NoOverlap"))
    readiness_status = str(bridge_row.get("readiness_status", "receipt_not_ready"))
    receipt_template_status = str(bridge_row.get("receipt_template_status", "missing"))
    receipt_target = str(bridge_row.get("receipt_target", ""))
    return {
        "operator_case": case_id,
        "operator_status": readiness_status,
        "operator_target": receipt_target,
        "operator_evidence": (
            "results/figures/speaker_profile_embedding_trial_execution_receipt_handoff_packet.md; "
            "results/figures/speaker_profile_embedding_trial_execution_receipt_handoff_packet_bridge_checklist.md"
        ),
        "operator_action": f"Reopen {receipt_target} for {case_id} after confirming the receipt handoff packet bridge.",
        "operator_note": (
            f"Speaker-profile receipt coordination for {case_id} reports readiness_status={readiness_status} "
            f"with receipt_template_status={receipt_template_status}. This remains experimental/frontier only, "
            "and does not fill the receipt or claim voiceprint success."
        ),
    }


def build_operator_brief_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Embedding Trial Execution Receipt Operator Brief",
        "",
        "This generated brief gives the next contributor a plain-language speaker-profile receipt action. "
        "It remains experimental/frontier coordination only and does not fill receipts or claim voiceprint success.",
        "",
        f"- Operator case: `{row['operator_case']}`",
        f"- Operator status: `{row['operator_status']}`",
        f"- Operator target: `{row['operator_target']}`",
        f"- Evidence path: `{row['operator_evidence']}`",
        f"- Operator action: {row['operator_action']}",
        f"- Operator note: {row['operator_note']}",
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_operator_brief.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_operator_brief.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_receipt_operator_brief.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OPERATOR_BRIEF_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_operator_brief_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    bridge_rows = load_handoff_bridge_rows()
    row = build_operator_brief_row(bridge_rows[0] if bridge_rows else {})
    if not row:
        print("Speaker-profile receipt handoff packet bridge checklist not found; operator brief not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote speaker profile embedding trial execution receipt operator brief CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt operator brief JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt operator brief note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
