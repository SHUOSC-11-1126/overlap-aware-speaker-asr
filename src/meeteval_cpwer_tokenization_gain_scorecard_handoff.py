from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT


HANDOFF_COLUMNS = [
    "handoff_status",
    "recommended_default_mode",
    "adapted_and_aligned_count",
    "case_count",
    "handoff_target",
    "handoff_goal",
    "expected_evidence",
    "handoff_note",
]


def load_scorecard_summary() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_tokenization_gain_scorecard_summary.json"
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def build_handoff_row(summary: dict[str, str]) -> dict[str, str]:
    recommended_default_mode = str(summary.get("recommended_default_mode", "case_by_case_review"))
    adapted_and_aligned_count = str(summary.get("adapted_and_aligned_count", "0"))
    case_count = str(summary.get("case_count", "0"))
    ready = (
        recommended_default_mode == "character_spaced"
        and int(adapted_and_aligned_count or 0) == int(case_count or 0)
        and int(case_count or 0) > 0
    )
    return {
        "handoff_status": "tokenization_gain_handoff_ready" if ready else "tokenization_gain_handoff_pending",
        "recommended_default_mode": recommended_default_mode,
        "adapted_and_aligned_count": adapted_and_aligned_count,
        "case_count": case_count,
        "handoff_target": "results/figures/meeteval_cpwer_tokenization_adaptation_completion_summary.md",
        "handoff_goal": (
            "Advance tokenization adaptation completion after the gain scorecard confirms character-spaced cpWER."
        ),
        "expected_evidence": "results/tables/meeteval_cpwer_tokenization_adaptation_completion_summary.csv",
        "handoff_note": (
            "experimental/frontier tokenization gain handoff only; "
            "full MeetEval benchmark completion is not claimed."
        ),
    }


def build_handoff_lines(row: dict[str, str]) -> list[str]:
    return [
        "# MeetEval cpWER Tokenization Gain Scorecard Handoff",
        "",
        "This generated handoff turns the tokenization gain scorecard into an adaptation completion action. "
        "It does not claim full MeetEval benchmark completion.",
        "",
        "| handoff_status | recommended_default_mode | adapted_and_aligned_count | case_count | handoff_target | handoff_goal | expected_evidence | handoff_note |",
        "| --- | --- | ---: | ---: | --- | --- | --- | --- |",
        (
            f"| {row['handoff_status']} | {row['recommended_default_mode']} | "
            f"{row['adapted_and_aligned_count']} | {row['case_count']} | {row['handoff_target']} | "
            f"{row['handoff_goal']} | {row['expected_evidence']} | {row['handoff_note']} |"
        ),
    ]


def write_outputs(handoff_row: dict[str, str]) -> tuple[Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    csv_path = tables_dir / "meeteval_cpwer_tokenization_gain_scorecard_handoff.csv"
    json_path = tables_dir / "meeteval_cpwer_tokenization_gain_scorecard_handoff.json"
    md_path = figures_dir / "meeteval_cpwer_tokenization_gain_scorecard_handoff.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HANDOFF_COLUMNS)
        writer.writeheader()
        writer.writerow(handoff_row)
    json_path.write_text(json.dumps(handoff_row, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text("\n".join(build_handoff_lines(handoff_row)) + "\n", encoding="utf-8")
    return csv_path, json_path, md_path


def main() -> None:
    summary = load_scorecard_summary()
    if not summary:
        print("Tokenization gain scorecard summary not found; handoff not written.")
        return
    handoff_row = build_handoff_row(summary)
    csv_path, json_path, md_path = write_outputs(handoff_row)
    print(f"Wrote MeetEval cpWER tokenization gain scorecard handoff CSV: {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER tokenization gain scorecard handoff JSON: {json_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER tokenization gain scorecard handoff note: {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Handoff status: {handoff_row['handoff_status']}")


if __name__ == "__main__":
    main()
