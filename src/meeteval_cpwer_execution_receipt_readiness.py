from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


READINESS_COLUMNS = [
    "scope",
    "case_id",
    "execution_chain_status",
    "receipt_template_status",
    "preflight_pass",
    "readiness_status",
    "readiness_note",
]


def load_json_dict(path_rel: str) -> dict[str, str]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_receipt_template(path_rel: str) -> dict[str, str]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        first = payload[0]
        return first if isinstance(first, dict) else {}
    return {}


def build_readiness_row(status: dict[str, str], receipt: dict[str, str]) -> dict[str, str]:
    case_id = str(status.get("case_id", receipt.get("case_id", "NoOverlap")))
    chain_status = str(status.get("execution_chain_status", "execution_chain_in_progress"))
    receipt_status = str(receipt.get("execution_status", "missing"))
    preflight_pass = str(receipt.get("preflight_pass", status.get("preflight_pass", "False")))
    ready_for_template_fill = (
        chain_status == "execution_chain_ready"
        and receipt_status == "template_only"
        and preflight_pass in {"True", "true"}
    )
    ready_for_character_fill = (
        chain_status == "execution_chain_ready"
        and receipt_status in {"official_cpwer_narrow_dry_run_complete", "template_only"}
        and preflight_pass in {"True", "true"}
    )
    fill_complete = receipt_status == "character_level_cpwer_receipt_fill_complete"
    if fill_complete:
        readiness_status = "character_level_receipt_fill_complete"
    elif ready_for_template_fill or ready_for_character_fill:
        readiness_status = "receipt_ready_to_fill"
    else:
        readiness_status = "receipt_not_ready"
    return {
        "scope": "meeteval_cpwer_execution_receipt",
        "case_id": case_id,
        "execution_chain_status": chain_status,
        "receipt_template_status": receipt_status,
        "preflight_pass": preflight_pass,
        "readiness_status": readiness_status,
        "readiness_note": (
            "experimental/frontier receipt readiness for one verified gold case; "
            "official MeetEval cpWER evaluation is not claimed."
        ),
    }


def build_readiness_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# MeetEval cpWER Execution Receipt Readiness",
        "",
        "This generated note records receipt-fill readiness for one verified gold case. "
        "It does not claim official MeetEval evaluation.",
        "",
        "| scope | case_id | execution_chain_status | receipt_template_status | preflight_pass | readiness_status | readiness_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['case_id']} | {row['execution_chain_status']} | {row['receipt_template_status']} | "
            f"{row['preflight_pass']} | {row['readiness_status']} | {row['readiness_note']} |"
        ),
    ]
    return lines


def write_outputs(readiness_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_execution_receipt_readiness.csv"
    json_path = tables_dir / "meeteval_cpwer_execution_receipt_readiness.json"
    md_path = figures_dir / "meeteval_cpwer_execution_receipt_readiness.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=READINESS_COLUMNS)
        writer.writeheader()
        writer.writerow(readiness_row)
    json_path.write_text(json.dumps(readiness_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_readiness_lines(readiness_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    status = load_json_dict("results/tables/meeteval_cpwer_execution_status.json")
    receipt = load_receipt_template("results/tables/meeteval_cpwer_execution_receipt.json")
    readiness_row = build_readiness_row(status, receipt)
    csv_path, json_path, md_path = write_outputs(readiness_row)
    print(f"Wrote MeetEval cpWER execution receipt readiness CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution receipt readiness JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER execution receipt readiness note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Readiness status: {readiness_row['readiness_status']}")


if __name__ == "__main__":
    main()
