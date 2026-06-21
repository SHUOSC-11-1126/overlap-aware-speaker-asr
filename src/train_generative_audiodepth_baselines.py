from __future__ import annotations

import json
from collections import Counter
from typing import Any

import numpy as np

from .generative_audiodepth_common import (
    DATASET_CSV,
    MAP_TASKS,
    MODEL_DIR,
    ROUTES,
    TEST_CSV,
    TRAIN_CSV,
    VALIDATION_CSV,
    load_npy,
    read_rows,
    safe_float,
    unique_samples,
    write_csv,
)
from .generative_audiodepth_models import (
    build_promptable_prototype,
    direct_regret_predict,
    direct_route_classifier_predict,
    select_route_from_regret,
)


TRAINING_LOG = "results/tables/generative_audiodepth_training_log.csv"
MODEL_STATUS = "results/tables/generative_audiodepth_model_status.csv"
BASELINE_PERFORMANCE = "results/tables/generative_audiodepth_baseline_performance.csv"


def cer_for_route(row: dict[str, Any], route: str) -> float:
    return safe_float(row.get(f"{route}_cer"), 1.0)


def evaluate_direct_classifier(train_samples: list[dict[str, Any]], eval_samples: list[dict[str, Any]]) -> dict[str, Any]:
    preds = []
    for row in eval_samples:
        route = direct_route_classifier_predict(row, train_samples)
        preds.append((row, route))
    acc = np.mean([route == row["oracle_route"] for row, route in preds]) if preds else 0.0
    avg_cer = np.mean([cer_for_route(row, route) for row, route in preds]) if preds else 0.0
    oracle = np.mean([safe_float(row.get("mixed_cer")) - safe_float(row.get("mixed_regret")) for row, _ in preds]) if preds else 0.0
    return {
        "model_name": "logmel_direct_classifier",
        "split": "test",
        "route_accuracy": round(float(acc), 6),
        "selected_route_cer": round(float(avg_cer), 6),
        "oracle_gap": round(float(avg_cer - oracle), 6),
        "map_mae": "",
        "sample_count": len(preds),
    }


def evaluate_regret_model(train_samples: list[dict[str, Any]], eval_samples: list[dict[str, Any]], model_name: str) -> dict[str, Any]:
    preds = []
    for row in eval_samples:
        regrets = direct_regret_predict(row, train_samples)
        route = select_route_from_regret(regrets)
        preds.append((row, route, regrets))
    acc = np.mean([route == row["oracle_route"] for row, route, _ in preds]) if preds else 0.0
    avg_cer = np.mean([cer_for_route(row, route) for row, route, _ in preds]) if preds else 0.0
    oracle = np.mean([min(cer_for_route(row, route) for route in ROUTES) for row, _, _ in preds]) if preds else 0.0
    mae = np.mean(
        [
            np.mean(
                np.abs(
                    pred
                    - np.asarray(
                        [safe_float(row.get("mixed_regret")), safe_float(row.get("separated_regret")), safe_float(row.get("cleaned_regret"))],
                        dtype=np.float32,
                    )
                )
            )
            for row, _, pred in preds
        ]
    ) if preds else 0.0
    return {
        "model_name": model_name,
        "split": "test",
        "route_accuracy": round(float(acc), 6),
        "selected_route_cer": round(float(avg_cer), 6),
        "oracle_gap": round(float(avg_cer - oracle), 6),
        "regret_mae": round(float(mae), 6),
        "map_mae": "",
        "sample_count": len(preds),
    }


def evaluate_map_generation(train_task_rows: list[dict[str, Any]], eval_task_rows: list[dict[str, Any]], eval_samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    train_samples = unique_samples(train_task_rows)
    model = build_promptable_prototype(train_samples, train_task_rows, load_npy)
    unconditioned_mae = []
    promptable_mae = []
    for row in eval_task_rows:
        if row["target_task"] not in MAP_TASKS:
            continue
        target = load_npy(row["target_path"])
        prompt_pred = model.predict(row, row["target_task"])
        global_pred = model.global_map[row["target_task"]]
        promptable_mae.append(float(np.mean(np.abs(prompt_pred - target))))
        unconditioned_mae.append(float(np.mean(np.abs(global_pred - target))))
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "generative_audiodepth_promptable_prototype.pt"
    payload = {
        "model_type": "promptable_prototype_no_torch",
        "tasks": sorted(MAP_TASKS),
        "train_samples": len(train_samples),
        "note": "Dependency-light prototype. Future work can replace this interface with a small U-Net.",
    }
    model_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return [
        {
            "model_name": "map_generation_unconditioned",
            "split": "test",
            "route_accuracy": "",
            "selected_route_cer": "",
            "oracle_gap": "",
            "regret_mae": "",
            "map_mae": round(float(np.mean(unconditioned_mae)), 6) if unconditioned_mae else 0.0,
            "sample_count": len(eval_samples),
        },
        {
            "model_name": "promptable_map_generator",
            "split": "test",
            "route_accuracy": "",
            "selected_route_cer": "",
            "oracle_gap": "",
            "regret_mae": "",
            "map_mae": round(float(np.mean(promptable_mae)), 6) if promptable_mae else 0.0,
            "sample_count": len(eval_samples),
        },
    ]


def main() -> None:
    all_rows = read_rows(DATASET_CSV)
    train_rows = read_rows(TRAIN_CSV)
    validation_rows = read_rows(VALIDATION_CSV)
    test_rows = read_rows(TEST_CSV)
    train_samples = unique_samples(train_rows)
    eval_samples = unique_samples(test_rows or validation_rows)
    eval_task_rows = test_rows or validation_rows
    perf = [
        evaluate_direct_classifier(train_samples, eval_samples),
        evaluate_regret_model(train_samples, eval_samples, "multitask_direct_model"),
    ]
    perf.extend(evaluate_map_generation(train_rows, eval_task_rows, eval_samples))
    logs = [
        {
            "model_name": row["model_name"],
            "epoch": 0,
            "train_samples": len(train_samples),
            "validation_samples": len(unique_samples(validation_rows)),
            "test_samples": len(eval_samples),
            "status": "deterministic_prototype_completed",
        }
        for row in perf
    ]
    status = [
        {
            "model_name": "promptable_map_generator",
            "status": "prototype_trained",
            "model_path": "models/generative_audiodepth_promptable_prototype.pt",
            "evidence_label": "controlled_silver_plus_frontier",
            "task_distribution": dict(Counter(row["target_task"] for row in all_rows)),
        }
    ]
    write_csv(__import__("pathlib").Path(TRAINING_LOG), logs)
    write_csv(__import__("pathlib").Path(MODEL_STATUS), status)
    write_csv(__import__("pathlib").Path(BASELINE_PERFORMANCE), perf)
    print(f"Wrote {len(perf)} Generative AudioDepth baseline rows")


if __name__ == "__main__":
    main()
