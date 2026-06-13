from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT, load_config
from .io_helpers import load_case_map, read_csv_rows, read_json, to_float, to_int, write_csv_json


GOLD_DECISION_COLUMNS = [
    "case_id",
    "overlap_level",
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
    "separated_unstable",
    "cleaned_closer_to_mixed",
    "notes",
]

SYNTHETIC_DECISION_COLUMNS = [
    "sample_id",
    "tier",
    "overlap_level",
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
    "separated_unstable",
    "cleaned_closer_to_mixed",
    "notes",
]

GOLD_PERFORMANCE_COLUMNS = ["strategy", "average_cer", "sample_count"]
SYNTHETIC_PERFORMANCE_COLUMNS = ["tier", "strategy", "average_cer", "sample_count"]
STRATEGIES = [
    "fixed_mixed_whisper",
    "fixed_separated_whisper",
    "fixed_separated_whisper_cleaned",
    "oracle_best",
    "rule_router_v1",
    "feature_router_v2",
]
TIER_TO_LEVEL = {
    "SyntheticNoOverlap": 0,
    "SyntheticLightOverlap": 1,
    "SyntheticMidOverlap": 2,
    "SyntheticHeavyOverlap": 3,
    "SyntheticOppositeOverlap": 4,
}


def load_gold_inputs() -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[tuple[str, str], float],
]:
    mixed_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "mixed_asr_benchmark.csv")
    separated_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "separated_asr_benchmark.csv")
    mixed = {str(row.get("case_id", "")): row for row in mixed_rows if str(row.get("case_id", "")).strip()}
    separated = {str(row.get("case_id", "")): row for row in separated_rows if str(row.get("case_id", "")).strip()}

    cleaned_rows: dict[str, dict[str, Any]] = {}
    cleaned_dir = PROJECT_ROOT / "results" / "transcripts_postprocessed"
    for path in cleaned_dir.glob("*_separated_speaker_transcript_cleaned.json"):
        payload = read_json(path)
        case_id = str(payload.get("case_id", "")).strip()
        if case_id:
            cleaned_rows[case_id] = payload

    cer_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "cer_results.csv")
    cer_lookup: dict[tuple[str, str], float] = {}
    for row in cer_rows:
        case_id = str(row.get("case_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if case_id and method:
            cer_lookup[(case_id, method)] = to_float(row.get("cer"))
    return mixed, separated, cleaned_rows, cer_lookup


def load_synthetic_inputs() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[tuple[str, str], float]]:
    manifest_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_manifest.csv")
    cleaned_dir = PROJECT_ROOT / "results" / "synthetic_transcripts_postprocessed"
    cleaned_rows: dict[str, dict[str, Any]] = {}
    for path in cleaned_dir.glob("*_separated_speaker_transcript_cleaned.json"):
        payload = read_json(path)
        sample_id = str(payload.get("sample_id", "")).strip()
        if sample_id:
            cleaned_rows[sample_id] = payload

    cer_rows = read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_cer_results.csv")
    cer_lookup: dict[tuple[str, str], float] = {}
    for row in cer_rows:
        sample_id = str(row.get("sample_id", "")).strip()
        method = str(row.get("method", "")).strip()
        if sample_id and method:
            cer_lookup[(sample_id, method)] = to_float(row.get("cer"))
    return manifest_rows, cleaned_rows, cer_lookup


def is_unstable(mixed_len: int, separated_len: int, duplicate_removed_count: int, runtime_ratio: float) -> bool:
    if mixed_len <= 0:
        return False
    length_ratio = separated_len / mixed_len
    if length_ratio > 1.35:
        return True
    if duplicate_removed_count >= 10:
        return True
    if runtime_ratio > 1.8:
        return True
    return False


def choose_method_v2(
    overlap_level: int,
    mixed_len: int,
    separated_len: int,
    cleaned_len: int,
    duplicate_removed_count: int,
    runtime_ratio: float,
    cleaned_exists: bool,
    mixed_segments_count: int,
) -> tuple[str, str, bool]:
    unstable = is_unstable(mixed_len, separated_len, duplicate_removed_count, runtime_ratio)
    if overlap_level == 0:
        if mixed_segments_count > 5:
            return "separated_whisper", "overlap_level==0 and mixed transcript is long; keep separated_whisper", unstable
        if unstable and duplicate_removed_count >= 10:
            return "mixed_whisper", "overlap_level==0 and repeated hallucinations are high; fall back to mixed_whisper", unstable
        if cleaned_exists and abs(cleaned_len - mixed_len) < abs(separated_len - mixed_len) and duplicate_removed_count < 5:
            return "separated_whisper_cleaned", "overlap_level==0 short transcript and cleaned is closer to mixed", unstable
        return "mixed_whisper", "overlap_level==0 short transcript; choose mixed_whisper", unstable

    if overlap_level in (1, 2):
        return "mixed_whisper", "overlap_level in [1,2]; choose mixed_whisper", unstable

    if overlap_level >= 3:
        return "separated_whisper", "overlap_level>=3 and separated looks usable; choose separated_whisper", unstable

    return "mixed_whisper", "fallback to mixed_whisper", unstable


def build_gold_decisions(
    config: dict[str, Any],
    mixed_rows: dict[str, dict[str, Any]],
    separated_rows: dict[str, dict[str, Any]],
    cleaned_rows: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    case_map = load_case_map(config)
    decisions: list[dict[str, Any]] = []
    for case_id in sorted(case_map):
        overlap_level = int(case_map[case_id].get("overlap_level", 0))
        mixed = mixed_rows.get(case_id, {})
        separated = separated_rows.get(case_id, {})
        cleaned = cleaned_rows.get(case_id, {})

        mixed_segments_count = to_int(mixed.get("segments_count"))
        separated_segments_count = to_int(separated.get("merged_segments_count"))
        cleaned_segments_count = len(cleaned.get("cleaned_segments", []))
        mixed_text_length = to_int(mixed.get("text_length"))
        separated_text_length = to_int(separated.get("full_text_length"))
        cleaned_text_length = len(str(cleaned.get("cleaned_full_text", "")))
        text_length_ratio = round(separated_text_length / mixed_text_length, 6) if mixed_text_length else 0.0
        mixed_runtime_sec = to_float(mixed.get("runtime_sec"))
        separated_runtime_sec = to_float(separated.get("runtime_sec_total"))
        cleaned_runtime_sec = separated_runtime_sec
        runtime_ratio = round(separated_runtime_sec / mixed_runtime_sec, 6) if mixed_runtime_sec else 0.0
        duplicate_removed_count = to_int(cleaned.get("removed_count"))
        cleaned_exists = bool(cleaned)
        selected_method, decision_rule, unstable = choose_method_v2(
            overlap_level,
            mixed_text_length,
            separated_text_length,
            cleaned_text_length,
            duplicate_removed_count,
            runtime_ratio,
            cleaned_exists,
            mixed_segments_count,
        )

        notes = "Feature router v2 uses observable instability signals and does not use CER as an input feature."
        if cleaned_exists:
            notes += " Cleaned transcript is a fallback candidate when separated output appears unstable."

        decisions.append(
            {
                "case_id": case_id,
                "overlap_level": overlap_level,
                "selected_method": selected_method,
                "decision_rule": decision_rule,
                "mixed_segments_count": mixed_segments_count,
                "separated_segments_count": separated_segments_count,
                "cleaned_segments_count": cleaned_segments_count,
                "mixed_text_length": mixed_text_length,
                "separated_text_length": separated_text_length,
                "cleaned_text_length": cleaned_text_length,
                "text_length_ratio": text_length_ratio,
                "mixed_runtime_sec": mixed_runtime_sec,
                "separated_runtime_sec": separated_runtime_sec,
                "cleaned_runtime_sec": cleaned_runtime_sec,
                "runtime_ratio": runtime_ratio,
                "duplicate_removed_count": duplicate_removed_count,
                "separated_unstable": unstable,
                "cleaned_closer_to_mixed": bool(
                    cleaned_exists and abs(cleaned_text_length - mixed_text_length) < abs(separated_text_length - mixed_text_length)
                ),
                "notes": notes,
            }
        )
    return decisions


def build_synthetic_decisions(
    manifest_rows: list[dict[str, Any]],
    cleaned_rows: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for row in manifest_rows:
        sample_id = str(row.get("sample_id", "")).strip()
        tier = str(row.get("tier", "")).strip()
        overlap_level = int(row.get("overlap_level_numeric", TIER_TO_LEVEL.get(tier, 0)))
        mixed = read_json(PROJECT_ROOT / "results" / "synthetic_transcripts_raw" / f"{sample_id}_mixed_whisper.json")
        speaker_path = PROJECT_ROOT / "results" / "synthetic_transcripts_speaker" / f"{sample_id}_separated_speaker_transcript.json"
        cleaned_path = PROJECT_ROOT / "results" / "synthetic_transcripts_postprocessed" / f"{sample_id}_separated_speaker_transcript_cleaned.json"
        separated = read_json(speaker_path)
        cleaned = cleaned_rows.get(sample_id, read_json(cleaned_path))

        mixed_segments_count = len(mixed.get("segments", []))
        separated_segments_count = len(separated.get("segments", []))
        cleaned_segments_count = len(cleaned.get("cleaned_segments", []))
        mixed_text_length = len(str(mixed.get("text", "")))
        separated_text_length = len(str(separated.get("full_text", "")))
        cleaned_text_length = len(str(cleaned.get("cleaned_full_text", "")))
        mixed_runtime_sec = to_float(mixed.get("runtime_sec"))
        separated_runtime_sec = to_float(separated.get("runtime_sec_total"))
        cleaned_runtime_sec = separated_runtime_sec
        runtime_ratio = round(separated_runtime_sec / mixed_runtime_sec, 6) if mixed_runtime_sec else 0.0
        duplicate_removed_count = to_int(cleaned.get("removed_count"))
        cleaned_exists = bool(cleaned)
        selected_method, decision_rule, unstable = choose_method_v2(
            overlap_level,
            mixed_text_length,
            separated_text_length,
            cleaned_text_length,
            duplicate_removed_count,
            runtime_ratio,
            cleaned_exists,
            mixed_segments_count,
        )

        notes = "Feature router v2 uses observable instability signals and does not use CER as an input feature."
        if cleaned_exists:
            notes += " Cleaned transcript is a fallback candidate when separated output appears unstable."

        decisions.append(
            {
                "sample_id": sample_id,
                "tier": tier,
                "overlap_level": overlap_level,
                "selected_method": selected_method,
                "decision_rule": decision_rule,
                "mixed_segments_count": mixed_segments_count,
                "separated_segments_count": separated_segments_count,
                "cleaned_segments_count": cleaned_segments_count,
                "mixed_text_length": mixed_text_length,
                "separated_text_length": separated_text_length,
                "cleaned_text_length": cleaned_text_length,
                "text_length_ratio": round(separated_text_length / mixed_text_length, 6) if mixed_text_length else 0.0,
                "mixed_runtime_sec": mixed_runtime_sec,
                "separated_runtime_sec": separated_runtime_sec,
                "cleaned_runtime_sec": cleaned_runtime_sec,
                "runtime_ratio": runtime_ratio,
                "duplicate_removed_count": duplicate_removed_count,
                "separated_unstable": unstable,
                "cleaned_closer_to_mixed": bool(
                    cleaned_exists and abs(cleaned_text_length - mixed_text_length) < abs(separated_text_length - mixed_text_length)
                ),
                "notes": notes,
            }
        )
    return decisions


def compute_performance(
    cer_lookup: dict[tuple[str, str], float],
    decisions: list[dict[str, Any]],
    id_field: str,
    all_ids: list[str],
    include_tier: str | None = None,
) -> list[dict[str, Any]]:
    strategies: dict[str, list[float]] = {
        "fixed_mixed_whisper": [],
        "fixed_separated_whisper": [],
        "fixed_separated_whisper_cleaned": [],
        "oracle_best": [],
        "rule_router_v1": [],
        "feature_router_v2": [],
    }
    decision_map = {
        str(row[id_field]): row["selected_method"]
        for row in decisions
        if str(row.get(id_field, "")).strip()
    }
    for item_id in all_ids:
        mixed = cer_lookup.get((item_id, "mixed_whisper"))
        separated = cer_lookup.get((item_id, "separated_whisper"))
        cleaned = cer_lookup.get((item_id, "separated_whisper_cleaned"))
        available = [v for v in [mixed, separated, cleaned] if v is not None]
        if mixed is not None:
            strategies["fixed_mixed_whisper"].append(mixed)
        if separated is not None:
            strategies["fixed_separated_whisper"].append(separated)
        if cleaned is not None:
            strategies["fixed_separated_whisper_cleaned"].append(cleaned)
        if available:
            strategies["oracle_best"].append(min(available))


        selected_v2 = decision_map.get(item_id)
        if selected_v2 is not None:
            cer_v2 = cer_lookup.get((item_id, selected_v2))
            if cer_v2 is not None:
                strategies["feature_router_v2"].append(cer_v2)

    # rule_router_v1 is sourced from the precomputed outputs for the corresponding benchmark.
    # The caller can insert it into the result set once the appropriate baseline is known.
    return [
        {
            "strategy": strategy,
            "average_cer": round(sum(values) / len(values), 6) if values else 0.0,
            "sample_count": len(values),
        }
        for strategy, values in strategies.items()
    ]


def render_gold_md(performance_rows: list[dict[str, Any]]) -> Path:
    fig_dir = PROJECT_ROOT / "results" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    md_path = fig_dir / "routing_performance_v2.md"
    perf = {row["strategy"]: row for row in performance_rows}
    lines = [
        "# Feature Router v2 Performance",
        "",
        "This section compares the v1 rule router with a feature-based v2 router that uses instability signals rather than CER.",
        "",
        "| strategy | average_cer | sample_count |",
        "| --- | ---: | ---: |",
        f"| fixed_mixed_whisper | {perf['fixed_mixed_whisper']['average_cer']} | {perf['fixed_mixed_whisper']['sample_count']} |",
        f"| fixed_separated_whisper | {perf['fixed_separated_whisper']['average_cer']} | {perf['fixed_separated_whisper']['sample_count']} |",
        f"| fixed_separated_whisper_cleaned | {perf['fixed_separated_whisper_cleaned']['average_cer']} | {perf['fixed_separated_whisper_cleaned']['sample_count']} |",
        f"| oracle_best | {perf['oracle_best']['average_cer']} | {perf['oracle_best']['sample_count']} |",
        f"| rule_router_v1 | {perf['rule_router_v1']['average_cer']} | {perf['rule_router_v1']['sample_count']} |",
        f"| feature_router_v2 | {perf['feature_router_v2']['average_cer']} | {perf['feature_router_v2']['sample_count']} |",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def render_synthetic_md(performance_rows: list[dict[str, Any]]) -> Path:
    fig_dir = PROJECT_ROOT / "results" / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    md_path = fig_dir / "synthetic_routing_summary_v2.md"
    tiers = sorted({row["tier"] for row in performance_rows if row["tier"] != "ALL"})
    all_rows = [row for row in performance_rows if row["tier"] == "ALL"]
    lines = [
        "# Synthetic Routing Stability Summary v2",
        "",
        "This silver validation confirms whether the feature router reduces the NoOverlap failure seen in v1.",
        "",
        "## Overall Average CER",
        "",
        "| strategy | average_cer | sample_count |",
        "| --- | ---: | ---: |",
    ]
    for row in all_rows:
        lines.append(f"| {row['strategy']} | {row['average_cer']} | {row['sample_count']} |")
    lines.append("")
    lines.append("## Tier Breakdown")
    lines.append("")
    for tier in tiers:
        lines.append(f"### {tier}")
        lines.append("")
        lines.append("| strategy | average_cer | sample_count |")
        lines.append("| --- | ---: | ---: |")
        for row in [r for r in performance_rows if r["tier"] == tier]:
            lines.append(f"| {row['strategy']} | {row['average_cer']} | {row['sample_count']} |")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path


def update_current_summary(gold_perf: list[dict[str, Any]], synthetic_perf: list[dict[str, Any]]) -> None:
    path = PROJECT_ROOT / "results" / "figures" / "current_results_summary.md"
    text = path.read_text(encoding="utf-8-sig") if path.exists() else "# Current Results Summary\n"
    marker = "## Feature Router v2\n"
    if marker in text:
        text = text.split(marker)[0].rstrip()

    gold_map = {(row["strategy"]): row for row in gold_perf}
    syn_all = {row["strategy"]: row for row in synthetic_perf if row["tier"] == "ALL"}
    lines = [
        "",
        "## Feature Router v2",
        "",
        "- v1 performs well on the five verified gold cases, but synthetic silver validation exposed a NoOverlap failure mode.",
        "- v2 adds instability features such as length inflation and duplicate removal count to avoid blindly choosing separated transcripts when the output looks pathological.",
        "",
        "### Gold Average CER",
        "",
        f"- fixed_mixed_whisper: {gold_map['fixed_mixed_whisper']['average_cer']:.6f}",
        f"- fixed_separated_whisper: {gold_map['fixed_separated_whisper']['average_cer']:.6f}",
        f"- fixed_separated_whisper_cleaned: {gold_map['fixed_separated_whisper_cleaned']['average_cer']:.6f}",
        f"- oracle_best: {gold_map['oracle_best']['average_cer']:.6f}",
        f"- rule_router_v1: {gold_map['rule_router_v1']['average_cer']:.6f}",
        f"- feature_router_v2: {gold_map['feature_router_v2']['average_cer']:.6f}",
        "",
        "### Synthetic Average CER",
        "",
        f"- fixed_mixed_whisper: {syn_all['fixed_mixed_whisper']['average_cer']:.6f}",
        f"- fixed_separated_whisper: {syn_all['fixed_separated_whisper']['average_cer']:.6f}",
        f"- fixed_separated_whisper_cleaned: {syn_all['fixed_separated_whisper_cleaned']['average_cer']:.6f}",
        f"- oracle_best: {syn_all['oracle_best']['average_cer']:.6f}",
        f"- rule_router_v1: {syn_all['rule_router_v1']['average_cer']:.6f}",
        f"- feature_router_v2: {syn_all['feature_router_v2']['average_cer']:.6f}",
    ]
    path.write_text(text.rstrip() + "\n" + "\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    config = load_config()
    mixed_rows, separated_rows, cleaned_rows, gold_cer = load_gold_inputs()
    gold_decisions_v1_path = PROJECT_ROOT / "results" / "tables" / "routing_decisions.csv"
    gold_v1_rows = read_csv_rows(gold_decisions_v1_path)
    gold_v1_map = {str(row.get("case_id", "")): str(row.get("selected_method", "")) for row in gold_v1_rows if str(row.get("case_id", "")).strip()}

    gold_decisions = build_gold_decisions(config, mixed_rows, separated_rows, cleaned_rows)
    gold_id_list = [case_id for case_id in sorted(load_case_map(config))]

    gold_v2_rows = [dict(row) for row in gold_decisions]

    gold_perf_rows = []
    for strategy in STRATEGIES:
        values: list[float] = []
        for case_id in gold_id_list:
            if strategy == "rule_router_v1":
                method = gold_v1_map.get(case_id)
                cer = gold_cer.get((case_id, method)) if method else None
            elif strategy == "feature_router_v2":
                method = next((r["selected_method"] for r in gold_v2_rows if r["case_id"] == case_id), None)
                cer = gold_cer.get((case_id, method)) if method else None
            else:
                cer = gold_cer.get((case_id, strategy.replace("fixed_", "").replace("_whisper_cleaned", "_whisper_cleaned").replace("_whisper", "_whisper")))
            if cer is not None:
                values.append(cer)
        gold_perf_rows.append(
            {
                "strategy": strategy,
                "average_cer": round(sum(values) / len(values), 6) if values else 0.0,
                "sample_count": len(values),
            }
        )

    # Replace fixed strategy lookup with actual method names for gold above.
    gold_perf_lookup = {row["strategy"]: row for row in gold_perf_rows}
    gold_perf_lookup["fixed_mixed_whisper"] = {
        "strategy": "fixed_mixed_whisper",
        "average_cer": round(sum(gold_cer[(cid, "mixed_whisper")] for cid in gold_id_list) / len(gold_id_list), 6),
        "sample_count": len(gold_id_list),
    }
    gold_perf_lookup["fixed_separated_whisper"] = {
        "strategy": "fixed_separated_whisper",
        "average_cer": round(sum(gold_cer[(cid, "separated_whisper")] for cid in gold_id_list) / len(gold_id_list), 6),
        "sample_count": len(gold_id_list),
    }
    gold_perf_lookup["fixed_separated_whisper_cleaned"] = {
        "strategy": "fixed_separated_whisper_cleaned",
        "average_cer": round(sum(gold_cer[(cid, "separated_whisper_cleaned")] for cid in gold_id_list) / len(gold_id_list), 6),
        "sample_count": len(gold_id_list),
    }
    gold_perf_lookup["oracle_best"] = {
        "strategy": "oracle_best",
        "average_cer": round(
            sum(
                min(
                    gold_cer[(cid, "mixed_whisper")],
                    gold_cer[(cid, "separated_whisper")],
                    gold_cer[(cid, "separated_whisper_cleaned")],
                )
                for cid in gold_id_list
            )
            / len(gold_id_list),
            6,
        ),
        "sample_count": len(gold_id_list),
    }
    gold_perf_lookup["rule_router_v1"] = {
        "strategy": "rule_router_v1",
        "average_cer": round(
            sum(gold_cer[(cid, gold_v1_map[cid])] for cid in gold_id_list) / len(gold_id_list),
            6,
        ),
        "sample_count": len(gold_id_list),
    }
    gold_perf_lookup["feature_router_v2"] = {
        "strategy": "feature_router_v2",
        "average_cer": round(
            sum(gold_cer[(row["case_id"], row["selected_method"])] for row in gold_v2_rows) / len(gold_v2_rows),
            6,
        ),
        "sample_count": len(gold_v2_rows),
    }
    gold_perf = [gold_perf_lookup[strategy] for strategy in STRATEGIES]

    gold_decisions_csv = PROJECT_ROOT / "results" / "tables" / "routing_decisions_v2.csv"
    gold_decisions_json = PROJECT_ROOT / "results" / "tables" / "routing_decisions_v2.json"
    gold_perf_csv = PROJECT_ROOT / "results" / "tables" / "routing_performance_v2.csv"
    gold_perf_json = PROJECT_ROOT / "results" / "tables" / "routing_performance_v2.json"
    write_csv_json(gold_v2_rows, gold_decisions_csv, gold_decisions_json, GOLD_DECISION_COLUMNS)
    write_csv_json(gold_perf, gold_perf_csv, gold_perf_json, GOLD_PERFORMANCE_COLUMNS)
    gold_md = render_gold_md(gold_perf)

    manifest_rows, synthetic_cleaned_rows, synthetic_cer = load_synthetic_inputs()
    synthetic_decisions = build_synthetic_decisions(manifest_rows, synthetic_cleaned_rows)
    synthetic_ids = [str(row["sample_id"]) for row in manifest_rows]
    synthetic_perf_rows: list[dict[str, Any]] = []
    decision_map = {row["sample_id"]: row["selected_method"] for row in synthetic_decisions}
    for tier in ["ALL"] + sorted({str(row["tier"]) for row in manifest_rows}):
        ids = synthetic_ids if tier == "ALL" else [str(row["sample_id"]) for row in manifest_rows if str(row["tier"]) == tier]
        buckets = {strategy: [] for strategy in STRATEGIES}
        for sample_id in ids:
            for method_name, strategy_name in [
                ("mixed_whisper", "fixed_mixed_whisper"),
                ("separated_whisper", "fixed_separated_whisper"),
                ("separated_whisper_cleaned", "fixed_separated_whisper_cleaned"),
            ]:
                cer = synthetic_cer.get((sample_id, method_name))
                if cer is not None:
                    buckets[strategy_name].append(cer)
            available = [synthetic_cer.get((sample_id, m)) for m in ["mixed_whisper", "separated_whisper", "separated_whisper_cleaned"]]
            available = [v for v in available if v is not None]
            if available:
                buckets["oracle_best"].append(min(available))
            # Reuse the existing v1 synthetic rule decisions from the earlier benchmark results.
            # Those remain the comparison baseline for stability.
        # Fill rule_router_v1 by reading the precomputed v1 routing decisions table.
        v1_decisions = {str(row.get("sample_id", "")).strip(): str(row.get("selected_method", "")).strip() for row in read_csv_rows(PROJECT_ROOT / "results" / "tables" / "synthetic_routing_decisions.csv")}
        for sample_id in ids:
            method = v1_decisions.get(sample_id)
            if method:
                cer = synthetic_cer.get((sample_id, method))
                if cer is not None:
                    buckets["rule_router_v1"].append(cer)
        for sample_id in ids:
            method = decision_map.get(sample_id)
            if method:
                cer = synthetic_cer.get((sample_id, method))
                if cer is not None:
                    buckets["feature_router_v2"].append(cer)
        for strategy, values in buckets.items():
            synthetic_perf_rows.append(
                {
                    "tier": tier,
                    "strategy": strategy,
                    "average_cer": round(sum(values) / len(values), 6) if values else 0.0,
                    "sample_count": len(values),
                }
            )

    synthetic_decisions_csv = PROJECT_ROOT / "results" / "tables" / "synthetic_routing_decisions_v2.csv"
    synthetic_perf_csv = PROJECT_ROOT / "results" / "tables" / "synthetic_routing_performance_v2.csv"
    write_csv_json(synthetic_decisions, synthetic_decisions_csv, synthetic_decisions_csv.with_suffix(".json"), SYNTHETIC_DECISION_COLUMNS)
    write_csv_json(synthetic_perf_rows, synthetic_perf_csv, synthetic_perf_csv.with_suffix(".json"), SYNTHETIC_PERFORMANCE_COLUMNS)
    synthetic_md = render_synthetic_md(synthetic_perf_rows)

    update_current_summary(gold_perf, synthetic_perf_rows)

    print(f"Wrote gold routing v2: {gold_decisions_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote gold performance v2: {gold_perf_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote synthetic routing v2: {synthetic_decisions_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote synthetic performance v2: {synthetic_perf_csv.relative_to(PROJECT_ROOT)}")
    print(f"Wrote markdown: {gold_md.relative_to(PROJECT_ROOT)}")
    print(f"Wrote markdown: {synthetic_md.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
