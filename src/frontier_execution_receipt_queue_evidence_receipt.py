from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


EVIDENCE_RECEIPT_COLUMNS = [
    "receipt_frontier",
    "receipt_action",
    "receipt_evidence",
    "receipt_completion_signal",
    "receipt_followup",
    "receipt_note",
]


def load_operator_brief() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "frontier_execution_receipt_queue_operator_brief.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_evidence_receipt_row(operator_brief: dict[str, str]) -> dict[str, str]:
    if not operator_brief:
        return {}
    frontier = str(operator_brief.get("operator_frontier", "unknown"))
    receipt_target = str(operator_brief.get("operator_receipt", ""))
    return {
        "receipt_frontier": frontier,
        "receipt_action": str(operator_brief.get("operator_action", "")),
        "receipt_evidence": str(operator_brief.get("operator_evidence", "")),
        "receipt_completion_signal": f"execution_status in {receipt_target} is no longer template_only",
        "receipt_followup": (
            "Archive the receipt queue evidence note and advance to the next frontier receipt in the handoff table."
        ),
        "receipt_note": (
            f"After the real {frontier} run, write back the evidence payload through {receipt_target}. "
            "No benchmark execution is claimed until the receipt is filled."
        ),
    }


def build_evidence_receipt_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Execution Receipt Queue Evidence Receipt",
        "",
        "This generated receipt shows what the current receipt-queue run must write back before the next contributor advances the stack. "
        "It remains experimental/frontier coordination only and does not claim benchmark execution.",
        "",
        f"- Receipt frontier: `{row['receipt_frontier']}`",
        f"- Receipt action: `{row['receipt_action']}`",
        f"- Receipt evidence: `{row['receipt_evidence']}`",
        f"- Completion signal: `{row['receipt_completion_signal']}`",
        f"- Follow-up: {row['receipt_followup']}",
        f"- Receipt note: {row['receipt_note']}",
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_queue_evidence_receipt.csv"
    json_path = tables_dir / "frontier_execution_receipt_queue_evidence_receipt.json"
    md_path = figures_dir / "frontier_execution_receipt_queue_evidence_receipt.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EVIDENCE_RECEIPT_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_evidence_receipt_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_evidence_receipt_row(load_operator_brief())
    if not row:
        print("Receipt queue operator brief not found; evidence receipt not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(
        "Wrote frontier execution receipt queue evidence receipt CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue evidence receipt JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote frontier execution receipt queue evidence receipt note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
