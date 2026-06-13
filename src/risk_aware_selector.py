from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .evaluate_cer import (
    aggregate_speaker_text,
    compute_cer,
    levenshtein_distance,
    list_verified_cases,
    load_json,
    load_reference,
    normalize_text,
    repetition_count_from_text,
)


CSV_COLUMNS = [
    "case_id",
    "overlap_level",
    "base_router_method",
    "final_selected_method",
    "risk_level",
    "risk_reasons",
    "recommended_action",
    "text_length_ratio",
    "duplicate_removed_count",
    "speaker_length_imbalance",
    "method_disagreement_score",
    "notes",
]

PERFORMANCE_COLUMNS = ["strategy", "average_cer"]

METHOD_ORDER = ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reference-free risk-aware final selector.")
    parser.add_argument("--case", required=True, help="Audio case id, e.g. NoOverlap, or all")
    return parser.parse_args()


repeat_phrase_count = repetition_count_from_text


def adjacent_repeat_count(segments: list[dict[str, Any]]) -> int:
    count = 0
    prev = ""
    for seg in segments:
        text = normalize_text(str(seg.get("text", "")))
        if text and text == prev:
            count += 1
        prev = text
    return count


def load_table(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing table: {path.relative_to(PROJECT_ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [row for row in csv.DictReader(f) if isinstance(row, dict)]


def load_map(path: Path, key_field: str) -> dict[str, dict[str, Any]]:
    rows = load_table(path)
    mapping: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row.get(key_field, "")).strip()
        if key:
            mapping[key] = row
    return mapping


def load_case_ids(case_arg: str) -> list[str]:
    if case_arg == "all":
        return list_verified_cases()
    return [case_arg]


def speaker_lengths_from_segments(segments: list[dict[str, Any]]) -> tuple[int, int]:
    s1 = len(aggregate_speaker_text(segments, "SPEAKER_1"))
    s2 = len(aggregate_speaker_text(segments, "SPEAKER_2"))
    return s1, s2


def compute_risk_features(
    case_id: str,
    base_v2_row: dict[str, Any],
    base_v1_row: dict[str, Any],
) -> dict[str, Any]:
    mixed_path = PROJECT_ROOT / "results" / "transcripts_raw" / f"{case_id}_mixed_whisper.json"
    separated_path = PROJECT_ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json"
    cleaned_path = PROJECT_ROOT / "results" / "transcripts_postprocessed" / f"{case_id}_separated_speaker_transcript_cleaned.json"

    mixed = load_json(mixed_path)
    separated = load_json(separated_path)
    cleaned = load_json(cleaned_path) if cleaned_path.exists() else {}

    mixed_text = str(mixed.get("text", ""))
    separated_text = str(separated.get("full_text", ""))
    cleaned_text = str(cleaned.get("cleaned_full_text", ""))
    separated_segments = list(separated.get("segments", []))
    cleaned_segments = list(cleaned.get("cleaned_segments", []))
    s1_len, s2_len = speaker_lengths_from_segments(separated_segments)
    speaker_len_total = max(s1_len, s2_len, 1)

    text_length_ratio = round(len(separated_text) / len(mixed_text), 6) if mixed_text else 0.0
    cleaned_to_separated_ratio = round(len(cleaned_text) / len(separated_text), 6) if separated_text else 0.0
    duplicate_removed_count = int(float(str(cleaned.get("removed_count", 0) or 0)))
    repetition_count = adjacent_repeat_count(separated_segments) + repetition_count_from_text(separated_text)
    speaker_length_imbalance = round(abs(s1_len - s2_len) / speaker_len_total, 6)
    method_disagreement_score = round(
        abs(len(separated_text) - len(mixed_text)) / max(len(separated_text), len(mixed_text), 1), 6
    )

    return {
        "mixed": mixed,
        "separated": separated,
        "cleaned": cleaned,
        "mixed_text": mixed_text,
        "separated_text": separated_text,
        "cleaned_text": cleaned_text,
        "text_length_ratio": text_length_ratio,
        "cleaned_to_separated_ratio": cleaned_to_separated_ratio,
        "duplicate_removed_count": duplicate_removed_count,
        "repetition_count": repetition_count,
        "speaker_length_imbalance": speaker_length_imbalance,
        "method_disagreement_score": method_disagreement_score,
        "base_v2_method": str(base_v2_row.get("selected_method", "")).strip(),
        "base_v1_method": str(base_v1_row.get("selected_method", "")).strip(),
        "base_v2_row": base_v2_row,
        "base_v1_row": base_v1_row,
    }


def classify_risk(features: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if features["repetition_count"] >= 6:
        reasons.append("repetition_hallucination_risk")
    elif features["repetition_count"] >= 3:
        reasons.append("repetition_hallucination_risk")

    if features["text_length_ratio"] >= 2.35:
        reasons.append("length_inflation_risk")

    if features["speaker_length_imbalance"] >= 0.35:
        reasons.append("speaker_imbalance_risk")

    if features["duplicate_removed_count"] >= 8 and features["cleaned_text"] and features["cleaned_to_separated_ratio"] <= 0.82:
        reasons.append("cleaned_over_deletion_risk")

    if features["method_disagreement_score"] >= 0.35:
        reasons.append("method_disagreement_risk")

    if not reasons:
        return "low", ["low_risk"]
    if len(reasons) == 1:
        return "medium", reasons
    if "cleaned_over_deletion_risk" in reasons and "speaker_imbalance_risk" in reasons:
        return "high", reasons
    if len(reasons) >= 3:
        return "high", reasons
    return "medium", reasons


def choose_final_method(features: dict[str, Any], risk_level: str, risk_reasons: list[str]) -> tuple[str, str]:
    base = features["base_v2_method"]
    overlap_level = int(features["base_v2_row"].get("overlap_level", 0))
    cleaned_exists = bool(features["cleaned_text"])
    cleaned_removed = int(features["duplicate_removed_count"])
    cleaned_ratio = float(features["cleaned_to_separated_ratio"])
    text_length_ratio = float(features["text_length_ratio"])

    repeated = "repetition_hallucination_risk" in risk_reasons
    inflated = "length_inflation_risk" in risk_reasons
    speaker_bad = "speaker_imbalance_risk" in risk_reasons
    cleaned_over = "cleaned_over_deletion_risk" in risk_reasons

    if base == "separated_whisper":
        if (repeated or inflated) and cleaned_exists and not cleaned_over and cleaned_removed <= 8 and cleaned_ratio >= 0.75:
            return "separated_whisper_cleaned", "repair separated output with cleaned transcript"
        if (repeated or inflated) and (cleaned_over or speaker_bad):
            return "mixed_whisper", "separated output is unstable and cleaned is not trustworthy"
        return "separated_whisper", "base separated output is stable enough"

    if base == "mixed_whisper":
        if overlap_level >= 3 and not (repeated or inflated or speaker_bad):
            return "separated_whisper", "high-overlap case with stable separated output"
        return "mixed_whisper", "keep mixed output because separated looks risky"

    if base == "separated_whisper_cleaned":
        if cleaned_over or speaker_bad:
            return "mixed_whisper", "cleaned output looks over-deleted or unbalanced"
        if repeated or inflated:
            return "separated_whisper_cleaned", "use cleaned transcript as the safest repair"
        return "separated_whisper_cleaned", "cleaned transcript is stable"

    if risk_level == "high" and (repeated or inflated or speaker_bad):
        return "manual_review", "risk is high and automatic selection is not reliable"
    return base, "fallback to base router"


def build_selection_row(case_id: str, features: dict[str, Any]) -> dict[str, Any]:
    risk_level, risk_reasons = classify_risk(features)
    final_selected_method, recommended_action = choose_final_method(features, risk_level, risk_reasons)

    notes = (
        "Reference-free selector uses only transcript stability signals; CER is reserved for evaluation."
    )
    if features["base_v2_method"] != features["base_v1_method"]:
        notes += " Base routers disagree on this case."
    else:
        notes += " Base routers agree on this case."

    return {
        "case_id": case_id,
        "overlap_level": int(features["base_v2_row"].get("overlap_level", 0)),
        "base_router_method": features["base_v2_method"],
        "final_selected_method": final_selected_method,
        "risk_level": risk_level,
        "risk_reasons": ";".join(risk_reasons),
        "recommended_action": recommended_action,
        "text_length_ratio": features["text_length_ratio"],
        "duplicate_removed_count": features["duplicate_removed_count"],
        "speaker_length_imbalance": features["speaker_length_imbalance"],
        "method_disagreement_score": features["method_disagreement_score"],
        "notes": notes,
    }


def write_csv_json(rows: list[dict[str, Any]], csv_path: Path, json_path: Path, fieldnames: list[str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def build_performance(rows: list[dict[str, Any]], cer_lookup: dict[tuple[str, str], float]) -> list[dict[str, Any]]:
    strategies = [
        "fixed_mixed_whisper",
        "fixed_separated_whisper",
        "fixed_separated_whisper_cleaned",
        "router_v1",
        "router_v2",
        "risk_aware_selector",
        "oracle_best",
    ]
    selected_map = {row["case_id"]: row for row in rows}

    routing_decisions_path = PROJECT_ROOT / "results" / "tables" / "routing_decisions.csv"
    router_v1_lookup: dict[str, str] = {}
    if routing_decisions_path.exists():
        for rrow in load_table(routing_decisions_path):
            cid = str(rrow.get("case_id", "")).strip()
            method = str(rrow.get("selected_method", "")).strip()
            if cid:
                router_v1_lookup[cid] = method

    performance: list[dict[str, Any]] = []

    for strategy in strategies:
        values: list[float] = []
        for case_id, row in selected_map.items():
            if strategy == "oracle_best":
                available = [
                    cer_lookup.get((case_id, method))
                    for method in METHOD_ORDER
                ]
                available = [v for v in available if v is not None]
                if available:
                    values.append(min(available))
                continue
            if strategy == "fixed_mixed_whisper":
                method = "mixed_whisper"
            elif strategy == "fixed_separated_whisper":
                method = "separated_whisper"
            elif strategy == "fixed_separated_whisper_cleaned":
                method = "separated_whisper_cleaned"
            elif strategy == "router_v1":
                method = router_v1_lookup.get(case_id, "")
            elif strategy == "router_v2":
                method = row["base_router_method"]
            elif strategy == "risk_aware_selector":
                method = row["final_selected_method"]
            else:
                method = None

            if method and method != "manual_review":
                cer = cer_lookup.get((case_id, method))
                if cer is not None:
                    values.append(cer)

        performance.append(
            {
                "strategy": strategy,
                "average_cer": round(sum(values) / len(values), 6) if values else 0.0,
            }
        )
    return performance


def render_summary(rows: list[dict[str, Any]], performance: list[dict[str, Any]], manual_review_count: int, coverage: float) -> Path:
    output_path = PROJECT_ROOT / "results" / "figures" / "risk_aware_selection_summary.md"
    perf_map = {row["strategy"]: row["average_cer"] for row in performance}
    lines = [
        "# Risk-Aware Final Selector Summary",
        "",
        "## Selection Table",
        "",
        "| case_id | final_selected_method | risk_level | risk_reasons |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['case_id']} | {row['final_selected_method']} | {row['risk_level']} | {row['risk_reasons']} |"
        )
    lines += [
        "",
        "## Performance",
        "",
        "| strategy | average_cer |",
        "| --- | ---: |",
    ]
    for strategy in [
        "fixed_mixed_whisper",
        "fixed_separated_whisper",
        "fixed_separated_whisper_cleaned",
        "router_v1",
        "router_v2",
        "risk_aware_selector",
        "oracle_best",
    ]:
        lines.append(f"| {strategy} | {perf_map[strategy]} |")
    lines += [
        "",
        "## Deployment Notes",
        "",
        f"- coverage: {coverage:.6f}",
        f"- manual_review_count: {manual_review_count}",
        "- The selector is reference-free during decision making; CER is only used after the selection is fixed.",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def update_current_summary(summary_path: Path) -> None:
    current_path = PROJECT_ROOT / "results" / "figures" / "current_results_summary.md"
    text = current_path.read_text(encoding="utf-8-sig") if current_path.exists() else "# Current Results Summary\n"
    marker = "## Post-hoc Risk Detection and Selective Repair\n"
    if marker in text:
        text = text.split(marker)[0].rstrip()
    lines = [
        "",
        "## Post-hoc Risk Detection and Selective Repair",
        "",
        "- cpCER-lite did not find a speaker swap problem in the verified gold cases; direct speaker assignment was always best.",
        "- The remaining errors are mostly content-level insertion and repetition issues, not speaker permutation issues.",
        "- The risk-aware selector is reference-free: it only uses transcript stability signals to pick a final output.",
        "- Ground-truth CER is reserved for after-the-fact evaluation and is never used for selection.",
        "",
        f"- Detailed risk-aware summary: {summary_path.relative_to(PROJECT_ROOT).as_posix()}",
    ]
    current_path.write_text(text.rstrip() + "\n" + "\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    _ = load_config()
    if args.case == "all":
        cases = list_verified_cases()
    else:
        cases = [args.case]

    v2_rows = load_map(PROJECT_ROOT / "results" / "tables" / "routing_decisions_v2.csv", "case_id")
    v1_rows = load_map(PROJECT_ROOT / "results" / "tables" / "routing_decisions.csv", "case_id")
    cer_rows = load_table(PROJECT_ROOT / "results" / "tables" / "cer_results.csv")
    cer_lookup: dict[tuple[str, str], float] = {}
    for row in cer_rows:
        case_id = str(row.get("case_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if case_id and method:
            try:
                cer_lookup[(case_id, method)] = float(str(row.get("cer", "0")).strip())
            except Exception:
                continue

    selection_rows: list[dict[str, Any]] = []
    for case_id in cases:
        if case_id not in v2_rows or case_id not in v1_rows:
            print(f"warning: missing router rows for {case_id}")
            continue
        features = compute_risk_features(case_id, v2_rows[case_id], v1_rows[case_id])
        selection_rows.append(build_selection_row(case_id, features))

    selection_csv = PROJECT_ROOT / "results" / "tables" / "risk_aware_selection.csv"
    selection_json = PROJECT_ROOT / "results" / "tables" / "risk_aware_selection.json"
    write_csv_json(selection_rows, selection_csv, selection_json, CSV_COLUMNS)

    performance_rows = build_performance(selection_rows, cer_lookup)
    performance_csv = PROJECT_ROOT / "results" / "tables" / "risk_aware_performance.csv"
    performance_json = PROJECT_ROOT / "results" / "tables" / "risk_aware_performance.json"
    write_csv_json(performance_rows, performance_csv, performance_json, PERFORMANCE_COLUMNS)

    manual_review_count = sum(1 for row in selection_rows if row["final_selected_method"] == "manual_review")
    coverage = 0.0
    if selection_rows:
        coverage = round((len(selection_rows) - manual_review_count) / len(selection_rows), 6)
    summary_md = render_summary(selection_rows, performance_rows, manual_review_count, coverage)
    update_current_summary(summary_md)

    print(f"Wrote risk-aware selection: {selection_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote risk-aware performance: {performance_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote risk-aware summary: {summary_md.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
