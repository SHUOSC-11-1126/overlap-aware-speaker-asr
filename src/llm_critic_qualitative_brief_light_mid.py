from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import to_float
from .separation_phase_diagram import GOLD_CASE_TIER_ANCHOR, compute_delta_cer

TARGET_CASES = ["LightOverlap", "MidOverlap"]

BRIEF_COLUMNS = [
    "case_id",
    "overlap_ratio_anchor",
    "mixed_cer",
    "separated_cer",
    "separated_cleaned_cer",
    "dominant_error_mixed",
    "dominant_error_separated",
    "separation_harm_observed",
    "critic_hypothesis",
    "candidate_repair",
    "uncertainty_note",
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



def build_error_lookup() -> dict[tuple[str, str], dict[str, str]]:
    lookup: dict[tuple[str, str], dict[str, str]] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "error_type_summary.csv"):
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        if case_id and method:
            lookup[(case_id, method)] = {key: str(value) for key, value in row.items()}
    return lookup


def build_cer_lookup() -> dict[tuple[str, str], float]:
    lookup: dict[tuple[str, str], float] = {}
    for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv"):
        case_id = str(row.get("case_id", ""))
        method = str(row.get("method", ""))
        cer = to_float(row.get("cer"))
        if case_id and method and cer is not None:
            lookup[(case_id, method)] = cer
    return lookup


def build_risk_lookup() -> dict[str, dict[str, str]]:
    return {
        str(row.get("case_id", "")): {key: str(value) for key, value in row.items()}
        for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "risk_aware_selection.csv")
    }


def build_brief_row(
    case_id: str,
    cer_lookup: dict[tuple[str, str], float],
    error_lookup: dict[tuple[str, str], dict[str, str]],
    risk_lookup: dict[str, dict[str, str]],
) -> dict[str, str]:
    mixed = cer_lookup.get((case_id, "mixed_whisper"))
    separated = cer_lookup.get((case_id, "separated_whisper"))
    cleaned = cer_lookup.get((case_id, "separated_whisper_cleaned"))
    mixed_error = error_lookup.get((case_id, "mixed_whisper"), {})
    separated_error = error_lookup.get((case_id, "separated_whisper"), {})
    risk_row = risk_lookup.get(case_id, {})
    _, anchor_ratio = GOLD_CASE_TIER_ANCHOR.get(case_id, ("", 0.0))

    delta_sep = compute_delta_cer(mixed or 0.0, separated or 0.0) if mixed is not None and separated is not None else 0.0
    separation_harm = delta_sep > 0
    dominant_mixed = str(mixed_error.get("dominant_error_type", "unknown"))
    dominant_sep = str(separated_error.get("dominant_error_type", "unknown"))
    insertion_count = str(separated_error.get("insertion_count", "0"))
    repetition_count = str(separated_error.get("repetition_count", "0"))
    recommended_action = str(risk_row.get("recommended_action", "prefer mixed route"))

    if separation_harm and dominant_sep == "insertion":
        critic_hypothesis = (
            f"Separation likely triggers insertion-heavy ASR hallucination "
            f"(insertions={insertion_count}, repetitions={repetition_count}) in the harmful overlap band."
        )
        candidate_repair = (
            f"Prefer mixed_whisper or apply {recommended_action}; do not treat separated output as authoritative."
        )
    elif separation_harm:
        critic_hypothesis = (
            "Separation increases CER in this overlap band; error mode shift suggests unstable separated decoding."
        )
        candidate_repair = f"Route to mixed_whisper or follow selector action: {recommended_action}."
    else:
        critic_hypothesis = "Separation does not appear harmful on CER alone; critic focus is precautionary for this band."
        candidate_repair = "Keep current selector route; re-check if overlap conditions change."

    return {
        "case_id": case_id,
        "overlap_ratio_anchor": str(anchor_ratio),
        "mixed_cer": str(mixed) if mixed is not None else "",
        "separated_cer": str(separated) if separated is not None else "",
        "separated_cleaned_cer": str(cleaned) if cleaned is not None else "",
        "dominant_error_mixed": dominant_mixed,
        "dominant_error_separated": dominant_sep,
        "separation_harm_observed": str(separation_harm),
        "critic_hypothesis": critic_hypothesis,
        "candidate_repair": candidate_repair,
        "uncertainty_note": (
            "Qualitative heuristic critic only; no LLM runtime or verified transcript repair was applied."
        ),
        "result_label": "qualitative/demo",
    }


def build_brief_rows(
    case_ids: list[str] | None = None,
    cer_lookup: dict[tuple[str, str], float] | None = None,
    error_lookup: dict[tuple[str, str], dict[str, str]] | None = None,
    risk_lookup: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    active_cases = case_ids or TARGET_CASES
    cer = cer_lookup or build_cer_lookup()
    errors = error_lookup or build_error_lookup()
    risks = risk_lookup or build_risk_lookup()
    return [build_brief_row(case_id, cer, errors, risks) for case_id in active_cases]


def build_summary_rows(brief_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    if not brief_rows:
        return []
    harm_count = sum(1 for row in brief_rows if row["separation_harm_observed"] == "True")
    insertion_harm = sum(
        1
        for row in brief_rows
        if row["separation_harm_observed"] == "True" and row["dominant_error_separated"] == "insertion"
    )
    return [
        {"metric": "target_case_count", "value": str(len(brief_rows)), "label": "stable/gold"},
        {
            "metric": "separation_harm_rate",
            "value": str(round(harm_count / len(brief_rows), 4)),
            "label": "qualitative/demo",
        },
        {
            "metric": "insertion_driven_harm_count",
            "value": str(insertion_harm),
            "label": "qualitative/demo",
        },
        {
            "metric": "critic_scope",
            "value": "LightOverlap,MidOverlap",
            "label": "qualitative/demo",
        },
    ]


def build_summary_lines(
    brief_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
) -> list[str]:
    lines = [
        "# LLM Critic Qualitative Brief — Light/Mid (qualitative/demo)",
        "",
        "Label: `qualitative/demo` — heuristic critic-style brief for the harmful overlap band.",
        "No LLM runtime call; does not claim verified transcript repair.",
        "",
        "## Summary",
        "",
        "| metric | value | label |",
        "| --- | ---: | --- |",
    ]
    for row in summary_rows:
        lines.append(f"| {row['metric']} | {row['value']} | {row['label']} |")
    for brief in brief_rows:
        lines.extend(
            [
                "",
                f"## {brief['case_id']}",
                "",
                f"- Mixed CER: {brief['mixed_cer']} | Separated CER: {brief['separated_cer']}",
                f"- Dominant errors: mixed={brief['dominant_error_mixed']}, separated={brief['dominant_error_separated']}",
                f"- Separation harm: {brief['separation_harm_observed']}",
                f"- Hypothesis: {brief['critic_hypothesis']}",
                f"- Candidate repair: {brief['candidate_repair']}",
                f"- Uncertainty: {brief['uncertainty_note']}",
            ]
        )
    return lines


def build_brief_report() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    brief_rows = build_brief_rows()
    return brief_rows, build_summary_rows(brief_rows)


def write_outputs(
    brief_rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
) -> tuple[Path, Path, Path, Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    figure_dir = PROJECT_ROOT / "results" / "figures"
    table_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    csv_path = table_dir / "llm_critic_qualitative_brief_light_mid.csv"
    json_path = table_dir / "llm_critic_qualitative_brief_light_mid.json"
    summary_csv_path = table_dir / "llm_critic_qualitative_brief_light_mid_summary.csv"
    summary_json_path = table_dir / "llm_critic_qualitative_brief_light_mid_summary.json"
    md_path = figure_dir / "llm_critic_qualitative_brief_light_mid.md"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRIEF_COLUMNS)
        writer.writeheader()
        writer.writerows(brief_rows)
    json_path.write_text(json.dumps(brief_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerows(summary_rows)
    summary_json_path.write_text(
        json.dumps(summary_rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text("\n".join(build_summary_lines(brief_rows, summary_rows)) + "\n", encoding="utf-8")
    return csv_path, json_path, summary_csv_path, summary_json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate qualitative critic brief for Light/Mid gold overlap cases."
    )
    return parser.parse_args()


def main() -> None:
    _ = parse_args()
    _ = load_config()
    brief_rows, summary_rows = build_brief_report()
    paths = write_outputs(brief_rows, summary_rows)
    for path in paths:
        print(f"Wrote: {path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
