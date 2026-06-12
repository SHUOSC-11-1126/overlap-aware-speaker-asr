from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config


POLISH_COLUMNS = [
    "section_id",
    "headline",
    "artifact_anchor",
    "presentation_note",
    "result_label",
]

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


def assert_writeback_ready(summary: dict[str, Any]) -> None:
    if str(summary.get("overall_state", "")) != "presentation_writeback_ready":
        raise RuntimeError(
            f"Demo go/no-go must be presentation_writeback_ready; got {summary.get('overall_state', 'missing')!r}"
        )


def build_polish_rows() -> list[dict[str, str]]:
    return [
        {
            "section_id": "hero",
            "headline": "Overlap-aware speaker ASR: when separation helps and when it hurts",
            "artifact_anchor": "README.md",
            "presentation_note": "Lead with the stable gold baseline finding before any frontier claim.",
            "result_label": "qualitative/demo",
        },
        {
            "section_id": "architecture",
            "headline": "Mixed → separated → cleaned ASR with risk-aware routing",
            "artifact_anchor": "results/figures/frontier_status_checklist.md",
            "presentation_note": "Point visitors to the frontier status checklist for module map context.",
            "result_label": "qualitative/demo",
        },
        {
            "section_id": "results",
            "headline": "Verified gold CER tables and phase/boundary diagnostics",
            "artifact_anchor": "results/tables/cer_results.csv",
            "presentation_note": "Keep gold and experimental/frontier tables visually separated in any README refresh.",
            "result_label": "qualitative/demo",
        },
        {
            "section_id": "frontier_wave3",
            "headline": "External AISHELL-4 sanity-check slice (not gold)",
            "artifact_anchor": "results/figures/external_validation_narrow_audio_eval.md",
            "presentation_note": "Label external validation as external/sanity-check only.",
            "result_label": "qualitative/demo",
        },
        {
            "section_id": "frontier_wave4",
            "headline": "Receipt-fill frontier: speaker profile + LLM critic qualitative paths",
            "artifact_anchor": "results/figures/frontier_execution_receipt_fill_execution_status.md",
            "presentation_note": "Show unified receipt-fill completion without claiming live demo delivery.",
            "result_label": "qualitative/demo",
        },
    ]


def build_storyboard_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "presentation_writeback_complete",
        "storyboard_scope": "full_storyboard_queue",
        "expected_inputs": "Completed storyboard review queue and presentation polish card.",
        "expected_outputs": "Narrow storyboard narrative writeback under qualitative/demo labeling.",
        "writeback_note": (
            "Storyboard presentation writeback recorded; no live demo, recording, or public launch claimed."
        ),
    }


def build_walkthrough_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "presentation_writeback_complete",
        "walkthrough_scope": "full_walkthrough_queue",
        "expected_inputs": "Completed walkthrough review queue and presentation polish card.",
        "expected_outputs": "Diagnostic walkthrough writeback under qualitative/demo labeling.",
        "writeback_note": (
            "Walkthrough presentation writeback recorded; no live demo, recording, or public launch claimed."
        ),
    }


def build_fill_row(polish_rows: list[dict[str, str]]) -> dict[str, str]:
    return {
        "fill_status": "writeback_filled",
        "writeback_scope": "presentation_polish_card",
        "storyboard_receipt_status": "presentation_writeback_complete",
        "walkthrough_receipt_status": "presentation_writeback_complete",
        "polish_section_count": str(len(polish_rows)),
        "blocker": "none_documented",
        "fill_note": "Filled presentation polish card and both demo receipts after queue completion.",
    }


def build_polish_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# Demo Presentation Polish Card (qualitative/demo)",
        "",
        "Presentation writeback only — not a live demo or recording claim.",
        "",
        "| section_id | headline | artifact_anchor | result_label |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['section_id']} | {row['headline']} | {row['artifact_anchor']} | {row['result_label']} |"
        )
    lines.append("")
    for row in rows:
        lines.append(f"- **{row['section_id']}**: {row['presentation_note']}")
    return lines


def write_outputs(
    polish_rows: list[dict[str, str]],
    fill_row: dict[str, str],
    storyboard_receipt: dict[str, str],
    walkthrough_receipt: dict[str, str],
) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    polish_csv = tables_dir / "demo_presentation_polish_card.csv"
    polish_json = tables_dir / "demo_presentation_polish_card.json"
    polish_md = figures_dir / "demo_presentation_polish_card.md"
    fill_csv = tables_dir / "demo_presentation_writeback.csv"
    fill_json = tables_dir / "demo_presentation_writeback.json"
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

    storyboard_json.write_text(json.dumps([storyboard_receipt], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    walkthrough_json.write_text(json.dumps([walkthrough_receipt], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return polish_csv, polish_json, polish_md, fill_csv, fill_json, storyboard_json, walkthrough_json


def run_presentation_writeback(force: bool = False) -> dict[str, str]:
    summary = load_json_dict("results/tables/demo_go_no_go_summary.json")
    assert_writeback_ready(summary)

    fill_path = PROJECT_ROOT / "results/tables/demo_presentation_writeback.json"
    if fill_path.exists() and not force:
        existing = load_json_dict("results/tables/demo_presentation_writeback.json")
        if str(existing.get("fill_status", "")) == "writeback_filled":
            return {
                "fill_status": "already_filled",
                "storyboard_receipt_status": str(existing.get("storyboard_receipt_status", "")),
                "walkthrough_receipt_status": str(existing.get("walkthrough_receipt_status", "")),
            }

    polish_rows = build_polish_rows()
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
    parser = argparse.ArgumentParser(description="Fill demo presentation writeback after queue completion.")
    parser.add_argument("--force", action="store_true", help="Overwrite an already-filled presentation writeback.")
    return parser.parse_args()


def main() -> None:
    _ = load_config()
    args = parse_args()
    result = run_presentation_writeback(force=args.force)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
