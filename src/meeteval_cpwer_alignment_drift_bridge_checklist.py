from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "drift_case_count",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_drift_diagnostic_receipt() -> list[dict[str, str]]:
    receipt_path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_alignment_drift_diagnostic_receipt.json"
    if not receipt_path.exists():
        return []
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    return list(payload) if isinstance(payload, list) else []


def build_bridge_checklist_rows(receipt_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    receipt = receipt_rows[0] if receipt_rows else {}
    drift_case_count = str(receipt.get("drift_case_count", "0"))
    return [
        {
            "checklist_order": "1",
            "drift_case_count": drift_case_count,
            "prerequisite_artifact": "results/figures/meeteval_cpwer_alignment_drift_diagnostic.md",
            "receipt_target": "results/figures/meeteval_cpwer_alignment_bridge_checklist.md",
            "checklist_goal": (
                "Verify the alignment drift diagnostic bridge before opening the alignment bridge checklist."
            ),
            "bridge_note": (
                f"Drift diagnostic reports drift_case_count={drift_case_count}; confirm HeavyOverlap drift "
                "context before advancing the alignment bridge."
            ),
            "next_gate": "Confirm this bridge before opening the cpWER alignment bridge checklist target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# MeetEval cpWER Alignment Drift Bridge Checklist",
        "",
        "This generated checklist turns the drift diagnostic into a row-by-row bridge verification path. "
        "It remains experimental/frontier coordination only and does not claim cpWER execution.",
        "",
        "| checklist_order | drift_case_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['drift_case_count']} | {row['prerequisite_artifact']} | "
            f"{row['receipt_target']} | {row['checklist_goal']} | {row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_alignment_drift_bridge_checklist.csv"
    json_path = tables_dir / "meeteval_cpwer_alignment_drift_bridge_checklist.json"
    md_path = figures_dir / "meeteval_cpwer_alignment_drift_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    receipt_rows = load_drift_diagnostic_receipt()
    rows = build_bridge_checklist_rows(receipt_rows)
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote MeetEval cpWER alignment drift bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote MeetEval cpWER alignment drift bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
