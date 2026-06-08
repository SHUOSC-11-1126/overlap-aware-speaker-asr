from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_order",
    "action_lane",
    "frontier_name",
    "combined_operator_status",
    "recommended_action",
    "expected_inputs",
    "expected_outputs",
    "handoff_note",
]


def load_json_payload(path_rel: str) -> dict | list:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, (dict, list)) else {}


def build_handoff_rows(
    status_row: dict[str, str],
    card_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    combined_status = str(status_row.get("combined_operator_status", "operator_status_unset"))
    rows: list[dict[str, str]] = []
    for order, card_row in enumerate(card_rows, start=1):
        action_lane = str(card_row.get("action_lane", ""))
        frontier_name = str(card_row.get("frontier_name", ""))
        operator_action = str(card_row.get("operator_action", ""))
        expected_output = str(card_row.get("target_artifact", ""))
        if not action_lane or not frontier_name:
            continue
        recommended_action = operator_action
        if action_lane == "blocked_lane":
            recommended_action = (
                f"{operator_action} Keep broader frontier reopening paused until the blocker artifact is updated."
            )
        rows.append(
            {
                "handoff_order": str(order),
                "action_lane": action_lane,
                "frontier_name": frontier_name,
                "combined_operator_status": combined_status,
                "recommended_action": recommended_action,
                "expected_inputs": (
                    "results/figures/frontier_operator_next_action_status.md; "
                    "results/figures/frontier_operator_next_action_status_bridge_checklist.md"
                ),
                "expected_outputs": expected_output,
                "handoff_note": (
                    f"Top-level operator handoff for {frontier_name} on {action_lane} while "
                    f"combined_operator_status={combined_status}; no frontier execution is claimed."
                ),
            }
        )
    return rows


def build_handoff_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Frontier Operator Next-Action Status Handoff",
        "",
        "This generated note turns the top-level operator status rollup into lane-specific handoff actions. "
        "It remains experimental/frontier coordination only and does not claim experiment completion.",
        "",
        "| handoff_order | action_lane | frontier_name | combined_operator_status | recommended_action | expected_inputs | expected_outputs | handoff_note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['handoff_order']} | {row['action_lane']} | {row['frontier_name']} | "
            f"{row['combined_operator_status']} | {row['recommended_action']} | {row['expected_inputs']} | "
            f"{row['expected_outputs']} | {row['handoff_note']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_operator_next_action_status_handoff.csv"
    json_path = tables_dir / "frontier_operator_next_action_status_handoff.json"
    md_path = figures_dir / "frontier_operator_next_action_status_handoff.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    status_payload = load_json_payload("results/tables/frontier_operator_next_action_status.json")
    card_payload = load_json_payload("results/tables/frontier_operator_next_action_card.json")
    rows = build_handoff_rows(
        status_payload if isinstance(status_payload, dict) else {},
        card_payload if isinstance(card_payload, list) else [],
    )
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote frontier operator next-action status handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action status handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier operator next-action status handoff note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
