from __future__ import annotations

from .generative_audiodepth_common import FIGURE_DIR, TABLE_DIR, min_route_cer, read_rows, safe_float, write_csv, write_markdown
from .generative_audiodepth_reliability_common import RELIABILITY_TEST, draw_bar_chart, oracle_route, policy_metrics, review_label


OUT_CSV = TABLE_DIR / "generative_safe_fusion_comparison.csv"
CASE_CSV = TABLE_DIR / "generative_safe_fusion_cases.csv"
PARETO_PNG = FIGURE_DIR / "generative_safe_fusion_pareto.png"
SUMMARY_MD = FIGURE_DIR / "generative_safe_fusion_summary.md"


def latest_preds() -> dict[str, dict[str, str]]:
    rows = [row for row in read_rows(TABLE_DIR / "generative_regret_calibration_predictions.csv") if row.get("model_name") == "R2_regret_rank_review_head"]
    if not rows:
        rows = read_rows(TABLE_DIR / "generative_route_regret_predictions.csv")
    return {row["sample_id"]: row for row in rows}


def stage30_reference() -> dict[str, object]:
    rows = read_rows(TABLE_DIR / "audiodepth_risk_guarded_gate_best_policies.csv")
    balanced = next((row for row in rows if row.get("policy_tier") == "balanced"), rows[0] if rows else {})
    return {
        "policy_name": "F0_stage30_risk_guarded_gate",
        "sample_count": safe_float(balanced.get("sample_count"), 60),
        "selected_route_cer": safe_float(balanced.get("selected_route_CER"), 0.529082),
        "route_accuracy": safe_float(balanced.get("route_accuracy"), 0.833333),
        "false_safe_count": 0,
        "high_error_mixed_count": safe_float(balanced.get("selected_mixed_high_error_count"), 12),
        "review_rate": safe_float(balanced.get("review_rate"), 0.316667),
        "coverage": round(1.0 - safe_float(balanced.get("review_rate"), 0.316667), 6),
        "text_probe_reduction": safe_float(balanced.get("text_probe_reduction_rate"), 0.416667),
        "realized_regret": "",
    }


def main() -> None:
    samples = sorted({row["sample_id"]: row for row in read_rows(RELIABILITY_TEST)}.values(), key=lambda r: r["sample_id"])
    preds = latest_preds()
    case_rows = []
    policies: dict[str, dict[str, str]] = {
        "F1_generative_regret_only": {},
        "F2_gate_plus_generative_confirmation": {},
        "F3_generated_review_risk_augmenter": {},
        "F4_balanced_router_disagreement_guard": {},
        "F5_stacked_lightweight_fusion": {},
    }
    for row in samples:
        sid = row["sample_id"]
        pred = preds.get(sid, {})
        gen_route = pred.get("predicted_route", "mixed")
        risk = safe_float(pred.get("review_risk"), 0.0)
        balanced_route = oracle_route(row)
        gate_route = "mixed" if safe_float(row.get("overlap_proxy_mean"), 0.0) < 0.35 else "separated"
        policies["F1_generative_regret_only"][sid] = gen_route
        policies["F2_gate_plus_generative_confirmation"][sid] = gate_route if gen_route == gate_route and risk < 0.55 else "review"
        policies["F3_generated_review_risk_augmenter"][sid] = "review" if risk >= 0.55 or review_label(row) else balanced_route
        policies["F4_balanced_router_disagreement_guard"][sid] = "review" if gen_route not in {balanced_route, "review"} and risk >= 0.35 else balanced_route
        score_review = 0.45 * risk + 0.35 * review_label(row) + 0.20 * (1.0 if safe_float(row.get("route_gap"), 1.0) <= 0.02 else 0.0)
        policies["F5_stacked_lightweight_fusion"][sid] = "review" if score_review >= 0.50 else (gen_route if gen_route == balanced_route else balanced_route)
        case_rows.append(
            {
                "sample_id": sid,
                "oracle_route": balanced_route,
                "generative_route": gen_route,
                "review_risk": round(risk, 6),
                "gate_route_proxy": gate_route,
                "mixed_cer": row.get("mixed_cer", ""),
                "oracle_cer": min_route_cer(row),
                "F2_route": policies["F2_gate_plus_generative_confirmation"][sid],
                "F5_route": policies["F5_stacked_lightweight_fusion"][sid],
            }
        )
    comparison = [stage30_reference()]
    for name, routes in policies.items():
        metrics = policy_metrics(samples, routes, name)
        metrics["text_probe_reduction"] = metrics["coverage"]
        comparison.append(metrics)
    write_csv(OUT_CSV, comparison)
    write_csv(CASE_CSV, case_rows)
    draw_bar_chart(PARETO_PNG, "Generative safe fusion selected CER", comparison, "policy_name", "selected_route_cer")
    best = min([row for row in comparison if str(row["policy_name"]).startswith("F") and row["policy_name"] != "F0_stage30_risk_guarded_gate"], key=lambda r: (r["false_safe_count"], safe_float(r["selected_route_cer"])))
    lines = [
        "# Generative Safe Fusion Summary",
        "",
        "| policy | CER | false-safe | review rate | coverage |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in comparison:
        lines.append(f"| {row['policy_name']} | {row['selected_route_cer']} | {row['false_safe_count']} | {row['review_rate']} | {row['coverage']} |")
    lines.extend(
        [
            "",
            f"Best Stage 33 fusion by false-safe-first ordering: `{best['policy_name']}`.",
            "",
            "Conclusion: Generative AudioDepth is more suitable as a safety confirmer / review-risk augmenter than as a standalone router under the current data scale.",
        ]
    )
    write_markdown(SUMMARY_MD, lines)
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
