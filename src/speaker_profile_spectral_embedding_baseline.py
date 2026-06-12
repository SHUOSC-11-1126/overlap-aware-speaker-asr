from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .speaker_profile_audio_proxy_trial import (
    average_profile_vector,
    build_audio_proxy_row,
    extract_audio_profile_vector,
)


BASELINE_COLUMNS = [
    "case_id",
    "trial_scope",
    "trial_status",
    "text_best_alignment",
    "spectral_best_alignment",
    "signals_agree",
    "text_confidence_gap",
    "spectral_confidence_gap",
    "direct_text_score",
    "swapped_text_score",
    "direct_spectral_score",
    "swapped_spectral_score",
    "result_label",
    "observation",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_text_profile_row(case_id: str) -> dict[str, str]:
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "speaker_profile_similarity.csv"):
        if str(row.get("case_id", "")) == case_id:
            return {key: str(value) for key, value in row.items()}
    return {}


def build_baseline_row(
    case_id: str,
    text_row: dict[str, str],
    spectral_row: dict[str, str],
    trial_scope: str = "NoOverlap_only",
) -> dict[str, str]:
    text_alignment = str(text_row.get("best_alignment", "unknown"))
    spectral_alignment = str(spectral_row.get("best_audio_alignment", "unknown"))
    return {
        "case_id": case_id,
        "trial_scope": trial_scope,
        "trial_status": "executed_baseline",
        "text_best_alignment": text_alignment,
        "spectral_best_alignment": spectral_alignment,
        "signals_agree": str(text_alignment == spectral_alignment),
        "text_confidence_gap": str(text_row.get("profile_confidence_gap", "0.0")),
        "spectral_confidence_gap": str(spectral_row.get("audio_confidence_gap", "0.0")),
        "direct_text_score": str(text_row.get("direct_profile_score", "0.0")),
        "swapped_text_score": str(text_row.get("swapped_profile_score", "0.0")),
        "direct_spectral_score": str(spectral_row.get("direct_audio_score", "0.0")),
        "swapped_spectral_score": str(spectral_row.get("swapped_audio_score", "0.0")),
        "result_label": "experimental/frontier",
        "observation": (
            "Narrow spectral-embedding baseline on one gold case using snippet enrollment vectors. "
            "Diagnostic risk signal only; not voiceprint identification."
        ),
    }


def build_summary_lines(row: dict[str, str]) -> list[str]:
    return [
        "# Speaker Profile Spectral Embedding Baseline (experimental/frontier)",
        "",
        "Label: `experimental/frontier` — executes a lightweight spectral profile baseline on "
        f"{row['case_id']} and compares it with the existing text-profile proxy.",
        "",
        "| case_id | text_alignment | spectral_alignment | signals_agree | text_gap | spectral_gap | trial_status |",
        "| --- | --- | --- | --- | ---: | ---: | --- |",
        (
            f"| {row['case_id']} | {row['text_best_alignment']} | {row['spectral_best_alignment']} | "
            f"{row['signals_agree']} | {row['text_confidence_gap']} | {row['spectral_confidence_gap']} | "
            f"{row['trial_status']} |"
        ),
        "",
        f"- Observation: {row['observation']}",
    ]


def build_nooverlap_baseline_row(config: dict[str, Any]) -> dict[str, str]:
    case_id = "NoOverlap"
    text_row = load_text_profile_row(case_id)
    snippets_dir = PROJECT_ROOT / str(config["paths"]["snippets_dir"])
    separated_audio_dir = PROJECT_ROOT / str(config["paths"]["separated_audio_dir"])
    case = next(item for item in config.get("audio_cases", []) if str(item.get("id")) == case_id)

    con_vector = average_profile_vector(sorted(snippets_dir.glob("con_*.wav")))
    pro_vector = average_profile_vector(sorted(snippets_dir.glob("pro_*.wav")))
    speaker_1_vector = extract_audio_profile_vector(separated_audio_dir / str(case["separated"]["spk1"]))
    speaker_2_vector = extract_audio_profile_vector(separated_audio_dir / str(case["separated"]["spk2"]))
    spectral_row = build_audio_proxy_row(
        case_id=case_id,
        hypothesis_source=text_row.get("hypothesis_source", "separated_whisper"),
        con_vector=con_vector,
        pro_vector=pro_vector,
        speaker_1_vector=speaker_1_vector,
        speaker_2_vector=speaker_2_vector,
    )
    return build_baseline_row(case_id, text_row, spectral_row)


def write_outputs(row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "speaker_profile_spectral_embedding_baseline.csv"
    json_path = tables_dir / "speaker_profile_spectral_embedding_baseline.json"
    md_path = figures_dir / "speaker_profile_spectral_embedding_baseline.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=BASELINE_COLUMNS)
        writer.writeheader()
        writer.writerow(row)
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(build_summary_lines(row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a narrow spectral embedding baseline on NoOverlap and compare with text proxy."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    config = load_config()
    row = build_nooverlap_baseline_row(config)
    paths = write_outputs(row)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
