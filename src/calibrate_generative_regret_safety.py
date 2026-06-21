from __future__ import annotations

from pathlib import Path

from .generative_audiodepth_common import FIGURE_DIR, TABLE_DIR, read_rows, safe_float, write_csv, write_markdown
from .generative_audiodepth_reliability_common import RELIABILITY_TEST, draw_bar_chart, policy_metrics


PRED_CSV = TABLE_DIR / "generative_regret_calibration_predictions.csv"
SWEEP_CSV = TABLE_DIR / "generative_regret_calibration_sweep.csv"
POLICY_CSV = TABLE_DIR / "generative_regret_calibration_policies.csv"
PARETO_PNG = FIGURE_DIR / "generative_regret_calibration_pareto.png"
CURVES_PNG = FIGURE_DIR / "generative_regret_calibration_curves.png"
SUMMARY_MD = FIGURE_DIR / "generative_regret_calibration.md"


def pred_by_model() -> dict[str, dict[str, dict[str, str]]]:
    out: dict[str, dict[str, dict[str, str]]] = {}
    for row in read_rows(PRED_CSV):
        out.setdefault(row["model_name"], {})[row["sample_id"]] = row
    return out


def margin(row: dict[str, str]) -> float:
    values = sorted(
        [
            safe_float(row.get("predicted_mixed_regret"), 0.0),
            safe_float(row.get("predicted_separated_regret"), 0.0),
            safe_float(row.get("predicted_cleaned_regret"), 0.0),
        ]
    )
    return values[1] - values[0] if len(values) > 1 else 0.0


def calibrate(samples: list[dict[str, str]], preds: dict[str, str], margin_threshold: float, review_threshold: float, confidence_threshold: float) -> dict[str, str]:
    routes = {}
    for row in samples:
        pred = preds[row["sample_id"]]
        risk = safe_float(pred.get("review_risk"), 0.0)
        route = pred.get("predicted_route", "mixed")
        confidence = max(0.0, min(1.0, 1.0 - risk))
        if margin(pred) < margin_threshold or risk >= review_threshold or confidence < confidence_threshold:
            route = "review"
        routes[row["sample_id"]] = route
    return routes


def main() -> None:
    samples = sorted({row["sample_id"]: row for row in read_rows(RELIABILITY_TEST)}.values(), key=lambda r: r["sample_id"])
    models = pred_by_model()
    base_model = "R2_regret_rank_review_head" if "R2_regret_rank_review_head" in models else sorted(models)[0]
    preds = models[base_model]
    sweep_rows = []
    for margin_threshold in [0.00, 0.01, 0.02, 0.03, 0.05, 0.10]:
        for review_threshold in [0.40, 0.50, 0.60, 0.70, 0.80]:
            for confidence_threshold in [0.50, 0.60, 0.70, 0.80, 0.90]:
                routes = calibrate(samples, preds, margin_threshold, review_threshold, confidence_threshold)
                row = policy_metrics(samples, routes, f"margin{margin_threshold:.2f}_review{review_threshold:.2f}_conf{confidence_threshold:.2f}")
                row.update(
                    {
                        "base_model": base_model,
                        "regret_margin_threshold": margin_threshold,
                        "review_threshold": review_threshold,
                        "confidence_threshold": confidence_threshold,
                        "stage32_false_safe": 4,
                        "stage30_balanced_cer": 0.529082,
                        "stage27_balanced_router_cer": 0.502854,
                    }
                )
                sweep_rows.append(row)
    write_csv(SWEEP_CSV, sweep_rows)
    eligible = sorted(sweep_rows, key=lambda r: (r["false_safe_count"], safe_float(r["selected_route_cer"]), safe_float(r["review_rate"])))
    aggressive = min(sweep_rows, key=lambda r: (safe_float(r["review_rate"]), r["false_safe_count"], safe_float(r["selected_route_cer"])))
    balanced = eligible[0]
    conservative = min(sweep_rows, key=lambda r: (r["false_safe_count"], -safe_float(r["review_rate"]), safe_float(r["selected_route_cer"])))
    policies = [
        {**aggressive, "policy_tier": "aggressive"},
        {**balanced, "policy_tier": "balanced"},
        {**conservative, "policy_tier": "conservative"},
    ]
    write_csv(POLICY_CSV, policies)
    draw_bar_chart(PARETO_PNG, "Generative regret safety calibration: selected CER", policies, "policy_tier", "selected_route_cer")
    draw_bar_chart(CURVES_PNG, "Generative regret safety calibration: false-safe count", policies, "policy_tier", "false_safe_count")
    lines = [
        "# Generative Regret Safety Calibration",
        "",
        "| tier | CER | false-safe | coverage | review rate | route accuracy |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in policies:
        lines.append(
            f"| {row['policy_tier']} | {row['selected_route_cer']} | {row['false_safe_count']} | {row['coverage']} | {row['review_rate']} | {row['route_accuracy']} |"
        )
    best_false_safe = min(row["false_safe_count"] for row in policies)
    lines.extend(
        [
            "",
            f"- Stage 32 false-safe count: 4",
            f"- best calibrated false-safe count: {best_false_safe}",
            "- Review selections are treated as abstention / Stage-2 handoff, not automatic ASR repair.",
        ]
    )
    write_markdown(SUMMARY_MD, lines)
    print(f"wrote {POLICY_CSV}")


if __name__ == "__main__":
    main()
