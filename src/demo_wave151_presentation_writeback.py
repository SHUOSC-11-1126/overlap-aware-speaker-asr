from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .demo_presentation_writeback import POLISH_COLUMNS, build_polish_lines
from .demo_wave150_presentation_writeback import build_extended_polish_rows as build_wave151_polish_rows


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


def assert_extension_preconditions(
    wave151_receipt: dict[str, Any],
    wave150_fill: dict[str, Any],
) -> None:
    if str(wave151_receipt.get("execution_status", "")) != "wave151_exploration_baseline_closure_complete":
        raise RuntimeError(
            "Wave150 exploration baseline closure must be complete before wave151 demo extension"
        )
    if str(wave150_fill.get("fill_status", "")) != "writeback_filled":
        raise RuntimeError("Demo Wave150 presentation writeback must be filled before wave151 extension")
    if str(wave150_fill.get("storyboard_receipt_status", "")) != "wave150_presentation_extension_complete":
        raise RuntimeError(
            "Demo Wave150 storyboard receipt must be wave150_presentation_extension_complete before wave151 extension"
        )


def build_wave151_section() -> dict[str, str]:
    return {
        "section_id": "frontier_wave151",
        "headline": "Wave151 exploration+baseline closure after Wave150 MeetEval chain boundary",
        "artifact_anchor": "results/figures/wave151_exploration_baseline_closure_card.md",
        "presentation_note": (
            "Show Wave81 closure card only; LightOverlap diagnostic coordination refresh remains "
            "experimental/frontier — qualitative/demo labeling required."
        ),
        "result_label": "qualitative/demo",
    }


def build_extended_polish_rows() -> list[dict[str, str]]:
    rows = build_wave151_polish_rows()
    if any(row["section_id"] == "frontier_wave151" for row in rows):
        return rows
    return rows + [build_wave151_section()]


def build_storyboard_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "wave151_presentation_extension_complete",
        "storyboard_scope": "wave151_storyboard_extension",
        "expected_inputs": "Wave104 exploration+baseline closure card.",
        "expected_outputs": "Wave82 storyboard extension under qualitative/demo labeling.",
        "writeback_note": (
            "Wave82 storyboard extension recorded; no live demo, recording, or benchmark timing claimed."
        ),
    }


def build_walkthrough_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "wave151_presentation_extension_complete",
        "walkthrough_scope": "wave151_walkthrough_extension",
        "expected_inputs": "Wave104 exploration+baseline closure card.",
        "expected_outputs": "Wave82 walkthrough extension under qualitative/demo labeling.",
        "writeback_note": (
            "Wave82 walkthrough extension recorded; no live demo, recording, or benchmark timing claimed."
        ),
    }


def build_fill_row(polish_rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "wave151_presentation_polish_extension",
        "storyboard_receipt_status": "wave151_presentation_extension_complete",
        "walkthrough_receipt_status": "wave151_presentation_extension_complete",
        "polish_section_count": str(len(polish_rows)),
        "blocker": "controlled_benchmark_timing_pending",
        "fill_note": "Extended presentation polish card with Wave151 exploration+baseline closure section.",
    }


def write_outputs(
    polish_rows: list[dict[str, str]],
    fill_row: dict[str, str],
    storyboard_receipt: dict[str, str],
    walkthrough_receipt: dict[str, str],
) -> Path:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    polish_csv = tables_dir / "demo_presentation_polish_card.csv"
    polish_json = tables_dir / "demo_presentation_polish_card.json"
    polish_md = figures_dir / "demo_presentation_polish_card.md"
    fill_csv = tables_dir / "demo_wave151_presentation_writeback.csv"
    fill_json = tables_dir / "demo_wave151_presentation_writeback.json"
    fill_md = figures_dir / "demo_wave151_presentation_writeback.md"
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
                "# Demo Wave128 Presentation Writeback",
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
    return fill_json


def run_wave151_presentation_writeback(force: bool = False) -> dict[str, str]:
    wave151_receipt = load_json_dict("results/tables/wave151_exploration_baseline_closure_receipt.json")
    wave150_fill = load_json_dict("results/tables/demo_wave150_presentation_writeback.json")
    assert_extension_preconditions(wave151_receipt, wave150_fill)

    fill_path = PROJECT_ROOT / "results/tables/demo_wave151_presentation_writeback.json"
    if fill_path.exists() and not force:
        existing = load_json_dict("results/tables/demo_wave151_presentation_writeback.json")
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
    parser = argparse.ArgumentParser(description="Extend demo presentation polish card with Wave151 section.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled wave151 presentation writeback.")
    return parser.parse_args()


def main() -> None:
    _ = load_config()
    args = parse_args()
    result = run_wave151_presentation_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
