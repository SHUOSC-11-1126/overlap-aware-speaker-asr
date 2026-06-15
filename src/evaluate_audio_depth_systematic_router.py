from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_router_common import LABEL_TO_METHOD, PROJECT_ROOT, ROUTE_LABELS, confusion_counts, draw_bar_chart, draw_confusion_matrix, read_csv, rel, route_cer, write_csv
from .audio_depth_systematic_common import (
    COMPARISON_CSV,
    MODEL_STATUS_CSV,
    PERFORMANCE_CSV,
    PER_RATIO_CSV,
    PER_TIER_CSV,
    PREDICTIONS_CSV,
    ROUTE_COSTS,
    SYSTEMATIC_FIGURE_PREFIX,
    SYSTEMATIC_MODEL_PREFIX,
    feature_vector,
    fixed_route_predictions,
    group_metric_rows,
    load_systematic_rows,
    metrics_for_predictions,
    split_systematic_rows,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate systematic AudioDepth-Hybrid routers.")
    return parser.parse_args()


def load_model_predict(model_name: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import torch
    from torch import nn

    path = SYSTEMATIC_MODEL_PREFIX / f"audio_depth_systematic_{model_name}.pt"
    if not path.exists():
        return []
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    arch = checkpoint["architecture"]
    model = nn.Sequential(nn.Linear(arch[0], arch[1]), nn.ReLU(), nn.Dropout(0.08), nn.Linear(arch[1], arch[2]), nn.ReLU(), nn.Linear(arch[2], arch[3]))
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    mean = np.asarray(checkpoint["mean"], dtype=np.float32)
    std = np.asarray(checkpoint["std"], dtype=np.float32)
    std[std == 0] = 1.0
    preds = []
    with torch.no_grad():
        x = np.asarray([feature_vector(row) for row in rows], dtype=np.float32)
        x = (x - mean) / std
        probs = torch.softmax(model(torch.from_numpy(x)), dim=1).cpu().numpy()
    for row, prob in zip(rows, probs):
        idx = int(np.argmax(prob))
        label = ROUTE_LABELS[idx]
        confidence = float(prob[idx])
        risk_level = "high" if confidence < 0.55 else "medium" if confidence < 0.75 else "low"
        fallback = "router_v2" if model_name == "calibrated_confidence_router" and confidence < 0.7 else "none"
        if fallback == "router_v2":
            label = router_v2_proxy(row)
        if model_name == "cost_aware_router":
            label = min(ROUTE_LABELS, key=lambda route: -float(prob[ROUTE_LABELS.index(route)]) + 0.04 * ROUTE_COSTS[route])
        preds.append(
            {
                "sample_id": row["sample_id"],
                "dataset": row.get("dataset", ""),
                "split": row.get("split", ""),
                "model_name": model_name,
                "true_route_label": row["best_route_label"],
                "predicted_route_label": label,
                "predicted_method": LABEL_TO_METHOD[label],
                "confidence": round(confidence, 6),
                "risk_level": risk_level,
                "fallback_strategy": fallback,
                "predicted_cer": route_cer(row, label),
                "expected_cost": ROUTE_COSTS[label],
                "overlap_tier": row.get("overlap_tier", ""),
                "overlap_ratio": row.get("overlap_ratio", ""),
                "explanation": explanation_for(row, label, confidence),
            }
        )
    return preds


def router_v2_proxy(row: dict[str, Any]) -> str:
    ratio = float(row.get("overlap_ratio") or 0.0)
    repetition = float(row.get("repetition_score") or 0.0)
    if repetition > 2.0 or ratio < 0.25:
        return "mixed"
    if ratio > 0.65:
        return "separated"
    return "mixed"


def explanation_for(row: dict[str, Any], label: str, confidence: float) -> str:
    ratio = float(row.get("overlap_ratio") or 0.0)
    rep = float(row.get("repetition_score") or 0.0)
    if label == "mixed":
        return f"mixed favored because overlap_ratio={ratio:.2f} or transcript repetition risk={rep:.2f} makes separation risky; confidence={confidence:.2f}"
    if label == "cleaned":
        return f"cleaned favored because separated route may help but cleanup risk controls repetition; confidence={confidence:.2f}"
    return f"separated favored because overlap_ratio={ratio:.2f} suggests separation can reduce occlusion; confidence={confidence:.2f}"


def oracle_predictions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    preds = []
    for row in rows:
        label = min(ROUTE_LABELS, key=lambda route: route_cer(row, route))
        preds.append({**fixed_route_predictions([row], "oracle_best", label)[0], "model_name": "oracle_best", "true_route_label": row["best_route_label"]})
    return preds


def main() -> None:
    rows = load_systematic_rows()
    _, _, test_rows = split_systematic_rows(rows)
    predictions: list[dict[str, Any]] = []
    for name in ["hybrid_mlp_v2", "hybrid_late_fusion_v2", "calibrated_confidence_router", "cost_aware_router"]:
        predictions.extend(load_model_predict(name, test_rows))
    predictions.extend(fixed_route_predictions(test_rows, "fixed_mixed", "mixed"))
    predictions.extend(fixed_route_predictions(test_rows, "fixed_separated", "separated"))
    predictions.extend(fixed_route_predictions(test_rows, "fixed_cleaned", "cleaned"))
    predictions.extend(fixed_route_predictions(test_rows, "previous_audio_depth_mvp", "separated"))
    predictions.extend(fixed_route_predictions(test_rows, "previous_model_zoo_best", "separated"))
    router_v2 = []
    for row in test_rows:
        router_v2.extend(fixed_route_predictions([row], "old_router_v2", router_v2_proxy(row)))
    predictions.extend(router_v2)
    predictions.extend(oracle_predictions(test_rows))
    perf = [metrics_for_predictions(name, [row for row in predictions if row["model_name"] == name], "baseline" if name.startswith("fixed") or name in {"old_router_v2", "oracle_best", "previous_audio_depth_mvp", "previous_model_zoo_best"} else "experimental/frontier") for name in sorted({row["model_name"] for row in predictions})]
    perf = sorted(perf, key=lambda row: float(row["routing_average_cer"]))
    write_csv(PREDICTIONS_CSV, predictions)
    write_csv(PERFORMANCE_CSV, perf)
    write_csv(PER_TIER_CSV, group_metric_rows(predictions, "overlap_tier"))
    write_csv(PER_RATIO_CSV, group_metric_rows(predictions, "overlap_ratio"))
    best = next(row for row in perf if row["label"] == "experimental/frontier")
    comparison = [{**row, "delta_vs_best_systematic": round(float(row["routing_average_cer"]) - float(best["routing_average_cer"]), 6)} for row in perf]
    write_csv(COMPARISON_CSV, comparison)
    draw_bar_chart(perf[:10], SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_leaderboard.png", "model_name", "routing_average_cer", "Systematic AudioDepth-Hybrid leaderboard")
    matrix_preds = [row for row in predictions if row["model_name"] == best["model_name"]]
    draw_confusion_matrix(confusion_counts([row["true_route_label"] for row in matrix_preds], [row["predicted_route_label"] for row in matrix_preds]), SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_confusion_matrix.png", best["model_name"])
    ratio_rows = [row for row in group_metric_rows(predictions, "overlap_ratio") if row["model_name"] == best["model_name"]]
    from .audio_depth_systematic_common import draw_simple_line

    draw_simple_line(ratio_rows, SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_overlap_curve.png", "overlap_ratio", "routing_average_cer", "Systematic CER by overlap ratio")
    (SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_summary.md").write_text(
        "\n".join(
            [
                "# Systematic AudioDepth-Hybrid Summary",
                "",
                f"Best systematic frontier model: `{best['model_name']}` with routing CER `{best['routing_average_cer']}` on `{best['sample_count']}` held-out systematic samples.",
                "",
                "Stress route CER is labeled `synthetic/silver_proxy` because Whisper is unavailable in this runtime. Treat improvements as systematic evidence to re-run with real ASR, not as gold replacement claims.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote systematic evaluation to {rel(PERFORMANCE_CSV)}")


if __name__ == "__main__":
    main()
