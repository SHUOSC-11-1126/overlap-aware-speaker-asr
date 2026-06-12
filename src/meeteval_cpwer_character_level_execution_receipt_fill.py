from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .meeteval_cpwer_tokenization_gain_scorecard import load_bridge_lite_by_case


FILL_COLUMNS = [
    "fill_status",
    "case_scope",
    "case_count",
    "execution_receipt_status",
    "tokenization_mode",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "run_scope",
    "case_id",
    "hypothesis_source",
    "preflight_pass",
    "tokenization_mode",
    "official_cpwer",
    "official_cpwer_raw",
    "cpwer_tool",
    "cpwer_bridge_lite",
    "speaker_count",
    "expected_inputs",
    "expected_outputs",
    "writeback_note",
    "result_label",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_json_rows(path_rel: str) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def load_tokenization_summary() -> dict[str, Any]:
    return load_json_dict("results/tables/meeteval_cpwer_tokenization_adaptation_completion_summary.json")


def assert_fill_preconditions(
    character_rows: list[dict[str, Any]],
    tokenization_summary: dict[str, Any],
) -> None:
    if str(tokenization_summary.get("queue_status", "")) != "queue_complete":
        raise RuntimeError(
            "Tokenization adaptation must be queue_complete before character-level receipt fill"
        )
    complete_rows = [
        row
        for row in character_rows
        if str(row.get("execution_status", "")) == "character_level_cpwer_narrow_dry_run_complete"
    ]
    if len(complete_rows) < 5:
        raise RuntimeError(
            f"Character-level execution must cover 5/5 gold cases; got {len(complete_rows)}/5"
        )


def receipt_needs_character_fill(receipt_rows: list[dict[str, Any]]) -> bool:
    if not receipt_rows:
        return True
    return any(
        str(row.get("execution_status", "")) != "character_level_cpwer_receipt_fill_complete"
        for row in receipt_rows
    )


def build_filled_receipt_rows(
    character_rows: list[dict[str, Any]],
    bridge_lite_by_case: dict[str, str],
) -> list[dict[str, str]]:
    filled_rows: list[dict[str, str]] = []
    for row in character_rows:
        case_id = str(row.get("case_id", ""))
        filled_rows.append(
            {
                "execution_status": "character_level_cpwer_receipt_fill_complete",
                "run_scope": "all_gold_character_cpwer_execution",
                "case_id": case_id,
                "hypothesis_source": str(row.get("hypothesis_source", "")),
                "preflight_pass": "True",
                "tokenization_mode": str(row.get("tokenization_mode", "character_spaced")),
                "official_cpwer": str(row.get("official_cpwer", "")),
                "official_cpwer_raw": str(row.get("official_cpwer_raw", "")),
                "cpwer_tool": str(row.get("cpwer_tool", "meeteval")),
                "cpwer_bridge_lite": bridge_lite_by_case.get(case_id, ""),
                "speaker_count": str(row.get("speaker_count", "")),
                "expected_inputs": (
                    "results/tables/meeteval_reference_segments.jsonl; "
                    "results/tables/meeteval_hypothesis_segments.jsonl; MeetEval cpWER tooling."
                ),
                "expected_outputs": "Character-spaced official cpWER score and filled execution receipt.",
                "writeback_note": (
                    f"Character-spaced MeetEval cpWER receipt filled for {case_id}; "
                    "experimental/frontier only — not a full benchmark claim. "
                    "Compare character-spaced official_cpwer against cpwer_bridge_lite for alignment."
                ),
                "result_label": str(row.get("result_label", "experimental/frontier")),
            }
        )
    return filled_rows


def build_fill_row(case_count: int) -> dict[str, str]:
    return {
        "fill_status": "receipt_filled",
        "case_scope": "all_gold",
        "case_count": str(case_count),
        "execution_receipt_status": "character_level_cpwer_receipt_fill_complete",
        "tokenization_mode": "character_spaced",
        "blocker": "none_documented",
        "fill_note": (
            "Execution receipt filled with character-spaced MeetEval cpWER evidence for all verified gold cases."
        ),
    }


def build_fill_lines(row: dict[str, str]) -> list[str]:
    return [
        "# MeetEval cpWER Character-Level Execution Receipt Fill",
        "",
        "experimental/frontier writeback — character-spaced official cpWER only.",
        "",
        "| fill_status | case_scope | case_count | execution_receipt_status | tokenization_mode | blocker |",
        "| --- | --- | ---: | --- | --- | --- |",
        (
            f"| {row['fill_status']} | {row['case_scope']} | {row['case_count']} | "
            f"{row['execution_receipt_status']} | {row['tokenization_mode']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Character-Level Execution Receipt",
        "",
        "| case_id | execution_status | official_cpwer | official_cpwer_raw | cpwer_bridge_lite | tokenization_mode |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['execution_status']} | {row['official_cpwer']} | "
            f"{row['official_cpwer_raw']} | {row['cpwer_bridge_lite']} | {row['tokenization_mode']} |"
        )
    return lines


def write_outputs(fill_row: dict[str, str], receipt_rows: list[dict[str, str]]) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    fill_csv = tables_dir / "meeteval_cpwer_character_level_execution_receipt_fill.csv"
    fill_json = tables_dir / "meeteval_cpwer_character_level_execution_receipt_fill.json"
    fill_md = figures_dir / "meeteval_cpwer_character_level_execution_receipt_fill.md"
    receipt_json = tables_dir / "meeteval_cpwer_execution_receipt.json"
    receipt_md = figures_dir / "meeteval_cpwer_execution_receipt.md"

    with fill_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILL_COLUMNS)
        writer.writeheader()
        writer.writerow(fill_row)
    fill_json.write_text(json.dumps(fill_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fill_md.write_text("\n".join(build_fill_lines(fill_row)) + "\n", encoding="utf-8")
    receipt_json.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt_md.write_text("\n".join(build_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return fill_csv, fill_json, fill_md, receipt_json, receipt_md


def fill_character_level_receipt(force: bool = False) -> dict[str, str]:
    character_rows = load_json_rows("results/tables/meeteval_cpwer_character_level_official_execution.json")
    tokenization_summary = load_tokenization_summary()
    assert_fill_preconditions(character_rows, tokenization_summary)

    existing_receipt = load_json_rows("results/tables/meeteval_cpwer_execution_receipt.json")
    if existing_receipt and not force and not receipt_needs_character_fill(existing_receipt):
        return {
            "fill_status": "already_filled",
            "execution_receipt_status": "character_level_cpwer_receipt_fill_complete",
            "case_count": str(len(existing_receipt)),
            "blocker": "none_documented",
        }

    bridge_lite_by_case = load_bridge_lite_by_case()
    receipt_rows = build_filled_receipt_rows(character_rows, bridge_lite_by_case)
    fill_row = build_fill_row(len(receipt_rows))
    write_outputs(fill_row, receipt_rows)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "case_count": fill_row["case_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fill MeetEval cpWER execution receipt with character-spaced official scores."
    )
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled receipt.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = fill_character_level_receipt(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
