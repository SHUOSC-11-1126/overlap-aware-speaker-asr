from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .demo_presentation_writeback import POLISH_COLUMNS, build_polish_lines, build_polish_rows


FILL_COLUMNS = [
    "fill_status",
    "writeback_scope",
    "storyboard_receipt_status",
    "walkthrough_receipt_status",
    "polish_section_count",
    "blocker",
    "fill_note",
]


def load_json_dict(path_rel: str) -> dict[str, Any]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_json_rows(path_rel: str) -> list[dict[str, Any]]:
    path = PROJECT_ROOT / path_rel
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def assert_extension_preconditions(
    phase_receipt: dict[str, Any],
    demo_summary: dict[str, Any],
    existing_fill: dict[str, Any],
) -> None:
    if str(phase_receipt.get("execution_status", "")) != "phase_coordination_writeback_complete":
        raise RuntimeError(
            "Separation phase coordination must be phase_coordination_writeback_complete before wave5 demo extension"
        )
    if str(demo_summary.get("overall_state", "")) != "presentation_polish_complete":
        raise RuntimeError(
            f"Demo go/no-go must be presentation_polish_complete; got {demo_summary.get('overall_state', 'missing')!r}"
        )
    if str(existing_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Base demo presentation writeback must be filled before wave5 extension")


def build_wave5_section() -> dict[str, str]:
    return {
        "section_id": "frontier_wave5",
        "headline": "MeetEval + cascade + separation phase coordination chain",
        "artifact_anchor": "results/figures/separation_phase_coordination_card.md",
        "presentation_note": (
            "Show Wave5 coordination cards only; label MeetEval as experimental/frontier and "
            "phase diagram as boundary evidence — not deployment proof."
        ),
        "result_label": "qualitative/demo",
    }


def build_extended_polish_rows() -> list[dict[str, str]]:
    rows = build_polish_rows()
    if any(row["section_id"] == "frontier_wave5" for row in rows):
        return rows
    return rows + [build_wave5_section()]


def build_storyboard_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "wave5_presentation_extension_complete",
        "storyboard_scope": "wave5_storyboard_extension",
        "expected_inputs": "Wave5 coordination cards and completed base presentation polish.",
        "expected_outputs": "Wave5 storyboard extension under qualitative/demo labeling.",
        "writeback_note": (
            "Wave5 storyboard extension recorded; no live demo, recording, or public launch claimed."
        ),
    }


def build_walkthrough_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "wave5_presentation_extension_complete",
        "walkthrough_scope": "wave5_walkthrough_extension",
        "expected_inputs": "Wave5 coordination cards and completed base presentation polish.",
        "expected_outputs": "Wave5 walkthrough extension under qualitative/demo labeling.",
        "writeback_note": (
            "Wave5 walkthrough extension recorded; no live demo, recording, or public launch claimed."
        ),
    }


def build_fill_row(polish_rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave5_presentation_polish_extension",
        "storyboard_receipt_status": "wave5_presentation_extension_complete",
        "walkthrough_receipt_status": "wave5_presentation_extension_complete",
        "polish_section_count": str(len(polish_rows)),
        "blocker": "none_documented",
        "fill_note": (
            "Extended presentation polish card with Wave5 frontier coordination section after phase writeback."
        ),
    }


def write_outputs(
    polish_rows: list[dict[str, str]],
    fill_row: dict[str, str],
    storyboard_receipt: dict[str, str],
    walkthrough_receipt: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    polish_csv = tables_dir / "demo_presentation_polish_card.csv"
    polish_json = tables_dir / "demo_presentation_polish_card.json"
    polish_md = figures_dir / "demo_presentation_polish_card.md"
    fill_csv = tables_dir / "demo_wave5_presentation_writeback.csv"
    fill_json = tables_dir / "demo_wave5_presentation_writeback.json"
    fill_md = figures_dir / "demo_wave5_presentation_writeback.md"
    storyboard_json = tables_dir / "demo_storyboard_receipt.json"
    walkthrough_json = tables_dir / "demo_walkthrough_receipt.json"

    with polish_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=POLISH_COLUMNS)
        writer.writeheader()
        writer.writerows(polish_rows)
    polish_json.write_text(json.dumps(polish_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    polish_md.write_text("\n".join(build_polish_lines(polish_rows)) + "\n", encoding="utf-8")

    with fill_csv.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FILL_COLUMNS)
        writer.writeheader()
        writer.writerow(fill_row)
    fill_json.write_text(json.dumps(fill_row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fill_md.write_text(
        "\n".join(
            [
                "# Demo Wave5 Presentation Writeback",
                "",
                f"polish_section_count: {fill_row['polish_section_count']}",
                f"execution_receipt_status: {fill_row['storyboard_receipt_status']}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    storyboard_json.write_text(json.dumps([storyboard_receipt], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    walkthrough_json.write_text(json.dumps([walkthrough_receipt], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return fill_json, polish_md, storyboard_json, walkthrough_json, fill_md


def run_wave5_presentation_writeback(force: bool = False) -> dict[str, str]:
    phase_receipt = load_json_dict("results/tables/separation_phase_coordination_receipt.json")
    demo_summary = load_json_dict("results/tables/demo_go_no_go_summary.json")
    existing_fill = load_json_dict("results/tables/demo_presentation_writeback.json")
    assert_extension_preconditions(phase_receipt, demo_summary, existing_fill)

    fill_path = PROJECT_ROOT / "results/tables/demo_wave5_presentation_writeback.json"
    if fill_path.exists() and not force:
        existing = load_json_dict("results/tables/demo_wave5_presentation_writeback.json")
        if str(existing.get("fill_status", "")) == "writeback_filled":
            return {
                "fill_status": "already_filled",
                "polish_section_count": str(existing.get("polish_section_count", "")),
                "storyboard_receipt_status": str(existing.get("storyboard_receipt_status", "")),
            }

    polish_rows = build_extended_polish_rows()
    fill_row = build_fill_row(polish_rows)
    write_outputs(
        polish_rows,
        fill_row,
        build_storyboard_receipt_row(),
        build_walkthrough_receipt_row(),
    )
    return {
        "fill_status": fill_row["fill_status"],
        "polish_section_count": fill_row["polish_section_count"],
        "storyboard_receipt_status": fill_row["storyboard_receipt_status"],
        "walkthrough_receipt_status": fill_row["walkthrough_receipt_status"],
        "blocker": fill_row["blocker"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extend demo presentation polish card with Wave5 frontier section.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled wave5 presentation writeback.")
    return parser.parse_args()


def main() -> None:
    _ = load_config()
    args = parse_args()
    result = run_wave5_presentation_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
