from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import PROJECT_ROOT
from .meeteval_cpwer_official_execution_alignment_audit import classify_alignment, compute_alignment_delta


SCORECARD_COLUMNS = [
    "case_id",
    "raw_official_cpwer",
    "character_level_cpwer",
    "cpwer_bridge_lite",
    "raw_to_character_gain",
    "character_to_bridge_delta",
    "adaptation_status",
    "recommendation",
]

SUMMARY_COLUMNS = [
    "scope",
    "case_count",
    "adapted_and_aligned_count",
    "average_raw_to_character_gain",
    "max_gain_case",
    "recommended_default_mode",
    "observation",
]


def load_json_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []
    return [row for row in payload if isinstance(row, dict)]


def load_bridge_lite_by_case() -> dict[str, str]:
    path = PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_bridge.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return {str(row.get("case_id", "")): str(row.get("cpwer_bridge_lite", "")) for row in reader}


def compute_gain(raw_official_cpwer: str, character_level_cpwer: str) -> str:
    if not raw_official_cpwer or not character_level_cpwer:
        return ""
    try:
        return str(round(float(raw_official_cpwer) - float(character_level_cpwer), 6))
    except ValueError:
        return ""


def build_scorecard_row(
    case_id: str,
    raw_official_cpwer: str,
    character_level_cpwer: str,
    cpwer_bridge_lite: str,
) -> dict[str, str]:
    raw_to_character_gain = compute_gain(raw_official_cpwer, character_level_cpwer)
    character_to_bridge_delta = compute_alignment_delta(character_level_cpwer, cpwer_bridge_lite)
    alignment_status = classify_alignment(character_to_bridge_delta)

    if raw_to_character_gain and alignment_status == "aligned":
        try:
            gain_value = float(raw_to_character_gain)
        except ValueError:
            gain_value = 0.0
        if gain_value > 0:
            adaptation_status = "adapted_and_aligned"
            recommendation = "Default to character_spaced MeetEval for this CJK case."
        else:
            adaptation_status = "aligned_without_gain"
            recommendation = "Character spacing is acceptable, but raw official cpWER showed no gain."
    elif character_level_cpwer and cpwer_bridge_lite:
        adaptation_status = "adapted_but_residual_drift"
        recommendation = "Inspect normalization or speaker aggregation before treating adaptation as settled."
    else:
        adaptation_status = "pending_inputs"
        recommendation = "Generate both raw and character-level official cpWER artifacts before scoring."

    return {
        "case_id": case_id,
        "raw_official_cpwer": raw_official_cpwer,
        "character_level_cpwer": character_level_cpwer,
        "cpwer_bridge_lite": cpwer_bridge_lite,
        "raw_to_character_gain": raw_to_character_gain,
        "character_to_bridge_delta": character_to_bridge_delta,
        "adaptation_status": adaptation_status,
        "recommendation": recommendation,
    }


def build_scorecard_rows(
    raw_rows: list[dict[str, str]],
    char_rows: list[dict[str, str]],
    bridge_lite_by_case: dict[str, str],
) -> list[dict[str, str]]:
    raw_by_case = {str(row.get("case_id", "")): row for row in raw_rows if str(row.get("case_id", ""))}
    char_by_case = {str(row.get("case_id", "")): row for row in char_rows if str(row.get("case_id", ""))}
    case_ids = sorted(set(raw_by_case) | set(char_by_case) | set(bridge_lite_by_case))

    return [
        build_scorecard_row(
            case_id=case_id,
            raw_official_cpwer=str(raw_by_case.get(case_id, {}).get("official_cpwer", "")),
            character_level_cpwer=str(char_by_case.get(case_id, {}).get("official_cpwer", "")),
            cpwer_bridge_lite=str(bridge_lite_by_case.get(case_id, "")),
        )
        for case_id in case_ids
    ]


def build_summary_row(rows: list[dict[str, str]]) -> dict[str, str]:
    adapted_and_aligned = [row for row in rows if row.get("adaptation_status") == "adapted_and_aligned"]
    gain_pairs: list[tuple[str, float]] = []
    for row in rows:
        gain = str(row.get("raw_to_character_gain", ""))
        if not gain:
            continue
        try:
            gain_pairs.append((str(row.get("case_id", "")), float(gain)))
        except ValueError:
            continue

    average_gain = round(sum(gain for _, gain in gain_pairs) / len(gain_pairs), 6) if gain_pairs else 0.0
    max_gain_case = max(gain_pairs, key=lambda item: item[1])[0] if gain_pairs else ""
    recommended_default_mode = (
        "character_spaced"
        if rows and len(adapted_and_aligned) == len(rows)
        else "case_by_case_review"
    )

    return {
        "scope": "meeteval_cpwer_tokenization_gain_scorecard",
        "case_count": str(len(rows)),
        "adapted_and_aligned_count": str(len(adapted_and_aligned)),
        "average_raw_to_character_gain": str(average_gain),
        "max_gain_case": max_gain_case,
        "recommended_default_mode": recommended_default_mode,
        "observation": (
            "Experimental/frontier scorecard only; it quantifies tokenization adaptation gain "
            "without claiming full MeetEval benchmark completion."
        ),
    }


def build_scorecard_lines(rows: list[dict[str, str]]) -> list[str]:
    adapted_count = sum(1 for row in rows if row.get("adaptation_status") == "adapted_and_aligned")
    lines = [
        "# MeetEval cpWER Tokenization Gain Scorecard",
        "",
        "This generated scorecard compares raw official cpWER, character-spaced official cpWER, and bridge-lite evidence. "
        "It remains experimental/frontier and does not claim full MeetEval benchmark completion.",
        "",
        f"Summary: `{adapted_count}/{len(rows)}` cases show positive adaptation gain and aligned character-level scores.",
        "",
        "| case_id | raw_official_cpwer | character_level_cpwer | cpwer_bridge_lite | raw_to_character_gain | character_to_bridge_delta | adaptation_status | recommendation |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        raw_display = row["raw_official_cpwer"] or "—"
        char_display = row["character_level_cpwer"] or "—"
        bridge_display = row["cpwer_bridge_lite"] or "—"
        gain_display = row["raw_to_character_gain"] or "—"
        delta_display = row["character_to_bridge_delta"] or "—"
        lines.append(
            f"| {row['case_id']} | {raw_display} | {char_display} | {bridge_display} | "
            f"{gain_display} | {delta_display} | {row['adaptation_status']} | {row['recommendation']} |"
        )
    return lines


def build_summary_lines(row: dict[str, str]) -> list[str]:
    lines = [
        "# MeetEval cpWER Tokenization Gain Scorecard Summary",
        "",
        "This generated summary condenses the tokenization gain scorecard into one deployment-facing recommendation. "
        "It remains experimental/frontier and does not claim full MeetEval benchmark completion.",
        "",
        "| scope | case_count | adapted_and_aligned_count | average_raw_to_character_gain | max_gain_case | recommended_default_mode | observation |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
        (
            f"| {row['scope']} | {row['case_count']} | {row['adapted_and_aligned_count']} | "
            f"{row['average_raw_to_character_gain']} | {row['max_gain_case']} | "
            f"{row['recommended_default_mode']} | {row['observation']} |"
        ),
    ]
    return lines


def write_outputs(rows: list[dict[str, str]], summary_row: dict[str, str]) -> tuple[Path, Path, Path, Path, Path, Path]:
    tables_dir = PROJECT_ROOT / "results" / "tables"
    figures_dir = PROJECT_ROOT / "results" / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    scorecard_csv = tables_dir / "meeteval_cpwer_tokenization_gain_scorecard.csv"
    scorecard_json = tables_dir / "meeteval_cpwer_tokenization_gain_scorecard.json"
    summary_csv = tables_dir / "meeteval_cpwer_tokenization_gain_scorecard_summary.csv"
    summary_json = tables_dir / "meeteval_cpwer_tokenization_gain_scorecard_summary.json"
    scorecard_md = figures_dir / "meeteval_cpwer_tokenization_gain_scorecard.md"
    summary_md = figures_dir / "meeteval_cpwer_tokenization_gain_scorecard_summary.md"

    with scorecard_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SCORECARD_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    scorecard_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    with summary_csv.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        writer.writerow(summary_row)
    summary_json.write_text(json.dumps(summary_row, ensure_ascii=False, indent=2), encoding="utf-8")

    scorecard_md.write_text("\n".join(build_scorecard_lines(rows)) + "\n", encoding="utf-8")
    summary_md.write_text("\n".join(build_summary_lines(summary_row)) + "\n", encoding="utf-8")
    return scorecard_csv, scorecard_json, summary_csv, summary_json, scorecard_md, summary_md


def main() -> None:
    raw_rows = load_json_rows(PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_official_execution.json")
    char_rows = load_json_rows(
        PROJECT_ROOT / "results" / "tables" / "meeteval_cpwer_character_level_official_execution.json"
    )
    rows = build_scorecard_rows(raw_rows, char_rows, load_bridge_lite_by_case())
    summary_row = build_summary_row(rows)
    outputs = write_outputs(rows, summary_row)

    print(f"Wrote MeetEval cpWER tokenization gain scorecard CSV: {outputs[0].relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER tokenization gain scorecard JSON: {outputs[1].relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER tokenization gain scorecard summary CSV: {outputs[2].relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER tokenization gain scorecard summary JSON: {outputs[3].relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER tokenization gain scorecard note: {outputs[4].relative_to(PROJECT_ROOT)}")
    print(f"Wrote MeetEval cpWER tokenization gain scorecard summary note: {outputs[5].relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
