from __future__ import annotations

import numpy as np


def bce_loss(pred: np.ndarray, target: np.ndarray, eps: float = 1e-7) -> float:
    pred = np.clip(np.asarray(pred, dtype=np.float32), eps, 1.0 - eps)
    target = np.asarray(target, dtype=np.float32)
    return float(-np.mean(target * np.log(pred) + (1.0 - target) * np.log(1.0 - pred)))


def smooth_l1(pred: np.ndarray, target: np.ndarray, beta: float = 1.0) -> float:
    diff = np.abs(np.asarray(pred, dtype=np.float32) - np.asarray(target, dtype=np.float32))
    loss = np.where(diff < beta, 0.5 * diff * diff / beta, diff - 0.5 * beta)
    return float(np.mean(loss))


def dice_loss(pred: np.ndarray, target: np.ndarray, eps: float = 1e-6) -> float:
    pred = np.asarray(pred, dtype=np.float32)
    target = np.asarray(target, dtype=np.float32)
    intersection = float(np.sum(pred * target))
    denom = float(np.sum(pred) + np.sum(target))
    return 1.0 - (2.0 * intersection + eps) / (denom + eps)


def pairwise_ranking_loss(pred_regret: np.ndarray, true_regret: np.ndarray, margin: float = 0.02) -> float:
    pred = np.asarray(pred_regret, dtype=np.float32)
    true = np.asarray(true_regret, dtype=np.float32)
    losses = []
    for i in range(len(true)):
        for j in range(len(true)):
            if true[i] + margin < true[j]:
                losses.append(max(0.0, margin - float(pred[j] - pred[i])))
    return float(np.mean(losses)) if losses else 0.0


def consistency_loss(pred_a: np.ndarray, pred_b: np.ndarray) -> float:
    return smooth_l1(pred_a, pred_b)


def multitask_loss(parts: dict[str, float], weights: dict[str, float] | None = None) -> float:
    weights = weights or {}
    return float(sum(value * weights.get(name, 1.0) for name, value in parts.items()))
