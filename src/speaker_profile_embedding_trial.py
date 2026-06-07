from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


TRIAL_COLUMNS = [
    "case_id",
    "method_direction",
    "trial_status",
    "direct_profile_score",
    "swapped_profile_score",
    "profile_confidence_gap",
    "trial_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "trial_scope",
    "case_id",
    "method_direction",
    "writeback_note",
]


def load_embedding_trial_handoff() -> dict[str, Any]:
    handoff_path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial_handoff.json"
    if not handoff_path.exists():
        return {}
    payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_profile_similarity_row(case_id: str) -> dict[str, str]:
    similarity_path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_similarity.csv"
    if not similarity_path.exists():
        return {}
    with similarity_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if str(row.get("case_id", "")) == case_id:
                return {key: str(value) for key, value in row.items()}
    return {}


def build_trial_row(handoff: dict[str, Any], profile_row: dict[str, str]) -> dict[str, str]:
    case_id = str(handoff.get("trial_case_target", profile_row.get("case_id", "NoOverlap")))
    method_direction = str(handoff.get("method_direction", "embedding_or_voiceprint_baseline"))
    return {
        "case_id": case_id,
        "method_direction": method_direction,
        "trial_status": "scaffold_only",
        "direct_profile_score": str(profile_row.get("direct_profile_score", "0.0")),
        "swapped_profile_score": str(profile_row.get("swapped_profile_score", "0.0")),
        "profile_confidence_gap": str(profile_row.get("profile_confidence_gap", "0.0")),
        "trial_note": (
            f"Template-only embedding trial diagnostic for {case_id} using existing text-profile similarity. "
            "No voiceprint or embedding model has been executed; improved speaker attribution remains unverified."
        ),
    }


def build_trial_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial",
        "",
        "This generated note records a template-only embedding trial diagnostic for one verified gold case. "
        "It does not claim voiceprint success or improved speaker attribution.",
        "",
        "| case_id | method_direction | trial_status | direct_profile_score | swapped_profile_score | profile_confidence_gap | trial_note |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
        (
            f"| {row['case_id']} | {row['method_direction']} | {row['trial_status']} | "
            f"{row['direct_profile_score']} | {row['swapped_profile_score']} | {row['profile_confidence_gap']} | "
            f"{row['trial_note']} |"
        ),
    ]
    return lines


def build_trial_receipt_rows(trial_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "trial_scaffold_complete",
            "trial_scope": "single_verified_case",
            "case_id": str(trial_row.get("case_id", "")),
            "method_direction": str(trial_row.get("method_direction", "")),
            "writeback_note": (
                "Embedding trial scaffold documented using text-profile proxy scores; "
                "voiceprint or embedding execution remains pending."
            ),
        }
    ]


def build_trial_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Receipt",
        "",
        "This receipt records the embedding trial scaffold writeback. It does not claim voiceprint success.",
        "",
        "| execution_status | trial_scope | case_id | method_direction | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['trial_scope']} | {row['case_id']} | "
            f"{row['method_direction']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    trial_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial.json"
    md_path = figures_dir / "speaker_profile_embedding_trial.md"
    receipt_json_path = tables_dir / "speaker_profile_embedding_trial_receipt.json"
    receipt_md_path = figures_dir / "speaker_profile_embedding_trial_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=TRIAL_COLUMNS)
        writer.writeheader()
        writer.writerow(trial_row)
    json_path.write_text(json.dumps(trial_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_trial_lines(trial_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_trial_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    handoff = load_embedding_trial_handoff()
    case_id = str(handoff.get("trial_case_target", "NoOverlap"))
    profile_row = load_profile_similarity_row(case_id)
    trial_row = build_trial_row(handoff, profile_row)
    receipt_rows = build_trial_receipt_rows(trial_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        trial_row,
        receipt_rows,
    )
    print(f"Wrote speaker profile embedding trial CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
