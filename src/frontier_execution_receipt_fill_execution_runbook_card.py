from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


RUNBOOK_COLUMNS = [
    "recommended_frontier",
    "recommended_action",
    "required_evidence",
    "completion_signal",
    "urgency",
    "runbook_note",
]


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_evidence_receipt() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_evidence_receipt.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_completion_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_fill_execution_completion_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_runbook_card_row(
    operator_brief: dict[str, str],
    evidence_receipt: dict[str, str],
    completion_summary: dict[str, str],
) -> dict[str, str]:
    if not operator_brief:
        return {}
    frontier = str(operator_brief.get("operator_frontier", "unknown"))
    awaiting = str(completion_summary.get("awaiting_fill_execution_count", "0"))
    total = str(completion_summary.get("total_frontier_count", "0"))
    return {
        "recommended_frontier": frontier,
        "recommended_action": str(operator_brief.get("operator_action", "")),
        "required_evidence": str(evidence_receipt.get("receipt_evidence", operator_brief.get("operator_evidence", ""))),
        "completion_signal": str(evidence_receipt.get("receipt_completion_signal", "")),
        "urgency": f"{awaiting}/{total} frontiers awaiting fill execution",
        "runbook_note": (
            f"Start with {frontier} because it is handoff_order=1 and all receipts remain template_only. "
            "No benchmark execution is claimed until the execution receipt is filled."
        ),
    }


def build_runbook_card_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# Frontier Execution Receipt Fill Execution Runbook Card",
        "",
        "This generated runbook card condenses the first fill execution action into a one-page execution card. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        f"- Recommended frontier: `{row['recommended_frontier']}`",
        f"- Recommended action: `{row['recommended_action']}`",
        f"- Required evidence: `{row['required_evidence']}`",
        f"- Completion signal: `{row['completion_signal']}`",
        f"- Urgency: {row['urgency']}",
        f"- Runbook note: {row['runbook_note']}",
    ]
    return lines


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_fill_execution_runbook_card.csv"
    json_path = tables_dir / "frontier_execution_receipt_fill_execution_runbook_card.json"
    md_path = figures_dir / "frontier_execution_receipt_fill_execution_runbook_card.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=RUNBOOK_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_runbook_card_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_runbook_card_row(
        load_operator_brief(),
        load_evidence_receipt(),
        load_completion_summary(),
    )
    if not row:
        print("Operator brief not found; runbook card not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier execution receipt fill execution runbook card CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution runbook card JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt fill execution runbook card note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
