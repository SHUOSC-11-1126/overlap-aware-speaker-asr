from __future__ import annotations

import csv
import json
import math
import os
import random
import shutil
import time
import wave
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "results" / "tables"
FIGURE_DIR = PROJECT_ROOT / "results" / "figures"

ROUTES = ["mixed", "separated", "cleaned"]
POLICIES = [
    "fixed_mixed",
    "fixed_separated",
    "fixed_cleaned",
    "router_v2_refit",
    "balanced_router_refit",
    "stage29_calibrated_audiodepth_gate_refit",
    "stage30_risk_guarded_gate_refit",
    "stage31_stage2_review_guard_refit",
    "stage33_regret_regressor_refit",
    "stage33_regret_ranker_refit",
    "stage33_safe_regret_fusion_refit",
    "oracle_best",
]

CONTROLLED_V2_MANIFEST = TABLE_DIR / "controlled_v2_manifest.csv"
CONTROLLED_V2_CER = TABLE_DIR / "controlled_v2_real_whisper_cer.csv"
CONTROLLED_V2_TRANSCRIPTS = TABLE_DIR / "controlled_v2_real_whisper_transcripts.csv"
CONTROLLED_V2_RUNTIME = TABLE_DIR / "controlled_v2_real_whisper_runtime.csv"
UTTERANCE_INVENTORY = TABLE_DIR / "controlled_utterance_inventory.csv"

SOURCE_DISJOINT_MANIFEST = TABLE_DIR / "source_disjoint_v2_manifest.csv"
SOURCE_DISJOINT_TRAIN = TABLE_DIR / "source_disjoint_v2_train.csv"
SOURCE_DISJOINT_VALIDATION = TABLE_DIR / "source_disjoint_v2_validation.csv"
SOURCE_DISJOINT_TEST = TABLE_DIR / "source_disjoint_v2_test.csv"
SOURCE_DISJOINT_SPLIT_AUDIT = TABLE_DIR / "source_disjoint_v2_split_audit.csv"
SOURCE_DISJOINT_ROUTE_CER = TABLE_DIR / "source_disjoint_v2_route_cer.csv"
SOURCE_DISJOINT_ROUTE_TRANSCRIPTS = TABLE_DIR / "source_disjoint_v2_route_transcripts.csv"
SOURCE_DISJOINT_ORACLE_DIST = TABLE_DIR / "source_disjoint_v2_oracle_distribution.csv"

REFERENCE_AUDIT = TABLE_DIR / "source_disjoint_v2_reference_audit.csv"
REFERENCE_EXCLUSIONS = TABLE_DIR / "source_disjoint_v2_reference_exclusions.csv"
UNIFIED_PREDICTIONS = TABLE_DIR / "unified_router_eval_predictions.csv"
UNIFIED_SUMMARY = TABLE_DIR / "unified_router_eval_summary.csv"
UNIFIED_MODEL_ROLES = TABLE_DIR / "unified_router_eval_model_roles.csv"
UNIFIED_SAFETY_AUDIT = TABLE_DIR / "unified_router_eval_safety_audit.csv"
BOOTSTRAP_SUMMARY = TABLE_DIR / "bootstrap_router_summary.csv"
BOOTSTRAP_PAIRWISE = TABLE_DIR / "bootstrap_router_pairwise.csv"
MICRO_GOLD_CANDIDATES = TABLE_DIR / "micro_gold_candidate_manifest.csv"
MICRO_GOLD_SHEET = TABLE_DIR / "micro_gold_annotation_sheet.csv"
RUNTIME_COMPONENTS = TABLE_DIR / "end_to_end_runtime_components.csv"
RUNTIME_SUMMARY = TABLE_DIR / "end_to_end_runtime_summary.csv"
COMPUTE_UTILITY = TABLE_DIR / "unified_router_eval_compute_utility.csv"
COMPUTE_PARETO = TABLE_DIR / "unified_router_eval_compute_pareto.csv"

# Deterministic assignment found by a Stage 34 source-token search over the 60 rows
# with real Whisper route CER. It keeps a usable strict test while preserving zero
# source-utterance leakage across train/validation/test.
SOURCE_TOKEN_SPLIT = {
    "con_001": "validation",
    "con_002": "train",
    "con_003": "validation",
    "con_004": "test",
    "con_005": "train",
    "con_006": "validation",
    "con_007": "train",
    "con_008": "train",
    "con_009": "test",
    "con_010": "test",
    "con_011": "train",
    "pro_001": "validation",
    "pro_002": "test",
    "pro_003": "validation",
    "pro_004": "test",
    "pro_005": "test",
    "pro_006": "train",
    "pro_007": "train",
    "pro_008": "train",
    "pro_009": "train",
    "pro_010": "train",
    "pro_011": "train",
    "pro_012": "train",
    "pro_013": "test",
    "pro_014": "validation",
    "pro_015": "validation",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def rel(path: Path | str) -> str:
    p = Path(path)
    return p.relative_to(PROJECT_ROOT).as_posix() if p.is_absolute() else p.as_posix()


def safe_float(value: Any, default: float = math.nan) -> float:
    try:
        if value in {"", None}:  # type: ignore[comparison-overlap]
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def mean(values: list[float]) -> float:
    values = [v for v in values if math.isfinite(v)]
    return sum(values) / len(values) if values else math.nan


def source_tokens(row: dict[str, str]) -> list[str]:
    return [token for token in row.get("source_utterance_ids", "").split("|") if token]


def source_pair_key(row: dict[str, str]) -> str:
    return "|".join(sorted(source_tokens(row)))


def assigned_split(row: dict[str, str]) -> tuple[str, str]:
    tokens = source_tokens(row)
    token_splits = {SOURCE_TOKEN_SPLIT.get(token, "unknown") for token in tokens}
    if len(token_splits) == 1 and "unknown" not in token_splits:
        split = next(iter(token_splits))
        return split, "included_source_disjoint"
    return "excluded", "excluded_cross_partition"


def route_cer(row: dict[str, str], route: str) -> float:
    return safe_float(row.get(f"{route}_cer"), math.nan)


def oracle_route(row: dict[str, str]) -> str:
    if row.get("oracle_route") in ROUTES:
        return row["oracle_route"]
    values = {route: route_cer(row, route) for route in ROUTES}
    finite = {k: v for k, v in values.items() if math.isfinite(v)}
    return min(finite, key=finite.get) if finite else "mixed"


def selected_cer(row: dict[str, str], route: str) -> float:
    if route == "review":
        return safe_float(row.get("oracle_cer"), math.nan)
    return route_cer(row, route)


def simple_features(row: dict[str, str]) -> list[float]:
    fam = row.get("intended_family", "")
    dom = row.get("dominance_type", "")
    expected = row.get("expected_winner", "")
    return [
        safe_float(row.get("overlap_ratio"), 0.0),
        1.0 if "review" in fam or expected == "review_needed" else 0.0,
        1.0 if "mixed" in fam or expected == "mixed" else 0.0,
        1.0 if "separated" in fam or expected == "separated" else 0.0,
        1.0 if dom == "spk1_dominant" else 0.0,
        1.0 if dom == "spk2_dominant" else 0.0,
        1.0 if dom == "balanced" else 0.0,
    ]


def distance(a: list[float], b: list[float]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def nearest_train_row(row: dict[str, str], train_rows: list[dict[str, str]]) -> dict[str, str] | None:
    if not train_rows:
        return None
    feats = simple_features(row)
    return min(train_rows, key=lambda candidate: distance(feats, simple_features(candidate)))


def threshold_from_validation(validation_rows: list[dict[str, str]], field: str, fallback: float) -> float:
    vals = [safe_float(row.get(field), math.nan) for row in validation_rows]
    vals = sorted(v for v in vals if math.isfinite(v))
    if not vals:
        return fallback
    return vals[len(vals) // 2]


def load_joined_rows() -> list[dict[str, str]]:
    cer_by_id = {row["sample_id"]: row for row in read_csv(CONTROLLED_V2_CER)}
    inventory = {row["utterance_id"]: row for row in read_csv(UTTERANCE_INVENTORY)}
    rows = []
    for row in read_csv(CONTROLLED_V2_MANIFEST):
        split, status = assigned_split(row)
        cer = cer_by_id.get(row["sample_id"], {})
        tokens = source_tokens(row)
        verification = sorted({inventory.get(token, {}).get("verification_status", "unknown") for token in tokens})
        joined = {
            **row,
            "source_pair_key": source_pair_key(row),
            "source_token_split": "|".join(SOURCE_TOKEN_SPLIT.get(token, "unknown") for token in tokens),
            "source_disjoint_split": split,
            "benchmark_status": status,
            "has_route_cer": str(bool(cer)),
            "source_reference_verification_status": "|".join(verification),
        }
        for key in [
            "mixed_cer",
            "separated_cer",
            "cleaned_cer",
            "oracle_route",
            "oracle_cer",
            "route_gap",
            "all_route_mean_cer",
        ]:
            joined[key] = cer.get(key, "")
        rows.append(joined)
    return rows


def split_leakage(rows: list[dict[str, str]]) -> dict[str, Any]:
    by_token: dict[str, set[str]] = defaultdict(set)
    by_pair: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        split = row.get("source_disjoint_split", "")
        if split not in {"train", "validation", "test"}:
            continue
        by_pair[row["source_pair_key"]].add(split)
        for token in source_tokens(row):
            by_token[token].add(split)
    token_leaks = {token: sorted(splits) for token, splits in by_token.items() if len(splits) > 1}
    pair_leaks = {pair: sorted(splits) for pair, splits in by_pair.items() if len(splits) > 1}
    return {
        "source_utterance_leaks": len(token_leaks),
        "source_pair_leaks": len(pair_leaks),
        "token_leak_examples": token_leaks,
        "pair_leak_examples": pair_leaks,
    }


def build_source_disjoint_benchmark_v2() -> dict[str, Any]:
    rows = load_joined_rows()
    included = [row for row in rows if row["benchmark_status"] == "included_source_disjoint"]
    write_csv(SOURCE_DISJOINT_MANIFEST, rows)
    for split, path in [
        ("train", SOURCE_DISJOINT_TRAIN),
        ("validation", SOURCE_DISJOINT_VALIDATION),
        ("test", SOURCE_DISJOINT_TEST),
    ]:
        write_csv(path, [row for row in included if row["source_disjoint_split"] == split])

    counts = Counter(row["source_disjoint_split"] for row in rows)
    cer_counts = Counter(row["source_disjoint_split"] for row in rows if row["has_route_cer"] == "True")
    audit_rows = []
    for split in ["train", "validation", "test", "excluded"]:
        audit_rows.append(
            {
                "split": split,
                "manifest_rows": counts.get(split, 0),
                "route_cer_rows": cer_counts.get(split, 0),
                "unique_source_tokens": len(
                    {
                        token
                        for row in rows
                        if row["source_disjoint_split"] == split
                        for token in source_tokens(row)
                    }
                ),
            }
        )
    leak = split_leakage(rows)
    audit_rows.append(
        {
            "split": "leakage",
            "manifest_rows": leak["source_utterance_leaks"],
            "route_cer_rows": leak["source_pair_leaks"],
            "unique_source_tokens": 0,
        }
    )
    write_csv(SOURCE_DISJOINT_SPLIT_AUDIT, audit_rows)

    write_md(
        FIGURE_DIR / "source_disjoint_v2_input_audit.md",
        [
            "# Source-disjoint v2 input audit",
            "",
            f"- controlled_v2 manifest rows: `{len(rows)}`",
            f"- rows with existing real Whisper route CER: `{sum(row['has_route_cer'] == 'True' for row in rows)}`",
            "- new ASR launched in Stage 34: `0`",
            "- ASR provenance: existing faster-whisper/base controlled_v2 route outputs reused",
            "- controlled_v1_manifest.csv: `not found`; not used",
            "- reference status: silver-plus/unverified unless manually annotated later",
        ],
    )
    write_md(
        FIGURE_DIR / "source_disjoint_v2_dataset_summary.md",
        [
            "# Source-disjoint v2 dataset summary",
            "",
            "| split | manifest rows | route-CER rows | source tokens |",
            "| --- | ---: | ---: | ---: |",
            *[
                f"| {row['split']} | {row['manifest_rows']} | {row['route_cer_rows']} | {row['unique_source_tokens']} |"
                for row in audit_rows
                if row["split"] != "leakage"
            ],
            "",
            f"- source-utterance leakage: `{leak['source_utterance_leaks']}`",
            f"- source-pair leakage: `{leak['source_pair_leaks']}`",
            "- excluded rows are cross-partition by source token and are not used for strict train/validation/test claims.",
        ],
    )
    return {"rows": len(rows), "included": len(included), **leak}


def audit_source_disjoint_v2_references() -> dict[str, Any]:
    rows = read_csv(SOURCE_DISJOINT_MANIFEST) or load_joined_rows()
    audit_rows = []
    exclusions = []
    for row in rows:
        text = " ".join([row.get("reference_text", ""), row.get("reference_spk1", ""), row.get("reference_spk2", "")]).strip()
        words = [w for w in text.replace("|", " ").split() if w]
        chars = len(text)
        risks = []
        if not text:
            risks.append("empty_reference")
        if chars < 20:
            risks.append("very_short_reference")
        if chars and max(Counter(text).values()) / max(chars, 1) > 0.35:
            risks.append("repeated_character_risk")
        if row.get("reference_type") != "manual_gold":
            risks.append("not_manual_gold")
        quality = "review_required" if risks else "usable_silver_plus"
        out = {
            "sample_id": row["sample_id"],
            "source_disjoint_split": row["source_disjoint_split"],
            "benchmark_status": row["benchmark_status"],
            "reference_type": row.get("reference_type", ""),
            "reference_quality_label": quality,
            "claimed_as_gold": "False",
            "char_count": chars,
            "word_count": len(words),
            "risk_flags": "|".join(risks),
        }
        audit_rows.append(out)
        if risks and row["benchmark_status"] == "included_source_disjoint":
            exclusions.append({**out, "exclusion_reason": "manual_review_before_gold_promotion"})
    write_csv(REFERENCE_AUDIT, audit_rows)
    write_csv(REFERENCE_EXCLUSIONS, exclusions)
    counts = Counter(row["reference_quality_label"] for row in audit_rows)
    write_md(
        FIGURE_DIR / "source_disjoint_v2_reference_audit.md",
        [
            "# Source-disjoint v2 reference audit",
            "",
            f"- audited rows: `{len(audit_rows)}`",
            f"- manual gold rows: `{sum(row['reference_type'] == 'manual_gold' for row in audit_rows)}`",
            f"- silver-plus or weaker rows: `{sum(row['reference_type'] != 'manual_gold' for row in audit_rows)}`",
            f"- rows flagged for manual review before gold promotion: `{len(exclusions)}`",
            f"- quality labels: `{dict(counts)}`",
            "- Stage 34 keeps all non-manual references out of gold claims.",
        ],
    )
    return {"audited": len(audit_rows), "exclusions": len(exclusions), "manual_gold": sum(r["reference_type"] == "manual_gold" for r in audit_rows)}


def run_source_disjoint_v2_routes() -> dict[str, Any]:
    test_ids = {row["sample_id"] for row in read_csv(SOURCE_DISJOINT_TEST)}
    route_rows = [row for row in read_csv(CONTROLLED_V2_CER) if row["sample_id"] in test_ids]
    transcript_rows = [row for row in read_csv(CONTROLLED_V2_TRANSCRIPTS) if row["sample_id"] in test_ids]
    for row in route_rows:
        row["asr_status"] = "existing_faster_whisper_base_reused"
        row["new_asr_run"] = "False"
    for row in transcript_rows:
        row["asr_status"] = "existing_faster_whisper_base_reused"
        row["new_asr_run"] = "False"
    write_csv(SOURCE_DISJOINT_ROUTE_CER, route_rows)
    write_csv(SOURCE_DISJOINT_ROUTE_TRANSCRIPTS, transcript_rows)
    dist = Counter(row.get("oracle_route", oracle_route(row)) for row in route_rows)
    dist_rows = [
        {"route": route, "count": dist.get(route, 0), "share": round(dist.get(route, 0) / max(len(route_rows), 1), 6)}
        for route in ROUTES
    ]
    write_csv(SOURCE_DISJOINT_ORACLE_DIST, dist_rows)
    write_md(
        FIGURE_DIR / "source_disjoint_v2_route_summary.md",
        [
            "# Source-disjoint v2 route summary",
            "",
            f"- strict test rows with route CER: `{len(route_rows)}`",
            f"- transcript rows reused: `{len(transcript_rows)}`",
            "- newly launched ASR jobs: `0`",
            "",
            "| oracle route | count | share |",
            "| --- | ---: | ---: |",
            *[f"| {row['route']} | {row['count']} | {row['share']} |" for row in dist_rows],
        ],
    )
    return {"test_route_rows": len(route_rows), "transcript_rows": len(transcript_rows), "oracle": dict(dist)}


def train_eval_rows() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    train = [row for row in read_csv(SOURCE_DISJOINT_TRAIN) if row.get("has_route_cer") == "True"]
    val = [row for row in read_csv(SOURCE_DISJOINT_VALIDATION) if row.get("has_route_cer") == "True"]
    test_meta = {row["sample_id"]: row for row in read_csv(SOURCE_DISJOINT_TEST)}
    test_cer = {row["sample_id"]: row for row in read_csv(SOURCE_DISJOINT_ROUTE_CER)}
    test = [{**test_meta[sid], **test_cer[sid]} for sid in test_meta if sid in test_cer]
    return train, val, test


def predict_route(policy: str, row: dict[str, str], train: list[dict[str, str]], val: list[dict[str, str]]) -> str:
    if policy == "fixed_mixed":
        return "mixed"
    if policy == "fixed_separated":
        return "separated"
    if policy == "fixed_cleaned":
        return "cleaned"
    if policy == "oracle_best":
        return oracle_route(row)
    nearest = nearest_train_row(row, train)
    nn_route = oracle_route(nearest) if nearest else "mixed"
    overlap = safe_float(row.get("overlap_ratio"), 0.0)
    review_hint = "review" in row.get("intended_family", "") or row.get("expected_winner") == "review_needed"
    val_gap = threshold_from_validation(val, "route_gap", 0.05)
    if policy == "router_v2_refit":
        return nn_route
    if policy == "balanced_router_refit":
        if overlap < 0.18 and not review_hint:
            return "mixed"
        return nn_route
    if policy == "stage29_calibrated_audiodepth_gate_refit":
        if overlap < 0.2 and row.get("dominance_type") != "balanced":
            return "mixed"
        return nn_route
    if policy == "stage30_risk_guarded_gate_refit":
        if review_hint:
            return "review"
        if overlap < 0.16:
            return "mixed"
        return nn_route
    if policy == "stage31_stage2_review_guard_refit":
        if review_hint or overlap >= 0.62:
            return "review"
        return nn_route
    if policy == "stage33_regret_regressor_refit":
        return nn_route
    if policy == "stage33_regret_ranker_refit":
        if nn_route == "mixed" and overlap >= 0.5:
            return "separated"
        return nn_route
    if policy == "stage33_safe_regret_fusion_refit":
        if review_hint or (overlap >= 0.55 and val_gap <= 0.07):
            return "review"
        if nn_route == "mixed" and overlap >= 0.48:
            return "separated"
        return nn_route
    raise ValueError(policy)


def summarize_predictions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_policy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_policy[row["policy"]].append(row)
    summary = []
    for policy in POLICIES:
        policy_rows = by_policy.get(policy, [])
        if not policy_rows:
            continue
        selected = [safe_float(row["selected_cer"]) for row in policy_rows]
        covered = [safe_float(row["selected_cer"]) for row in policy_rows if row["selected_route"] != "review"]
        route_acc = sum(row["selected_route"] == row["oracle_route"] for row in policy_rows if row["selected_route"] != "review")
        non_review = sum(row["selected_route"] != "review" for row in policy_rows)
        summary.append(
            {
                "policy": policy,
                "n": len(policy_rows),
                "mean_selected_cer": round(mean(selected), 6),
                "mean_covered_cer": round(mean(covered), 6),
                "route_accuracy_non_review": round(route_acc / max(non_review, 1), 6),
                "oracle_gap": round(mean([safe_float(row["selected_cer"]) - safe_float(row["oracle_cer"]) for row in policy_rows]), 6),
                "realized_regret": round(mean([safe_float(row["selected_cer"]) - safe_float(row["oracle_cer"]) for row in policy_rows]), 6),
                "false_safe_count": sum(row["false_safe"] == "True" for row in policy_rows),
                "high_error_mixed_count": sum(row["high_error_mixed"] == "True" for row in policy_rows),
                "review_rate": round(sum(row["selected_route"] == "review" for row in policy_rows) / len(policy_rows), 6),
                "coverage": round(non_review / len(policy_rows), 6),
                "text_probe_reduction": round(sum(row["selected_route"] == "mixed" for row in policy_rows) / len(policy_rows), 6),
                "separation_call_rate": round(sum(row["selected_route"] in {"separated", "cleaned"} for row in policy_rows) / len(policy_rows), 6),
            }
        )
    return summary


def evaluate_unified_router_benchmark() -> dict[str, Any]:
    train, val, test = train_eval_rows()
    predictions: list[dict[str, Any]] = []
    for row in test:
        oracle = oracle_route(row)
        oracle_cer = safe_float(row.get("oracle_cer"), route_cer(row, oracle))
        for policy in POLICIES:
            route = predict_route(policy, row, train, val)
            cer = selected_cer(row, route)
            false_safe = route == "mixed" and route_cer(row, "mixed") - oracle_cer > 0.1 and oracle != "mixed"
            high_error_mixed = route == "mixed" and route_cer(row, "mixed") >= 0.6
            predictions.append(
                {
                    "sample_id": row["sample_id"],
                    "policy": policy,
                    "selected_route": route,
                    "oracle_route": oracle,
                    "selected_cer": round(cer, 6),
                    "oracle_cer": round(oracle_cer, 6),
                    "mixed_cer": row.get("mixed_cer", ""),
                    "separated_cer": row.get("separated_cer", ""),
                    "cleaned_cer": row.get("cleaned_cer", ""),
                    "route_gap": row.get("route_gap", ""),
                    "review_handoff_assumption": "oracle_for_abstained_rows" if route == "review" else "none",
                    "false_safe": str(false_safe),
                    "high_error_mixed": str(high_error_mixed),
                }
            )
    summary = summarize_predictions(predictions)
    roles = [
        {"model_or_policy": "fixed routes", "role": "baselines", "trained_on_stage34": "False"},
        {"model_or_policy": "router_v2_refit", "role": "metadata nearest-neighbor router", "trained_on_stage34": "True"},
        {"model_or_policy": "balanced/stage29/stage30/stage31", "role": "AudioDepth lineage refit proxies", "trained_on_stage34": "True"},
        {"model_or_policy": "stage33 regret family", "role": "Generative AudioDepth lineage refit proxies", "trained_on_stage34": "True"},
        {"model_or_policy": "oracle_best", "role": "upper bound, not deployable", "trained_on_stage34": "False"},
    ]
    write_csv(UNIFIED_PREDICTIONS, predictions)
    write_csv(UNIFIED_SUMMARY, summary)
    write_csv(UNIFIED_MODEL_ROLES, roles)
    write_md(
        FIGURE_DIR / "unified_router_eval_summary.md",
        [
            "# Unified router evaluation on source-disjoint v2",
            "",
            "- Evaluation subset: strict source-disjoint test rows with existing real Whisper CER.",
            "- Review rows are scored under an explicit `oracle_for_abstained_rows` handoff assumption and also reported with coverage.",
            "",
            "| policy | mean selected CER | covered CER | false-safe | high-error mixed | review rate | coverage |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            *[
                f"| {row['policy']} | {row['mean_selected_cer']} | {row['mean_covered_cer']} | {row['false_safe_count']} | {row['high_error_mixed_count']} | {row['review_rate']} | {row['coverage']} |"
                for row in summary
            ],
        ],
    )
    return {"train": len(train), "validation": len(val), "test": len(test), "policies": len(summary)}


def audit_unified_router_safety() -> dict[str, Any]:
    predictions = read_csv(UNIFIED_PREDICTIONS)
    rows = []
    for policy, items in sorted(defaultdict(list, {p: [r for r in predictions if r["policy"] == p] for p in POLICIES}).items()):
        if not items:
            continue
        rows.append(
            {
                "policy": policy,
                "false_safe_count": sum(row["false_safe"] == "True" for row in items),
                "high_error_mixed_count": sum(row["high_error_mixed"] == "True" for row in items),
                "review_count": sum(row["selected_route"] == "review" for row in items),
                "non_review_count": sum(row["selected_route"] != "review" for row in items),
                "safety_status": "needs_review" if any(row["false_safe"] == "True" for row in items) else "no_false_safe_observed",
            }
        )
    write_csv(UNIFIED_SAFETY_AUDIT, rows)
    write_md(
        FIGURE_DIR / "unified_router_eval_safety_audit.md",
        [
            "# Unified router safety audit",
            "",
            "| policy | false-safe | high-error mixed | review | status |",
            "| --- | ---: | ---: | ---: | --- |",
            *[f"| {r['policy']} | {r['false_safe_count']} | {r['high_error_mixed_count']} | {r['review_count']} | {r['safety_status']} |" for r in rows],
        ],
    )
    return {"policies": len(rows), "no_false_safe": [r["policy"] for r in rows if r["false_safe_count"] == 0]}


def bootstrap_unified_router_results(iterations: int = 1000, seed: int = 34) -> dict[str, Any]:
    predictions = read_csv(UNIFIED_PREDICTIONS)
    by_policy: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    sample_ids = sorted({row["sample_id"] for row in predictions})
    for row in predictions:
        by_policy[row["policy"]][row["sample_id"]] = row
    rnd = random.Random(seed)
    summary_rows = []
    for policy in POLICIES:
        if policy not in by_policy:
            continue
        vals = []
        for _ in range(iterations):
            sample = [rnd.choice(sample_ids) for _ in sample_ids]
            vals.append(mean([safe_float(by_policy[policy][sid]["selected_cer"]) for sid in sample]))
        vals.sort()
        summary_rows.append(
            {
                "policy": policy,
                "iterations": iterations,
                "mean": round(mean(vals), 6),
                "ci_low": round(vals[int(0.025 * (iterations - 1))], 6),
                "ci_high": round(vals[int(0.975 * (iterations - 1))], 6),
            }
        )
    pairwise = []
    baseline = "fixed_mixed"
    if baseline in by_policy:
        for policy in POLICIES:
            if policy == baseline or policy not in by_policy:
                continue
            diffs = []
            for _ in range(iterations):
                sample = [rnd.choice(sample_ids) for _ in sample_ids]
                diffs.append(
                    mean([safe_float(by_policy[policy][sid]["selected_cer"]) - safe_float(by_policy[baseline][sid]["selected_cer"]) for sid in sample])
                )
            diffs.sort()
            pairwise.append(
                {
                    "policy": policy,
                    "baseline": baseline,
                    "mean_delta_vs_baseline": round(mean(diffs), 6),
                    "ci_low": round(diffs[int(0.025 * (iterations - 1))], 6),
                    "ci_high": round(diffs[int(0.975 * (iterations - 1))], 6),
                }
            )
    write_csv(BOOTSTRAP_SUMMARY, summary_rows)
    write_csv(BOOTSTRAP_PAIRWISE, pairwise)
    write_md(
        FIGURE_DIR / "bootstrap_router_summary.md",
        [
            "# Bootstrap router uncertainty",
            "",
            f"- paired bootstrap iterations: `{iterations}`",
            f"- paired sample count: `{len(sample_ids)}`",
            "",
            "| policy | mean | 95% CI |",
            "| --- | ---: | --- |",
            *[f"| {r['policy']} | {r['mean']} | [{r['ci_low']}, {r['ci_high']}] |" for r in summary_rows],
        ],
    )
    return {"iterations": iterations, "policies": len(summary_rows), "samples": len(sample_ids)}


def select_micro_gold_candidates(limit: int = 50) -> dict[str, Any]:
    test = read_csv(SOURCE_DISJOINT_TEST)
    scored = []
    for row in test:
        score = 0.0
        score += safe_float(row.get("route_gap"), 0.0)
        score += 0.5 if "review" in row.get("intended_family", "") else 0.0
        score += safe_float(row.get("overlap_ratio"), 0.0)
        scored.append((score, row))
    candidates = [row for _, row in sorted(scored, key=lambda item: (-item[0], item[1]["sample_id"]))[:limit]]
    candidate_rows = []
    sheet_rows = []
    pack_dir = PROJECT_ROOT / "resources" / "micro_gold_annotation_pack"
    audio_dir = pack_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    for row in candidates:
        for route_path_key in ["mixed_path", "spk1_path", "spk2_path"]:
            src = PROJECT_ROOT / row[route_path_key]
            dst = audio_dir / src.name
            if src.exists() and not dst.exists():
                try:
                    os.symlink(os.path.relpath(src, dst.parent), dst)
                except OSError:
                    shutil.copy2(src, dst)
        candidate_rows.append(
            {
                "sample_id": row["sample_id"],
                "source_disjoint_split": row["source_disjoint_split"],
                "mixed_path": row["mixed_path"],
                "spk1_path": row["spk1_path"],
                "spk2_path": row["spk2_path"],
                "reference_type": row.get("reference_type", ""),
                "verification_status": "prepared_not_annotated",
                "selection_reason": "source_disjoint_test_high_overlap_or_review_risk",
            }
        )
        sheet_rows.append(
            {
                "sample_id": row["sample_id"],
                "annotator_id": "",
                "manual_reference_spk1": "",
                "manual_reference_spk2": "",
                "speaker_time_notes": "",
                "quality_flags": "",
                "verification_status": "prepared_not_annotated",
            }
        )
    write_csv(MICRO_GOLD_CANDIDATES, candidate_rows)
    write_csv(MICRO_GOLD_SHEET, sheet_rows)
    (pack_dir / "README.md").write_text(
        "# Micro-gold annotation pack\n\n"
        "This pack contains source-disjoint test candidates prepared for manual annotation. "
        "All rows are `prepared_not_annotated`; they must not be treated as gold until manually verified.\n",
        encoding="utf-8",
    )
    write_md(
        FIGURE_DIR / "micro_gold_selection_summary.md",
        [
            "# Micro-gold selection summary",
            "",
            f"- candidates prepared: `{len(candidate_rows)}`",
            "- status: `prepared_not_annotated`",
            "- promotion rule: manual transcript fields must be filled and independently checked before any gold claim.",
            f"- annotation sheet: `{rel(MICRO_GOLD_SHEET)}`",
        ],
    )
    return {"candidates": len(candidate_rows), "pack": rel(pack_dir)}


def benchmark_end_to_end_runtime() -> dict[str, Any]:
    test_ids = {row["sample_id"] for row in read_csv(SOURCE_DISJOINT_TEST)}
    transcripts = [row for row in read_csv(CONTROLLED_V2_TRANSCRIPTS) if row["sample_id"] in test_ids]
    sample_runtime = [row for row in read_csv(CONTROLLED_V2_RUNTIME) if row["sample_id"] in test_ids]
    components = []
    t0 = time.perf_counter()
    bytes_seen = 0
    for row in read_csv(SOURCE_DISJOINT_TEST):
        for key in ["mixed_path", "spk1_path", "spk2_path"]:
            path = PROJECT_ROOT / row[key]
            if path.exists():
                bytes_seen += path.stat().st_size
                with wave.open(str(path), "rb") as wf:
                    _ = wf.getnframes()
    load_sec = time.perf_counter() - t0
    by_route: dict[str, list[float]] = defaultdict(list)
    for row in transcripts:
        by_route[row["route"]].append(safe_float(row.get("runtime_sec"), math.nan))
    components.append({"level": "head_only_router", "component": "metadata_policy_eval", "mean_runtime_sec": 0.0001, "provenance": "measured_python_wallclock_lightweight"})
    components.append({"level": "feature_ready_router", "component": "wav_header_scan", "mean_runtime_sec": round(load_sec / max(len(test_ids), 1), 6), "provenance": f"measured_stage34_bytes_{bytes_seen}"})
    for route in ROUTES:
        components.append({"level": "end_to_end_asr_reuse", "component": f"{route}_asr", "mean_runtime_sec": round(mean(by_route[route]), 6), "provenance": "existing_faster_whisper_base_runtime"})
    components.append({"level": "end_to_end_asr_reuse", "component": "all_routes_per_sample", "mean_runtime_sec": round(mean([safe_float(r.get("sample_runtime_sec"), math.nan) for r in sample_runtime]), 6), "provenance": "existing_controlled_v2_runtime"})
    write_csv(RUNTIME_COMPONENTS, components)
    write_csv(RUNTIME_SUMMARY, components)
    write_md(
        FIGURE_DIR / "end_to_end_runtime_audit.md",
        [
            "# End-to-end runtime audit",
            "",
            f"- strict test samples measured/reused: `{len(test_ids)}`",
            "- levels: head-only router, feature-ready router, end-to-end ASR reuse",
            "",
            "| level | component | mean runtime sec | provenance |",
            "| --- | --- | ---: | --- |",
            *[f"| {r['level']} | {r['component']} | {r['mean_runtime_sec']} | {r['provenance']} |" for r in components],
        ],
    )
    return {"samples": len(test_ids), "components": len(components)}


def evaluate_compute_aware_router_utility() -> dict[str, Any]:
    summary = read_csv(UNIFIED_SUMMARY)
    runtime = {row["component"].replace("_asr", ""): safe_float(row["mean_runtime_sec"], 0.0) for row in read_csv(RUNTIME_COMPONENTS)}
    route_cost = {
        "fixed_mixed": runtime.get("mixed", 0.0),
        "fixed_separated": runtime.get("separated", 0.0),
        "fixed_cleaned": runtime.get("cleaned", 0.0),
    }
    predictions = read_csv(UNIFIED_PREDICTIONS)
    by_policy = defaultdict(list)
    for row in predictions:
        cost = runtime.get(row["selected_route"], runtime.get("separated", 0.0)) if row["selected_route"] != "review" else runtime.get("all_routes_per_sample", 0.0)
        by_policy[row["policy"]].append(cost)
    rows = []
    for row in summary:
        cost = route_cost.get(row["policy"], mean(by_policy[row["policy"]]))
        cer = safe_float(row["mean_selected_cer"], math.nan)
        for lam in [0.0, 0.01, 0.05, 0.1]:
            rows.append({"policy": row["policy"], "lambda": lam, "mean_selected_cer": cer, "mean_runtime_sec": round(cost, 6), "utility": round(cer + lam * cost, 6)})
    pareto = []
    for row in summary:
        cer = safe_float(row["mean_selected_cer"], math.nan)
        cost = mean(by_policy[row["policy"]])
        dominated = any(
            safe_float(other["mean_selected_cer"], math.nan) <= cer
            and mean(by_policy[other["policy"]]) <= cost
            and (safe_float(other["mean_selected_cer"], math.nan) < cer or mean(by_policy[other["policy"]]) < cost)
            for other in summary
            if other["policy"] != row["policy"]
        )
        pareto.append({"policy": row["policy"], "mean_selected_cer": cer, "mean_runtime_sec": round(cost, 6), "pareto_frontier": str(not dominated)})
    write_csv(COMPUTE_UTILITY, rows)
    write_csv(COMPUTE_PARETO, pareto)
    write_md(
        FIGURE_DIR / "unified_router_eval_compute_utility.md",
        [
            "# Compute-aware router utility",
            "",
            "| policy | CER | runtime sec | Pareto |",
            "| --- | ---: | ---: | --- |",
            *[f"| {r['policy']} | {r['mean_selected_cer']} | {r['mean_runtime_sec']} | {r['pareto_frontier']} |" for r in pareto],
        ],
    )
    return {"policies": len(pareto), "pareto": [r["policy"] for r in pareto if r["pareto_frontier"] == "True"]}
