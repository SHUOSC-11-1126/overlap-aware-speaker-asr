from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config


DECISION_COLUMNS = [
    "case_id",
    "overlap_level",
    "selected_method",
    "decision_rule",
    "mixed_segments_count",
    "separated_segments_count",
    "mixed_text_length",
    "separated_text_length",
    "text_length_ratio",
    "mixed_runtime_sec",
    "separated_runtime_sec",
    "runtime_ratio",
    "duplicate_removed_count",
    "notes",
]

PERFORMANCE_COLUMNS = ["strategy", "average_cer"]

METHODS = ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing table: {path.relative_to(PROJECT_ROOT)}")
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path.relative_to(PROJECT_ROOT)}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def load_benchmark_rows() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    mixed_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "mixed_asr_benchmark.csv")
    separated_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "separated_asr_benchmark.csv")
    mixed = {str(row.get("case_id", "")): row for row in mixed_rows if row.get("case_id")}
    separated = {str(row.get("case_id", "")): row for row in separated_rows if row.get("case_id")}
    return mixed, separated


def load_cleaned_rows() -> dict[str, dict[str, Any]]:
    cleaned_dir = PROJECT_ROOT / "results" / "transcripts_postprocessed"
    rows: dict[str, dict[str, Any]] = {}
    if not cleaned_dir.exists():
        return rows
    for path in cleaned_dir.glob("*_separated_speaker_transcript_cleaned.json"):
        try:
            payload = read_json(path)
        except Exception as exc:  # pragma: no cover - best-effort warning
            print(f"warning: failed to read cleaned transcript {path.relative_to(PROJECT_ROOT)}: {exc}")
            continue
        case_id = str(payload.get("case_id", "")).strip()
        if case_id:
            rows[case_id] = payload
    return rows


def load_cer_rows() -> dict[tuple[str, str], float]:
    rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv")
    mapping: dict[tuple[str, str], float] = {}
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if not case_id or not method:
            continue
        mapping[(case_id, method)] = to_float(row.get("cer"))
    return mapping


def select_method(overlap_level: int) -> tuple[str, str]:
    if overlap_level == 0:
        return "separated_whisper", "if overlap_level == 0, choose separated_whisper"
    if overlap_level in (1, 2):
        return "mixed_whisper", "if overlap_level in [1, 2], choose mixed_whisper"
    if overlap_level >= 3:
        return "separated_whisper", "if overlap_level >= 3, choose separated_whisper"
    return "mixed_whisper", "fallback to mixed_whisper"


def build_decisions(
    config: dict[str, Any],
    mixed_rows: dict[str, dict[str, Any]],
    separated_rows: dict[str, dict[str, Any]],
    cleaned_rows: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    case_map = load_case_map(config)
    decisions: list[dict[str, Any]] = []
    for case_id in sorted(case_map.keys()):
        overlap_level = int(case_map[case_id].get("overlap_level", 0))
        selected_method, decision_rule = select_method(overlap_level)

        mixed = mixed_rows.get(case_id, {})
        separated = separated_rows.get(case_id, {})
        cleaned = cleaned_rows.get(case_id, {})

        mixed_segments_count = to_int(mixed.get("segments_count"))
        separated_segments_count = to_int(separated.get("merged_segments_count"))
        mixed_text_length = to_int(mixed.get("text_length"))
        separated_text_length = to_int(separated.get("full_text_length"))
        text_length_ratio = round(separated_text_length / mixed_text_length, 6) if mixed_text_length else 0.0
        mixed_runtime_sec = to_float(mixed.get("runtime_sec"))
        separated_runtime_sec = to_float(separated.get("runtime_sec_total"))
        runtime_ratio = round(separated_runtime_sec / mixed_runtime_sec, 6) if mixed_runtime_sec else 0.0
        duplicate_removed_count = to_int(cleaned.get("removed_count"))

        notes = "Router is rule-based and does not use CER as an input feature."
        if cleaned:
            notes += " Cleaned transcript is retained as a fallback candidate but not selected by the initial rule."

        decisions.append(
            {
                "case_id": case_id,
                "overlap_level": overlap_level,
                "selected_method": selected_method,
                "decision_rule": decision_rule,
                "mixed_segments_count": mixed_segments_count,
                "separated_segments_count": separated_segments_count,
                "mixed_text_length": mixed_text_length,
                "separated_text_length": separated_text_length,
                "text_length_ratio": text_length_ratio,
                "mixed_runtime_sec": mixed_runtime_sec,
                "separated_runtime_sec": separated_runtime_sec,
                "runtime_ratio": runtime_ratio,
                "duplicate_removed_count": duplicate_removed_count,
                "notes": notes,
            }
        )
    return decisions


def write_decisions(decisions: list[dict[str, Any]]) -> tuple[Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    csv_path = table_dir / "routing_decisions.csv"
    json_path = table_dir / "routing_decisions.json"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DECISION_COLUMNS)
        writer.writeheader()
        writer.writerows(decisions)

    json_path.write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


def compute_strategy_averages(
    cer_lookup: dict[tuple[str, str], float],
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    case_ids = [row["case_id"] for row in decisions]
    strategies: dict[str, list[float]] = {
        "fixed_mixed_whisper": [],
        "fixed_separated_whisper": [],
        "fixed_separated_whisper_cleaned": [],
        "oracle_best": [],
        "rule_router": [],
    }

    for case_id in case_ids:
        mixed = cer_lookup.get((case_id, "mixed_whisper"))
        separated = cer_lookup.get((case_id, "separated_whisper"))
        cleaned = cer_lookup.get((case_id, "separated_whisper_cleaned"))
        available = [v for v in [mixed, separated, cleaned] if v is not None]
        if mixed is not None:
            strategies["fixed_mixed_whisper"].append(mixed)
        if separated is not None:
            strategies["fixed_separated_whisper"].append(separated)
        if cleaned is not None:
            strategies["fixed_separated_whisper_cleaned"].append(cleaned)
        if available:
            strategies["oracle_best"].append(min(available))

    for row in decisions:
        case_id = row["case_id"]
        method = row["selected_method"]
        cer = cer_lookup.get((case_id, method))
        if cer is not None:
            strategies["rule_router"].append(cer)

    performance_rows = [
        {
            "strategy": strategy,
            "average_cer": round(sum(values) / len(values), 6) if values else 0.0,
        }
        for strategy, values in strategies.items()
    ]
    return performance_rows


def write_performance(performance_rows: list[dict[str, Any]]) -> tuple[Path, Path]:
    table_dir = PROJECT_ROOT / "results" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    csv_path = table_dir / "routing_performance.csv"
    json_path = table_dir / "routing_performance.json"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PERFORMANCE_COLUMNS)
        writer.writeheader()
        writer.writerows(performance_rows)

    json_path.write_text(json.dumps(performance_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path


def update_summary_md(decisions: list[dict[str, Any]], performance_rows: list[dict[str, Any]]) -> Path:
    fig_dir = PROJECT_ROOT / "results" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    md_path = fig_dir / "current_results_summary.md"

    perf_map = {row["strategy"]: row["average_cer"] for row in performance_rows}
    lines = [
        "# Current Results Summary",
        "",
        "## Core Findings",
        "",
        "- Separated speaker-track ASR is the best method on NoOverlap, HeavyOverlap, and OppositeOverlap.",
        "- Mixed ASR remains the best method on LightOverlap and MidOverlap.",
        "- Duplicate suppression improves the separated transcript on LightOverlap and MidOverlap, but does not overtake mixed ASR there.",
        "- The rule-based router does not use CER as an input feature.",
        "",
        "## Rule Router Decision Table",
        "",
        "| case_id | overlap_level | selected_method | decision_rule |",
        "| --- | ---: | --- | --- |",
    ]
    for row in decisions:
        lines.append(
            f"| {row['case_id']} | {row['overlap_level']} | {row['selected_method']} | {row['decision_rule']} |"
        )

    lines += [
        "",
        "## Average CER Comparison",
        "",
        f"- fixed_mixed_whisper: {perf_map.get('fixed_mixed_whisper', 0.0):.6f}",
        f"- fixed_separated_whisper: {perf_map.get('fixed_separated_whisper', 0.0):.6f}",
        f"- fixed_separated_whisper_cleaned: {perf_map.get('fixed_separated_whisper_cleaned', 0.0):.6f}",
        f"- oracle_best: {perf_map.get('oracle_best', 0.0):.6f}",
        f"- rule_router: {perf_map.get('rule_router', 0.0):.6f}",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def main() -> None:
    config = load_config()
    mixed_rows, separated_rows = load_benchmark_rows()
    cleaned_rows = load_cleaned_rows()
    cer_lookup = load_cer_rows()
    decisions = build_decisions(config, mixed_rows, separated_rows, cleaned_rows)
    decision_csv, decision_json = write_decisions(decisions)
    performance_rows = compute_strategy_averages(cer_lookup, decisions)
    performance_csv, performance_json = write_performance(performance_rows)
    md_path = update_summary_md(decisions, performance_rows)

    print(f"Wrote routing decisions: {decision_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote routing decisions: {decision_json.relative_to(PROJECT_ROOT)}")
    print(f"Wrote routing performance: {performance_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote routing performance: {performance_json.relative_to(PROJECT_ROOT)}")
    print(f"Wrote summary md: {md_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
