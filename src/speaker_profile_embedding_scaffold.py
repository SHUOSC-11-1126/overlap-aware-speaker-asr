from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


SCAFFOLD_COLUMNS = [
    "dominant_pattern",
    "method_direction",
    "scaffold_status",
    "expected_inputs",
    "expected_outputs",
    "scaffold_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "method_scope",
    "method_direction",
    "expected_inputs",
    "writeback_note",
]


def load_profile_triage() -> dict[str, str]:
    triage_path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_triage.csv"
    if not triage_path.exists():
        return {"dominant_pattern": "swapped_bias"}
    with triage_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return {
                "dominant_pattern": str(row.get("dominant_pattern", "swapped_bias")),
                "next_action": str(row.get("next_action", "")),
            }
    return {"dominant_pattern": "swapped_bias"}


def build_embedding_scaffold_row(triage: dict[str, str]) -> dict[str, str]:
    return {
        "dominant_pattern": str(triage.get("dominant_pattern", "swapped_bias")),
        "method_direction": "embedding_or_voiceprint_baseline",
        "scaffold_status": "scaffold_only",
        "expected_inputs": "con/pro snippet audio plus separated speaker-track transcripts for one verified case.",
        "expected_outputs": "Diagnostic embedding-similarity note comparing direct vs swapped speaker assignment.",
        "scaffold_note": (
            "Template-only stronger-method scaffold. The current text-profile signal is diagnostic only "
            "and should not be treated as speaker-ID success."
        ),
    }


def build_embedding_scaffold_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Scaffold",
        "",
        "This generated note records a template-only stronger-method scaffold for speaker-profile risk detection. "
        "It does not claim voiceprint or speaker-ID success.",
        "",
        "| dominant_pattern | method_direction | scaffold_status | expected_inputs | expected_outputs | scaffold_note |",
        "| --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['dominant_pattern']} | {row['method_direction']} | {row['scaffold_status']} | "
            f"{row['expected_inputs']} | {row['expected_outputs']} | {row['scaffold_note']} |"
        ),
    ]
    return lines


def build_embedding_scaffold_receipt_rows(scaffold_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "scaffold_complete",
            "method_scope": "single_verified_case",
            "method_direction": str(scaffold_row.get("method_direction", "")),
            "expected_inputs": str(scaffold_row.get("expected_inputs", "")),
            "writeback_note": "Embedding scaffold documented; no stronger speaker-profile method has been executed yet.",
        }
    ]


def build_embedding_scaffold_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Scaffold Receipt",
        "",
        "This receipt records the stronger-method scaffold writeback. It does not claim improved speaker attribution.",
        "",
        "| execution_status | method_scope | method_direction | expected_inputs | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['method_scope']} | {row['method_direction']} | "
            f"{row['expected_inputs']} | {row['writeback_note']} |"
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

    scaffold_csv_path = tables_dir / "speaker_profile_embedding_scaffold.csv"
    scaffold_json_path = tables_dir / "speaker_profile_embedding_scaffold.json"
    scaffold_md_path = figures_dir / "speaker_profile_embedding_scaffold.md"
    receipt_json_path = tables_dir / "speaker_profile_embedding_scaffold_receipt.json"
    receipt_md_path = figures_dir / "speaker_profile_embedding_scaffold_receipt.md"

    with scaffold_csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SCAFFOLD_COLUMNS)
        writer.writeheader()
        writer.writerow(scaffold_row)
    scaffold_json_path.write_text(json.dumps(scaffold_row, ensure_ascii=False, indent=2), encoding="utf-8")
    scaffold_md_path.write_text("\n".join(build_embedding_scaffold_lines(scaffold_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_embedding_scaffold_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return scaffold_csv_path, scaffold_json_path, scaffold_md_path, receipt_json_path, receipt_md_path


def main() -> None:
    triage = load_profile_triage()
    scaffold_row = build_embedding_scaffold_row(triage)
    receipt_rows = build_embedding_scaffold_receipt_rows(scaffold_row)
    scaffold_csv_path, scaffold_json_path, scaffold_md_path, receipt_json_path, receipt_md_path = write_outputs(
        scaffold_row,
        receipt_rows,
    )
    print(f"Wrote speaker profile embedding scaffold CSV: {scaffold_csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding scaffold JSON: {scaffold_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding scaffold note: {scaffold_md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding scaffold receipt JSON: {receipt_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding scaffold receipt note: {receipt_md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
