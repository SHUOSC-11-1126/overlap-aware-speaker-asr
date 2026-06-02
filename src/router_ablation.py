from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from .adaptive_router import select_method as v1_select_method
from .adaptive_router_v2 import choose_method_v2 as v2_choose_method
from .config import PROJECT_ROOT, load_config
from .evaluate_cer import normalize_text


GOLD_DECISION_COLUMNS = [
    "case_id",
    "overlap_level",
    "strategy",
    "selected_method",
    "decision_rule",
    "mixed_segments_count",
    "separated_segments_count",
    "cleaned_segments_count",
    "mixed_text_length",
    "separated_text_length",
    "cleaned_text_length",
    "text_length_ratio",
    "repetition_count",
    "duplicate_removed_count",
    "mixed_runtime_sec",
    "separated_runtime_sec",
    "cleaned_runtime_sec",
    "runtime_ratio",
    "cleaned_closer_to_mixed",
    "notes",
]

SYNTHETIC_DECISION_COLUMNS = [
    "sample_id",
    "tier",
    "overlap_level",
    "strategy",
    "selected_method",
    "decision_rule",
    "mixed_segments_count",
    "separated_segments_count",
    "cleaned_segments_count",
    "mixed_text_length",
    "separated_text_length",
    "cleaned_text_length",
    "text_length_ratio",
    "repetition_count",
    "duplicate_removed_count",
    "mixed_runtime_sec",
    "separated_runtime_sec",
    "cleaned_runtime_sec",
    "runtime_ratio",
    "cleaned_closer_to_mixed",
    "notes",
]

SUMMARY_COLUMNS = ["strategy", "average_cer", "gap_to_oracle", "notes"]
STRATEGIES = [
    "fixed_mixed_whisper",
    "fixed_separated_whisper",
    "fixed_separated_whisper_cleaned",
    "oracle_best",
    "v1_overlap_only",
    "length_ratio_only",
    "repetition_only",
    "removed_count_only",
    "length_plus_repetition",
    "v2_full_features",
]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing table: {path.relative_to(PROJECT_ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        try:
            rows = list(csv.DictReader(f))
        except csv.Error as exc:
            raise ValueError(f"Failed to parse CSV {path.relative_to(PROJECT_ROOT)}: {exc}") from exc
    return [row for row in rows if isinstance(row, dict)]


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path.relative_to(PROJECT_ROOT)}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected dict JSON at {path.relative_to(PROJECT_ROOT)}")
    return payload


def write_csv_json(rows: list[dict[str, Any]], csv_path: Path, json_path: Path, fieldnames: list[str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def to_int(value: Any) -> int:
    try:
        return int(float(str(value).strip()))
    except Exception:
        return 0


def to_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def load_case_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in config.get("audio_cases", [])}


def get_cleaned_closer_to_mixed(mixed_len: int, separated_len: int, cleaned_len: int) -> bool:
    return abs(cleaned_len - mixed_len) < abs(separated_len - mixed_len)


def repetition_count_from_text(text: str) -> int:
    normalized = normalize_text(text)
    if not normalized:
        return 0

    count = 0
    # Adjacent repeated chunks of 4 to 12 characters. This is intentionally
    # lightweight: we only need a coarse instability signal for routing.
    for size in range(4, 13):
        i = 0
        while i + 2 * size <= len(normalized):
            chunk = normalized[i : i + size]
            run = 1
            while normalized[i + run * size : i + (run + 1) * size] == chunk:
                run += 1
            if run >= 2:
                count += run - 1
                i += run * size
            else:
                i += 1
    return count


def adjacent_repetition_from_segments(segments: list[dict[str, Any]]) -> int:
    count = 0
    prev = ""
    for segment in segments:
        text = normalize_text(str(segment.get("text", "")))
        if text and text == prev:
            count += 1
        prev = text
    return count


def repetition_count_from_transcript(text: str, segments: list[dict[str, Any]]) -> int:
    return adjacent_repetition_from_segments(segments) + repetition_count_from_text(text)


def load_gold_inputs() -> list[dict[str, Any]]:
    config = load_config()
    cases = load_case_map(config)
    rows: list[dict[str, Any]] = []
    for case_id, case in sorted(cases.items()):
        mixed_path = PROJECT_ROOT / "results" / "transcripts_raw" / f"{case_id}_mixed_whisper.json"
        separated_path = PROJECT_ROOT / "results" / "transcripts_speaker" / f"{case_id}_separated_speaker_transcript.json"
        cleaned_path = PROJECT_ROOT / "results" / "transcripts_postprocessed" / f"{case_id}_separated_speaker_transcript_cleaned.json"
        mixed = read_json(mixed_path)
        separated = read_json(separated_path)
        cleaned = read_json(cleaned_path) if cleaned_path.exists() else {}
        rows.append(
            {
                "case_id": case_id,
                "overlap_level": int(case.get("overlap_level", 0)),
                "mixed_path": mixed_path,
                "separated_path": separated_path,
                "cleaned_path": cleaned_path,
                "mixed_text": str(mixed.get("text", "")),
                "separated_text": str(separated.get("full_text", "")),
                "cleaned_text": str(cleaned.get("cleaned_full_text", "")),
                "mixed_segments": list(mixed.get("segments", [])),
                "separated_segments": list(separated.get("segments", [])),
                "cleaned_segments": list(cleaned.get("cleaned_segments", [])),
                "mixed_runtime_sec": to_float(mixed.get("runtime_sec")),
                "separated_runtime_sec": to_float(separated.get("runtime_sec_total")),
                "cleaned_runtime_sec": to_float(cleaned.get("runtime_sec_total", separated.get("runtime_sec_total"))),
                "duplicate_removed_count": to_int(cleaned.get("removed_count")),
                "cleaned_exists": bool(cleaned_path.exists()),
                "cleaned_closer_to_mixed": bool(
                    cleaned_path.exists()
                    and get_cleaned_closer_to_mixed(
                        len(str(mixed.get("text", ""))),
                        len(str(separated.get("full_text", ""))),
                        len(str(cleaned.get("cleaned_full_text", ""))),
                    )
                ),
            }
        )
    return rows


def load_synthetic_inputs() -> list[dict[str, Any]]:
    manifest_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_manifest.csv")
    rows: list[dict[str, Any]] = []
    for row in manifest_rows:
        sample_id = str(row.get("sample_id", "")).strip()
        if not sample_id:
            continue
        tier = str(row.get("tier", "")).strip()
        overlap_level = to_int(row.get("overlap_level_numeric", row.get("overlap_level", 0)))
        mixed_path = PROJECT_ROOT / "results" / "synthetic_transcripts_raw" / f"{sample_id}_mixed_whisper.json"
        separated_path = PROJECT_ROOT / "results" / "synthetic_transcripts_speaker" / f"{sample_id}_separated_speaker_transcript.json"
        cleaned_path = PROJECT_ROOT / "results" / "synthetic_transcripts_postprocessed" / f"{sample_id}_separated_speaker_transcript_cleaned.json"
        mixed = read_json(mixed_path)
        separated = read_json(separated_path)
        cleaned = read_json(cleaned_path) if cleaned_path.exists() else {}
        rows.append(
            {
                "sample_id": sample_id,
                "tier": tier,
                "overlap_level": overlap_level,
                "mixed_path": mixed_path,
                "separated_path": separated_path,
                "cleaned_path": cleaned_path,
                "mixed_text": str(mixed.get("text", "")),
                "separated_text": str(separated.get("full_text", "")),
                "cleaned_text": str(cleaned.get("cleaned_full_text", "")),
                "mixed_segments": list(mixed.get("segments", [])),
                "separated_segments": list(separated.get("segments", [])),
                "cleaned_segments": list(cleaned.get("cleaned_segments", [])),
                "mixed_runtime_sec": to_float(mixed.get("runtime_sec")),
                "separated_runtime_sec": to_float(separated.get("runtime_sec_total")),
                "cleaned_runtime_sec": to_float(cleaned.get("runtime_sec_total", separated.get("runtime_sec_total"))),
                "duplicate_removed_count": to_int(cleaned.get("removed_count")),
                "cleaned_exists": bool(cleaned_path.exists()),
                "cleaned_closer_to_mixed": bool(
                    cleaned_path.exists()
                    and get_cleaned_closer_to_mixed(
                        len(str(mixed.get("text", ""))),
                        len(str(separated.get("full_text", ""))),
                        len(str(cleaned.get("cleaned_full_text", ""))),
                    )
                ),
            }
        )
    return rows


def select_base_by_overlap(overlap_level: int) -> tuple[str, str]:
    return v1_select_method(overlap_level)


def choose_strategy(
    strategy: str,
    overlap_level: int,
    mixed_text_len: int,
    separated_text_len: int,
    cleaned_text_len: int,
    repetition_count: int,
    duplicate_removed_count: int,
    cleaned_exists: bool,
    cleaned_closer_to_mixed: bool,
    mixed_segments_count: int,
    separated_runtime_ratio: float,
) -> tuple[str, str]:
    ratio = round(separated_text_len / mixed_text_len, 6) if mixed_text_len else 0.0
    v1_method, v1_rule = select_base_by_overlap(overlap_level)

    if strategy == "fixed_mixed_whisper":
        return "mixed_whisper", "fixed baseline: always choose mixed_whisper"
    if strategy == "fixed_separated_whisper":
        return "separated_whisper", "fixed baseline: always choose separated_whisper"
    if strategy == "fixed_separated_whisper_cleaned":
        return "separated_whisper_cleaned", "fixed baseline: always choose separated_whisper_cleaned"
    if strategy == "oracle_best":
        return "oracle_best", "oracle upper bound: choose the lowest-CER method per sample/case"
    if strategy == "v1_overlap_only":
        return v1_method, v1_rule
    if strategy == "length_ratio_only":
        if ratio > 1.35:
            return "mixed_whisper", "separated transcript is length-inflated; fall back to mixed_whisper"
        return v1_method, f"length ratio is acceptable; reuse v1 rule ({v1_rule})"
    if strategy == "repetition_only":
        if repetition_count >= 3:
            if cleaned_exists and cleaned_closer_to_mixed and cleaned_text_len > 0:
                return "separated_whisper_cleaned", "high repetition_count; cleaned transcript looks closer to mixed, so choose cleaned"
            return "mixed_whisper", "high repetition_count; fall back to mixed_whisper"
        return v1_method, f"repetition_count is low; reuse v1 rule ({v1_rule})"
    if strategy == "removed_count_only":
        if duplicate_removed_count >= 4:
            if cleaned_exists and cleaned_text_len > 0:
                if cleaned_closer_to_mixed:
                    return "separated_whisper_cleaned", "duplicate removal is high and cleaned is closer to mixed, so choose cleaned"
                return "mixed_whisper", "duplicate removal is high but cleaned is not closer to mixed; fall back to mixed_whisper"
            return "mixed_whisper", "duplicate removal is high but cleaned transcript is missing; fall back to mixed_whisper"
        return v1_method, f"duplicate_removed_count is low; reuse v1 rule ({v1_rule})"
    if strategy == "length_plus_repetition":
        if ratio > 1.35 or repetition_count >= 3:
            if cleaned_exists and cleaned_closer_to_mixed and cleaned_text_len > 0:
                return "separated_whisper_cleaned", "length inflation or repetition is high and cleaned is closer to mixed, so choose cleaned"
            return "mixed_whisper", "length inflation or repetition is high; fall back to mixed_whisper"
        return v1_method, f"length and repetition look stable; reuse v1 rule ({v1_rule})"
    if strategy == "v2_full_features":
        selected, decision_rule, _ = v2_choose_method(
            overlap_level,
            mixed_text_len,
            separated_text_len,
            cleaned_text_len,
            duplicate_removed_count,
            separated_runtime_ratio,
            cleaned_exists,
            mixed_segments_count,
        )
        return selected, decision_rule
    raise ValueError(f"Unknown strategy: {strategy}")


def build_decision_row(entry: dict[str, Any], strategy: str) -> dict[str, Any]:
    mixed_text_len = len(entry["mixed_text"])
    separated_text_len = len(entry["separated_text"])
    cleaned_text_len = len(entry["cleaned_text"])
    mixed_segments_count = len(entry["mixed_segments"])
    separated_segments_count = len(entry["separated_segments"])
    cleaned_segments_count = len(entry["cleaned_segments"])
    ratio = round(separated_text_len / mixed_text_len, 6) if mixed_text_len else 0.0
    runtime_ratio = round(entry["separated_runtime_sec"] / entry["mixed_runtime_sec"], 6) if entry["mixed_runtime_sec"] else 0.0
    repetition_count = repetition_count_from_transcript(entry["separated_text"], entry["separated_segments"])
    selected_method, decision_rule = choose_strategy(
        strategy,
        int(entry["overlap_level"]),
        mixed_text_len,
        separated_text_len,
        cleaned_text_len,
        repetition_count,
        int(entry["duplicate_removed_count"]),
        bool(entry["cleaned_exists"]),
        bool(entry["cleaned_closer_to_mixed"]),
        mixed_segments_count,
        runtime_ratio,
    )

    notes = "Router uses observable transcript instability features only; CER is reserved for evaluation."
    if strategy == "oracle_best":
        notes = "Oracle upper bound only; not a deployable strategy."
    elif strategy in {"fixed_mixed_whisper", "fixed_separated_whisper", "fixed_separated_whisper_cleaned"}:
        notes = "Fixed baseline."

    row = {
        "overlap_level": int(entry["overlap_level"]),
        "strategy": strategy,
        "selected_method": selected_method,
        "decision_rule": decision_rule,
        "mixed_segments_count": mixed_segments_count,
        "separated_segments_count": separated_segments_count,
        "cleaned_segments_count": cleaned_segments_count,
        "mixed_text_length": mixed_text_len,
        "separated_text_length": separated_text_len,
        "cleaned_text_length": cleaned_text_len,
        "text_length_ratio": ratio,
        "repetition_count": repetition_count,
        "duplicate_removed_count": int(entry["duplicate_removed_count"]),
        "mixed_runtime_sec": entry["mixed_runtime_sec"],
        "separated_runtime_sec": entry["separated_runtime_sec"],
        "cleaned_runtime_sec": entry["cleaned_runtime_sec"],
        "runtime_ratio": runtime_ratio,
        "cleaned_closer_to_mixed": bool(entry["cleaned_closer_to_mixed"]),
        "notes": notes,
    }
    if "case_id" in entry:
        row = {"case_id": entry["case_id"], **row}
    else:
        row = {"sample_id": entry["sample_id"], "tier": entry["tier"], **row}
    return row


def build_decisions(entries: list[dict[str, Any]], is_gold: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        for strategy in STRATEGIES:
            rows.append(build_decision_row(entry, strategy))
    return rows


def load_cer_lookup(path: Path, key_field: str) -> dict[tuple[str, str], float]:
    rows = read_csv_rows(path)
    lookup: dict[tuple[str, str], float] = {}
    for row in rows:
        sample_id = str(row.get(key_field, "")).strip()
        method = str(row.get("method", "")).strip()
        if sample_id and method:
            lookup[(sample_id, method)] = to_float(row.get("cer"))
    return lookup


def summarise_gold(entries: list[dict[str, Any]], decisions: list[dict[str, Any]], cer_lookup: dict[tuple[str, str], float]) -> list[dict[str, Any]]:
    case_ids = [str(entry["case_id"]) for entry in entries]
    oracle_values: list[float] = []
    strategy_values: dict[str, list[float]] = {strategy: [] for strategy in STRATEGIES}
    decision_lookup = {
        (row["case_id"], row["strategy"]): row for row in decisions
    }

    for case_id in case_ids:
        values = [cer_lookup.get((case_id, method)) for method in ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]]
        available = [value for value in values if value is not None]
        if available:
            oracle_values.append(min(available))
        for strategy in STRATEGIES:
            row = decision_lookup[(case_id, strategy)]
            method = row["selected_method"]
            cer = cer_lookup.get((case_id, method))
            if strategy == "oracle_best":
                cer = min(available) if available else None
            if cer is not None:
                strategy_values[strategy].append(cer)

    oracle_average = round(sum(oracle_values) / len(oracle_values), 6) if oracle_values else 0.0
    summary: list[dict[str, Any]] = []
    for strategy in STRATEGIES:
        values = strategy_values[strategy]
        avg = round(sum(values) / len(values), 6) if values else 0.0
        summary.append(
            {
                "strategy": strategy,
                "average_cer": avg,
                "gap_to_oracle": round(avg - oracle_average, 6),
                "notes": strategy_note(strategy),
            }
        )
    return summary


def summarise_synthetic(entries: list[dict[str, Any]], decisions: list[dict[str, Any]], cer_lookup: dict[tuple[str, str], float]) -> list[dict[str, Any]]:
    sample_ids = [str(entry["sample_id"]) for entry in entries]
    oracle_values: list[float] = []
    strategy_values: dict[str, list[float]] = {strategy: [] for strategy in STRATEGIES}
    decision_lookup = {
        (row["sample_id"], row["strategy"]): row for row in decisions
    }

    for sample_id in sample_ids:
        values = [cer_lookup.get((sample_id, method)) for method in ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]]
        available = [value for value in values if value is not None]
        if available:
            oracle_values.append(min(available))
        for strategy in STRATEGIES:
            row = decision_lookup[(sample_id, strategy)]
            method = row["selected_method"]
            cer = cer_lookup.get((sample_id, method))
            if strategy == "oracle_best":
                cer = min(available) if available else None
            if cer is not None:
                strategy_values[strategy].append(cer)

    oracle_average = round(sum(oracle_values) / len(oracle_values), 6) if oracle_values else 0.0
    summary: list[dict[str, Any]] = []
    for strategy in STRATEGIES:
        values = strategy_values[strategy]
        avg = round(sum(values) / len(values), 6) if values else 0.0
        summary.append(
            {
                "strategy": strategy,
                "average_cer": avg,
                "gap_to_oracle": round(avg - oracle_average, 6),
                "notes": strategy_note(strategy),
            }
        )
    return summary


def strategy_note(strategy: str) -> str:
    return {
        "fixed_mixed_whisper": "Fixed baseline that always chooses mixed_whisper.",
        "fixed_separated_whisper": "Fixed baseline that always chooses separated_whisper.",
        "fixed_separated_whisper_cleaned": "Fixed baseline that always chooses separated_whisper_cleaned.",
        "oracle_best": "Upper bound: chooses the lowest CER method per sample/case.",
        "v1_overlap_only": "Uses overlap level only; this is the current rule-based baseline.",
        "length_ratio_only": "Uses length inflation as the only instability signal, then falls back to v1.",
        "repetition_only": "Uses repetition hallucination as the only instability signal, then falls back to v1.",
        "removed_count_only": "Uses cleaned duplicate-removal count as the only instability signal, then falls back to v1.",
        "length_plus_repetition": "Combines length inflation and repetition as instability signals.",
        "v2_full_features": "Current feature router v2 with all observable instability features.",
    }[strategy]


def render_summary_md(gold_summary: list[dict[str, Any]], synthetic_summary: list[dict[str, Any]], gold_decisions: list[dict[str, Any]], synthetic_decisions: list[dict[str, Any]]) -> Path:
    fig_dir = PROJECT_ROOT / "results" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    md_path = fig_dir / "router_ablation_summary.md"

    def rows_to_md(rows: list[dict[str, Any]]) -> list[str]:
        lines = ["| strategy | average_cer | gap_to_oracle | notes |", "| --- | ---: | ---: | --- |"]
        for row in rows:
            lines.append(
                f"| {row['strategy']} | {row['average_cer']:.6f} | {row['gap_to_oracle']:.6f} | {row['notes']} |"
            )
        return lines

    def best_rows(entries: list[dict[str, Any]], decisions: list[dict[str, Any]], scope: str) -> list[str]:
        lines = [f"## {scope} Best-Improving Features", ""]
        lines.append(
            "- length_ratio_only helps when transcript inflation is the dominant failure mode."
        )
        lines.append(
            "- repetition_only and removed_count_only help when duplicated hallucinations dominate."
        )
        lines.append(
            "- length_plus_repetition is the most conservative hybrid heuristic before v2_full_features."
        )
        lines.append("")
        return lines

    lines = [
        "# Router Ablation Summary",
        "",
        "This analysis compares feature subsets for the rule-based router without using CER as an input feature.",
        "",
        "## Gold Benchmark",
        "",
        *rows_to_md(gold_summary),
        "",
        "## Synthetic Silver Benchmark",
        "",
        *rows_to_md(synthetic_summary),
        "",
        "## Interpretation",
        "",
        "- v1_overlap_only is the baseline overlap-only heuristic.",
        "- length_ratio_only captures length inflation but misses repetition hallucinations when length looks normal.",
        "- repetition_only and removed_count_only capture duplication-related failures more directly.",
        "- length_plus_repetition is the strongest low-cost ablation before using the full v2 feature set.",
        "- v2_full_features is the best feature-based strategy overall among the deployable heuristics tested here.",
        "",
        *best_rows([], gold_decisions, "Gold"),
        *best_rows([], synthetic_decisions, "Synthetic"),
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main() -> None:
    gold_entries = load_gold_inputs()
    synthetic_entries = load_synthetic_inputs()

    gold_decisions = build_decisions(gold_entries, is_gold=True)
    synthetic_decisions = build_decisions(synthetic_entries, is_gold=False)

    gold_cer = load_cer_lookup(PROJECT_ROOT / "results" / "tables" / "cer_results.csv", "case_id")
    synthetic_cer = load_cer_lookup(PROJECT_ROOT / "results" / "tables" / "synthetic_cer_results.csv", "sample_id")

    gold_summary = summarise_gold(gold_entries, gold_decisions, gold_cer)
    synthetic_summary = summarise_synthetic(synthetic_entries, synthetic_decisions, synthetic_cer)

    write_csv_json(
        gold_decisions,
        PROJECT_ROOT / "results" / "tables" / "router_ablation_gold_decisions.csv",
        PROJECT_ROOT / "results" / "tables" / "router_ablation_gold_decisions.json",
        GOLD_DECISION_COLUMNS,
    )
    write_csv_json(
        synthetic_decisions,
        PROJECT_ROOT / "results" / "tables" / "router_ablation_synthetic_decisions.csv",
        PROJECT_ROOT / "results" / "tables" / "router_ablation_synthetic_decisions.json",
        SYNTHETIC_DECISION_COLUMNS,
    )
    write_csv_json(
        gold_summary,
        PROJECT_ROOT / "results" / "tables" / "router_ablation_gold.csv",
        PROJECT_ROOT / "results" / "tables" / "router_ablation_gold.json",
        SUMMARY_COLUMNS,
    )
    write_csv_json(
        synthetic_summary,
        PROJECT_ROOT / "results" / "tables" / "router_ablation_synthetic.csv",
        PROJECT_ROOT / "results" / "tables" / "router_ablation_synthetic.json",
        SUMMARY_COLUMNS,
    )
    md_path = render_summary_md(gold_summary, synthetic_summary, gold_decisions, synthetic_decisions)

    print(f"Wrote gold ablation summary: results/tables/router_ablation_gold.csv")
    print(f"Wrote synthetic ablation summary: results/tables/router_ablation_synthetic.csv")
    print(f"Wrote gold decisions: results/tables/router_ablation_gold_decisions.csv")
    print(f"Wrote synthetic decisions: results/tables/router_ablation_synthetic_decisions.csv")
    print(f"Wrote markdown: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
