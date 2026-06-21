from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .generative_audiodepth_common import MAP_TASKS, ROUTES, TASKS, VECTOR_TASKS, feature_vector, nearest_index


TASK_TO_INDEX = {task: idx for idx, task in enumerate(TASKS)}


@dataclass
class PromptablePrototypeModel:
    """Tiny prompt-conditioned prototype model for Stage-32 first closure.

    This is intentionally not a large neural generator. It provides the same
    interface a future U-Net or patch transformer should obey while remaining
    deterministic and dependency-light for the first evidence pass.
    """

    train_features: np.ndarray
    map_targets: dict[str, list[np.ndarray]]
    vector_targets: dict[str, list[np.ndarray]]
    global_map: dict[str, np.ndarray]
    global_vector: dict[str, np.ndarray]

    def predict(self, mixed_feature_row: dict[str, Any], task_token: str) -> np.ndarray:
        if task_token not in TASK_TO_INDEX:
            raise ValueError(f"Unknown task token: {task_token}")
        query = feature_vector(mixed_feature_row)
        idx = nearest_index(self.train_features, query)
        if task_token in MAP_TASKS:
            targets = self.map_targets.get(task_token, [])
            if idx < len(targets):
                return targets[idx].astype(np.float32)
            return self.global_map[task_token].astype(np.float32)
        if task_token in VECTOR_TASKS:
            targets = self.vector_targets.get(task_token, [])
            if idx < len(targets):
                return targets[idx].astype(np.float32)
            return self.global_vector[task_token].astype(np.float32)
        raise ValueError(f"Unsupported task token: {task_token}")


def direct_route_classifier_predict(row: dict[str, Any], train_rows: list[dict[str, Any]]) -> str:
    """Nearest-neighbor direct route classifier using mixed-only metadata."""
    if not train_rows:
        return "mixed"
    train_x = np.stack([feature_vector(r) for r in train_rows])
    idx = nearest_index(train_x, feature_vector(row))
    route = train_rows[idx].get("oracle_route", "mixed")
    return route if route in ROUTES else "mixed"


def direct_regret_predict(row: dict[str, Any], train_rows: list[dict[str, Any]]) -> np.ndarray:
    """Nearest-neighbor sample-level regret predictor using mixed-only metadata."""
    if not train_rows:
        return np.zeros(3, dtype=np.float32)
    train_x = np.stack([feature_vector(r) for r in train_rows])
    idx = nearest_index(train_x, feature_vector(row))
    source = train_rows[idx]
    return np.asarray(
        [float(source.get("mixed_regret", 0.0)), float(source.get("separated_regret", 0.0)), float(source.get("cleaned_regret", 0.0))],
        dtype=np.float32,
    )


def build_promptable_prototype(train_sample_rows: list[dict[str, Any]], train_task_rows: list[dict[str, Any]], loader) -> PromptablePrototypeModel:
    features = np.stack([feature_vector(row) for row in train_sample_rows]) if train_sample_rows else np.zeros((0, 10), dtype=np.float32)
    by_sample = {row["sample_id"]: idx for idx, row in enumerate(train_sample_rows)}
    map_targets: dict[str, list[np.ndarray]] = {task: [np.zeros((64, 96), dtype=np.float32) for _ in train_sample_rows] for task in MAP_TASKS}
    vector_targets: dict[str, list[np.ndarray]] = {task: [np.zeros(3, dtype=np.float32) for _ in train_sample_rows] for task in VECTOR_TASKS}
    for row in train_task_rows:
        idx = by_sample.get(row["sample_id"])
        if idx is None:
            continue
        task = row["target_task"]
        arr = loader(row["target_path"])
        if task in MAP_TASKS:
            map_targets[task][idx] = arr.astype(np.float32)
        elif task in VECTOR_TASKS:
            vector_targets[task][idx] = arr.astype(np.float32)
    global_map = {
        task: (np.mean(np.stack(values), axis=0).astype(np.float32) if values else np.zeros((64, 96), dtype=np.float32))
        for task, values in map_targets.items()
    }
    global_vector = {
        task: (np.mean(np.stack(values), axis=0).astype(np.float32) if values else np.zeros(3, dtype=np.float32))
        for task, values in vector_targets.items()
    }
    return PromptablePrototypeModel(features, map_targets, vector_targets, global_map, global_vector)


def select_route_from_regret(regrets: np.ndarray, cost_weight: float = 0.0) -> str:
    costs = np.asarray([1.0, 1.8, 2.0], dtype=np.float32)
    idx = int(np.argmin(np.asarray(regrets, dtype=np.float32) + cost_weight * costs))
    return ROUTES[idx]
