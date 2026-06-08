from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


READINESS_COLUMNS = [
    "frontier_name",
    "chain_status",
    "receipt_target",
    "readiness_state",
    "next_verification_artifact",
    "readiness_note",
]


def load_handoff_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_queue_handoff.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_readiness_rows(handoff_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for handoff in handoff_rows:
        frontier_name = str(handoff.get("frontier_name", "unknown"))
        chain_status = str(handoff.get("chain_status", "execution_chain_in_progress"))
        receipt_target = str(handoff.get("expected_outputs", ""))
        readiness_state = (
            "ready_for_receipt_fill"
            if chain_status == "execution_chain_ready"
            else "bridge_or_scaffold_pending"
        )
        rows.append(
            {
                "frontier_name": frontier_name,
                "chain_status": chain_status,
                "receipt_target": receipt_target,
                "readiness_state": readiness_state,
                "next_verification_artifact": (
                    "results/figures/frontier_execution_queue_handoff_bridge_checklist.md"
                ),
                "readiness_note": (
                    f"{frontier_name} currently reports readiness_state={readiness_state} "
                    f"while chain_status={chain_status}; no benchmark execution or external audio staging is claimed."
                ),
            }
        )
    return rows


def build_readiness_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Execution Queue Receipt Readiness Board",
        "",
        "This generated board summarizes which frontier receipts are ready to fill and which still need bridge or scaffold work. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        "| frontier_name | chain_status | receipt_target | readiness_state | next_verification_artifact | readiness_note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['frontier_name']} | {row['chain_status']} | {row['receipt_target']} | "
            f"{row['readiness_state']} | {row['next_verification_artifact']} | {row['readiness_note']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_queue_receipt_readiness_board.csv"
    json_path = tables_dir / "frontier_execution_queue_receipt_readiness_board.json"
    md_path = figures_dir / "frontier_execution_queue_receipt_readiness_board.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=READINESS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_readiness_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_readiness_rows(load_handoff_rows())
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote frontier execution queue receipt readiness board CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue receipt readiness board JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution queue receipt readiness board note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
