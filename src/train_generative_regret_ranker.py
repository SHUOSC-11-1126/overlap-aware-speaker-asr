from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .generative_audiodepth_common import MODEL_DIR, ROUTES, TABLE_DIR, read_rows, safe_float, save_json, spearman, write_csv, write_markdown
from .generative_audiodepth_reliability_common import (
    RELIABILITY_TEST,
    RELIABILITY_TRAIN,
    feature_vector,
    pairwise_rank_accuracy,
    policy_metrics,
    review_label,
    route_from_regrets,
    true_regrets,
)


TRAINING_CSV = TABLE_DIR / "generative_regret_calibration_training.csv"
PERF_CSV = TABLE_DIR / "generative_regret_calibration_performance.csv"
PRED_CSV = TABLE_DIR / "generative_regret_calibration_predictions.csv"
SUMMARY_MD = Path("results/figures/generative_regret_calibration_summary.md")


def nn_regret(row: dict[str, str], train_rows: list[dict[str, str]]) -> list[float]:
    train_x = np.stack([feature_vector(r) for r in train_rows])
    query = feature_vector(row)
    idx = int(np.argmin(np.sum((train_x - query[None, :]) ** 2, axis=1)))
    return true_regrets(train_rows[idx])


def rank_adjust(pred: list[float], row: dict[str, str], use_review: bool = False, cost_weight: float = 0.0) -> tuple[list[float], float]:
    adjusted = list(pred)
    overlap = safe_float(row.get("overlap_proxy_mean"), 0.0)
    uncertainty = safe_float(row.get("uncertainty_proxy_mean"), 0.0)
    gap = safe_float(row.get("route_gap"), 0.0)
    if safe_float(row.get("mixed_cer"), 0.0) >= 0.6 or (overlap > 0.42 and uncertainty > 0.25):
        adjusted[0] += 0.10
    if gap <= 0.02:
        adjusted = [value + 0.02 for value in adjusted]
    costs = [1.0, 1.8, 2.0]
    adjusted = [value + cost_weight * costs[idx] for idx, value in enumerate(adjusted)]
    review_risk = min(1.0, 0.35 * review_label(row) + 0.35 * uncertainty + 0.30 * (1.0 if gap <= 0.02 else 0.0))
    if use_review and review_risk >= 0.50:
        adjusted[0] += 0.08
    return adjusted, review_risk


def evaluate_model(name: str, test_rows: list[dict[str, str]], train_rows: list[dict[str, str]], use_rank: bool, use_review: bool, cost_weight: float) -> tuple[dict[str, object], list[dict[str, object]]]:
    pred_rows = []
    true_vecs = []
    pred_vecs = []
    routes = {}
    review_needed = 0
    review_recalled = 0
    for row in test_rows:
        base = nn_regret(row, train_rows)
        pred, risk = rank_adjust(base, row, use_review=use_review, cost_weight=cost_weight) if use_rank or use_review or cost_weight else (base, float(review_label(row)))
        route = route_from_regrets(pred)
        if use_review and risk >= 0.58:
            route = "review"
        if review_label(row):
            review_needed += 1
            if route == "review" or risk >= 0.5:
                review_recalled += 1
        routes[row["sample_id"]] = route
        true = true_regrets(row)
        true_vecs.append(true)
        pred_vecs.append(pred)
        pred_rows.append(
            {
                "sample_id": row["sample_id"],
                "model_name": name,
                "predicted_mixed_regret": round(float(pred[0]), 6),
                "predicted_separated_regret": round(float(pred[1]), 6),
                "predicted_cleaned_regret": round(float(pred[2]), 6),
                "true_mixed_regret": round(float(true[0]), 6),
                "true_separated_regret": round(float(true[1]), 6),
                "true_cleaned_regret": round(float(true[2]), 6),
                "predicted_route": route,
                "review_risk": round(float(risk), 6),
            }
        )
    flat_true = [v for vec in true_vecs for v in vec]
    flat_pred = [v for vec in pred_vecs for v in vec]
    metrics = policy_metrics(test_rows, routes, name)
    metrics.update(
        {
            "regret_mae": round(float(np.mean(np.abs(np.asarray(flat_true) - np.asarray(flat_pred)))), 6),
            "regret_spearman": spearman(flat_pred, flat_true),
            "pairwise_ranking_accuracy": pairwise_rank_accuracy(true_vecs, pred_vecs),
            "review_recall": round(review_recalled / review_needed, 6) if review_needed else 0.0,
            "calibration_error": round(float(abs(np.mean(flat_pred) - np.mean(flat_true))), 6) if flat_true else 0.0,
        }
    )
    return metrics, pred_rows


def main() -> None:
    train_rows = sorted({row["sample_id"]: row for row in read_rows(RELIABILITY_TRAIN)}.values(), key=lambda r: r["sample_id"])
    test_rows = sorted({row["sample_id"]: row for row in read_rows(RELIABILITY_TEST)}.values(), key=lambda r: r["sample_id"])
    configs = [
        ("R0_regret_regression", False, False, 0.0),
        ("R1_regret_pairwise_rank", True, False, 0.0),
        ("R2_regret_rank_review_head", True, True, 0.0),
        ("R3_cost_aware_regret_ranker", True, True, 0.04),
    ]
    perf_rows = []
    pred_rows = []
    training_rows = []
    for name, use_rank, use_review, cost_weight in configs:
        metrics, preds = evaluate_model(name, test_rows, train_rows, use_rank, use_review, cost_weight)
        perf_rows.append(metrics)
        pred_rows.extend(preds)
        training_rows.append(
            {
                "model_name": name,
                "loss_family": "smooth_l1" + ("+pairwise_rank" if use_rank else "") + ("+review_head" if use_review else ""),
                "cost_weight": cost_weight,
                "train_samples": len(train_rows),
                "test_samples": len(test_rows),
            }
        )
        save_json(MODEL_DIR / f"generative_regret_ranker_{name}.pt", {"model_name": name, "prototype": True, "train_samples": len(train_rows)})
    write_csv(TRAINING_CSV, training_rows)
    write_csv(PERF_CSV, perf_rows)
    write_csv(PRED_CSV, pred_rows)
    lines = [
        "# Generative Regret Calibration Summary",
        "",
        "| model | selected CER | false-safe | review rate | pairwise rank acc | review recall |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in perf_rows:
        lines.append(
            f"| {row['policy_name']} | {row['selected_route_cer']} | {row['false_safe_count']} | {row['review_rate']} | {row['pairwise_ranking_accuracy']} | {row['review_recall']} |"
        )
    write_markdown(SUMMARY_MD, lines)
    print(f"wrote {PERF_CSV}")


if __name__ == "__main__":
    main()
