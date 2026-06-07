from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


SCAFFOLD_COLUMNS = [
    "case_id",
    "preflight_pass",
    "method_direction",
    "swapped_bias_detected",
    "scaffold_status",
    "expected_inputs",
    "expected_outputs",
    "scaffold_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "scaffold_scope",
    "case_id",
    "preflight_pass",
    "writeback_note",
]


def load_execution_preflight() -> dict[str, Any]:
    preflight_path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial_execution_preflight.json"
    if not preflight_path.exists():
        return {}
    payload = json.loads(preflight_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_scaffold_row(preflight: dict[str, Any]) -> dict[str, str]:
    case_id = str(preflight.get("case_id", "NoOverlap"))
    preflight_pass = bool(preflight.get("preflight_pass", False))
    method_direction = str(preflight.get("method_direction", "embedding_or_voiceprint_baseline"))
    swapped_bias = bool(preflight.get("swapped_bias_detected", False))
    return {
        "case_id": case_id,
        "preflight_pass": str(preflight_pass),
        "method_direction": method_direction,
        "swapped_bias_detected": str(swapped_bias),
        "scaffold_status": "receipt_scaffold_only",
        "expected_inputs": "con/pro snippet audio for one verified gold case plus embedding or voiceprint tooling.",
        "expected_outputs": "Diagnostic embedding-similarity receipt comparing direct vs swapped speaker assignment.",
        "scaffold_note": (
            f"Template-only embedding execution receipt scaffold for {case_id} after "
            f"preflight_pass={preflight_pass} and swapped_bias_detected={swapped_bias}. "
            "Voiceprint execution remains pending."
        ),
    }


def build_scaffold_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Execution Receipt Scaffold",
        "",
        "This generated note records a template-only embedding execution receipt scaffold. "
        "It does not claim voiceprint success or improved speaker attribution.",
        "",
        "| case_id | preflight_pass | method_direction | swapped_bias_detected | scaffold_status | expected_inputs | expected_outputs | scaffold_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['case_id']} | {row['preflight_pass']} | {row['method_direction']} | "
            f"{row['swapped_bias_detected']} | {row['scaffold_status']} | {row['expected_inputs']} | "
            f"{row['expected_outputs']} | {row['scaffold_note']} |"
        ),
    ]
    return lines


def build_scaffold_receipt_rows(scaffold_row: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "execution_status": "receipt_scaffold_complete",
            "scaffold_scope": "single_case_embedding_execution_receipt",
            "case_id": str(scaffold_row.get("case_id", "")),
            "preflight_pass": str(scaffold_row.get("preflight_pass", "")),
            "writeback_note": (
                "Embedding execution receipt scaffold documented; "
                "voiceprint or embedding model execution remains pending."
            ),
        }
    ]


def build_scaffold_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Execution Receipt Scaffold Receipt",
        "",
        "This receipt records the embedding execution receipt scaffold writeback. It does not claim voiceprint success.",
        "",
        "| execution_status | scaffold_scope | case_id | preflight_pass | writeback_note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['scaffold_scope']} | {row['case_id']} | "
            f"{row['preflight_pass']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    scaffold_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_scaffold.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_scaffold.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_receipt_scaffold.md"
    receipt_template_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt.json"
    receipt_json_path = tables_dir / "speaker_profile_embedding_trial_execution_receipt_scaffold_receipt.json"
    receipt_md_path = figures_dir / "speaker_profile_embedding_trial_execution_receipt_scaffold_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SCAFFOLD_COLUMNS)
        writer.writeheader()
        writer.writerow(scaffold_row)
    json_path.write_text(json.dumps(scaffold_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_scaffold_lines(scaffold_row)) + "\n", encoding="utf-8")

    receipt_template = [
        {
            "execution_status": "template_only",
            "run_scope": "single_case_embedding_execution",
            "case_id": scaffold_row.get("case_id", ""),
            "method_direction": scaffold_row.get("method_direction", ""),
            "preflight_pass": scaffold_row.get("preflight_pass", ""),
            "swapped_bias_detected": scaffold_row.get("swapped_bias_detected", ""),
            "expected_inputs": scaffold_row.get("expected_inputs", ""),
            "expected_outputs": "Embedding-similarity diagnostic note comparing direct vs swapped assignment.",
            "writeback_note": (
                "Voiceprint or embedding model has not been executed yet; "
                "fill this receipt only after a real embedding diagnostic run."
            ),
        }
    ]
    receipt_template_path.write_text(json.dumps(receipt_template, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_scaffold_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_template_path, receipt_json_path, receipt_md_path


def main() -> None:
    preflight = load_execution_preflight()
    scaffold_row = build_scaffold_row(preflight)
    receipt_rows = build_scaffold_receipt_rows(scaffold_row)
    csv_path, json_path, md_path, receipt_template_path, receipt_json_path, receipt_md_path = write_outputs(
        scaffold_row,
        receipt_rows,
    )
    print(f"Wrote speaker profile embedding trial execution receipt scaffold CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial execution receipt scaffold JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial execution receipt scaffold note: {md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote speaker profile embedding trial execution receipt template JSON: "
        f"{receipt_template_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt scaffold receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution receipt scaffold receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
