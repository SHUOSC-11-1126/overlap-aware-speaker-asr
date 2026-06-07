from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


STATUS_COLUMNS = [
    "scope",
    "case_id",
    "preflight_pass",
    "swapped_bias_detected",
    "receipt_scaffold_status",
    "execution_receipt_status",
    "execution_chain_status",
    "status_note",
]


def load_json_dict(path_rel: str) -> dict[str, str]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_receipt_template_status(path_rel: str) -> str:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return "missing"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return str(first.get("execution_status", "unknown"))
    return "unknown"


def build_status_row(
    preflight: dict[str, str],
    receipt_scaffold: dict[str, str],
    execution_receipt_status: str,
) -> dict[str, str]:
    case_id = str(preflight.get("case_id", receipt_scaffold.get("case_id", "NoOverlap")))
    preflight_pass = bool(preflight.get("preflight_pass", False))
    swapped_bias = bool(preflight.get("swapped_bias_detected", False))
    scaffold_status = str(receipt_scaffold.get("scaffold_status", "missing"))
    chain_ready = preflight_pass and scaffold_status == "receipt_scaffold_only"
    chain_status = "execution_chain_ready" if chain_ready else "execution_chain_in_progress"
    return {
        "scope": "speaker_profile_embedding_execution_chain",
        "case_id": case_id,
        "preflight_pass": str(preflight_pass),
        "swapped_bias_detected": str(swapped_bias),
        "receipt_scaffold_status": scaffold_status,
        "execution_receipt_status": execution_receipt_status,
        "execution_chain_status": chain_status,
        "status_note": (
            "experimental/frontier embedding execution-chain rollup for one verified gold case; "
            "voiceprint or embedding model execution is not claimed."
        ),
    }


def build_status_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Speaker Profile Embedding Trial Execution Status",
        "",
        "This generated note rolls up the embedding execution chain status for one verified gold case. "
        "It does not claim voiceprint success or improved speaker attribution.",
        "",
        "| scope | case_id | preflight_pass | swapped_bias_detected | receipt_scaffold_status | execution_receipt_status | execution_chain_status | status_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['case_id']} | {row['preflight_pass']} | {row['swapped_bias_detected']} | "
            f"{row['receipt_scaffold_status']} | {row['execution_receipt_status']} | {row['execution_chain_status']} | "
            f"{row['status_note']} |"
        ),
    ]
    return lines


def write_outputs(status_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_embedding_trial_execution_status.csv"
    json_path = tables_dir / "speaker_profile_embedding_trial_execution_status.json"
    md_path = figures_dir / "speaker_profile_embedding_trial_execution_status.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=STATUS_COLUMNS)
        writer.writeheader()
        writer.writerow(status_row)
    json_path.write_text(json.dumps(status_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_status_lines(status_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    preflight = load_json_dict("results/tables/speaker_profile_embedding_trial_execution_preflight.json")
    receipt_scaffold = load_json_dict("results/tables/speaker_profile_embedding_trial_execution_receipt_scaffold.json")
    execution_receipt_status = load_receipt_template_status(
        "results/tables/speaker_profile_embedding_trial_execution_receipt.json"
    )
    status_row = build_status_row(preflight, receipt_scaffold, execution_receipt_status)
    csv_path, json_path, md_path = write_outputs(status_row)
    print(f"Wrote speaker profile embedding trial execution status CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial execution status JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile embedding trial execution status note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Execution chain status: {status_row['execution_chain_status']}")


if __name__ == "__main__":
    main()
