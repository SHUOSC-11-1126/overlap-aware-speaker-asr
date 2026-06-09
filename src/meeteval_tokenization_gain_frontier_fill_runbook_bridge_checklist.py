from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "runbook_status",
    "recommended_frontier",
    "prerequisite_artifact",
    "execution_receipt_target",
    "checklist_goal",
    "bridge_note",
    "guardrail_note",
    "next_gate",
]


def load_runbook_card() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_tokenization_gain_frontier_fill_runbook_card.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(runbook: dict[str, str]) -> list[dict[str, str]]:
    if not runbook:
        return []

    frontier = str(runbook.get("recommended_frontier", "meeteval_compatibility"))
    runbook_status = str(runbook.get("runbook_status", "tokenization_gain_frontier_fill_runbook_pending"))
    ratio = str(runbook.get("adapted_case_ratio", "0/0"))
    completion_signal = str(runbook.get("completion_signal", ""))
    return [
        {
            "checklist_order": "1",
            "runbook_status": runbook_status,
            "recommended_frontier": frontier,
            "prerequisite_artifact": "results/figures/meeteval_tokenization_gain_frontier_fill_runbook_card.md",
            "execution_receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
            "checklist_goal": (
                f"Verify the tokenization gain frontier fill runbook for {frontier} before updating the execution receipt."
            ),
            "bridge_note": (
                f"Runbook status={runbook_status}; adapted_case_ratio={ratio}; "
                f"completion_signal={completion_signal}."
            ),
            "guardrail_note": str(runbook.get("guardrail_note", "")),
            "next_gate": "Confirm this bridge only after real execution evidence is ready for the MeetEval receipt.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval Tokenization Gain Frontier Fill Runbook Bridge Checklist",
        "",
        "This generated checklist connects the tokenization gain frontier fill runbook card to the MeetEval "
        "execution receipt. It remains experimental/frontier coordination only.",
        "",
        "| checklist_order | runbook_status | recommended_frontier | prerequisite_artifact | execution_receipt_target | checklist_goal | bridge_note | guardrail_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['runbook_status']} | {row['recommended_frontier']} | "
            f"{row['prerequisite_artifact']} | {row['execution_receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['guardrail_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist.csv"
    json_path = tables_dir / "meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist.json"
    md_path = figures_dir / "meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_runbook_card())
    if not rows:
        print("Tokenization gain frontier fill runbook card not found; bridge checklist not written.")
        return
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote MeetEval tokenization gain frontier fill runbook bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval tokenization gain frontier fill runbook bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval tokenization gain frontier fill runbook bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
