from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .separation_phase_diagram import GOLD_CASE_TIER_ANCHOR
from .speaker_profile_multisignal_diagnostic import (
    build_multisignal_row,
    build_multisignal_summary_row,
)


SWEEP_COLUMNS = [
    "case_id",
    "overlap_tier",
    "overlap_ratio_anchor",
    "hypothesis_source",
    "text_best_alignment",
    "audio_best_alignment",
    "text_confidence_gap",
    "audio_confidence_gap",
    "alignment_agreement",
    "audio_support_level",
    "combined_signal_status",
    "recommended_next_step",
    "result_label",
]

SUMMARY_COLUMNS = [
    "metric",
    "value",
    "label",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_sweep_row(
    profile_row: dict[str, str],
    audio_row: dict[str, str],
) -> dict[str, str]:
    case_id = str(profile_row.get("case_id", audio_row.get("case_id", "")))
    multisignal = build_multisignal_row(profile_row, audio_row)
    _, anchor_ratio = GOLD_CASE_TIER_ANCHOR.get(case_id, ("", 0.0))
    return {
        "case_id": case_id,
        "overlap_tier": case_id,
        "overlap_ratio_anchor": str(anchor_ratio),
        "hypothesis_source": multisignal["hypothesis_source"],
        "text_best_alignment": multisignal["text_best_alignment"],
        "audio_best_alignment": multisignal["audio_best_alignment"],
        "text_confidence_gap": multisignal["text_confidence_gap"],
        "audio_confidence_gap": multisignal["audio_confidence_gap"],
        "alignment_agreement": multisignal["alignment_agreement"],
        "audio_support_level": multisignal["audio_support_level"],
        "combined_signal_status": multisignal["combined_signal_status"],
        "recommended_next_step": multisignal["recommended_next_step"],
        "result_label": "experimental/frontier",
    }


def build_summary_rows(sweep_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not sweep_rows:
        return []
    count = len(sweep_rows)
    agreement_count = sum(1 for row in sweep_rows if row["alignment_agreement"] == "agree")
    weak_support_count = sum(1 for row in sweep_rows if row["audio_support_level"] == "weak_support")
    swapped_text_count = sum(1 for row in sweep_rows if row["text_best_alignment"] == "swapped")
    multisignal_summary = build_multisignal_summary_row(sweep_rows)
    return [
        {"metric": "gold_case_count", "value": str(count), "label": "stable/gold"},
        {
            "metric": "signal_agreement_rate",
            "value": str(round(agreement_count / count, 4)),
            "label": "experimental/frontier",
        },
        {
            "metric": "weak_audio_support_rate",
            "value": str(round(weak_support_count / count, 4)),
            "label": "experimental/frontier",
        },
        {
            "metric": "swapped_text_consensus_rate",
            "value": str(round(swapped_text_count / count, 4)),
            "label": "experimental/frontier",
        },
        {
            "metric": "frontier_decision",
            "value": multisignal_summary["frontier_decision"],
            "label": "experimental/frontier",
        },
    ]


def build_summary_lines(
    sweep_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
) -> list[str]:
    lines = [
        "# Speaker Profile Multisignal Gold Sweep (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — sweeps text and audio proxy signals across all gold cases.",
        "Diagnostic risk signal only; not speaker identification.",
        "",
        "## Summary",
        "",
        "| metric | value | label |",
        "| --- | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['metric']} | {row['value']} | {row['label']} |")
    lines.extend(
        [
            "",
            "## Per-case Sweep",
            "",
            "| case_id | tier | text | audio | agreement | audio_support | status |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in sweep_rows:
        lines.append(
            f"| {row['case_id']} | {row['overlap_tier']} | {row['text_best_alignment']} | "
            f"{row['audio_best_alignment']} | {row['alignment_agreement']} | "
            f"{row['audio_support_level']} | {row['combined_signal_status']} |"
        )
    return lines


def build_sweep_report() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    profile_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "speaker_profile_similarity.csv")
    audio_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "speaker_profile_audio_proxy_trial.csv")
    audio_by_case = {str(row.get("case_id", "")): {key: str(value) for key, value in row.items()} for row in audio_rows}
    sweep_rows = [
        build_sweep_row(
            {key: str(value) for key, value in profile_row.items()},
            audio_by_case.get(str(profile_row.get("case_id", "")), {}),
        )
        for profile_row in profile_rows
    ]
    sweep_rows = sorted(sweep_rows, key=lambda row: float(row["overlap_ratio_anchor"]))
    return sweep_rows, build_summary_rows(sweep_rows)


def write_outputs(
    sweep_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "speaker_profile_multisignal_gold_sweep.csv"
    json_path = table_dir / "speaker_profile_multisignal_gold_sweep.json"
    summary_csv_path = table_dir / "speaker_profile_multisignal_gold_sweep_summary.csv"
    summary_json_path = table_dir / "speaker_profile_multisignal_gold_sweep_summary.json"
    md_path = figure_dir / "speaker_profile_multisignal_gold_sweep.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SWEEP_COLUMNS)
        writer.writeheader()
        writer.writerows(sweep_rows)
    json_path.write_text(json.dumps(sweep_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text("\n".join(build_summary_lines(sweep_rows, summary_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep multisignal speaker-profile proxies across all gold benchmark cases."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    sweep_rows, summary_rows = build_sweep_report()
    paths = write_outputs(sweep_rows, summary_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
