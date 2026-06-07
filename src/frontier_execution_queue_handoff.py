from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_order",
    "frontier_name",
    "chain_status",
    "recommended_action",
    "expected_inputs",
    "expected_outputs",
    "handoff_note",
]

FRONTIER_CHAINS = [
    ("meeteval_compatibility", "meeteval_chain_status", "meeteval_cpwer_execution_receipt.json"),
    ("speaker_profile", "speaker_profile_chain_status", "speaker_profile_embedding_trial_execution_receipt.json"),
    (
        "external_validation",
        "external_staging_chain_status",
        "external_validation_slice_staging_handoff_receipt.json",
    ),
]


def load_status_row() -> dict[str, str]:
    status_path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_status.json"
    if not status_path.exists():
        return {}
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_handoff_rows(status_row: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for order, (frontier_name, status_key, receipt_target) in enumerate(FRONTIER_CHAINS, start=1):
        chain_status = str(status_row.get(status_key, "execution_chain_in_progress"))
        action = (
            f"Fill the execution receipt at results/tables/{receipt_target} after final bridge verification."
            if chain_status == "execution_chain_ready"
            else "Complete the remaining execution-chain scaffold before opening the receipt."
        )
        rows.append(
            {
                "handoff_order": str(order),
                "frontier_name": frontier_name,
                "chain_status": chain_status,
                "recommended_action": action,
                "expected_inputs": f"results/figures/frontier_execution_queue_status.md; per-frontier status bridge checklist.",
                "expected_outputs": f"results/tables/{receipt_target}",
                "handoff_note": (
                    f"Coordination handoff for {frontier_name} while chain_status={chain_status}; "
                    "no benchmark execution or external audio staging is claimed."
                ),
            }
        )
    return rows


def build_handoff_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Queue Handoff",
        "",
        "This generated note turns the unified frontier execution-chain rollup into per-frontier handoff actions. "
        "It remains experimental/frontier coordination only and does not claim benchmark completion.",
        "",
        "| handoff_order | frontier_name | chain_status | recommended_action | expected_inputs | expected_outputs | handoff_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['handoff_order']} | {row['frontier_name']} | {row['chain_status']} | "
            f"{row['recommended_action']} | {row['expected_inputs']} | {row['expected_outputs']} | {row['handoff_note']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_handoff.csv"
    json_path = tables_dir / "frontier_execution_queue_handoff.json"
    md_path = figures_dir / "frontier_execution_queue_handoff.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    status_row = load_status_row()
    rows = build_handoff_rows(status_row)
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote frontier execution queue handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue handoff note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
