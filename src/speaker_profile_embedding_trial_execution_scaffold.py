from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


SCAFFOLD_COLUMNS = [
    "case_id",
    "method_direction",
    "trial_status",
    "profile_confidence_gap",
    "scaffold_status",
    "expected_inputs",
    "expected_outputs",
    "scaffold_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "scaffold_scope",
    "case_id",
    "method_direction",
    "writeback_note",
]


def load_embedding_trial() -> dict[str, Any]:
    trial_path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial.json"
    if not trial_path.exists():
        return {}
    payload = json.loads(trial_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_execution_scaffold_row(trial: dict[str, Any]) -> dict[str, str]:
    case_id = str(trial.get("case_id", "NoOverlap"))
    method_direction = str(trial.get("method_direction", "embedding_or_voiceprint_baseline"))
    trial_status = str(trial.get("trial_status", "scaffold_only"))
    profile_confidence_gap = str(trial.get("profile_confidence_gap", "0.0"))
    return {
        "case_id": case_id,
        "method_direction": method_direction,
        "trial_status": trial_status,
        "profile_confidence_gap": profile_confidence_gap,
        "scaffold_status": "execution_scaffold_only",
        "expected_inputs": "con/pro snippet audio for one verified gold case plus embedding or voiceprint tooling.",
        "expected_outputs": "Diagnostic embedding-similarity receipt comparing direct vs swapped speaker assignment.",
        "scaffold_note": (
            f"Template-only embedding execution scaffold for {case_id} after trial_status={trial_status}. "
            "Voiceprint or embedding model execution remains pending."
        ),
    }


def build_scaffold_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Execution Scaffold",
        "",
        "This generated note records a template-only embedding execution scaffold. "
        "It does not claim voiceprint success or improved speaker attribution.",
        "",
        "| case_id | method_direction | trial_status | profile_confidence_gap | scaffold_status | expected_inputs | expected_outputs | scaffold_note |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- |",
        (
            f"| {row['case_id']} | {row['method_direction']} | {row['trial_status']} | {row['profile_confidence_gap']} | "
            f"{row['scaffold_status']} | {row['expected_inputs']} | {row['expected_outputs']} | {row['scaffold_note']} |"
        ),
    ]
    return lines


def build_scaffold_receipt_rows(scaffold_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "execution_scaffold_complete",
            "scaffold_scope": "single_case_embedding_execution",
            "case_id": str(scaffold_row.get("case_id", "")),
            "method_direction": str(scaffold_row.get("method_direction", "")),
            "writeback_note": (
                "Embedding execution scaffold documented; voiceprint or embedding model execution remains pending."
            ),
        }
    ]


def build_scaffold_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Execution Scaffold Receipt",
        "",
        "This receipt records the embedding execution scaffold writeback. It does not claim voiceprint success.",
        "",
        "| execution_status | scaffold_scope | case_id | method_direction | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['scaffold_scope']} | {row['case_id']} | "
            f"{row['method_direction']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    scaffold_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_scaffold.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_scaffold.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_scaffold.md"
    receipt_json_path = tables_dir / "speaker_profile_embedding_trial_execution_scaffold_receipt.json"
    receipt_md_path = figures_dir / "speaker_profile_embedding_trial_execution_scaffold_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SCAFFOLD_COLUMNS)
        writer.writeheader()
        writer.writerow(scaffold_row)
    json_path.write_text(json.dumps(scaffold_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_scaffold_lines(scaffold_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_scaffold_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    trial = load_embedding_trial()
    scaffold_row = build_execution_scaffold_row(trial)
    receipt_rows = build_scaffold_receipt_rows(scaffold_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        scaffold_row,
        receipt_rows,
    )
    print(f"Wrote speaker profile embedding trial execution scaffold CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial execution scaffold JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial execution scaffold note: {md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote speaker profile embedding trial execution scaffold receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution scaffold receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
