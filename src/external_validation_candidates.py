from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


CSV_COLUMNS = [
    "dataset_name",
    "label",
    "source_note",
    "license_note",
    "fit_note",
    "first_preprocessing_step",
    "next_action",
]


def build_external_validation_candidate_rows() -> list[dict[str, str]]:
    return [
        {
            "dataset_name": "AISHELL-4",
            "label": "external/sanity-check",
            "source_note": "Official AISHELL-4 release page and paper.",
            "license_note": "Check the official license terms before local reuse.",
            "fit_note": "Chinese multi-speaker meeting data with realistic overlap and strong domain relevance.",
            "first_preprocessing_step": "Map a tiny subset into the repository speaker-reference format.",
            "next_action": "Confirm license and choose a tiny sanity-check slice.",
        },
        {
            "dataset_name": "AliMeeting",
            "label": "external/sanity-check",
            "source_note": "Official AliMeeting dataset release and paper.",
            "license_note": "Check the official license terms before local reuse.",
            "fit_note": "Meeting-style overlap and diarization structure are close to the current ASR framing.",
            "first_preprocessing_step": "Select one short meeting excerpt and normalize segment timestamps.",
            "next_action": "Confirm license and choose one compact overlap-heavy excerpt.",
        },
        {
            "dataset_name": "AMI",
            "label": "external/sanity-check",
            "source_note": "AMI Meeting Corpus distribution page.",
            "license_note": "Check the AMI corpus license and redistribution rules before use.",
            "fit_note": "Classic meeting benchmark with overlap and established evaluation conventions.",
            "first_preprocessing_step": "Extract one short meeting clip and align speaker annotations to repo schema.",
            "next_action": "Confirm license and compare one clip against current meeting-style exports.",
        },
        {
            "dataset_name": "LibriCSS",
            "label": "external/sanity-check",
            "source_note": "LibriCSS release page and benchmark paper.",
            "license_note": "Check the official license terms before local reuse.",
            "fit_note": "Overlap-heavy conversational speech is useful for a focused external overlap sanity-check.",
            "first_preprocessing_step": "Map one overlap condition into the repository transcript/reference format.",
            "next_action": "Confirm license and choose one overlap condition for a narrow sanity-check.",
        },
    ]


def build_external_validation_candidate_lines(rows: list[dict[str, str]]) -> list[str]:
    lines = [
        "# External Validation Candidates",
        "",
        "This generated note lists candidate external sanity-check datasets. It does not claim that any external benchmark has already been run.",
        "",
        "| dataset_name | label | source_note | license_note | fit_note | first_preprocessing_step | next_action |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['dataset_name']} | {row['label']} | {row['source_note']} | {row['license_note']} | "
            f"{row['fit_note']} | {row['first_preprocessing_step']} | {row['next_action']} |"
        )
    return lines


def write_outputs(rows: list[dict[str, str]]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    csv_path = tables_dir / "external_validation_candidates.csv"
    json_path = tables_dir / "external_validation_candidates.json"
    md_path = figures_dir / "external_validation_candidates.md"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_external_validation_candidate_lines(rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    rows = build_external_validation_candidate_rows()
    csv_path, json_path, md_path = write_outputs(rows)
    print(f"Wrote external validation candidates: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external validation JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote external validation note: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
