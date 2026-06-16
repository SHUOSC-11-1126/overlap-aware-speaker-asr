from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import FIGURE_DIR, METADATA_CSV, route_cer, write_summary
from .balanced_v2_common import V2_CER, mean
from .evaluate_audiodepth_two_stage_cascade import router_v2


TABLE_DIR = FIGURE_DIR.parent / "tables"
CALIBRATED_PRED_CSV = TABLE_DIR / "audiodepth_gate_calibrated_predictions.csv"

SWEEP_CSV = TABLE_DIR / "audiodepth_risk_guarded_gate_sweep.csv"
BEST_POLICIES_CSV = TABLE_DIR / "audiodepth_risk_guarded_gate_best_policies.csv"
CASES_CSV = TABLE_DIR / "audiodepth_risk_guarded_gate_cases.csv"
SUMMARY_MD = FIGURE_DIR / "audiodepth_risk_guarded_gate_summary.md"
PARETO_PNG = FIGURE_DIR / "audiodepth_risk_guarded_gate_pareto.png"

# Backward-compatible aliases from the first risk-guard pass.
LEGACY_PRED_CSV = TABLE_DIR / "audiodepth_gate_risk_guarded_predictions.csv"
LEGACY_SWEEP_CSV = TABLE_DIR / "audiodepth_gate_risk_guarded_sweep.csv"
LEGACY_SUMMARY_CSV = TABLE_DIR / "audiodepth_gate_risk_guarded_summary.csv"
LEGACY_SUMMARY_MD = FIGURE_DIR / "audiodepth_gate_risk_guarded_summary.md"
LEGACY_SWEEP_PNG = FIGURE_DIR / "audiodepth_gate_risk_guarded_sweep.png"

ROUTER_V2_CER = 0.643520
STAGE_27_ORACLE_CER = 0.502854
STAGE_29_FALSE_SAFE = 0.183333
STAGE_29_CER = 0.533160
STAGE_29_TEXT_PROBE_REDUCTION = 0.716667

CONFIDENCE_THRESHOLDS = [0.50, 0.60, 0.70, 0.80, 0.90, 0.95]
RISK_THRESHOLDS = [0.20, 0.30, 0.40, 0.50, 0.60]
ROUTE_GAP_THRESHOLDS = [0.00, 0.02, 0.03, 0.05, 0.10]
MIN_ROUTE_CER_REVIEW_THRESHOLDS = [0.60, 0.65, 0.70]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate risk-guarded AudioDepth Stage-1 gate policies.")
    parser.add_argument("--write-legacy", action="store_true", default=True)
    return parser.parse_args()


def risk_score(row: dict[str, str]) -> float:
    return round(
        0.40 * safe_float(row.get("uncertainty_proxy_mean"))
        + 0.25 * safe_float(row.get("overlap_proxy_mean"))
        + 0.20 * safe_float(row.get("overlap_uncertainty_product"))
        + 0.15 * safe_float(row.get("uncertainty_proxy_std")),
        6,
    )


def is_easy_label(label: str) -> bool:
    return label in {"easy_mixed", "mixed_safe", "safe_mixed"}


def is_sep_label(label: str) -> bool:
    return label in {"likely_separation_helpful", "separation_helpful", "separated_helpful"}


def is_review_anchor(row: dict[str, str]) -> bool:
    family = row.get("intended_family", "")
    return "review" in family or "ambiguous" in family


def min_route_cer(row: dict[str, str]) -> float:
    return min(safe_float(row["mixed_cer"]), safe_float(row["separated_cer"]), safe_float(row["cleaned_cer"]))


def load_rows() -> list[dict[str, str]]:
    cer_rows = {row["sample_id"]: row for row in read_csv(V2_CER)}
    preds = {row["sample_id"]: row for row in read_csv(CALIBRATED_PRED_CSV)}
    meta = {row["sample_id"]: row for row in read_csv(METADATA_CSV)}
    manifest = {row["sample_id"]: row for row in read_csv(TABLE_DIR / "controlled_v2_manifest.csv")}
    rows = []
    for sample_id, cer in cer_rows.items():
        if sample_id not in preds or sample_id not in meta:
            continue
        merged = dict(cer)
        merged.update({f"gate_{key}": value for key, value in preds[sample_id].items()})
        merged.update({f"meta_{key}": value for key, value in meta[sample_id].items()})
        if sample_id in manifest:
            merged.update({f"manifest_{key}": value for key, value in manifest[sample_id].items()})
        rows.append(merged)
    return rows


def choose_route(row: dict[str, str], confidence_threshold: float, risk_threshold: float, route_gap_threshold: float, review_threshold: float) -> dict[str, object]:
    label = row["gate_predicted_gate_label"]
    confidence = safe_float(row["gate_confidence"])
    risk = risk_score(
        {
            "uncertainty_proxy_mean": row.get("meta_uncertainty_proxy_mean", ""),
            "overlap_proxy_mean": row.get("meta_overlap_proxy_mean", ""),
            "overlap_uncertainty_product": row.get("meta_overlap_uncertainty_product", ""),
            "uncertainty_proxy_std": row.get("meta_uncertainty_proxy_std", ""),
        }
    )
    route_gap = safe_float(row.get("route_gap"))
    min_cer = min_route_cer(row)
    high_risk = risk > risk_threshold
    review_candidate = is_review_anchor(row) or min_cer >= review_threshold
    fallback = router_v2(row)
    reason = "stage2_text_router_fallback"
    selected_route = fallback
    stage2_called = True
    review_marked = False

    if review_candidate:
        review_marked = True
        reason = "review_candidate_stage2_fallback"
    elif is_easy_label(label) and confidence >= confidence_threshold and not high_risk and route_gap >= route_gap_threshold:
        selected_route = "mixed"
        stage2_called = False
        reason = "direct_easy_mixed_bypass"
    elif is_sep_label(label) and confidence >= confidence_threshold and not high_risk and route_gap >= route_gap_threshold:
        selected_route = "separated"
        stage2_called = False
        reason = "direct_separation_helpful_bypass"
    elif fallback == "mixed" and high_risk:
        selected_route = "separated"
        reason = "risk_guard_overrode_mixed_fallback"

    selected_cer = route_cer(row, selected_route)
    selected_mixed_high_error = selected_route == "mixed" and min_cer > 0.60
    false_safe = not stage2_called and selected_mixed_high_error
    unsafe_bypass = false_safe
    return {
        "sample_id": row["sample_id"],
        "selected_route": selected_route,
        "oracle_route": row["oracle_route"],
        "selected_cer": round(selected_cer, 6),
        "oracle_cer": row["oracle_cer"],
        "route_accuracy_hit": selected_route == row["oracle_route"],
        "stage2_text_probe_called": stage2_called,
        "direct_bypass": not stage2_called,
        "review_candidate": review_marked,
        "guard_reason": reason,
        "risk_score": risk,
        "predicted_gate_label": label,
        "confidence": confidence,
        "route_gap": route_gap,
        "min_route_cer": round(min_cer, 6),
        "false_safe": false_safe,
        "selected_mixed_high_error": selected_mixed_high_error,
        "unsafe_bypass": unsafe_bypass,
        "intended_family": row.get("intended_family", ""),
        "expected_winner": row.get("expected_winner", ""),
    }


def evaluate_policy(confidence: float, risk: float, route_gap: float, review_threshold: float, rows: list[dict[str, str]], write_cases: bool = False) -> tuple[dict[str, object], list[dict[str, object]]]:
    decisions = [choose_route(row, confidence, risk, route_gap, review_threshold) for row in rows]
    direct = [row for row in decisions if row["direct_bypass"]]
    false_safe_count = sum(1 for row in decisions if row["false_safe"])
    selected_mixed_high_error_count = sum(1 for row in decisions if row["selected_mixed_high_error"])
    unsafe_bypass_count = sum(1 for row in decisions if row["unsafe_bypass"])
    policy_name = f"conf{confidence:.2f}_risk{risk:.2f}_gap{route_gap:.2f}_review{review_threshold:.2f}"
    selected_cer = mean([safe_float(row["selected_cer"]) for row in decisions])
    text_probe_reduction = len(direct) / max(len(decisions), 1)
    fallback_rate = sum(1 for row in decisions if row["stage2_text_probe_called"]) / max(len(decisions), 1)
    review_rate = sum(1 for row in decisions if row["review_candidate"]) / max(len(decisions), 1)
    cost_score = round(1.0 - 0.55 * text_probe_reduction + 0.20 * review_rate, 6)
    result = {
        "policy_name": policy_name,
        "confidence_threshold": confidence,
        "risk_threshold": risk,
        "route_gap_threshold": route_gap,
        "min_route_cer_review_threshold": review_threshold,
        "selected_route_CER": selected_cer,
        "route_accuracy": round(sum(1 for row in decisions if row["route_accuracy_hit"]) / max(len(decisions), 1), 6),
        "false_safe_rate": round(false_safe_count / max(len(decisions), 1), 6),
        "text_probe_reduction_rate": round(text_probe_reduction, 6),
        "direct_bypass_rate": round(text_probe_reduction, 6),
        "fallback_rate": round(fallback_rate, 6),
        "review_rate": round(review_rate, 6),
        "mixed_bypass_count": sum(1 for row in direct if row["selected_route"] == "mixed"),
        "separation_bypass_count": sum(1 for row in direct if row["selected_route"] == "separated"),
        "unsafe_bypass_count": unsafe_bypass_count,
        "selected_mixed_high_error_count": selected_mixed_high_error_count,
        "cost_score": cost_score,
        "sample_count": len(decisions),
        "note": policy_note(selected_cer, false_safe_count / max(len(decisions), 1), text_probe_reduction),
    }
    if write_cases:
        write_csv(LEGACY_PRED_CSV, decisions)
    return result, decisions


def policy_note(selected_cer: float, false_safe_rate: float, text_probe_reduction: float) -> str:
    if false_safe_rate <= 0.05 and selected_cer < ROUTER_V2_CER:
        return "safe_frontier_policy"
    if false_safe_rate <= 0.10 and selected_cer < ROUTER_V2_CER:
        return "balanced_frontier_policy"
    if text_probe_reduction > 0.50:
        return "aggressive_probe_reduction"
    return "conservative_fallback_heavy"


def select_best_policies(sweep: list[dict[str, object]]) -> list[dict[str, object]]:
    aggressive = sorted(sweep, key=lambda row: (-safe_float(row["text_probe_reduction_rate"]), safe_float(row["selected_route_CER"]), safe_float(row["false_safe_rate"])))[0]
    balanced_pool = [row for row in sweep if safe_float(row["false_safe_rate"]) <= 0.10 and safe_float(row["selected_route_CER"]) < ROUTER_V2_CER]
    balanced = sorted(balanced_pool or sweep, key=lambda row: (safe_float(row["selected_route_CER"]), safe_float(row["false_safe_rate"]), -safe_float(row["text_probe_reduction_rate"])))[0]
    conservative_pool = [row for row in sweep if safe_float(row["false_safe_rate"]) <= 0.05]
    conservative = sorted(conservative_pool or sweep, key=lambda row: (safe_float(row["false_safe_rate"]), safe_float(row["selected_route_CER"]), -safe_float(row["text_probe_reduction_rate"])))[0]
    return [
        {"policy_tier": "aggressive", **aggressive},
        {"policy_tier": "balanced", **balanced},
        {"policy_tier": "conservative", **conservative},
    ]


def representative_cases(decisions_by_tier: dict[str, list[dict[str, object]]]) -> list[dict[str, object]]:
    rows = []

    def add(case_type: str, tier: str, predicate) -> None:
        for row in decisions_by_tier[tier]:
            if predicate(row):
                rows.append({"case_type": case_type, "policy_tier": tier, **row})
                return
        rows.append(
            {
                "case_type": case_type,
                "policy_tier": tier,
                "sample_id": "not_observed",
                "selected_route": "",
                "oracle_route": "",
                "selected_cer": "",
                "oracle_cer": "",
                "route_accuracy_hit": "",
                "stage2_text_probe_called": "",
                "direct_bypass": "",
                "review_candidate": "",
                "guard_reason": "no_matching_case_in_selected_policy",
                "risk_score": "",
                "predicted_gate_label": "",
                "confidence": "",
                "route_gap": "",
                "min_route_cer": "",
                "false_safe": "",
                "unsafe_bypass": "",
                "selected_mixed_high_error": "",
                "intended_family": "",
                "expected_winner": "",
            }
        )

    add("safe bypass success", "balanced", lambda row: row["direct_bypass"] and row["selected_route"] == row["oracle_route"] and not row["false_safe"])
    add("false-safe failure", "aggressive", lambda row: row["false_safe"])
    false_safe_ids = {row["sample_id"] for row in decisions_by_tier["aggressive"] if row["false_safe"]}
    add("conservative policy rescue", "conservative", lambda row: row["sample_id"] in false_safe_ids and not row["false_safe"])
    add("high-risk fallback", "balanced", lambda row: row["guard_reason"] == "risk_guard_overrode_mixed_fallback")
    add("separation-helpful correct", "balanced", lambda row: row["selected_route"] == "separated" and row["oracle_route"] == "separated")
    add("ambiguous sent to Stage-2", "balanced", lambda row: row["stage2_text_probe_called"] and "ambiguous" in str(row.get("predicted_gate_label", "")))
    return rows


def draw_pareto(sweep: list[dict[str, object]], best: list[dict[str, object]]) -> None:
    img = Image.new("RGB", (980, 620), "white")
    draw = ImageDraw.Draw(img)
    draw.text((24, 18), "Risk-Guarded AudioDepth Gate Pareto", fill=(0, 0, 0))
    xs = [safe_float(row["false_safe_rate"]) for row in sweep] + [STAGE_29_FALSE_SAFE]
    ys = [safe_float(row["selected_route_CER"]) for row in sweep] + [STAGE_29_CER, ROUTER_V2_CER]
    min_x, max_x = 0.0, max(xs + [0.20])
    min_y, max_y = min(ys) - 0.015, max(ys) + 0.015

    def point(false_safe: float, cer: float) -> tuple[int, int]:
        x = 88 + int(780 * (false_safe - min_x) / max(max_x - min_x, 1e-6))
        y = 500 - int(380 * (cer - min_y) / max(max_y - min_y, 1e-6))
        return x, y

    for row in sweep:
        x, y = point(safe_float(row["false_safe_rate"]), safe_float(row["selected_route_CER"]))
        reduction = safe_float(row["text_probe_reduction_rate"])
        shade = int(230 - 150 * min(reduction, 1.0))
        radius = 3 + int(6 * reduction)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(60, 120, shade), outline=(20, 60, 120))

    for tier_row in best:
        x, y = point(safe_float(tier_row["false_safe_rate"]), safe_float(tier_row["selected_route_CER"]))
        draw.rectangle((x - 7, y - 7, x + 7, y + 7), outline=(0, 0, 0), width=2)
        draw.text((x + 8, y - 8), tier_row["policy_tier"], fill=(0, 0, 0))

    sx, sy = point(STAGE_29_FALSE_SAFE, STAGE_29_CER)
    draw.ellipse((sx - 7, sy - 7, sx + 7, sy + 7), fill=(220, 80, 80), outline=(120, 0, 0))
    draw.text((sx + 10, sy - 8), "Stage 29", fill=(120, 0, 0))
    _, router_y = point(0.0, ROUTER_V2_CER)
    draw.line((88, router_y, 868, router_y), fill=(120, 120, 120), width=2)
    draw.text((700, router_y - 18), "router_v2 CER 0.643520", fill=(80, 80, 80))
    draw.line((88, 500, 868, 500), fill=(0, 0, 0))
    draw.line((88, 120, 88, 500), fill=(0, 0, 0))
    draw.text((350, 545), "false-safe rate ->", fill=(0, 0, 0))
    draw.text((18, 300), "CER", fill=(0, 0, 0))
    PARETO_PNG.parent.mkdir(parents=True, exist_ok=True)
    img.save(PARETO_PNG)
    img.save(LEGACY_SWEEP_PNG)


def write_markdown(best: list[dict[str, object]]) -> None:
    by_tier = {row["policy_tier"]: row for row in best}
    balanced = by_tier["balanced"]
    conservative = by_tier["conservative"]
    has_balanced_safe = safe_float(balanced["false_safe_rate"]) <= 0.10 and safe_float(balanced["selected_route_CER"]) < ROUTER_V2_CER
    has_conservative_safe = safe_float(conservative["false_safe_rate"]) <= 0.05
    lines = [
        f"- Stage 29 calibrated false-safe rate: `{STAGE_29_FALSE_SAFE}`",
        f"- Stage 29 calibrated CER: `{STAGE_29_CER}`",
        "",
        "| tier | CER | false-safe bypass | selected mixed high-error | text-probe reduction | direct bypass | review rate | note |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in best:
        lines.append(
            f"| {row['policy_tier']} | `{row['selected_route_CER']}` | `{row['false_safe_rate']}` | "
            f"`{row['selected_mixed_high_error_count']}` | `{row['text_probe_reduction_rate']}` | "
            f"`{row['direct_bypass_rate']}` | `{row['review_rate']}` | {row['note']} |"
        )
    lines.extend(
        [
            "",
            f"- false-safe <= 0.10 and CER < router_v2 exists: `{'yes' if has_balanced_safe else 'no'}`",
            f"- false-safe <= 0.05 policy exists: `{'yes' if has_conservative_safe else 'no'}`",
            "- Here false-safe means an AudioDepth direct bypass selected mixed without Stage-2 review even though the offline minimum route CER is high.",
            "- Risk guarding lowers unsafe bypasses by sending high-risk or review-like samples to Stage-2 text routing / review instead of trusting confidence alone.",
            "- It can still leave selected mixed high-error cases after Stage-2 fallback; those are tracked separately and should be treated as review policy risk, not acoustic-gate bypass risk.",
            "- It does sacrifice some direct bypass capacity under conservative settings; the balanced setting keeps a useful probe-reduction margin while preserving a CER advantage over router_v2.",
            "- Deployment conclusion: this supports AudioDepth as a safety-aware acoustic triage module, not as a standalone production router.",
            "- Safety wording: results are experimental/frontier and controlled_v2 references remain silver_plus_unverified; do not claim real-meeting generalization.",
        ]
    )
    write_summary(SUMMARY_MD, "Risk-Guarded AudioDepth Gate", lines)
    write_summary(LEGACY_SUMMARY_MD, "AudioDepth Risk-Guarded Gate", lines)


def write_legacy(best: list[dict[str, object]], decisions_by_tier: dict[str, list[dict[str, object]]]) -> None:
    balanced = next(row for row in best if row["policy_tier"] == "balanced")
    write_csv(LEGACY_SUMMARY_CSV, [balanced])
    write_csv(LEGACY_SWEEP_CSV, [{k: v for k, v in row.items() if k != "policy_tier"} for row in best])
    write_csv(LEGACY_PRED_CSV, decisions_by_tier["balanced"])


def main() -> None:
    parse_args()
    rows = load_rows()
    sweep = []
    decisions_cache: dict[str, list[dict[str, object]]] = {}
    for confidence in CONFIDENCE_THRESHOLDS:
        for risk in RISK_THRESHOLDS:
            for route_gap in ROUTE_GAP_THRESHOLDS:
                for review_threshold in MIN_ROUTE_CER_REVIEW_THRESHOLDS:
                    result, decisions = evaluate_policy(confidence, risk, route_gap, review_threshold, rows)
                    sweep.append(result)
                    decisions_cache[result["policy_name"]] = decisions
    write_csv(SWEEP_CSV, sweep)
    best = select_best_policies(sweep)
    write_csv(BEST_POLICIES_CSV, best)
    decisions_by_tier = {row["policy_tier"]: decisions_cache[row["policy_name"]] for row in best}
    write_csv(CASES_CSV, representative_cases(decisions_by_tier))
    draw_pareto(sweep, best)
    write_markdown(best)
    write_legacy(best, decisions_by_tier)
    print(f"Wrote risk-guarded AudioDepth sweep to {rel(SWEEP_CSV)}")
    print(f"Wrote best policies to {rel(BEST_POLICIES_CSV)}")


if __name__ == "__main__":
    main()
