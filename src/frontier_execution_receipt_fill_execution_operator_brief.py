from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


OPERATOR_BRIEF_COLUMNS = [
    "operator_frontier",
    "operator_action",
    "operator_receipt",
    "operator_evidence",
    "operator_urgency",
    "operator_note",
]


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_handoff_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_handoff.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_operator_brief_row(
    summary: dict[str, str],
    handoff_rows: list[dict[str, str]],
) -> dict[str, str]:
    if not handoff_rows:
        return {}
    head = handoff_rows[0]
    awaiting = str(summary.get("awaiting_fill_execution_count", "0"))
    total = str(summary.get("total_frontier_count", "0"))
    combined = str(summary.get("combined_fill_execution_status", "fill_execution_in_progress"))
    frontier_name = str(head.get("frontier_name", "unknown"))
    return {
        "operator_frontier": frontier_name,
        "operator_action": str(head.get("recommended_action", "")),
        "operator_receipt": str(head.get("expected_outputs", "")),
        "operator_evidence": (
            "results/figures/frontier_execution_receipt_fill_execution_handoff.md; "
            "results/figures/frontier_execution_receipt_fill_execution_handoff_bridge_checklist.md"
        ),
        "operator_urgency": f"{awaiting}/{total} frontiers awaiting fill execution",
        "operator_note": (
            f"Fill execution coordination reports combined_fill_execution_status={combined}; "
            f"start with {frontier_name} as the first receipt-fill execution target. "
            "No benchmark execution is claimed until the execution receipt is filled."
        ),
    }


def build_operator_brief_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Operator Brief",
        "",
        "This generated brief gives the current frontier operator a plain-language next step summary. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        f"- Operator frontier: `{row['operator_frontier']}`",
        f"- Operator action: `{row['operator_action']}`",
        f"- Receipt target: `{row['operator_receipt']}`",
        f"- Evidence to collect: `{row['operator_evidence']}`",
        f"- Urgency: {row['operator_urgency']}",
        f"- Operator note: {row['operator_note']}",
    ]
    return lines


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_operator_brief.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_operator_brief.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_operator_brief.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=OPERATOR_BRIEF_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_operator_brief_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_operator_brief_row(load_completion_summary(), load_handoff_rows())
    if not row:
        print("No fill execution handoff rows found; operator brief not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier execution receipt fill execution operator brief CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution operator brief JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution operator brief note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
