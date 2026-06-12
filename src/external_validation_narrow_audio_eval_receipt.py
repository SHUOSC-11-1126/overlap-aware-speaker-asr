from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config


RECEIPT_COLUMNS = [
    "execution_status",
    "run_scope",
    "dataset_name",
    "slice_id",
    "label",
    "model",
    "eval_status",
    "text_length",
    "transcript_path",
    "blocker",
    "writeback_note",
]

WRITEUP_COLUMNS = [
    "receipt_status",
    "dataset_name",
    "slice_id",
    "label",
    "eval_status",
    "blocker",
    "receipt_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_receipt_row(eval_row: dict[str, Any]) -> dict[str, str]:
    return {
        "execution_status": "narrow_asr_complete",
        "run_scope": "single_external_slice_eval",
        "dataset_name": str(eval_row.get("dataset_name", "AISHELL-4")),
        "slice_id": str(eval_row.get("slice_id", "")),
        "label": str(eval_row.get("result_label", "external/sanity-check")),
        "model": str(eval_row.get("model", "")),
        "eval_status": str(eval_row.get("eval_status", "")),
        "text_length": str(eval_row.get("text_length", "")),
        "transcript_path": str(eval_row.get("transcript_path", "")),
        "blocker": "none_documented",
        "writeback_note": (
            "Narrow external/sanity-check ASR receipt recorded; no gold CER or benchmark completion claimed."
        ),
    }


def build_writeup_row(eval_row: dict[str, Any]) -> dict[str, str]:
    return {
        "receipt_status": "eval_receipt_filled",
        "dataset_name": str(eval_row.get("dataset_name", "AISHELL-4")),
        "slice_id": str(eval_row.get("slice_id", "")),
        "label": str(eval_row.get("result_label", "external/sanity-check")),
        "eval_status": str(eval_row.get("eval_status", "")),
        "blocker": "none_documented",
        "receipt_note": (
            "Writeback after narrow ASR eval; reference alignment and external benchmark claims remain out of scope."
        ),
    }


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# External Validation Narrow Audio Eval Receipt",
        "",
        "external/sanity-check eval writeback only — not gold benchmark.",
        "",
        "| execution_status | run_scope | dataset_name | slice_id | model | eval_status | text_length | blocker | writeback_note |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- | --- |",
        (
            f"| {row['execution_status']} | {row['run_scope']} | {row['dataset_name']} | {row['slice_id']} | "
            f"{row['model']} | {row['eval_status']} | {row['text_length']} | {row['blocker']} | {row['writeback_note']} |"
        ),
    ]
    return lines


def write_outputs(receipt_row: dict[str, str], writeup_row: dict[str, str]) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    receipt_csv = tables_dir / "external_validation_narrow_audio_eval_receipt.csv"
    receipt_json = tables_dir / "external_validation_narrow_audio_eval_receipt.json"
    receipt_md = figures_dir / "external_validation_narrow_audio_eval_receipt.md"
    writeup_csv = tables_dir / "external_validation_narrow_audio_eval_receipt_writeup.csv"
    writeup_json = tables_dir / "external_validation_narrow_audio_eval_receipt_writeup.json"

    with receipt_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=RECEIPT_COLUMNS)
        writer.writeheader()
        writer.writerow(receipt_row)
    receipt_json.write_text(json.dumps(receipt_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt_md.write_text("\n".join(build_receipt_lines(receipt_row)) + "\n", encoding="utf-8")

    with writeup_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=WRITEUP_COLUMNS)
        writer.writeheader()
        writer.writerow(writeup_row)
    writeup_json.write_text(json.dumps(writeup_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt_csv, receipt_json, receipt_md, writeup_csv, writeup_json


def fill_eval_receipt() -> dict[str, str]:
    eval_row = load_json_dict("results/tables/external_validation_narrow_audio_eval.json")
    if str(eval_row.get("eval_status", "")) != "narrow_asr_complete":
        raise RuntimeError("Narrow audio eval must complete before filling eval receipt")

    receipt_row = build_receipt_row(eval_row)
    writeup_row = build_writeup_row(eval_row)
    write_outputs(receipt_row, writeup_row)
    return {
        "receipt_status": writeup_row["receipt_status"],
        "execution_status": receipt_row["execution_status"],
        "blocker": receipt_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill external narrow audio eval receipt after ASR completes.")
    return parser.parse_args()


def main() -> None:
    _ = load_config()
    _ = parse_args()
    result = fill_eval_receipt()
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
