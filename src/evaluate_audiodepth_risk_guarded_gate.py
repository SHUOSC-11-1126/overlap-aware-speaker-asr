from __future__ import annotations

import argparse

import numpy as np
from PIL import Image, ImageDraw

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import FIGURE_DIR, METADATA_CSV, route_cer, write_summary
from .balanced_v2_common import V2_CER, mean
from .evaluate_audiodepth_two_stage_cascade import router_v2


TABLE_DIR = FIGURE_DIR.parent / "tables"
PRED_CSV = TABLE_DIR / "audiodepth_gate_risk_guarded_predictions.csv"
SWEEP_CSV = TABLE_DIR / "audiodepth_gate_risk_guarded_sweep.csv"
SUMMARY_CSV = TABLE_DIR / "audiodepth_gate_risk_guarded_summary.csv"
CALIBRATED_PRED_CSV = TABLE_DIR / "audiodepth_gate_calibrated_predictions.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate risk-guarded AudioDepth Stage-1 gate.")
    parser.add_argument("--confidence", type=float, default=0.30)
    parser.add_argument("--risk-quantile", type=float, default=0.55)
    return parser.parse_args()


def risk_score(row: dict[str, str]) -> float:
    return round(
        0.40 * safe_float(row.get("uncertainty_proxy_mean"))
        + 0.25 * safe_float(row.get("overlap_proxy_mean"))
        + 0.20 * safe_float(row.get("overlap_uncertainty_product"))
        + 0.15 * safe_float(row.get("uncertainty_proxy_std")),
        6,
    )


def choose_route(cer: dict[str, str], pred: dict[str, str], meta: dict[str, str], confidence: float, risk_ceiling: float) -> tuple[str, bool, str]:
    label = pred["predicted_gate_label"]
    conf = safe_float(pred["confidence"])
    risk = risk_score(meta)
    high_risk = risk > risk_ceiling
    if conf >= confidence and label == "easy_mixed" and not high_risk:
        return "mixed", False, "direct_easy_mixed"
    if conf >= confidence and label == "likely_separation_helpful":
        return "separated", False, "direct_separation_helpful"
    fallback = router_v2(cer)
    if fallback == "mixed" and high_risk:
        return "separated", True, "risk_guard_overrode_mixed"
    return fallback, True, "text_router_fallback"


def evaluate(confidence: float, risk_quantile: float, write_predictions: bool = False) -> dict[str, object]:
    cer_rows = read_csv(V2_CER)
    preds = {row["sample_id"]: row for row in read_csv(CALIBRATED_PRED_CSV)}
    meta = {row["sample_id"]: row for row in read_csv(METADATA_CSV)}
    rows = [row for row in cer_rows if row["sample_id"] in preds and row["sample_id"] in meta]
    risks = [risk_score(meta[row["sample_id"]]) for row in rows]
    risk_ceiling = float(np.quantile(risks, risk_quantile)) if risks else 0.0
    out = []
    for row in rows:
        pred = preds[row["sample_id"]]
        m = meta[row["sample_id"]]
        route, text_probe, reason = choose_route(row, pred, m, confidence, risk_ceiling)
        min_cer = min(safe_float(row["mixed_cer"]), safe_float(row["separated_cer"]), safe_float(row["cleaned_cer"]))
        out.append(
            {
                "sample_id": row["sample_id"],
                "selected_route": route,
                "oracle_route": row["oracle_route"],
                "selected_cer": route_cer(row, route),
                "oracle_cer": row["oracle_cer"],
                "stage2_text_probe_called": "True" if text_probe else "False",
                "guard_reason": reason,
                "risk_score": risk_score(m),
                "risk_ceiling": round(risk_ceiling, 6),
                "predicted_gate_label": pred["predicted_gate_label"],
                "confidence": pred["confidence"],
                "false_safe": "True" if route == "mixed" and min_cer > 0.6 else "False",
                "intended_family": row.get("intended_family", ""),
            }
        )
    if write_predictions:
        write_csv(PRED_CSV, out)
    return {
        "confidence": confidence,
        "risk_quantile": risk_quantile,
        "risk_ceiling": round(risk_ceiling, 6),
        "selected_route_cer": mean([safe_float(row["selected_cer"]) for row in out]),
        "route_accuracy": round(sum(1 for row in out if row["selected_route"] == row["oracle_route"]) / max(len(out), 1), 6),
        "text_probe_reduction_rate": round(sum(1 for row in out if row["stage2_text_probe_called"] == "False") / max(len(out), 1), 6),
        "false_safe_rate": round(sum(1 for row in out if row["false_safe"] == "True") / max(len(out), 1), 6),
        "separation_call_rate": round(sum(1 for row in out if row["selected_route"] == "separated") / max(len(out), 1), 6),
        "risk_guard_override_count": sum(1 for row in out if row["guard_reason"] == "risk_guard_overrode_mixed"),
        "sample_count": len(out),
    }


def draw_sweep(rows: list[dict[str, object]]) -> None:
    img = Image.new("RGB", (920, 500), "white")
    draw = ImageDraw.Draw(img)
    draw.text((24, 18), "Risk-guarded AudioDepth gate sweep", fill=(0, 0, 0))
    xs = [safe_float(row["text_probe_reduction_rate"]) for row in rows]
    ys = [safe_float(row["selected_route_cer"]) for row in rows]
    fs = [safe_float(row["false_safe_rate"]) for row in rows]
    min_y, max_y = min(ys + [0]), max(ys + [1e-6])
    for x_val, y_val, f_val in zip(xs, ys, fs):
        x = 80 + int(760 * x_val)
        y = 390 - int(280 * (y_val - min_y) / max(max_y - min_y, 1e-6))
        shade = int(255 - 180 * min(f_val / 0.25, 1.0))
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(220, shade, shade))
    draw.line((80, 390, 840, 390), fill=(0, 0, 0))
    draw.line((80, 110, 80, 390), fill=(0, 0, 0))
    draw.text((320, 430), "text-probe reduction ->", fill=(0, 0, 0))
    draw.text((8, 250), "CER", fill=(0, 0, 0))
    out = FIGURE_DIR / "audiodepth_gate_risk_guarded_sweep.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def main() -> None:
    args = parse_args()
    sweep = []
    for confidence in [0.30, 0.40, 0.50, 0.60, 0.70]:
        for risk_quantile in [0.35, 0.45, 0.55, 0.65, 0.75, 0.85]:
            sweep.append(evaluate(confidence, risk_quantile))
    write_csv(SWEEP_CSV, sweep)
    feasible = [row for row in sweep if safe_float(row["false_safe_rate"]) <= 0.10]
    best_pool = feasible or sweep
    best = sorted(best_pool, key=lambda row: (safe_float(row["selected_route_cer"]), -safe_float(row["text_probe_reduction_rate"])))[0]
    final = evaluate(safe_float(best["confidence"]), safe_float(best["risk_quantile"]), write_predictions=True)
    write_csv(SUMMARY_CSV, [final])
    draw_sweep(sweep)
    write_summary(
        FIGURE_DIR / "audiodepth_gate_risk_guarded_summary.md",
        "AudioDepth Risk-Guarded Gate",
        [
            f"- selected confidence: `{final['confidence']}`",
            f"- selected risk quantile: `{final['risk_quantile']}`",
            f"- selected CER: `{final['selected_route_cer']}`",
            f"- text-probe reduction: `{final['text_probe_reduction_rate']}`",
            f"- false-safe rate: `{final['false_safe_rate']}`",
            f"- risk-guard overrides: `{final['risk_guard_override_count']}`",
            "- This layer protects the calibrated gate by blocking mixed fallback on high-risk AudioDepth maps.",
        ],
    )
    print(f"Wrote risk-guarded AudioDepth gate to {rel(SUMMARY_CSV)}")


if __name__ == "__main__":
    main()
