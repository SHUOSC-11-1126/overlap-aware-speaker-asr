from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


BRIDGE_CHECKLIST_COLUMNS = [
    "checklist_order",
    "dataset_name",
    "readiness_status",
    "blocker",
    "prerequisite_artifact",
    "receipt_target",
    "checklist_goal",
    "bridge_note",
    "next_gate",
]


def load_readiness_row() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "external_validation_slice_staging_handoff_receipt_readiness.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_bridge_checklist_rows(readiness: dict[str, str]) -> list[dict[str, str]]:
    dataset_name = str(readiness.get("dataset_name", "AISHELL-4"))
    readiness_status = str(readiness.get("readiness_status", "receipt_not_ready"))
    blocker = str(readiness.get("blocker", "license_confirmation_pending"))
    return [
        {
            "checklist_order": "1",
            "dataset_name": dataset_name,
            "readiness_status": readiness_status,
            "blocker": blocker,
            "prerequisite_artifact": "results/figures/external_validation_slice_staging_handoff_receipt_readiness.md",
            "receipt_target": "results/tables/external_validation_slice_staging_handoff_receipt.json",
            "checklist_goal": f"Verify external staging receipt readiness for {dataset_name} before any audio staging.",
            "bridge_note": (
                f"Readiness reports readiness_status={readiness_status} with blocker={blocker}; "
                "confirm receipt readiness before any external audio staging."
            ),
            "next_gate": "Confirm this bridge before claiming any external audio staging or benchmark execution.",
        }
    ]


def build_bridge_checklist_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Slice Staging Handoff Receipt Readiness Bridge Checklist",
        "",
        "This generated checklist turns the external staging receipt readiness rollup into a bridge verification path. "
        "It remains external/sanity-check coordination only and does not claim benchmark execution.",
        "",
        "| checklist_order | dataset_name | readiness_status | blocker | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['checklist_order']} | {row['dataset_name']} | {row['readiness_status']} | {row['blocker']} | "
            f"{row['prerequisite_artifact']} | {row['receipt_target']} | {row['checklist_goal']} | "
            f"{row['bridge_note']} | {row['next_gate']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "external_validation_slice_staging_handoff_receipt_readiness_bridge_checklist.csv"
    json_path = tables_dir / "external_validation_slice_staging_handoff_receipt_readiness_bridge_checklist.json"
    md_path = figures_dir / "external_validation_slice_staging_handoff_receipt_readiness_bridge_checklist.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=BRIDGE_CHECKLIST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_bridge_checklist_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_bridge_checklist_rows(load_readiness_row())
    csv_path, json_path, md_path = write_outputs(rows)
    print(
        "Wrote external validation slice staging handoff receipt readiness bridge checklist CSV: "
        f"{csv_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external validation slice staging handoff receipt readiness bridge checklist JSON: "
        f"{json_path.relative_to(PROJECT_ROOT)}"
    )
    print(
        "Wrote external validation slice staging handoff receipt readiness bridge checklist note: "
        f"{md_path.relative_to(PROJECT_ROOT)}"
    )


if __name__ == "__main__":
    main()
