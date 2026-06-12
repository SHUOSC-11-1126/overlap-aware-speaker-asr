from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .external_validation_go_no_go_board import mini_check_audio_ready


RECEIPT_COLUMNS = [
    "execution_status",
    "run_scope",
    "dataset_name",
    "blocker",
    "audio_path",
    "reference_path",
    "staging_status",
    "expected_inputs",
    "expected_outputs",
    "writeback_note",
]

FILL_COLUMNS = [
    "fill_status",
    "dataset_name",
    "slice_id",
    "label",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_mini_check() -> dict[str, Any]:
    return load_json_dict("results/tables/external_validation_mini_sanity_check.json")


def load_slice_mapping() -> dict[str, Any]:
    return load_json_dict("results/tables/external_validation_slice_mapping.json")


def build_filled_receipt_rows(mini_check: dict[str, Any], mapping: dict[str, Any]) -> list[dict[str, str]]:
    dataset_name = str(mini_check.get("dataset_name", mapping.get("dataset_name", "AISHELL-4")))
    return [
        {
            "execution_status": "audio_excerpt_staged",
            "run_scope": "single_external_slice_staging",
            "dataset_name": dataset_name,
            "blocker": "none_documented",
            "audio_path": str(mapping.get("audio_path", "")),
            "reference_path": str(mapping.get("reference_path", "")),
            "staging_status": str(mapping.get("staging_status", "audio_excerpt_staged")),
            "expected_inputs": "AISHELL-4 excerpt wav, reference scaffold, license confirmation artifact.",
            "expected_outputs": "Filled staging execution receipt under external/sanity-check labeling.",
            "writeback_note": (
                "Audio excerpt staged locally from HuggingFace AISHELL-4 test clip; "
                "narrow eval may proceed without claiming gold benchmark results."
            ),
        }
    ]


def build_fill_row(mini_check: dict[str, Any], mapping: dict[str, Any]) -> dict[str, str]:
    return {
        "fill_status": "receipt_filled",
        "dataset_name": str(mini_check.get("dataset_name", "AISHELL-4")),
        "slice_id": str(mini_check.get("slice_id", mapping.get("slice_id", ""))),
        "label": str(mini_check.get("result_label", "external/sanity-check")),
        "execution_receipt_status": "audio_excerpt_staged",
        "blocker": "none_documented",
        "fill_note": (
            "Execution receipt filled after mini sanity check confirmed staged audio and reference paths."
        ),
    }


def build_fill_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# External Validation Staging Execution Receipt Fill",
        "",
        "Filled staging execution receipt after AISHELL-4 excerpt staging. "
        "external/sanity-check only — not gold benchmark.",
        "",
        "| fill_status | dataset_name | slice_id | label | execution_receipt_status | blocker | fill_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['fill_status']} | {row['dataset_name']} | {row['slice_id']} | {row['label']} | "
            f"{row['execution_receipt_status']} | {row['blocker']} | {row['fill_note']} |"
        ),
    ]
    return lines


def build_handoff_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Handoff Receipt",
        "",
        "Filled execution receipt for the first external slice staging excerpt.",
        "",
        "| execution_status | run_scope | dataset_name | blocker | audio_path | reference_path | staging_status | writeback_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution_status']} | {row['run_scope']} | {row['dataset_name']} | {row['blocker']} | "
            f"{row['audio_path']} | {row['reference_path']} | {row['staging_status']} | {row['writeback_note']} |"
        )
    return lines


def write_outputs(
    fill_row: dict[str, str],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    fill_csv = tables_dir / "external_validation_staging_execution_receipt_fill.csv"
    fill_json = tables_dir / "external_validation_staging_execution_receipt_fill.json"
    fill_md = figures_dir / "external_validation_staging_execution_receipt_fill.md"
    handoff_receipt_json = tables_dir / "external_validation_slice_staging_handoff_receipt.json"
    handoff_receipt_md = figures_dir / "external_validation_slice_staging_handoff_receipt.md"

    with fill_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILL_COLUMNS)
        writer.writeheader()
        writer.writerow(fill_row)
    fill_json.write_text(json.dumps(fill_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fill_md.write_text("\n".join(build_fill_lines(fill_row)) + "\n", encoding="utf-8")
    handoff_receipt_json.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    handoff_receipt_md.write_text("\n".join(build_handoff_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return fill_csv, fill_json, fill_md, handoff_receipt_json, handoff_receipt_md


def fill_execution_receipt(force: bool = False) -> dict[str, str]:
    mini_check = load_mini_check()
    if not mini_check_audio_ready(mini_check):
        raise RuntimeError("Mini sanity check must confirm staged audio and reference before filling receipt")

    mapping = load_slice_mapping()
    handoff_receipt_path = PROJECT_ROOT / "results/tables/external_validation_slice_staging_handoff_receipt.json"
    if handoff_receipt_path.exists() and not force:
        payload = json.loads(handoff_receipt_path.read_text(encoding="utf-8"))
        if isinstance(payload, list) and payload:
            status = str(payload[0].get("execution_status", ""))
            if status == "audio_excerpt_staged":
                return {"fill_status": "already_filled", "execution_receipt_status": status}

    receipt_rows = build_filled_receipt_rows(mini_check, mapping)
    fill_row = build_fill_row(mini_check, mapping)
    write_outputs(fill_row, receipt_rows)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill external staging execution receipt after audio excerpt staging.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled receipt.")
    return parser.parse_args()


def main() -> None:
    _ = load_config()
    args = parse_args()
    result = fill_execution_receipt(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
