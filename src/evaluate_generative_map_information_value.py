from __future__ import annotations

import random
from pathlib import Path
from typing import Callable

import numpy as np

from .generative_audiodepth_common import FIGURE_DIR, ROUTES, TABLE_DIR, read_rows, safe_float, write_csv, write_markdown
from .generative_audiodepth_reliability_common import (
    RELIABILITY_TEST,
    RELIABILITY_TRAIN,
    classification_metrics,
    draw_bar_chart,
    generated_map_features,
    handcrafted_features,
    logmel_features,
    nearest_neighbor_predict,
    regression_metrics,
    review_label,
    route_gap_bucket,
    separation_helpful_label,
    standardize,
    teacher_map_features,
    true_regrets,
    write_input_audit,
)


OUT_CSV = TABLE_DIR / "generative_audiodepth_reliability_information_value.csv"
PRED_CSV = TABLE_DIR / "generative_audiodepth_reliability_probe_predictions.csv"
OUT_PNG = FIGURE_DIR / "generative_audiodepth_reliability_information_value.png"
OUT_MD = FIGURE_DIR / "generative_audiodepth_reliability_information_value.md"


def feature_builders(dataset_rows: list[dict[str, str]], train_rows: list[dict[str, str]]) -> dict[str, Callable[[dict[str, str]], list[float]]]:
    shuffled_cache: dict[str, list[float]] = {}
    train_generated = [generated_map_features(row, train_rows, dataset_rows) for row in train_rows]
    shuffled = train_generated[:]
    random.Random(33).shuffle(shuffled)
    for row, feats in zip(train_rows, shuffled):
        shuffled_cache[row["sample_id"]] = feats

    def generated(row: dict[str, str]) -> list[float]:
        return generated_map_features(row, train_rows, dataset_rows)

    def logmel_generated(row: dict[str, str]) -> list[float]:
        return logmel_features(row) + generated(row)

    def shuffled_generated(row: dict[str, str]) -> list[float]:
        if row["sample_id"] in shuffled_cache:
            return shuffled_cache[row["sample_id"]]
        sid = sorted(shuffled_cache)[safe_hash(row["sample_id"]) % len(shuffled_cache)] if shuffled_cache else ""
        return shuffled_cache.get(sid, [0.0] * 15)

    return {
        "logmel_only": logmel_features,
        "handcrafted_audiodepth_v2": handcrafted_features,
        "generated_maps_only": generated,
        "logmel_plus_generated_maps": logmel_generated,
        "teacher_maps_upper_bound": lambda row: teacher_map_features(row, dataset_rows),
        "shuffled_generated_maps": shuffled_generated,
        "zero_maps": lambda row: [0.0] * 15,
    }


def safe_hash(text: str) -> int:
    return sum(ord(ch) for ch in text)


def evaluate_classification(
    train_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
    builder: Callable[[dict[str, str]], list[float]],
    labeler: Callable[[dict[str, str]], object],
    task_name: str,
    input_name: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    train_x = np.asarray([builder(row) for row in train_rows], dtype=np.float32)
    test_x = np.asarray([builder(row) for row in test_rows], dtype=np.float32)
    train_x, test_x = standardize(train_x, test_x)
    truth = [labeler(row) for row in test_rows]
    pred = nearest_neighbor_predict(train_x, [labeler(row) for row in train_rows], test_x, truth[0] if truth else "")
    metrics = classification_metrics(truth, pred)
    rows = [
        {
            "sample_id": row["sample_id"],
            "input_name": input_name,
            "task_name": task_name,
            "truth": truth[idx],
            "prediction": pred[idx],
        }
        for idx, row in enumerate(test_rows)
    ]
    return {"input_name": input_name, "task_name": task_name, **metrics}, rows


def evaluate_regret(
    train_rows: list[dict[str, str]],
    test_rows: list[dict[str, str]],
    builder: Callable[[dict[str, str]], list[float]],
    input_name: str,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    train_x = np.asarray([builder(row) for row in train_rows], dtype=np.float32)
    test_x = np.asarray([builder(row) for row in test_rows], dtype=np.float32)
    train_x, test_x = standardize(train_x, test_x)
    train_y = [true_regrets(row) for row in train_rows]
    pred_vecs = nearest_neighbor_predict(train_x, train_y, test_x, [0.0, 0.0, 0.0])
    truth_vecs = [true_regrets(row) for row in test_rows]
    truth = [v for vec in truth_vecs for v in vec]
    pred = [v for vec in pred_vecs for v in vec]
    metrics = regression_metrics(truth, pred)
    rows = []
    for idx, row in enumerate(test_rows):
        rows.append(
            {
                "sample_id": row["sample_id"],
                "input_name": input_name,
                "task_name": "route_regret_regression",
                "truth": "|".join(f"{x:.6f}" for x in truth_vecs[idx]),
                "prediction": "|".join(f"{float(x):.6f}" for x in pred_vecs[idx]),
            }
        )
    return {"input_name": input_name, "task_name": "route_regret_regression", **metrics}, rows


def main() -> None:
    dataset_rows = read_rows(TABLE_DIR / "generative_audiodepth_dataset.csv")
    train_rows = sorted({row["sample_id"]: row for row in read_rows(RELIABILITY_TRAIN)}.values(), key=lambda r: r["sample_id"])
    test_rows = sorted({row["sample_id"]: row for row in read_rows(RELIABILITY_TEST)}.values(), key=lambda r: r["sample_id"])
    builders = feature_builders(dataset_rows, train_rows)
    summary_rows: list[dict[str, object]] = []
    pred_rows: list[dict[str, object]] = []
    classification_tasks = {
        "oracle_route_classification": lambda row: row.get("oracle_route", "mixed"),
        "separation_helpful_binary": separation_helpful_label,
        "review_risk_detection": review_label,
        "route_gap_bucket_prediction": route_gap_bucket,
    }
    for input_name, builder in builders.items():
        for task_name, labeler in classification_tasks.items():
            result, rows = evaluate_classification(train_rows, test_rows, builder, labeler, task_name, input_name)
            summary_rows.append(result)
            pred_rows.extend(rows)
        result, rows = evaluate_regret(train_rows, test_rows, builder, input_name)
        summary_rows.append(result)
        pred_rows.extend(rows)
    write_csv(OUT_CSV, summary_rows)
    write_csv(PRED_CSV, pred_rows)
    chart_rows = [row for row in summary_rows if row["task_name"] == "review_risk_detection"]
    draw_bar_chart(OUT_PNG, "Generative AudioDepth information value: review-risk accuracy", chart_rows, "input_name", "accuracy")
    by_key = {(row["input_name"], row["task_name"]): row for row in summary_rows}
    gen_review = safe_float(by_key[("generated_maps_only", "review_risk_detection")].get("accuracy"))
    shuf_review = safe_float(by_key[("shuffled_generated_maps", "review_risk_detection")].get("accuracy"))
    logmel_review = safe_float(by_key[("logmel_only", "review_risk_detection")].get("accuracy"))
    combo_review = safe_float(by_key[("logmel_plus_generated_maps", "review_risk_detection")].get("accuracy"))
    teacher_review = safe_float(by_key[("teacher_maps_upper_bound", "review_risk_detection")].get("accuracy"))
    logmel_gap = safe_float(by_key[("logmel_only", "route_gap_bucket_prediction")].get("accuracy"))
    combo_gap = safe_float(by_key[("logmel_plus_generated_maps", "route_gap_bucket_prediction")].get("accuracy"))
    gen_gap = safe_float(by_key[("generated_maps_only", "route_gap_bucket_prediction")].get("accuracy"))
    shuf_gap = safe_float(by_key[("shuffled_generated_maps", "route_gap_bucket_prediction")].get("accuracy"))
    lines = [
        "# Generative AudioDepth Reliability Information Value",
        "",
        "A single nearest-neighbor probe is used across all inputs to avoid capacity differences.",
        "",
        f"- generated maps vs shuffled maps on review-risk: {gen_review:.6f} vs {shuf_review:.6f}",
        f"- logmel + generated maps vs logmel only on review-risk: {combo_review:.6f} vs {logmel_review:.6f}",
        f"- generated maps vs shuffled maps on route-gap buckets: {gen_gap:.6f} vs {shuf_gap:.6f}",
        f"- logmel + generated maps vs logmel only on route-gap buckets: {combo_gap:.6f} vs {logmel_gap:.6f}",
        f"- teacher-map upper bound vs generated maps on review-risk: {teacher_review:.6f} vs {gen_review:.6f}",
        "",
        "## Interpretation",
        "",
    ]
    if combo_review > logmel_review or combo_gap > logmel_gap or gen_review > shuf_review or gen_gap > shuf_gap:
        lines.append("Generated map summaries provide measurable weak information for at least one safety or generalization-facing probe.")
    else:
        lines.append("Generated maps are interpretable but currently provide little incremental predictive information beyond log-mel features.")
    lines.extend(
        [
            "",
            "The current probe should be read as a reliability screen, not as a final model comparison.",
        ]
    )
    write_markdown(OUT_MD, lines)
    write_input_audit(["Information-value probe completed with shared nearest-neighbor capacity."])
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
