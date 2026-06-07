from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_status",
    "dominant_pattern",
    "method_direction",
    "trial_case_target",
    "handoff_goal",
    "expected_evidence",
    "handoff_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "handoff_scope",
    "method_direction",
    "writeback_note",
]


def load_embedding_scaffold() -> dict[str, Any]:
    scaffold_path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_scaffold.json"
    if not scaffold_path.exists():
        return {}
    payload = json.loads(scaffold_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_handoff_row(scaffold: dict[str, Any]) -> dict[str, str]:
    dominant_pattern = str(scaffold.get("dominant_pattern", "swapped_bias"))
    method_direction = str(scaffold.get("method_direction", "embedding_or_voiceprint_baseline"))
    return {
        "handoff_status": "embedding_trial_handoff_ready",
        "dominant_pattern": dominant_pattern,
        "method_direction": method_direction,
        "trial_case_target": "NoOverlap",
        "handoff_goal": (
            "Run a narrow embedding-or-voiceprint diagnostic trial on one verified gold case "
            "without claiming improved speaker attribution."
        ),
        "expected_evidence": "results/tables/speaker_profile_embedding_trial_receipt.json",
        "handoff_note": (
            "experimental/frontier embedding trial handoff only; voiceprint success is not claimed."
        ),
    }


def build_handoff_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Handoff",
        "",
        "This generated handoff turns the embedding scaffold into the next narrow speaker-profile frontier step. "
        "It does not claim voiceprint success or improved speaker attribution.",
        "",
        "| handoff_status | dominant_pattern | method_direction | trial_case_target | handoff_goal | expected_evidence | handoff_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['handoff_status']} | {row['dominant_pattern']} | {row['method_direction']} | "
            f"{row['trial_case_target']} | {row['handoff_goal']} | {row['expected_evidence']} | {row['handoff_note']} |"
        ),
    ]
    return lines


def build_handoff_receipt_rows(handoff_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "handoff_documented",
            "handoff_scope": "single_case_embedding_trial",
            "method_direction": str(handoff_row.get("method_direction", "")),
            "writeback_note": (
                "Embedding trial handoff documented for coordination; "
                "improved speaker attribution remains unverified."
            ),
        }
    ]


def build_handoff_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Handoff Receipt",
        "",
        "This receipt records the embedding trial handoff writeback. It does not claim voiceprint success.",
        "",
        "| execution_status | handoff_scope | method_direction | writeback_note |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['handoff_scope']} | {row['method_direction']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    handoff_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_handoff.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_handoff.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_handoff.md"
    receipt_json_path = tables_dir / "speaker_profile_embedding_trial_handoff_receipt.json"
    receipt_md_path = figures_dir / "speaker_profile_embedding_trial_handoff_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerow(handoff_row)
    json_path.write_text(json.dumps(handoff_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(handoff_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_handoff_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    scaffold = load_embedding_scaffold()
    handoff_row = build_handoff_row(scaffold)
    receipt_rows = build_handoff_receipt_rows(handoff_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        handoff_row,
        receipt_rows,
    )
    print(f"Wrote speaker profile embedding trial handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial handoff note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial handoff receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial handoff receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
