from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


SUMMARY_COLUMNS = [
    "case_count",
    "dominant_alignment",
    "average_confidence_gap",
    "signal_strength",
    "next_action",
]


def load_audio_proxy_rows() -> list[dict[str, str]]:
    path = PROJECT_ROOT / "results" / "tables" / "speaker_profile_audio_proxy_trial.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [{key: str(value) for key, value in row.items()} for row in csv.DictReader(f)]


def build_audio_proxy_summary_row(rows: list[dict[str, str]]) -> dict[str, str]:
    case_count = len(rows)
    swapped_count = sum(1 for row in rows if str(row.get("best_audio_alignment", "")) == "swapped")
    direct_count = sum(1 for row in rows if str(row.get("best_audio_alignment", "")) == "direct")
    average_gap = (
        round(sum(float(row.get("audio_confidence_gap", "0.0")) for row in rows) / case_count, 6)
        if case_count
        else 0.0
    )
    dominant_alignment = "swapped_bias" if swapped_count > direct_count else "direct_bias_or_tie"
    signal_strength = "weak_near_tie" if average_gap < 0.01 else "separable_signal"
    next_action = (
        "Current lightweight audio proxy does not yet justify attribution claims; keep it as frontier diagnostics only."
        if signal_strength == "weak_near_tie"
        else "A stronger embedding baseline is worth testing before any attribution claim is advanced."
    )
    return {
        "case_count": str(case_count),
        "dominant_alignment": dominant_alignment,
        "average_confidence_gap": f"{average_gap:.6f}",
        "signal_strength": signal_strength,
        "next_action": next_action,
    }


def build_audio_proxy_summary_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Audio Proxy Summary",
        "",
        "This generated card summarizes the lightweight audio-profile trial. It remains experimental/frontier and does not claim speaker identification.",
        "",
        "| case_count | dominant_alignment | average_confidence_gap | signal_strength | next_action |",
        "| ---: | --- | ---: | --- | --- |",
        (
            f"| {row['case_count']} | {row['dominant_alignment']} | {row['average_confidence_gap']} | "
            f"{row['signal_strength']} | {row['next_action']} |"
        ),
    ]


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_audio_proxy_summary.csv"
    json_path = tables_dir / "speaker_profile_audio_proxy_summary.json"
    md_path = figures_dir / "speaker_profile_audio_proxy_summary.md"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(build_audio_proxy_summary_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = load_audio_proxy_rows()
    summary_row = build_audio_proxy_summary_row(rows)
    csv_path, json_path, md_path = write_outputs(summary_row)
    print(f"Wrote speaker profile audio proxy summary CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile audio proxy summary JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote speaker profile audio proxy summary note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
