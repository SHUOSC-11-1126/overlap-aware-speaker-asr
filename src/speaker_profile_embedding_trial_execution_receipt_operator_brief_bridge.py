from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_COLUMNS = [
    "operator_case",
    "prerequisite_artifact",
    "receipt_target",
    "bridge_note",
]


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial_execution_receipt_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_row(operator_brief: dict[str, str]) -> dict[str, str]:
    if not operator_brief:
        return {}
    case_id = str(operator_brief.get("operator_case", "NoOverlap"))
    operator_status = str(operator_brief.get("operator_status", "receipt_not_ready"))
    operator_target = str(operator_brief.get("operator_target", ""))
    return {
        "operator_case": case_id,
        "prerequisite_artifact": "results/figures/speaker_profile_embedding_trial_execution_receipt_operator_brief.md",
        "receipt_target": operator_target,
        "bridge_note": (
            f"Open the operator brief for {case_id} first; operator_status={operator_status}. "
            "Then continue through the current speaker-profile readiness target. "
            "This bridge remains experimental/frontier coordination only and does not claim voiceprint success."
        ),
    }


def build_bridge_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Embedding Trial Execution Receipt Operator Brief Bridge",
        "",
        "This generated bridge connects the speaker-profile receipt operator brief to the current readiness target. "
        "It remains experimental/frontier coordination only and does not fill receipts or claim voiceprint success.",
        "",
        "| operator_case | prerequisite_artifact | receipt_target | bridge_note |",
        "| --- | --- | --- | --- |",
        (
            f"| {row['operator_case']} | {row['prerequisite_artifact']} | {row['receipt_target']} | "
            f"{row['bridge_note']} |"
        ),
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_bridge_row(load_operator_brief())
    if not row:
        print("Speaker-profile receipt operator brief not found; operator brief bridge not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote speaker profile embedding trial execution receipt operator brief bridge CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt operator brief bridge JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt operator brief bridge note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
