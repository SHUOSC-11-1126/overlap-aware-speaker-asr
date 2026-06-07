from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .meeteval_cpwer_execution_preflight_batch import GOLD_CASES


SCAFFOLD_COLUMNS = [
    "case_id",
    "preflight_pass",
    "hypothesis_source",
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


def load_preflight_batch() -> list[dict[str, Any]]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_execution_preflight_batch.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_scaffold_row(preflight: dict[str, Any]) -> dict[str, str]:
    case_id = str(preflight.get("case_id", "NoOverlap"))
    preflight_pass = bool(preflight.get("preflight_pass", False))
    hypothesis_source = str(preflight.get("hypothesis_source", ""))
    return {
        "case_id": case_id,
        "preflight_pass": str(preflight_pass),
        "hypothesis_source": hypothesis_source,
        "scaffold_status": "receipt_batch_scaffold_only",
        "expected_inputs": (
            "results/tables/meeteval_reference_segments.jsonl; "
            "results/tables/meeteval_hypothesis_segments.jsonl; MeetEval cpWER tooling."
        ),
        "expected_outputs": "Official cpWER score and evaluation receipt for one verified gold case.",
        "scaffold_note": (
            f"Template-only batch official cpWER execution receipt scaffold for {case_id} after "
            f"preflight_pass={preflight_pass}. Official MeetEval evaluation remains pending."
        ),
    }


def build_scaffold_rows(preflight_rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    if preflight_rows:
        return [build_scaffold_row(row) for row in preflight_rows]
    return [build_scaffold_row({"case_id": case_id}) for case_id in GOLD_CASES]


def build_scaffold_lines(rows: list[dict[str, str]]) -> list[str]:
    pass_count = sum(1 for row in rows if row.get("preflight_pass") == "True")
    lines = [
        "# MeetEval cpWER Execution Receipt Batch Scaffold",
        "",
        "This generated note records template-only official cpWER execution receipt scaffolds "
        "across all five verified gold cases. It does not claim official cpWER evaluation or benchmark completion.",
        "",
        f"Summary: `{pass_count}/{len(rows)}` cases have receipt scaffolds after preflight.",
        "",
        "| case_id | preflight_pass | hypothesis_source | scaffold_status | expected_inputs | expected_outputs | scaffold_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['preflight_pass']} | {row['hypothesis_source']} | {row['scaffold_status']} | "
            f"{row['expected_inputs']} | {row['expected_outputs']} | {row['scaffold_note']} |"
        )
    return lines


def build_scaffold_receipt_rows(scaffold_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    pass_count = sum(1 for row in scaffold_rows if row.get("preflight_pass") == "True")
    return [
        {
            "execution_status": "receipt_batch_scaffold_complete",
            "scaffold_scope": "all_gold_cpwer_execution_receipt",
            "case_id": "ALL",
            "preflight_pass": str(pass_count == len(scaffold_rows) and bool(scaffold_rows)),
            "writeback_note": (
                f"Batch official cpWER execution receipt scaffolds documented for {pass_count}/{len(scaffold_rows)} "
                "cases; MeetEval benchmark completion remains pending."
            ),
        }
    ]


def build_scaffold_receipt_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Receipt Batch Scaffold Receipt",
        "",
        "This receipt records the batch execution receipt scaffold writeback. It does not claim cpWER execution.",
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
    scaffold_rows: list[dict[str, str]],
    receipt_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_receipt_batch_scaffold.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_receipt_batch_scaffold.json"
    md_path = figures_dir / "meeteval_cpwer_execution_receipt_batch_scaffold.md"
    receipt_template_path = tables_dir / "meeteval_cpwer_execution_receipt.json"
    receipt_json_path = tables_dir / "meeteval_cpwer_execution_receipt_batch_scaffold_receipt.json"
    receipt_md_path = figures_dir / "meeteval_cpwer_execution_receipt_batch_scaffold_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SCAFFOLD_COLUMNS)
        writer.writeheader()
        writer.writerows(scaffold_rows)
    json_path.write_text(json.dumps(scaffold_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_scaffold_lines(scaffold_rows)) + "\n", encoding="utf-8")

    receipt_template = [
        {
            "execution_status": "template_only",
            "run_scope": "all_gold_cpwer_execution",
            "case_id": row.get("case_id", ""),
            "hypothesis_source": row.get("hypothesis_source", ""),
            "preflight_pass": row.get("preflight_pass", ""),
            "expected_inputs": row.get("expected_inputs", ""),
            "expected_outputs": "Official cpWER score and evaluation note.",
            "writeback_note": (
                "Official MeetEval cpWER has not been executed yet; "
                "fill this receipt only after a real cpWER evaluation run."
            ),
        }
        for row in scaffold_rows
    ]
    receipt_template_path.write_text(json.dumps(receipt_template, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_json_path.write_text(json.dumps(receipt_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    receipt_md_path.write_text("\n".join(build_scaffold_receipt_lines(receipt_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path, receipt_template_path, receipt_json_path, receipt_md_path


def main() -> None:
    scaffold_rows = build_scaffold_rows(load_preflight_batch())
    receipt_rows = build_scaffold_receipt_rows(scaffold_rows)
    csv_path, json_path, md_path, receipt_template_path, receipt_json_path, receipt_md_path = write_outputs(
        scaffold_rows,
        receipt_rows,
    )
    print(f"Wrote MeetEval cpWER execution receipt batch scaffold CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution receipt batch scaffold JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution receipt batch scaffold note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution receipt template JSON: {receipt_template_path.relative_to(PROJECT_ROOT)}")
    print(
        "Wrote MeetEval cpWER execution receipt batch scaffold receipt JSON: "
        f"{receipt_json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER execution receipt batch scaffold receipt note: "
        f"{receipt_md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
