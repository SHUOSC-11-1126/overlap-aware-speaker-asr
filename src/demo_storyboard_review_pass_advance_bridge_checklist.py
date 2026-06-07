from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "card_index",
    "card_title",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_storyboard_advance() -> dict[str, str]:
    advance_path = PROJECT_ROOT / "results" / "tables" / "demo_storyboard_review_pass_advance.json"
    if not advance_path.exists():
        return {}
    payload = json.loads(advance_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(advance_row: dict[str, str]) -> list[dict[str, str]]:
    card_index = str(advance_row.get("card_index", "2"))
    card_title = str(advance_row.get("card_title", "Pipeline"))
    prior_card_status = str(advance_row.get("prior_card_status", "Problem review_complete"))
    return [
        {
            "checklist_order": "1",
            "card_index": card_index,
            "card_title": card_title,
            "prerequisite_artifact": "results/figures/demo_storyboard_review_pass_advance.md",
            "receipt_target": "results/figures/demo_storyboard_review_pass.md",
            "checklist_goal": (
                f"Verify the storyboard review advance bridge for card {card_index} ({card_title}) "
                "before opening the third card review pass."
            ),
            "bridge_note": (
                f"Storyboard review advanced with prior_card_status={prior_card_status}; "
                "confirm card order before advancing to the Findings card."
            ),
            "next_gate": "Confirm this bridge before opening the demo storyboard review pass third target.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Storyboard Review Pass Advance Bridge Checklist",
        "",
        "This generated checklist turns the storyboard review advance into a row-by-row bridge verification path. "
        "It remains qualitative/demo only and does not claim live demo or recording delivery.",
        "",
        "| checklist_order | card_index | card_title | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['card_index']} | {row['card_title']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "demo_storyboard_review_pass_advance_bridge_checklist.csv"
    json_path = tables_dir / "demo_storyboard_review_pass_advance_bridge_checklist.json"
    md_path = figures_dir / "demo_storyboard_review_pass_advance_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    advance_row = load_storyboard_advance()
    rows = build_bridge_checklist_rows(advance_row)
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote demo storyboard review pass advance bridge checklist CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard review pass advance bridge checklist JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote demo storyboard review pass advance bridge checklist note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
