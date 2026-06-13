from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .adaptive_router import select_method as v1_select_method
from .adaptive_router_v2 import choose_method_v2 as v2_choose_method
from .build_synthetic_references import read_csv_rows, read_json
from .config import PROJECT_ROOT
from .evaluate_cer import normalize_text
from .io_helpers import to_float, to_int


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

DECISION_COLUMNS = [
    "sample_id",
    "tier",
    "split",
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

PERFORMANCE_COLUMNS = ["scope", "strategy", "average_cer", "gap_to_oracle", "sample_count", "notes"]


def dataset_paths() -> dict[str, Path]:
    return {
        "manifest": PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv",
        "cer": PROJECT_ROOT / "results" / "tables" / "synthetic_split_cer_results.csv",
        "raw_dir": PROJECT_ROOT / "results" / "synthetic_overlap_v2" / "transcripts_raw",
        "speaker_dir": PROJECT_ROOT / "results" / "synthetic_overlap_v2" / "transcripts_speaker",
        "cleaned_dir": PROJECT_ROOT / "results" / "synthetic_overlap_v2" / "transcripts_postprocessed",
        "decisions_csv": PROJECT_ROOT / "results" / "tables" / "router_ablation_synthetic_split_decisions.csv",
        "decisions_json": PROJECT_ROOT / "results" / "tables" / "router_ablation_synthetic_split_decisions.json",
        "summary_csv": PROJECT_ROOT / "results" / "tables" / "router_ablation_synthetic_split.csv",
        "summary_json": PROJECT_ROOT / "results" / "tables" / "router_ablation_synthetic_split.json",
        "summary_md": PROJECT_ROOT / "results" / "figures" / "router_ablation_synthetic_split_summary.md",
    }


def load_manifest() -> list[dict[str, Any]]:
    return read_csv_rows(dataset_paths()["manifest"])


def load_cer_lookup() -> dict[tuple[str, str], float]:
    rows = read_csv_rows(dataset_paths()["cer"])
    lookup: dict[tuple[str, str], float] = {}
    for row in rows:
        sample_id = str(row.get("sample_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if sample_id and method:
            lookup[(sample_id, method)] = to_float(row.get("cer"))
    return lookup


def load_cleaned_rows() -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    cleaned_dir = dataset_paths()["cleaned_dir"]
    if not cleaned_dir.exists():
        return payloads
    for path in cleaned_dir.glob("*_separated_speaker_transcript_cleaned.json"):
        try:
            payload = read_json(path)
        except Exception as exc:
            try:
                display_path = path.relative_to(PROJECT_ROOT)
            except ValueError:
                display_path = path
            print(f"warning: failed to read cleaned transcript {display_path}: {exc}")
            continue
        sample_id = str(payload.get("sample_id", "")).strip()
        if sample_id:
            payloads[sample_id] = payload
    return payloads


def repetition_count(segments: list[dict[str, Any]]) -> int:
    texts = [normalize_text(str(seg.get("text", ""))) for seg in segments]
    count = 0
    for prev, curr in zip(texts, texts[1:]):
        if prev and prev == curr:
            count += 1
    return count


def build_entry(row: dict[str, Any], cleaned_rows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sample_id = str(row.get("sample_id", "")).strip()
    tier = str(row.get("tier", "")).strip()
    split = str(row.get("split", "")).strip()
    overlap_level = to_int(row.get("overlap_level_numeric", row.get("overlap_level", 0)))
    paths = dataset_paths()
    mixed = read_json(paths["raw_dir"] / f"{sample_id}_mixed_whisper.json")
    separated_path = paths["speaker_dir"] / f"{sample_id}_separated_speaker_transcript.json"
    cleaned_path = paths["cleaned_dir"] / f"{sample_id}_separated_speaker_transcript_cleaned.json"
    separated_payload = read_json(separated_path)
    cleaned_payload = cleaned_rows.get(sample_id, read_json(cleaned_path) if cleaned_path.exists() else {})
    mixed_text = str(mixed.get("text", ""))
    separated_text = str(separated_payload.get("full_text", ""))
    cleaned_text = str(cleaned_payload.get("cleaned_full_text", ""))
    mixed_runtime_sec = to_float(mixed.get("runtime_sec"))
    separated_runtime_sec = to_float(separated_payload.get("runtime_sec_total"))
    cleaned_runtime_sec = to_float(cleaned_payload.get("runtime_sec_total", separated_runtime_sec))
    return {
        "sample_id": sample_id,
        "tier": tier,
        "split": split,
        "overlap_level": overlap_level,
        "mixed_text_length": len(mixed_text),
        "separated_text_length": len(separated_text),
        "cleaned_text_length": len(cleaned_text),
        "text_length_ratio": round(len(separated_text) / len(mixed_text), 6) if mixed_text else 0.0,
        "repetition_count": repetition_count(list(separated_payload.get("segments", []))),
        "duplicate_removed_count": to_int(cleaned_payload.get("removed_count")),
        "mixed_segments_count": len(mixed.get("segments", [])),
        "separated_segments_count": len(separated_payload.get("segments", [])),
        "cleaned_segments_count": len(cleaned_payload.get("cleaned_segments", [])),
        "mixed_runtime_sec": mixed_runtime_sec,
        "separated_runtime_sec": separated_runtime_sec,
        "cleaned_runtime_sec": cleaned_runtime_sec,
        "runtime_ratio": round(separated_runtime_sec / mixed_runtime_sec, 6) if mixed_runtime_sec else 0.0,
        "cleaned_closer_to_mixed": bool(
            cleaned_path.exists()
            and abs(len(cleaned_text) - len(mixed_text)) < abs(len(separated_text) - len(mixed_text))
        ),
        "notes": "Router uses observable transcript instability features only; CER is reserved for evaluation.",
        "mixed_text": mixed_text,
        "separated_text": separated_text,
        "cleaned_text": cleaned_text,
    }


def choose_strategy(entry: dict[str, Any], strategy: str) -> tuple[str, str]:
    overlap_level = int(entry["overlap_level"])
    mixed_len = int(entry["mixed_text_length"])
    separated_len = int(entry["separated_text_length"])
    cleaned_len = int(entry["cleaned_text_length"])
    repetition = int(entry["repetition_count"])
    duplicate_removed = int(entry["duplicate_removed_count"])
    runtime_ratio = float(entry["runtime_ratio"])
    cleaned_exists = cleaned_len > 0
    cleaned_closer = bool(entry["cleaned_closer_to_mixed"])
    mixed_segments_count = int(entry["mixed_segments_count"])

    v1_method, v1_rule = v1_select_method(overlap_level)
    v2_method, v2_rule, _ = v2_choose_method(
        overlap_level,
        mixed_len,
        separated_len,
        cleaned_len,
        duplicate_removed,
        runtime_ratio,
        cleaned_exists,
        mixed_segments_count,
    )

    if strategy == "fixed_mixed_whisper":
        return "mixed_whisper", "fixed baseline: always choose mixed_whisper"
    if strategy == "fixed_separated_whisper":
        return "separated_whisper", "fixed baseline: always choose separated_whisper"
    if strategy == "fixed_separated_whisper_cleaned":
        return "separated_whisper_cleaned", "fixed baseline: always choose separated_whisper_cleaned"
    if strategy == "oracle_best":
        return "oracle_best", "oracle upper bound: choose the lowest CER method per sample."
    if strategy == "v1_overlap_only":
        return v1_method, v1_rule
    if strategy == "length_ratio_only":
        if entry["text_length_ratio"] > 1.35:
            return "mixed_whisper", "separated transcript is length-inflated; fall back to mixed_whisper"
        return v1_method, f"length ratio is acceptable; reuse v1 rule ({v1_rule})"
    if strategy == "repetition_only":
        if repetition >= 3:
            if cleaned_exists and cleaned_closer:
                return "separated_whisper_cleaned", "high repetition_count; cleaned transcript is closer to mixed"
            return "mixed_whisper", "high repetition_count; fall back to mixed_whisper"
        return v1_method, f"repetition_count is low; reuse v1 rule ({v1_rule})"
    if strategy == "removed_count_only":
        if duplicate_removed >= 4:
            if cleaned_exists and cleaned_closer:
                return "separated_whisper_cleaned", "duplicate removal is high and cleaned is closer to mixed"
            return "mixed_whisper", "duplicate removal is high; fall back to mixed_whisper"
        return v1_method, f"duplicate_removed_count is low; reuse v1 rule ({v1_rule})"
    if strategy == "length_plus_repetition":
        if entry["text_length_ratio"] > 1.35 or repetition >= 3:
            if cleaned_exists and cleaned_closer:
                return "separated_whisper_cleaned", "length inflation or repetition is high and cleaned is closer to mixed"
            return "mixed_whisper", "length inflation or repetition is high; fall back to mixed_whisper"
        return v1_method, f"length and repetition look stable; reuse v1 rule ({v1_rule})"
    if strategy == "v2_full_features":
        return v2_method, v2_rule
    raise ValueError(strategy)


def build_decisions(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in entries:
        for strategy in STRATEGIES:
            selected_method, decision_rule = choose_strategy(entry, strategy)
            rows.append(
                {
                    "sample_id": entry["sample_id"],
                    "tier": entry["tier"],
                    "split": entry["split"],
                    "strategy": strategy,
                    "selected_method": selected_method,
                    "decision_rule": decision_rule,
                    "mixed_segments_count": entry["mixed_segments_count"],
                    "separated_segments_count": entry["separated_segments_count"],
                    "cleaned_segments_count": entry["cleaned_segments_count"],
                    "mixed_text_length": entry["mixed_text_length"],
                    "separated_text_length": entry["separated_text_length"],
                    "cleaned_text_length": entry["cleaned_text_length"],
                    "text_length_ratio": entry["text_length_ratio"],
                    "repetition_count": entry["repetition_count"],
                    "duplicate_removed_count": entry["duplicate_removed_count"],
                    "mixed_runtime_sec": entry["mixed_runtime_sec"],
                    "separated_runtime_sec": entry["separated_runtime_sec"],
                    "cleaned_runtime_sec": entry["cleaned_runtime_sec"],
                    "runtime_ratio": entry["runtime_ratio"],
                    "cleaned_closer_to_mixed": entry["cleaned_closer_to_mixed"],
                    "notes": entry["notes"],
                }
            )
    return rows


def compute_scope_average(
    cer_lookup: dict[tuple[str, str], float],
    entries: list[dict[str, Any]],
    strategy: str,
) -> tuple[float, int]:
    values: list[float] = []
    for entry in entries:
        sample_id = entry["sample_id"]
        if strategy == "oracle_best":
            available = [
                cer_lookup.get((sample_id, method))
                for method in ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]
            ]
            available = [v for v in available if v is not None]
            if available:
                values.append(min(available))
            continue
        selected_method, _ = choose_strategy(entry, strategy)
        cer = cer_lookup.get((sample_id, selected_method))
        if cer is not None:
            values.append(cer)
    return (round(sum(values) / len(values), 6) if values else 0.0, len(values))


def build_performance(
    cer_lookup: dict[tuple[str, str], float],
    entries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    scopes: list[tuple[str, list[dict[str, Any]]]] = [("ALL", entries)]
    for split in ["dev", "test"]:
        split_entries = [entry for entry in entries if entry["split"] == split]
        scopes.append((split.upper(), split_entries))
    for tier in sorted({entry["tier"] for entry in entries}):
        tier_entries = [entry for entry in entries if entry["tier"] == tier]
        scopes.append((tier, tier_entries))

    performance: list[dict[str, Any]] = []
    for scope, scope_entries in scopes:
        oracle_avg, oracle_count = compute_scope_average(cer_lookup, scope_entries, "oracle_best")
        for strategy in STRATEGIES:
            avg, count = compute_scope_average(cer_lookup, scope_entries, strategy)
            performance.append(
                {
                    "scope": scope,
                    "strategy": strategy,
                    "average_cer": avg,
                    "gap_to_oracle": round(avg - oracle_avg, 6),
                    "sample_count": count,
                    "notes": (
                        "Oracle upper bound only; not deployable."
                        if strategy == "oracle_best"
                        else (
                            "v1 overlap-only baseline."
                            if strategy == "v1_overlap_only"
                            else (
                                "Full feature router v2."
                                if strategy == "v2_full_features"
                                else "Ablation strategy."
                            )
                        )
                    ),
                }
            )
    return performance


def write_outputs(paths: dict[str, Path], decisions: list[dict[str, Any]], performance: list[dict[str, Any]]) -> None:
    paths["decisions_csv"].parent.mkdir(parents=True, exist_ok=True)
    paths["summary_csv"].parent.mkdir(parents=True, exist_ok=True)
    paths["summary_md"].parent.mkdir(parents=True, exist_ok=True)

    with paths["decisions_csv"].open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=DECISION_COLUMNS)
        writer.writeheader()
        writer.writerows(decisions)
    paths["decisions_json"].write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")

    with paths["summary_csv"].open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PERFORMANCE_COLUMNS)
        writer.writeheader()
        writer.writerows(performance)
    paths["summary_json"].write_text(json.dumps(performance, ensure_ascii=False, indent=2), encoding="utf-8")

    perf_map = {(row["scope"], row["strategy"]): row for row in performance}
    lines = [
        "# Router Ablation Summary - Synthetic Split",
        "",
        "This analysis compares feature subsets for the rule-based router on the held-out synthetic split benchmark.",
        "The dev split is available for inspection, but the test split is not used to tune any thresholds.",
        "",
    ]
    for scope in ["ALL", "DEV", "TEST"]:
        if any((scope, strategy) in perf_map for strategy in STRATEGIES):
            lines.extend([f"## {scope}", "", "| strategy | average_cer | gap_to_oracle | sample_count | notes |", "| --- | ---: | ---: | ---: | --- |"])
            for strategy in STRATEGIES:
                row = perf_map.get((scope, strategy))
                if row:
                    lines.append(
                        f"| {row['strategy']} | {row['average_cer']} | {row['gap_to_oracle']} | {row['sample_count']} | {row['notes']} |"
                    )
            lines.append("")
    for tier in sorted({row["tier"] for row in decisions}):
        lines.extend([f"## {tier}", "", "| strategy | average_cer | gap_to_oracle | sample_count | notes |", "| --- | ---: | ---: | ---: | --- |"])
        for strategy in STRATEGIES:
            row = perf_map.get((tier, strategy))
            if row:
                lines.append(
                    f"| {row['strategy']} | {row['average_cer']} | {row['gap_to_oracle']} | {row['sample_count']} | {row['notes']} |"
                )
        lines.append("")
    paths["summary_md"].write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    paths = dataset_paths()
    manifest_rows = read_csv_rows(paths["manifest"])
    cleaned_rows = load_cleaned_rows()
    entries = [build_entry(row, cleaned_rows) for row in manifest_rows]
    decisions = build_decisions(entries)
    cer_lookup = load_cer_lookup()
    performance = build_performance(cer_lookup, entries)
    write_outputs(paths, decisions, performance)
    print(f"Wrote router ablation summary: {paths['summary_csv'].relative_to(PROJECT_ROOT)}")
    print(f"Wrote router ablation decisions: {paths['decisions_csv'].relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
