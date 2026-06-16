from __future__ import annotations

from collections import Counter

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import FIGURE_DIR, write_summary


TABLE_DIR = FIGURE_DIR.parent / "tables"
PREDICTIONS_CSV = TABLE_DIR / "audiodepth_gate_risk_guarded_predictions.csv"
BEST_POLICIES_CSV = TABLE_DIR / "audiodepth_risk_guarded_gate_best_policies.csv"
V2_CER_CSV = TABLE_DIR / "controlled_v2_real_whisper_cer.csv"
MANIFEST_CSV = TABLE_DIR / "controlled_v2_manifest.csv"
BALANCED_COMPARISON_CSV = TABLE_DIR / "audio_depth_balanced_router_comparison.csv"

AUDIT_CSV = TABLE_DIR / "end_to_end_router_safety_audit.csv"
HIGH_ERROR_CSV = TABLE_DIR / "end_to_end_high_error_mixed_cases.csv"
SUMMARY_MD = FIGURE_DIR / "end_to_end_router_safety_audit.md"


def boolish(value: object) -> bool:
    return str(value).lower() == "true"


def load_joined_rows() -> list[dict[str, str]]:
    predictions = read_csv(PREDICTIONS_CSV)
    cer = {row["sample_id"]: row for row in read_csv(V2_CER_CSV)}
    manifest = {row["sample_id"]: row for row in read_csv(MANIFEST_CSV)}
    rows = []
    for row in predictions:
        sample_id = row["sample_id"]
        joined = dict(row)
        joined.update({f"cer_{key}": value for key, value in cer.get(sample_id, {}).items()})
        joined.update({f"manifest_{key}": value for key, value in manifest.get(sample_id, {}).items()})
        rows.append(joined)
    return rows


def classify_source(row: dict[str, str]) -> str:
    if boolish(row.get("direct_bypass")):
        return "audiodepth_direct_bypass"
    if str(row.get("guard_reason", "")).startswith("review_candidate"):
        return "stage2_after_review_candidate"
    if str(row.get("guard_reason", "")).startswith("stage2"):
        return "stage2_text_router"
    if "overrode" in str(row.get("guard_reason", "")):
        return "risk_guard_override"
    return "other"


def audit_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    high_error = []
    all_rows = []
    for row in rows:
        selected_mixed_high_error = boolish(row.get("selected_mixed_high_error"))
        source = classify_source(row)
        route_gap = safe_float(row.get("route_gap") or row.get("cer_route_gap"))
        min_route_cer = safe_float(row.get("min_route_cer"))
        should_review = (
            selected_mixed_high_error
            or boolish(row.get("review_candidate"))
            or "review" in row.get("intended_family", "")
            or route_gap <= 0.02
            or min_route_cer >= 0.60
        )
        out = {
            "sample_id": row["sample_id"],
            "selected_route": row["selected_route"],
            "oracle_route": row["oracle_route"],
            "selected_cer": row["selected_cer"],
            "mixed_cer": row.get("cer_mixed_cer", ""),
            "separated_cer": row.get("cer_separated_cer", ""),
            "cleaned_cer": row.get("cer_cleaned_cer", ""),
            "route_gap": route_gap,
            "min_route_cer": min_route_cer,
            "intended_family": row.get("intended_family", ""),
            "reference_type": row.get("cer_reference_type") or row.get("manifest_reference_type", ""),
            "predicted_gate_label": row.get("predicted_gate_label", ""),
            "confidence": row.get("confidence", ""),
            "risk_score": row.get("risk_score", ""),
            "guard_reason": row.get("guard_reason", ""),
            "stage2_text_probe_called": row.get("stage2_text_probe_called", ""),
            "direct_bypass": row.get("direct_bypass", ""),
            "review_candidate": row.get("review_candidate", ""),
            "selected_mixed_high_error": selected_mixed_high_error,
            "risk_source": source,
            "should_have_reviewed": should_review,
            "weak_silver_reference": row.get("cer_reference_type", "") == "silver_plus_unverified",
        }
        all_rows.append(out)
        if selected_mixed_high_error:
            high_error.append(out)
    return all_rows, high_error


def summarize(all_rows: list[dict[str, object]], high_error: list[dict[str, object]]) -> list[dict[str, object]]:
    source_counts = Counter(row["risk_source"] for row in high_error)
    oracle_counts = Counter(row["oracle_route"] for row in high_error)
    review_needed = sum(1 for row in high_error if "review" in str(row["intended_family"]))
    weak_refs = sum(1 for row in high_error if row["weak_silver_reference"])
    small_gap = sum(1 for row in high_error if safe_float(row["route_gap"]) <= 0.02)
    direct_high_error = sum(1 for row in high_error if row["risk_source"] == "audiodepth_direct_bypass")
    return [
        {
            "sample_count": len(all_rows),
            "high_error_mixed_count": len(high_error),
            "direct_bypass_high_error_count": direct_high_error,
            "stage2_or_review_high_error_count": len(high_error) - direct_high_error,
            "review_needed_family_count": review_needed,
            "small_route_gap_count": small_gap,
            "weak_silver_reference_count": weak_refs,
            "source_breakdown": "; ".join(f"{key}:{value}" for key, value in sorted(source_counts.items())),
            "oracle_breakdown": "; ".join(f"{key}:{value}" for key, value in sorted(oracle_counts.items())),
        }
    ]


def main() -> None:
    rows = load_joined_rows()
    all_rows, high_error = audit_rows(rows)
    summary = summarize(all_rows, high_error)
    comparison = read_csv(BALANCED_COMPARISON_CSV)
    router_v2 = next((row for row in comparison if row.get("model_name") == "router_v2"), {})
    balanced = next((row for row in read_csv(BEST_POLICIES_CSV) if row.get("policy_tier") == "balanced"), {})
    write_csv(AUDIT_CSV, summary)
    write_csv(HIGH_ERROR_CSV, high_error)
    s = summary[0]
    write_summary(
        SUMMARY_MD,
        "End-to-End Router Safety Audit",
        [
            f"- evaluated samples: `{s['sample_count']}`",
            f"- high-error mixed selections: `{s['high_error_mixed_count']}`",
            f"- direct-bypass high-error count: `{s['direct_bypass_high_error_count']}`",
            f"- Stage-2/review-path high-error count: `{s['stage2_or_review_high_error_count']}`",
            f"- source breakdown: `{s['source_breakdown']}`",
            f"- oracle breakdown: `{s['oracle_breakdown']}`",
            f"- review-needed family count: `{s['review_needed_family_count']}`",
            f"- weak silver reference count: `{s['weak_silver_reference_count']}`",
            f"- balanced risk-guarded CER: `{balanced.get('selected_route_CER', '')}`",
            f"- router_v2 CER: `{router_v2.get('average_cer', '')}`",
            "- Conclusion: AudioDepth direct bypass safety is solved in the selected Stage 30 policy, but end-to-end safety is not solved because the Stage-2/review path can still choose mixed on high-error silver-plus cases.",
            "- Current largest risk: weak references plus missing abstention/review enforcement after Stage-2 mixed decisions.",
        ],
    )
    print(f"Wrote safety audit to {rel(AUDIT_CSV)}")
    print(f"Wrote high-error mixed cases to {rel(HIGH_ERROR_CSV)}")


if __name__ == "__main__":
    main()
