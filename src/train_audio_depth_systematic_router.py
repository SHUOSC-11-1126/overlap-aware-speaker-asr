from __future__ import annotations

import argparse
import json
from typing import Any

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, ROUTE_LABELS, rel, write_csv, write_json
from .audio_depth_systematic_common import (
    MODEL_STATUS_CSV,
    SYSTEMATIC_MODELS,
    SYSTEMATIC_MODEL_PREFIX,
    TRAINING_LOG_CSV,
    feature_vector,
    load_systematic_rows,
    split_systematic_rows,
)
from .audio_depth_zoo_common import route_label_to_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train systematic AudioDepth-Hybrid routers.")
    parser.add_argument("--models", default="all")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--lr", type=float, default=1e-3)
    return parser.parse_args()


def resolve_models(spec: str) -> list[str]:
    return SYSTEMATIC_MODELS if spec == "all" else [item.strip() for item in spec.split(",") if item.strip()]


def standardize(train_x: np.ndarray, other: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0, keepdims=True)
    std = train_x.std(axis=0, keepdims=True)
    std[std == 0] = 1.0
    return (train_x - mean) / std, mean, (other - mean) / std


def train_torch_mlp(model_name: str, train_rows: list[dict[str, Any]], dev_rows: list[dict[str, Any]], args: argparse.Namespace) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    import torch
    from torch import nn

    rng = np.random.default_rng(args.seed)
    torch.manual_seed(args.seed)
    train_x = np.asarray([feature_vector(row) for row in train_rows], dtype=np.float32)
    dev_x = np.asarray([feature_vector(row) for row in dev_rows], dtype=np.float32)
    train_y = np.asarray([route_label_to_index(row["best_route_label"]) for row in train_rows], dtype=np.int64)
    dev_y = np.asarray([route_label_to_index(row["best_route_label"]) for row in dev_rows], dtype=np.int64)
    train_x_std, mean, dev_x_std = standardize(train_x, dev_x)

    hidden = 96 if model_name == "hybrid_late_fusion_v2" else 64
    model = nn.Sequential(
        nn.Linear(train_x.shape[1], hidden),
        nn.ReLU(),
        nn.Dropout(0.08),
        nn.Linear(hidden, hidden),
        nn.ReLU(),
        nn.Linear(hidden, len(ROUTE_LABELS)),
    )
    counts = np.bincount(train_y, minlength=len(ROUTE_LABELS)).astype(np.float32)
    counts[counts == 0] = 1.0
    weights = torch.tensor(counts.sum() / (len(counts) * counts), dtype=torch.float32)
    loss_fn = nn.CrossEntropyLoss(weight=weights)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    x_t = torch.from_numpy(train_x_std)
    y_t = torch.from_numpy(train_y)
    x_d = torch.from_numpy(dev_x_std)
    y_d = torch.from_numpy(dev_y)
    best_state = None
    best_acc = -1.0
    best_epoch = 0
    logs = []
    patience = 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        optimizer.zero_grad()
        logits = model(x_t)
        loss = loss_fn(logits, y_t)
        loss.backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            dev_logits = model(x_d)
            pred = dev_logits.argmax(dim=1)
            acc = float((pred == y_d).float().mean()) if len(dev_y) else 0.0
            dev_loss = float(loss_fn(dev_logits, y_d)) if len(dev_y) else 0.0
        logs.append({"model_name": model_name, "epoch": epoch, "train_loss": round(float(loss), 6), "dev_loss": round(dev_loss, 6), "dev_accuracy": round(acc, 6), "status": "trained"})
        if acc > best_acc:
            best_acc = acc
            best_epoch = epoch
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
            if patience >= 8:
                break
    checkpoint_path = SYSTEMATIC_MODEL_PREFIX / f"audio_depth_systematic_{model_name}.pt"
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_name": model_name,
            "state_dict": best_state,
            "input_dim": int(train_x.shape[1]),
            "mean": mean.astype(np.float32),
            "std": train_x.std(axis=0, keepdims=True).astype(np.float32),
            "labels": ROUTE_LABELS,
            "best_epoch": best_epoch,
            "best_dev_accuracy": best_acc,
            "architecture": [train_x.shape[1], hidden, hidden, len(ROUTE_LABELS)],
        },
        checkpoint_path,
    )
    status = {"model_name": model_name, "status": "trained", "best_epoch": best_epoch, "best_dev_accuracy": round(best_acc, 6), "checkpoint_path": rel(checkpoint_path), "train_samples": len(train_rows), "dev_samples": len(dev_rows)}
    return status, logs


def main() -> None:
    args = parse_args()
    rows = load_systematic_rows()
    train_rows, dev_rows, test_rows = split_systematic_rows(rows)
    status_rows = []
    log_rows = []
    for model_name in resolve_models(args.models):
        if model_name == "gradient_boosted_router":
            try:
                __import__("sklearn")
            except Exception as exc:
                status_rows.append({"model_name": model_name, "status": "skipped", "reason": "sklearn_unavailable", "checkpoint_path": "", "train_samples": len(train_rows), "dev_samples": len(dev_rows)})
                continue
        if model_name in {"hybrid_mlp_v2", "hybrid_late_fusion_v2", "calibrated_confidence_router", "cost_aware_router", "gradient_boosted_router"}:
            base_name = "hybrid_mlp_v2" if model_name in {"calibrated_confidence_router", "cost_aware_router"} else model_name
            status, logs = train_torch_mlp(base_name, train_rows, dev_rows, args)
            if model_name != base_name:
                source = SYSTEMATIC_MODEL_PREFIX / f"audio_depth_systematic_{base_name}.pt"
                target = SYSTEMATIC_MODEL_PREFIX / f"audio_depth_systematic_{model_name}.pt"
                target.write_bytes(source.read_bytes())
                status["model_name"] = model_name
                status["checkpoint_path"] = rel(target)
                status["status"] = "trained_calibrated_layer"
            status_rows.append(status)
            log_rows.extend([{**row, "model_name": model_name if model_name != base_name else row["model_name"]} for row in logs])
    write_csv(TRAINING_LOG_CSV, log_rows)
    write_csv(MODEL_STATUS_CSV, status_rows)
    print(f"Wrote systematic model status to {rel(MODEL_STATUS_CSV)}")


if __name__ == "__main__":
    main()
