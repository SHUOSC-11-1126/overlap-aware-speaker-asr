from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


READINESS_COLUMNS = [
    "scope",
    "dataset_name",
    "execution_chain_status",
    "receipt_template_status",
    "blocker",
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
    dataset_name = str(status.get("dataset_name", receipt.get("dataset_name", "AISHELL-4")))
    chain_status = str(status.get("execution_chain_status", "execution_chain_in_progress"))
    receipt_status = str(receipt.get("execution_status", "missing"))
    blocker = str(status.get("blocker", receipt.get("blocker", "license_confirmation_pending")))
    ready = chain_status == "execution_chain_ready" and receipt_status == "template_only"
    return {
        "scope": "external_validation_slice_staging_receipt",
        "dataset_name": dataset_name,
        "execution_chain_status": chain_status,
        "receipt_template_status": receipt_status,
        "blocker": blocker,
        "readiness_status": "receipt_ready_to_fill" if ready else "receipt_not_ready",
        "readiness_note": (
            "external/sanity-check receipt readiness for one narrow slice; "
            "external audio staging and benchmark evaluation are not claimed."
        ),
    }


def build_readiness_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Handoff Receipt Readiness",
        "",
        "This generated note records receipt-fill readiness for one external slice staging path. "
        "It does not claim external audio download or benchmark execution.",
        "",
        "| scope | dataset_name | execution_chain_status | receipt_template_status | blocker | readiness_status | readiness_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['dataset_name']} | {row['execution_chain_status']} | "
            f"{row['receipt_template_status']} | {row['blocker']} | {row['readiness_status']} | {row['readiness_note']} |"
        ),
    ]
    return lines


def write_outputs(readiness_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "external_validation_slice_staging_handoff_receipt_readiness.csv"
    json_path = tables_dir / "external_validation_slice_staging_handoff_receipt_readiness.json"
    md_path = figures_dir / "external_validation_slice_staging_handoff_receipt_readiness.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=READINESS_COLUMNS)
        writer.writeheader()
        writer.writerow(readiness_row)
    json_path.write_text(json.dumps(readiness_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_readiness_lines(readiness_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    status = load_json_dict("results/tables/external_validation_slice_staging_execution_status.json")
    receipt = load_receipt_template("results/tables/external_validation_slice_staging_handoff_receipt.json")
    readiness_row = build_readiness_row(status, receipt)
    csv_path, json_path, md_path = write_outputs(readiness_row)
    print(
        "Wrote external validation slice staging handoff receipt readiness CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external validation slice staging handoff receipt readiness JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external validation slice staging handoff receipt readiness note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )
    print(f"Readiness status: {readiness_row['readiness_status']}")


if __name__ == "__main__":
    main()
