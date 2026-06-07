from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


FILL_STATUS_COLUMNS = [
    "fill_order",
    "frontier_name",
    "receipt_path",
    "execution_status",
    "readiness_status",
    "fill_status",
    "fill_note",
]

TEMPLATE_STATUSES = {"template_only", "receipt_scaffold_only", "scaffold_only"}


def load_handoff_rows() -> list[dict[str, str]]:
    handoff_path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_queue_handoff.json"
    if not path_exists(handoff_path):
        return []
    payload = json.loads(handoff_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def path_exists(path: Path) -> bool:
    return path.exists()


def load_receipt_execution_status(receipt_rel: str) -> str:
    path = PROJECT_ROOT / receipt_rel
    if not path.exists():
        return "missing"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return str(first.get("execution_status", "unknown"))
    if isinstance(payload, dict):
        return str(payload.get("execution_status", "unknown"))
    return "unknown"


def derive_fill_status(execution_status: str, readiness_status: str) -> str:
    if readiness_status != "receipt_ready_to_fill":
        return "fill_blocked"
    if execution_status in TEMPLATE_STATUSES:
        return "awaiting_fill"
    if execution_status == "missing":
        return "receipt_missing"
    return "fill_complete"


def build_fill_status_rows(handoff_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for handoff in handoff_rows:
        order = str(handoff.get("handoff_order", len(rows) + 1))
        frontier_name = str(handoff.get("frontier_name", "unknown"))
        readiness_status = str(handoff.get("readiness_status", "receipt_not_ready"))
        receipt_path = str(handoff.get("expected_outputs", ""))
        execution_status = load_receipt_execution_status(receipt_path) if receipt_path else "missing"
        fill_status = derive_fill_status(execution_status, readiness_status)
        rows.append(
            {
                "fill_order": order,
                "frontier_name": frontier_name,
                "receipt_path": receipt_path,
                "execution_status": execution_status,
                "readiness_status": readiness_status,
                "fill_status": fill_status,
                "fill_note": (
                    f"Receipt fill status for {frontier_name} while execution_status={execution_status}; "
                    "no benchmark execution or external audio staging is claimed."
                ),
            }
        )
    return rows


def build_status_summary(rows: list[dict[str, str]]) -> dict[str, str]:
    awaiting = sum(1 for row in rows if row["fill_status"] == "awaiting_fill")
    blocked = sum(1 for row in rows if row["fill_status"] == "fill_blocked")
    complete = sum(1 for row in rows if row["fill_status"] == "fill_complete")
    total = len(rows)
    if total == 0:
        combined = "fill_queue_empty"
    elif awaiting == total:
        combined = "fill_queue_ready"
    elif complete == total:
        combined = "fill_queue_complete"
    else:
        combined = "fill_queue_in_progress"
    return {
        "scope": "frontier_execution_receipt_fill_queue",
        "total_frontier_count": str(total),
        "awaiting_fill_count": str(awaiting),
        "fill_blocked_count": str(blocked),
        "fill_complete_count": str(complete),
        "combined_fill_status": combined,
        "fill_note": (
            "experimental/frontier receipt-fill coordination rollup; "
            "template-only receipts remain unfilled and no benchmark execution is claimed."
        ),
    }


def build_fill_status_lines(rows: list[dict[str, str]], summary: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Queue Status",
        "",
        "This generated note rolls up receipt-fill status across the three frontier execution receipts. "
        "It remains experimental/frontier coordination only and does not claim benchmark completion.",
        "",
        "## Summary",
        "",
        f"- combined_fill_status: `{summary['combined_fill_status']}`",
        f"- awaiting_fill_count: `{summary['awaiting_fill_count']}/{summary['total_frontier_count']}`",
        f"- fill_complete_count: `{summary['fill_complete_count']}/{summary['total_frontier_count']}`",
        "",
        "| fill_order | frontier_name | receipt_path | execution_status | readiness_status | fill_status | fill_note |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['fill_order']} | {row['frontier_name']} | {row['receipt_path']} | "
            f"{row['execution_status']} | {row['readiness_status']} | {row['fill_status']} | {row['fill_note']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]], summary: dict[str, str]) -> tuple[Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_queue_status.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_queue_status.json"
    summary_path = tables_dir / "frontier_execution_receipt_fill_queue_summary.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_queue_status.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FILL_STATUS_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_fill_status_lines(rows, summary)) + "\n", encoding="utf-8")
    return csv_path, json_path, summary_path, md_path


def main() -> None:
    handoff_rows = load_handoff_rows()
    rows = build_fill_status_rows(handoff_rows)
    summary = build_status_summary(rows)
    csv_path, json_path, summary_path, md_path = write_outputs(rows, summary)
    print(f"Wrote frontier execution receipt fill queue status CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt fill queue status JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt fill queue summary JSON: {summary_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt fill queue status note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Combined fill status: {summary['combined_fill_status']}")


if __name__ == "__main__":
    main()
