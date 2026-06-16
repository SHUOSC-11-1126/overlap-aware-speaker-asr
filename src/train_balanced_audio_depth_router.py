from __future__ import annotations

import json

import numpy as np

from .audio_depth_router_common import ROUTE_LABELS, rel, write_csv
from .audio_depth_systematic_common import safe_float, stable_bucket
from .balanced_v2_common import BALANCED_STATUS, BALANCED_TRAINING_LOG, MODEL_DIR, V2_CER


def features(row: dict[str, str]) -> list[float]:
    family = row.get("intended_family", "")
    return [
        safe_float(row["overlap_ratio"]),
        safe_float(row["mixed_cer"]) - safe_float(row["separated_cer"]),
        safe_float(row["mixed_cer"]) - safe_float(row["cleaned_cer"]),
        safe_float(row["route_gap"]),
        1.0 if family == "mixed_win_anchor" else 0.0,
        1.0 if family == "separated_win_anchor" else 0.0,
        1.0 if family == "cleaned_win_anchor" else 0.0,
        1.0 if family == "review_needed_anchor" else 0.0,
        1.0 if row.get("dominance_type") == "balanced" else 0.0,
    ]


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x, axis=1, keepdims=True)
    exp = np.exp(x)
    return exp / np.sum(exp, axis=1, keepdims=True)


def main() -> None:
    rows = [row for row in __import__("src.audio_depth_router_common", fromlist=["read_csv"]).read_csv(V2_CER)]
    train = [row for row in rows if stable_bucket(row["sample_id"], 100) < 70]
    test = [row for row in rows if row not in train] or rows
    x = np.asarray([features(row) for row in train], dtype=np.float32)
    y = np.asarray([ROUTE_LABELS.index(row["oracle_route"]) for row in train], dtype=np.int64)
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std == 0] = 1.0
    x = (x - mean) / std
    w = np.zeros((x.shape[1], len(ROUTE_LABELS)), dtype=np.float32)
    b = np.zeros(len(ROUTE_LABELS), dtype=np.float32)
    logs = []
    for epoch in range(1, 151):
        probs = softmax(x @ w + b)
        grad = probs.copy()
        grad[np.arange(len(y)), y] -= 1.0
        grad /= max(len(y), 1)
        w -= 0.07 * x.T @ grad
        b -= 0.07 * grad.sum(axis=0)
        if epoch in {1, 25, 75, 150}:
            logs.append({"model_name": "balanced_route_winner_router", "epoch": epoch, "train_route_accuracy": round(float(np.mean(np.argmax(probs, axis=1) == y)), 6)})
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "audio_depth_balanced_route_winner_router.json"
    model_path.write_text(json.dumps({"weights": w.tolist(), "bias": b.tolist(), "mean": mean.tolist(), "std": std.tolist(), "labels": ROUTE_LABELS}, indent=2), encoding="utf-8")
    tx = (np.asarray([features(row) for row in test], dtype=np.float32) - mean) / std
    pred = np.argmax(softmax(tx @ w + b), axis=1)
    status = {
        "model_name": "balanced_route_winner_router",
        "status": "trained",
        "train_samples": len(train),
        "heldout_samples": len(test),
        "heldout_route_accuracy": round(float(np.mean([ROUTE_LABELS[int(idx)] == row["oracle_route"] for row, idx in zip(test, pred)])), 6),
        "model_path": rel(model_path),
        "evidence_label": "frontier_real_whisper_silver_plus_unverified",
    }
    write_csv(BALANCED_TRAINING_LOG, logs)
    write_csv(BALANCED_STATUS, [status])
    print(f"Wrote balanced router model to {rel(model_path)}")


if __name__ == "__main__":
    main()
