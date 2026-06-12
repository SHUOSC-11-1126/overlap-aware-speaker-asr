from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .llm_critic_qualitative_brief_light_mid import build_brief_report, write_outputs as write_brief_outputs


FILL_COLUMNS = [
    "fill_status",
    "writeback_scope",
    "case_scope",
    "brief_case_count",
    "execution_receipt_status",
    "blocker",
    "fill_note",
]

RECEIPT_COLUMNS = [
    "execution_status",
    "review_scope",
    "case_id",
    "review_outcome",
    "brief_artifact",
    "expected_inputs",
    "writeback_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_go_no_go_summary() -> dict[str, Any]:
    return load_json_dict("results/tables/llm_critic_go_no_go_summary.json")


def assert_writeback_ready(summary: dict[str, Any]) -> None:
    if str(summary.get("overall_state", "")) != "qualitative_writeback_ready":
        raise RuntimeError(
            f"LLM critic go/no-go must be qualitative_writeback_ready; got {summary.get('overall_state', 'missing')!r}"
        )


def build_receipt_row(brief_rows: list[dict[str, str]]) -> dict[str, str]:
    case_ids = ", ".join(row["case_id"] for row in brief_rows)
    return {
        "execution_status": "qualitative_writeback_complete",
        "review_scope": "light_mid_qualitative_brief",
        "case_id": case_ids or "LightOverlap,MidOverlap",
        "review_outcome": (
            "Qualitative Light/Mid critic brief written back under qualitative/demo labeling; "
            "no verified transcript repair applied."
        ),
        "brief_artifact": "results/figures/llm_critic_qualitative_brief_light_mid.md",
        "expected_inputs": "Gold CER/error/risk tables plus qualitative review queue completion.",
        "writeback_note": (
            "Heuristic qualitative brief only; does not claim LLM runtime execution or verified correction."
        ),
    }


def build_fill_row(brief_rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "light_mid_qualitative_brief",
        "case_scope": ",".join(row["case_id"] for row in brief_rows),
        "brief_case_count": str(len(brief_rows)),
        "execution_receipt_status": "qualitative_writeback_complete",
        "blocker": "none_documented",
        "fill_note": "Filled qualitative writeback after Light/Mid brief generation.",
    }


def build_fill_lines(row: dict[str, str]) -> list[str]:
    return [
        "# LLM Critic Qualitative Writeback",
        "",
        "qualitative/demo only — not verified repair.",
        "",
        "| fill_status | writeback_scope | case_scope | brief_case_count | execution_receipt_status | blocker |",
        "| --- | --- | --- | ---: | --- | --- |",
        (
            f"| {row['fill_status']} | {row['writeback_scope']} | {row['case_scope']} | "
            f"{row['brief_case_count']} | {row['execution_receipt_status']} | {row['blocker']} |"
        ),
    ]


def build_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# LLM Critic Review Receipt (Qualitative Writeback)",
        "",
        "| execution_status | review_scope | case_id | brief_artifact | writeback_note |",
        "| --- | --- | --- | --- | --- |",
        (
            f"| {row['execution_status']} | {row['review_scope']} | {row['case_id']} | "
            f"{row['brief_artifact']} | {row['writeback_note']} |"
        ),
    ]


def write_fill_outputs(fill_row: dict[str, str], receipt_row: dict[str, str]) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    fill_csv = tables_dir / "llm_critic_qualitative_writeback.csv"
    fill_json = tables_dir / "llm_critic_qualitative_writeback.json"
    fill_md = figures_dir / "llm_critic_qualitative_writeback.md"
    receipt_json = tables_dir / "llm_critic_review_receipt.json"
    receipt_md = figures_dir / "llm_critic_review_receipt.md"

    with fill_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILL_COLUMNS)
        writer.writeheader()
        writer.writerow(fill_row)
    fill_json.write_text(json.dumps(fill_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fill_md.write_text("\n".join(build_fill_lines(fill_row)) + "\n", encoding="utf-8")
    receipt_json.write_text(json.dumps([receipt_row], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt_md.write_text("\n".join(build_receipt_lines(receipt_row)) + "\n", encoding="utf-8")
    return fill_csv, fill_json, fill_md, receipt_json, receipt_md


def run_qualitative_writeback(force: bool = False) -> dict[str, str]:
    summary = load_go_no_go_summary()
    assert_writeback_ready(summary)

    receipt_path = PROJECT_ROOT / "results/tables/llm_critic_review_receipt.json"
    if receipt_path.exists() and not force:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        if isinstance(payload, list) and payload:
            status = str(payload[0].get("execution_status", ""))
            if status == "qualitative_writeback_complete":
                return {"fill_status": "already_filled", "execution_receipt_status": status}

    brief_rows, summary_rows = build_brief_report()
    write_brief_outputs(brief_rows, summary_rows)
    receipt_row = build_receipt_row(brief_rows)
    fill_row = build_fill_row(brief_rows)
    write_fill_outputs(fill_row, receipt_row)
    return {
        "fill_status": fill_row["fill_status"],
        "execution_receipt_status": fill_row["execution_receipt_status"],
        "brief_case_count": fill_row["brief_case_count"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill LLM critic qualitative writeback for Light/Mid cases.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled writeback receipt.")
    return parser.parse_args()


def main() -> None:
    _ = load_config()
    args = parse_args()
    result = run_qualitative_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
