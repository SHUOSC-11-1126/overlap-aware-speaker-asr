from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT


PREFLIGHT_COLUMNS = [
    "case_id",
    "handoff_status",
    "method_direction",
    "best_profile_alignment",
    "profile_confidence_gap",
    "profile_data_valid",
    "swapped_bias_detected",
    "preflight_pass",
    "preflight_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "run_scope",
    "case_id",
    "method_direction",
    "preflight_pass",
    "writeback_note",
]


def load_execution_handoff() -> dict[str, Any]:
    handoff_path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_embedding_trial_execution_handoff.json"
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


def run_preflight(case_id: str, handoff: dict[str, Any], profile_row: dict[str, str]) -> dict[str, Any]:
    profile_data_valid = bool(profile_row)
    best_alignment = str(profile_row.get("best_profile_alignment", ""))
    confidence_gap = str(profile_row.get("profile_confidence_gap", "0.0"))
    swapped_bias_detected = best_alignment == "swapped"
    preflight_pass = profile_data_valid and float(confidence_gap or 0.0) > 0.0

    if preflight_pass and swapped_bias_detected:
        preflight_note = (
            f"Execution preflight for {case_id} found valid text-profile proxy data with swapped_bias detected. "
            "Voiceprint or embedding execution remains pending; improved attribution is not claimed."
        )
    elif preflight_pass:
        preflight_note = (
            f"Execution preflight for {case_id} found valid profile proxy data. "
            "Voiceprint or embedding execution remains pending."
        )
    else:
        preflight_note = (
            f"Execution preflight for {case_id} found missing or invalid profile proxy data; "
            "review speaker_profile_similarity before voiceprint execution."
        )

    return {
        "case_id": case_id,
        "handoff_status": str(handoff.get("handoff_status", "execution_handoff_ready")),
        "method_direction": str(handoff.get("method_direction", "embedding_or_voiceprint_baseline")),
        "best_profile_alignment": best_alignment,
        "profile_confidence_gap": confidence_gap,
        "profile_data_valid": profile_data_valid,
        "swapped_bias_detected": swapped_bias_detected,
        "preflight_pass": preflight_pass,
        "preflight_note": preflight_note,
    }


def build_preflight_lines(row: dict[str, Any]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Execution Preflight",
        "",
        "This generated note records a narrow embedding execution preflight for one verified gold case. "
        "It does not claim voiceprint success or improved speaker attribution.",
        "",
        "| case_id | handoff_status | method_direction | best_profile_alignment | profile_confidence_gap | "
        "profile_data_valid | swapped_bias_detected | preflight_pass | preflight_note |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
        (
            f"| {row['case_id']} | {row['handoff_status']} | {row['method_direction']} | "
            f"{row['best_profile_alignment']} | {row['profile_confidence_gap']} | {row['profile_data_valid']} | "
            f"{row['swapped_bias_detected']} | {row['preflight_pass']} | {row['preflight_note']} |"
        ),
    ]
    return lines


def build_receipt_rows(preflight_row: dict[str, Any]) -> list[dict[str, str]]:
    status = "preflight_complete" if preflight_row.get("preflight_pass") else "preflight_failed"
    return [
        {
            "execution_status": status,
            "run_scope": "single_case_embedding_execution_preflight",
            "case_id": str(preflight_row.get("case_id", "")),
            "method_direction": str(preflight_row.get("method_direction", "")),
            "preflight_pass": str(preflight_row.get("preflight_pass", False)),
            "writeback_note": (
                "Embedding execution preflight documented; voiceprint or embedding model execution remains pending."
            ),
        }
    ]


def build_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Execution Preflight Receipt",
        "",
        "This receipt records the embedding execution preflight writeback. It does not claim voiceprint success.",
        "",
        "| execution_status | run_scope | case_id | method_direction | preflight_pass | writeback_note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['run_scope']} | {row['case_id']} | "
            f"{row['method_direction']} | {row['preflight_pass']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    preflight_row: dict[str, Any],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_preflight.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_preflight.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_preflight.md"
    receipt_json_path = tables_dir / "speaker_profile_embedding_trial_execution_preflight_receipt.json"
    receipt_md_path = figures_dir / "speaker_profile_embedding_trial_execution_preflight_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PREFLIGHT_COLUMNS)
        writer.writeheader()
        writer.writerow(preflight_row)
    json_path.write_text(json.dumps(preflight_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_preflight_lines(preflight_row)) + "\n", encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_json_path, receipt_md_path


def main() -> None:
    handoff = load_execution_handoff()
    case_id = str(handoff.get("case_id", "NoOverlap"))
    profile_row = load_profile_similarity_row(case_id)
    preflight_row = run_preflight(case_id, handoff, profile_row)
    receipt_rows = build_receipt_rows(preflight_row)
    csv_path, json_path, md_path, receipt_json_path, receipt_md_path = write_outputs(
        preflight_row,
        receipt_rows,
    )
    print(f"Wrote speaker profile embedding trial execution preflight CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial execution preflight JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial execution preflight note: {md_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote speaker profile embedding trial execution preflight receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote speaker profile embedding trial execution preflight receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
