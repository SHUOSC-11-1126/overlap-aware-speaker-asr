from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .adaptive_router import select_method as v1_select_method
from .adaptive_router_v2 import choose_method_v2 as v2_choose_method
from .build_synthetic_references import read_csv_rows, read_json
from .config import PROJECT_ROOT
from .io_helpers import to_float, to_int


STRATEGIES = [
    "fixed_mixed_whisper",
    "fixed_separated_whisper",
    "fixed_separated_whisper_cleaned",
    "oracle_best",
    "v1_overlap_only",
    "v2_full_features",
]

BASE_DECISION_COLUMNS = [
    "sample_id",
    "tier",
    "selected_method",
    "decision_rule",
    "mixed_segments_count",
    "separated_segments_count",
    "cleaned_segments_count",
    "mixed_text_length",
    "separated_text_length",
    "cleaned_text_length",
    "text_length_ratio",
    "mixed_runtime_sec",
    "separated_runtime_sec",
    "cleaned_runtime_sec",
    "runtime_ratio",
    "duplicate_removed_count",
    "notes",
]

SPLIT_DECISION_COLUMNS = [
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
    "mixed_runtime_sec",
    "separated_runtime_sec",
    "cleaned_runtime_sec",
    "runtime_ratio",
    "duplicate_removed_count",
    "notes",
]

PERFORMANCE_COLUMNS = ["scope", "strategy", "average_cer", "sample_count"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate synthetic routing strategies.")
    parser.add_argument(
        "--dataset",
        choices=["synthetic_overlap", "synthetic_overlap_v2"],
        default="synthetic_overlap",
        help="Synthetic benchmark dataset to evaluate.",
    )
    return parser.parse_args()


def dataset_paths(dataset: str) -> dict[str, Path]:
    if dataset == "synthetic_overlap":
        return {
            "manifest": PROJECT_ROOT / "results" / "tables" / "synthetic_manifest.csv",
            "cer": PROJECT_ROOT / "results" / "tables" / "synthetic_cer_results.csv",
            "raw_dir": PROJECT_ROOT / "results" / "synthetic_transcripts_raw",
            "speaker_dir": PROJECT_ROOT / "results" / "synthetic_transcripts_speaker",
            "cleaned_dir": PROJECT_ROOT / "results" / "synthetic_transcripts_postprocessed",
            "decisions_csv": PROJECT_ROOT / "results" / "tables" / "synthetic_routing_decisions.csv",
            "decisions_json": PROJECT_ROOT / "results" / "tables" / "synthetic_routing_decisions.json",
            "performance_csv": PROJECT_ROOT / "results" / "tables" / "synthetic_routing_performance.csv",
            "performance_json": PROJECT_ROOT / "results" / "tables" / "synthetic_routing_performance.json",
            "summary_md": PROJECT_ROOT / "results" / "figures" / "synthetic_routing_summary.md",
        }
    if dataset == "synthetic_overlap_v2":
        return {
            "manifest": PROJECT_ROOT / "results" / "tables" / "synthetic_split_manifest.csv",
            "cer": PROJECT_ROOT / "results" / "tables" / "synthetic_split_cer_results.csv",
            "raw_dir": PROJECT_ROOT / "results" / "synthetic_overlap_v2" / "transcripts_raw",
            "speaker_dir": PROJECT_ROOT / "results" / "synthetic_overlap_v2" / "transcripts_speaker",
            "cleaned_dir": PROJECT_ROOT / "results" / "synthetic_overlap_v2" / "transcripts_postprocessed",
            "decisions_csv": PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_decisions.csv",
            "decisions_json": PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_decisions.json",
            "performance_csv": PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_performance.csv",
            "performance_json": PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_performance.json",
            "summary_md": PROJECT_ROOT / "results" / "figures" / "synthetic_split_routing_summary.md",
        }
    raise ValueError(f"Unsupported dataset: {dataset}")


def load_manifest(path: Path) -> list[dict[str, Any]]:
    return read_csv_rows(path)


def load_cer_lookup(path: Path) -> dict[tuple[str, str], float]:
    rows = read_csv_rows(path)
    lookup: dict[tuple[str, str], float] = {}
    for row in rows:
        sample_id = str(row.get("sample_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if sample_id and method:
            lookup[(sample_id, method)] = to_float(row.get("cer"))
    return lookup


def load_cleaned_rows(cleaned_dir: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    if not cleaned_dir.exists():
        return payloads
    for path in cleaned_dir.glob("*_separated_speaker_transcript_cleaned.json"):
        try:
            payload = read_json(path)
        except Exception as exc:
            print(f"warning: failed to read cleaned transcript {path.relative_to(PROJECT_ROOT)}: {exc}")
            continue
        sample_id = str(payload.get("sample_id", "")).strip()
        if sample_id:
            payloads[sample_id] = payload
    return payloads


def selected_method_v1(overlap_level: int) -> tuple[str, str]:
    return v1_select_method(overlap_level)


def build_decision_row(
    row: dict[str, Any],
    cleaned_rows: dict[str, dict[str, Any]],
    dataset: str,
) -> dict[str, Any]:
    dirs = dataset_paths(dataset)
    sample_id = str(row.get("sample_id", "")).strip()
    tier = str(row.get("tier", "")).strip()
    split = str(row.get("split", "")).strip()
    overlap_level = to_int(row.get("overlap_level_numeric", row.get("overlap_level", 0)))

    mixed = read_json(dirs["raw_dir"] / f"{sample_id}_mixed_whisper.json")

    separated_path = dirs["speaker_dir"] / f"{sample_id}_separated_speaker_transcript.json"
    cleaned_path = dirs["cleaned_dir"] / f"{sample_id}_separated_speaker_transcript_cleaned.json"
    separated = read_json(separated_path)
    cleaned = cleaned_rows.get(sample_id, read_json(cleaned_path) if cleaned_path.exists() else {})

    mixed_text = str(mixed.get("text", ""))
    separated_text = str(separated.get("full_text", ""))
    cleaned_text = str(cleaned.get("cleaned_full_text", ""))
    mixed_segments_count = len(mixed.get("segments", []))
    separated_segments_count = len(separated.get("segments", []))
    cleaned_segments_count = len(cleaned.get("cleaned_segments", []))
    mixed_runtime_sec = to_float(mixed.get("runtime_sec"))
    separated_runtime_sec = to_float(separated.get("runtime_sec_total"))
    cleaned_runtime_sec = to_float(cleaned.get("runtime_sec_total", separated_runtime_sec))
    runtime_ratio = round(separated_runtime_sec / mixed_runtime_sec, 6) if mixed_runtime_sec else 0.0
    duplicate_removed_count = to_int(cleaned.get("removed_count"))
    repetition_count = sum(
        1 for prev, curr in zip(
            [str(seg.get("text", "")).strip() for seg in separated.get("segments", [])],
            [str(seg.get("text", "")).strip() for seg in separated.get("segments", [])[1:]],
        )
        if prev and prev == curr
    )

    if dataset == "synthetic_overlap_v2":
        selected_v1, decision_v1 = selected_method_v1(overlap_level)
        selected_v2, decision_v2, _ = v2_choose_method(
            overlap_level,
            len(mixed_text),
            len(separated_text),
            len(cleaned_text),
            duplicate_removed_count,
            runtime_ratio,
            bool(cleaned_text),
            mixed_segments_count,
        )

        def route_for(strategy: str) -> tuple[str, str]:
            if strategy == "fixed_mixed_whisper":
                return "mixed_whisper", "fixed baseline: always choose mixed_whisper"
            if strategy == "fixed_separated_whisper":
                return "separated_whisper", "fixed baseline: always choose separated_whisper"
            if strategy == "fixed_separated_whisper_cleaned":
                return "separated_whisper_cleaned", "fixed baseline: always choose separated_whisper_cleaned"
            if strategy == "oracle_best":
                return "oracle_best", "oracle upper bound only; not a deployable strategy."
            if strategy == "v1_overlap_only":
                return selected_v1, decision_v1
            if strategy == "v2_full_features":
                return selected_v2, decision_v2
            raise ValueError(strategy)

    else:
        selected_v1, decision_v1 = selected_method_v1(overlap_level)

        def route_for(strategy: str) -> tuple[str, str]:
            if strategy == "fixed_mixed_whisper":
                return "mixed_whisper", "fixed baseline: always choose mixed_whisper"
            if strategy == "fixed_separated_whisper":
                return "separated_whisper", "fixed baseline: always choose separated_whisper"
            if strategy == "fixed_separated_whisper_cleaned":
                return "separated_whisper_cleaned", "fixed baseline: always choose separated_whisper_cleaned"
            if strategy == "oracle_best":
                return "oracle_best", "oracle upper bound only; not a deployable strategy."
            if strategy == "v1_overlap_only":
                return selected_v1, decision_v1
            if strategy == "v2_full_features":
                selected_v2, decision_v2, _ = v2_choose_method(
                    overlap_level,
                    len(mixed_text),
                    len(separated_text),
                    len(cleaned_text),
                    duplicate_removed_count,
                    runtime_ratio,
                    bool(cleaned_text),
                    mixed_segments_count,
                )
                return selected_v2, decision_v2
            raise ValueError(strategy)

    strategy = "v1_overlap_only"
    selected_method, decision_rule = route_for(strategy)

    row_out: dict[str, Any] = {
        "sample_id": sample_id,
        "tier": tier,
        "selected_method": selected_method,
        "decision_rule": decision_rule,
        "mixed_segments_count": mixed_segments_count,
        "separated_segments_count": separated_segments_count,
        "cleaned_segments_count": cleaned_segments_count,
        "mixed_text_length": len(mixed_text),
        "separated_text_length": len(separated_text),
        "cleaned_text_length": len(cleaned_text),
        "text_length_ratio": round(len(separated_text) / len(mixed_text), 6) if mixed_text else 0.0,
        "mixed_runtime_sec": mixed_runtime_sec,
        "separated_runtime_sec": separated_runtime_sec,
        "cleaned_runtime_sec": cleaned_runtime_sec,
        "runtime_ratio": runtime_ratio,
        "duplicate_removed_count": duplicate_removed_count,
        "notes": "Router uses observable transcript instability features only; CER is reserved for evaluation.",
    }
    if split:
        row_out["split"] = split
    return row_out


def build_decisions(
    manifest_rows: list[dict[str, Any]],
    cleaned_rows: dict[str, dict[str, Any]],
    dataset: str,
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for row in manifest_rows:
        base = build_decision_row(row, cleaned_rows, dataset)
        for strategy in STRATEGIES:
            decision = dict(base)
            if strategy == "fixed_mixed_whisper":
                decision["selected_method"] = "mixed_whisper"
                decision["decision_rule"] = "fixed baseline: always choose mixed_whisper"
            elif strategy == "fixed_separated_whisper":
                decision["selected_method"] = "separated_whisper"
                decision["decision_rule"] = "fixed baseline: always choose separated_whisper"
            elif strategy == "fixed_separated_whisper_cleaned":
                decision["selected_method"] = "separated_whisper_cleaned"
                decision["decision_rule"] = "fixed baseline: always choose separated_whisper_cleaned"
            elif strategy == "oracle_best":
                decision["selected_method"] = "oracle_best"
                decision["decision_rule"] = "oracle upper bound only; not a deployable strategy."
            elif strategy == "v1_overlap_only":
                selected, rule = selected_method_v1(to_int(row.get("overlap_level_numeric", row.get("overlap_level", 0))))
                decision["selected_method"] = selected
                decision["decision_rule"] = rule
            elif strategy == "v2_full_features":
                sample_id = str(row.get("sample_id", "")).strip()
                dirs = dataset_paths(dataset)
                separated_path = dirs["speaker_dir"] / f"{sample_id}_separated_speaker_transcript.json"
                cleaned_path = dirs["cleaned_dir"] / f"{sample_id}_separated_speaker_transcript_cleaned.json"
                mixed = read_json(dirs["raw_dir"] / f"{sample_id}_mixed_whisper.json")
                separated = read_json(separated_path)
                cleaned = cleaned_rows.get(sample_id, read_json(cleaned_path) if cleaned_path.exists() else {})
                selected, rule, _ = v2_choose_method(
                    to_int(row.get("overlap_level_numeric", row.get("overlap_level", 0))),
                    len(str(mixed.get("text", ""))),
                    len(str(separated.get("full_text", ""))),
                    len(str(cleaned.get("cleaned_full_text", ""))),
                    to_int(cleaned.get("removed_count")),
                    round(to_float(separated.get("runtime_sec_total")) / to_float(mixed.get("runtime_sec")), 6)
                    if to_float(mixed.get("runtime_sec"))
                    else 0.0,
                    bool(cleaned),
                    len(mixed.get("segments", [])),
                )
                decision["selected_method"] = selected
                decision["decision_rule"] = rule
            decision["strategy"] = strategy
            decisions.append(decision)
    return decisions


def compute_average(
    cer_lookup: dict[tuple[str, str], float],
    sample_ids: list[str],
    selected_map: dict[tuple[str, str], str],
    strategy: str,
) -> tuple[float, int]:
    values: list[float] = []
    for sample_id in sample_ids:
        if strategy == "oracle_best":
            available = [
                cer_lookup.get((sample_id, method))
                for method in ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]
            ]
            available = [v for v in available if v is not None]
            if available:
                values.append(min(available))
            continue
        method = selected_map.get((sample_id, strategy))
        if method:
            cer = cer_lookup.get((sample_id, method))
            if cer is not None:
                values.append(cer)
    return (round(sum(values) / len(values), 6) if values else 0.0, len(values))


def build_performance(
    manifest_rows: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    cer_lookup: dict[tuple[str, str], float],
) -> list[dict[str, Any]]:
    sample_ids = [str(row.get("sample_id", "")).strip() for row in manifest_rows if str(row.get("sample_id", "")).strip()]
    selected_map = {(row["sample_id"], row["strategy"]): row["selected_method"] for row in decisions}
    scopes: list[tuple[str, list[str]]] = [("ALL", sample_ids)]
    splits = sorted({str(row.get("split", "")).strip() for row in manifest_rows if str(row.get("split", "")).strip()})
    for split in splits:
        scopes.append((split.upper(), [str(row.get("sample_id", "")).strip() for row in manifest_rows if str(row.get("split", "")).strip() == split]))
    tiers = sorted({str(row.get("tier", "")).strip() for row in manifest_rows if str(row.get("tier", "")).strip()})
    for tier in tiers:
        scopes.append((tier, [str(row.get("sample_id", "")).strip() for row in manifest_rows if str(row.get("tier", "")).strip() == tier]))

    performance: list[dict[str, Any]] = []
    for scope, ids in scopes:
        for strategy in STRATEGIES:
            avg, count = compute_average(cer_lookup, ids, selected_map, strategy)
            performance.append(
                {
                    "scope": scope,
                    "strategy": strategy,
                    "average_cer": avg,
                    "sample_count": count,
                }
            )
    return performance


def write_outputs(paths: dict[str, Path], decisions: list[dict[str, Any]], performance: list[dict[str, Any]]) -> None:
    paths["decisions_csv"].parent.mkdir(parents=True, exist_ok=True)
    paths["performance_csv"].parent.mkdir(parents=True, exist_ok=True)
    paths["summary_md"].parent.mkdir(parents=True, exist_ok=True)

    fieldnames = SPLIT_DECISION_COLUMNS if any("split" in row for row in decisions) else BASE_DECISION_COLUMNS
    with paths["decisions_csv"].open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(decisions)
    paths["decisions_json"].write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")

    with paths["performance_csv"].open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PERFORMANCE_COLUMNS)
        writer.writeheader()
        writer.writerows(performance)
    paths["performance_json"].write_text(json.dumps(performance, ensure_ascii=False, indent=2), encoding="utf-8")

    perf_map = {(row["scope"], row["strategy"]): row for row in performance}
    lines = [
        "# Synthetic Routing Stability Summary",
        "",
        "This is a stability check based on silver references built from snippet Whisper transcriptions.",
        "The test split is held out from any router tuning.",
        "",
        "## Average CER by Scope",
        "",
    ]
    for scope in ["ALL", "DEV", "TEST"]:
        if any((scope, strategy) in perf_map for strategy in STRATEGIES):
            lines.extend([f"### {scope}", "", "| strategy | average_cer | sample_count |", "| --- | ---: | ---: |"])
            for strategy in STRATEGIES:
                row = perf_map.get((scope, strategy))
                if row:
                    lines.append(f"| {row['strategy']} | {row['average_cer']} | {row['sample_count']} |")
            lines.append("")
    tier_scopes = sorted({row["scope"] for row in performance if row["scope"] not in {"ALL", "DEV", "TEST"}})
    if tier_scopes:
        lines.append("## Tier Breakdown")
        lines.append("")
        for scope in tier_scopes:
            lines.append(f"### {scope}")
            lines.append("")
            lines.append("| strategy | average_cer | sample_count |")
            lines.append("| --- | ---: | ---: |")
            for strategy in STRATEGIES:
                row = perf_map.get((scope, strategy))
                if row:
                    lines.append(f"| {row['strategy']} | {row['average_cer']} | {row['sample_count']} |")
            lines.append("")
    paths["summary_md"].write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    paths = dataset_paths(args.dataset)
    manifest_rows = load_manifest(paths["manifest"])
    cleaned_rows = load_cleaned_rows(paths["cleaned_dir"])
    decisions = build_decisions(manifest_rows, cleaned_rows, args.dataset)
    cer_lookup = load_cer_lookup(paths["cer"])
    performance = build_performance(manifest_rows, decisions, cer_lookup)
    write_outputs(paths, decisions, performance)
    print(f"Wrote synthetic routing decisions: {paths['decisions_csv'].relative_to(PROJECT_ROOT)}")
    print(f"Wrote synthetic routing performance: {paths['performance_csv'].relative_to(PROJECT_ROOT)}")
    print(f"Wrote synthetic routing summary: {paths['summary_md'].relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
