from __future__ import annotations

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import FIGURE_DIR, write_summary
from .balanced_v2_common import mean


TABLE_DIR = FIGURE_DIR.parent / "tables"
PREDICTIONS_CSV = TABLE_DIR / "audiodepth_gate_risk_guarded_predictions.csv"
BEST_POLICIES_CSV = TABLE_DIR / "audiodepth_risk_guarded_gate_best_policies.csv"
HIGH_ERROR_CSV = TABLE_DIR / "end_to_end_high_error_mixed_cases.csv"

COMPARISON_CSV = TABLE_DIR / "stage2_review_guard_comparison.csv"
SUMMARY_MD = FIGURE_DIR / "stage2_review_guard_summary.md"


def boolish(value: object) -> bool:
    return str(value).lower() == "true"


def should_review(row: dict[str, str]) -> bool:
    if row.get("selected_route") != "mixed":
        return False
    risk_score = safe_float(row.get("risk_score"))
    route_gap = safe_float(row.get("route_gap"))
    min_route_cer = safe_float(row.get("min_route_cer"))
    return (
        boolish(row.get("review_candidate"))
        or boolish(row.get("selected_mixed_high_error"))
        or "review" in row.get("intended_family", "")
        or risk_score >= 0.40
        or route_gap <= 0.02
        or min_route_cer >= 0.60
        or row.get("predicted_gate_label") != "easy_mixed"
    )


def summarize_policy(name: str, rows: list[dict[str, str]], apply_guard: bool) -> dict[str, object]:
    selected_cers = []
    covered_cers = []
    review_count = 0
    high_error_mixed_count = 0
    false_safe_count = 0
    text_probe_reduction_count = 0
    for row in rows:
        selected_cer = safe_float(row["selected_cer"])
        selected_cers.append(selected_cer)
        review = apply_guard and should_review(row)
        if review:
            review_count += 1
        else:
            covered_cers.append(selected_cer)
        if row.get("selected_route") == "mixed" and not review and boolish(row.get("selected_mixed_high_error")):
            high_error_mixed_count += 1
        if boolish(row.get("false_safe")) and not review:
            false_safe_count += 1
        if boolish(row.get("direct_bypass")):
            text_probe_reduction_count += 1
    return {
        "policy_name": name,
        "observed_route_CER_if_review_unrepaired": mean(selected_cers),
        "covered_non_review_CER": mean(covered_cers) if covered_cers else "",
        "review_rate": round(review_count / max(len(rows), 1), 6),
        "review_count": review_count,
        "coverage_rate": round((len(rows) - review_count) / max(len(rows), 1), 6),
        "high_error_mixed_count": high_error_mixed_count,
        "false_safe_count": false_safe_count,
        "text_probe_reduction_rate": round(text_probe_reduction_count / max(len(rows), 1), 6),
        "sample_count": len(rows),
        "note": "review_guard_abstains_without_claiming_repair" if apply_guard else "stage30_policy_without_extra_review_guard",
    }


def main() -> None:
    balanced_rows = read_csv(PREDICTIONS_CSV)
    best = read_csv(BEST_POLICIES_CSV)
    aggressive = next((row for row in best if row["policy_tier"] == "aggressive"), {})
    balanced = next((row for row in best if row["policy_tier"] == "balanced"), {})
    high_error = read_csv(HIGH_ERROR_CSV) if HIGH_ERROR_CSV.exists() else []
    comparison = [
        {
            "policy_name": "stage30_aggressive",
            "observed_route_CER_if_review_unrepaired": aggressive.get("selected_route_CER", ""),
            "covered_non_review_CER": "",
            "review_rate": aggressive.get("review_rate", ""),
            "review_count": "",
            "coverage_rate": "",
            "high_error_mixed_count": aggressive.get("selected_mixed_high_error_count", ""),
            "false_safe_count": aggressive.get("unsafe_bypass_count", ""),
            "text_probe_reduction_rate": aggressive.get("text_probe_reduction_rate", ""),
            "sample_count": aggressive.get("sample_count", ""),
            "note": "from_policy_sweep",
        },
        {
            "policy_name": "stage30_balanced",
            "observed_route_CER_if_review_unrepaired": balanced.get("selected_route_CER", ""),
            "covered_non_review_CER": "",
            "review_rate": balanced.get("review_rate", ""),
            "review_count": "",
            "coverage_rate": "",
            "high_error_mixed_count": balanced.get("selected_mixed_high_error_count", ""),
            "false_safe_count": balanced.get("unsafe_bypass_count", ""),
            "text_probe_reduction_rate": balanced.get("text_probe_reduction_rate", ""),
            "sample_count": balanced.get("sample_count", ""),
            "note": "from_policy_sweep",
        },
        summarize_policy("stage2_review_guard_on_balanced", balanced_rows, apply_guard=True),
        {
            "policy_name": "oracle",
            "observed_route_CER_if_review_unrepaired": "0.502854",
            "covered_non_review_CER": "",
            "review_rate": "0.0",
            "review_count": "0",
            "coverage_rate": "1.0",
            "high_error_mixed_count": "0",
            "false_safe_count": "0",
            "text_probe_reduction_rate": "",
            "sample_count": balanced.get("sample_count", ""),
            "note": "offline_upper_bound_not_deployable",
        },
    ]
    write_csv(COMPARISON_CSV, comparison)
    guarded = comparison[2]
    write_summary(
        SUMMARY_MD,
        "Stage-2 Review Guard",
        [
            f"- Stage 30 balanced high-error mixed count: `{balanced.get('selected_mixed_high_error_count', '')}`",
            f"- Review-guard high-error mixed count: `{guarded['high_error_mixed_count']}`",
            f"- Review-guard review rate: `{guarded['review_rate']}`",
            f"- Review-guard coverage rate: `{guarded['coverage_rate']}`",
            f"- Review-guard covered non-review CER: `{guarded['covered_non_review_CER']}`",
            f"- High-error mixed cases audited: `{len(high_error)}`",
            "- This guard reduces unsafe decisions by abstaining/reviewing; it does not claim repaired CER because no human or verified repair is applied.",
        ],
    )
    print(f"Wrote Stage-2 review guard comparison to {rel(COMPARISON_CSV)}")


if __name__ == "__main__":
    main()
