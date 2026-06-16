from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, ROUTE_LABELS, read_csv, rel, write_csv
from .audio_depth_systematic_common import stable_bucket, safe_float
from .controlled_benchmark_common import CER_CSV, MODEL_DIR


TRAINING_LOG = PROJECT_ROOT / "results" / "tables" / "controlled_audio_depth_training_log.csv"
MODEL_STATUS = PROJECT_ROOT / "results" / "tables" / "controlled_audio_depth_model_status.csv"


def features(row: dict[str, str]) -> list[float]:
    ratio = safe_float(row["overlap_ratio"])
    return [
        ratio,
        safe_float(row["mixed_cer"]) - safe_float(row["separated_cer"]),
        safe_float(row["mixed_cer"]) - safe_float(row["cleaned_cer"]),
        1.0 if row.get("dominance_type") == "balanced" else 0.0,
        1.0 if "dominant" in row.get("dominance_type", "") else 0.0,
        safe_float(row["route_gap"]),
        safe_float(row["separation_gain"]),
    ]


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x, axis=1, keepdims=True)
    exp = np.exp(x)
    return exp / np.sum(exp, axis=1, keepdims=True)


def train_linear(name: str, train_rows: list[dict[str, str]], test_rows: list[dict[str, str]]) -> tuple[dict, list[dict]]:
    x = np.asarray([features(row) for row in train_rows], dtype=np.float32)
    y = np.asarray([ROUTE_LABELS.index(row["oracle_route"]) for row in train_rows], dtype=np.int64)
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std == 0] = 1.0
    x = (x - mean) / std
    w = np.zeros((x.shape[1], len(ROUTE_LABELS)), dtype=np.float32)
    b = np.zeros(len(ROUTE_LABELS), dtype=np.float32)
    lr = 0.08
    logs = []
    for epoch in range(1, 121):
        probs = softmax(x @ w + b)
        grad = probs
        grad[np.arange(len(y)), y] -= 1
        grad /= len(y)
        w -= lr * x.T @ grad
        b -= lr * grad.sum(axis=0)
        if epoch in {1, 20, 60, 120}:
            pred = np.argmax(probs, axis=1)
            logs.append({"model_name": name, "epoch": epoch, "train_accuracy": round(float(np.mean(pred == y)), 6)})
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / f"audio_depth_controlled_{name}.json"
    model_path.write_text(json.dumps({"weights": w.tolist(), "bias": b.tolist(), "mean": mean.tolist(), "std": std.tolist(), "labels": ROUTE_LABELS}, indent=2), encoding="utf-8")
    tx = np.asarray([features(row) for row in test_rows], dtype=np.float32)
    tx = (tx - mean) / std
    pred = np.argmax(softmax(tx @ w + b), axis=1) if len(test_rows) else []
    cer = []
    acc = []
    for row, idx in zip(test_rows, pred):
        route = ROUTE_LABELS[int(idx)]
        cer.append(safe_float(row[f"{route}_cer"]))
        acc.append(1.0 if route == row["oracle_route"] else 0.0)
    status = {
        "model_name": name,
        "status": "trained",
        "train_samples": len(train_rows),
        "test_samples": len(test_rows),
        "test_average_cer": round(float(np.mean(cer)), 6) if cer else "",
        "test_route_accuracy": round(float(np.mean(acc)), 6) if acc else "",
        "model_path": rel(model_path),
    }
    return status, logs


def main() -> None:
    rows = read_csv(CER_CSV)
    train = [row for row in rows if stable_bucket(row["sample_id"], 100) < 70]
    test = [row for row in rows if row not in train]
    statuses = []
    logs = []
    for name in ["hybrid_mlp_controlled", "hybrid_late_fusion_controlled", "calibrated_confidence_controlled", "cost_aware_controlled"]:
        status, model_logs = train_linear(name, train, test)
        statuses.append(status)
        logs.extend(model_logs)
    write_csv(TRAINING_LOG, logs)
    write_csv(MODEL_STATUS, statuses)
    print(f"Wrote controlled model status to {rel(MODEL_STATUS)}")


if __name__ == "__main__":
    main()
