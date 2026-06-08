from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


WRITEBACK_OPEN_COLUMNS = [
    "frontier_name",
    "writeback_status",
    "receipt_target",
    "open_action",
    "open_note",
]


def load_handoff_bridge_rows() -> list[dict[str, str]]:
    path = (
        PROJECT_ROOT
        / "results"
        / "tables"
        / "frontier_execution_receipt_queue_writeback_handoff_bridge_checklist.json"
    )
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def build_writeback_open_card_row(handoff_bridge_rows: list[dict[str, str]]) -> dict[str, str]:
    if not handoff_bridge_rows:
        return {}
    preferred = next(
        (row for row in handoff_bridge_rows if str(row.get("writeback_status")) != "writeback_complete"),
        handoff_bridge_rows[0],
    )
    frontier_name = str(preferred.get("frontier_name", "unknown"))
    writeback_status = str(preferred.get("writeback_status", "receipt_missing"))
    receipt_target = str(preferred.get("receipt_target", ""))
    return {
        "frontier_name": frontier_name,
        "writeback_status": writeback_status,
        "receipt_target": receipt_target,
        "open_action": (
            f"Open {receipt_target} for {frontier_name} after the writeback handoff bridge is confirmed."
        ),
        "open_note": (
            f"Writeback open card for {frontier_name} while writeback_status={writeback_status}. "
            "This remains coordination-only and does not itself fill the receipt or claim benchmark execution."
        ),
    }


def build_writeback_open_card_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Frontier Execution Receipt Queue Writeback Open Card",
        "",
        "This generated card gives the next contributor the current writeback target to open after the handoff bridge. "
        "It remains experimental/frontier coordination only and does not fill receipts or claim benchmark execution.",
        "",
        f"- Frontier name: `{row['frontier_name']}`",
        f"- Writeback status: `{row['writeback_status']}`",
        f"- Receipt target: `{row['receipt_target']}`",
        f"- Open action: {row['open_action']}",
        f"- Open note: {row['open_note']}",
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "frontier_execution_receipt_queue_writeback_open_card.csv"
    json_path = tables_dir / "frontier_execution_receipt_queue_writeback_open_card.json"
    md_path = figures_dir / "frontier_execution_receipt_queue_writeback_open_card.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=WRITEBACK_OPEN_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_writeback_open_card_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    row = build_writeback_open_card_row(load_handoff_bridge_rows())
    if not row:
        print("Writeback handoff bridge checklist not found; writeback open card not written.")
        return
    csv_path, json_path, md_path = write_outputs(row)
    print(f"Wrote frontier execution receipt queue writeback open card CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt queue writeback open card JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote frontier execution receipt queue writeback open card note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
