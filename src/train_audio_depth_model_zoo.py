from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, ROUTE_LABELS, rel, summarize_counts, write_csv, write_json
from .audio_depth_zoo_common import (
    FEATURES_CSV,
    MODEL_NAMES,
    MODEL_STATUS_CSV,
    TRAINING_LOG_CSV,
    ZOO_DIR,
    build_hybrid_features_table,
    ensure_maps,
    feature_keys,
    load_hybrid_features,
    majority_label,
    route_label_to_index,
    safe_float,
)
from .audio_depth_zoo_models import build_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the AudioDepth model zoo.")
    parser.add_argument("--models", default="all", help="Comma-separated model list or 'all'.")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--patience", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def _stable_bucket(sample_id: str) -> int:
    return int(hashlib.sha1(sample_id.encode("utf-8")).hexdigest(), 16) % 5


def split_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    train_pool = [row for row in rows if row.get("split") == "dev"]
    test_rows = [row for row in rows if row.get("split") == "test"]
    train_rows = [row for row in train_pool if _stable_bucket(str(row["sample_id"])) != 0]
    val_rows = [row for row in train_pool if _stable_bucket(str(row["sample_id"])) == 0]
    if not train_rows:
        train_rows = train_pool[: max(1, len(train_pool) // 2)]
        val_rows = train_pool[max(1, len(train_pool) // 2) :]
    return train_rows, val_rows, test_rows


def resolve_models(spec: str) -> list[str]:
    if spec == "all":
        return MODEL_NAMES
    names = [name.strip() for name in spec.split(",") if name.strip()]
    unknown = [name for name in names if name not in MODEL_NAMES]
    if unknown:
        raise KeyError(f"Unknown zoo model(s): {', '.join(unknown)}")
    return names


def model_mode(model_name: str) -> str:
    if model_name == "mlp_handcrafted":
        return "tabular"
    if model_name == "cnn_logmel":
        return "logmel"
    if model_name == "analysis_upper_bound_cnn":
        return "analysis"
    return "deployable"


def needs_tabular(model_name: str) -> bool:
    return model_name in {"mlp_handcrafted", "hybrid_late_fusion"}


def load_matrix_rows(
    rows: list[dict[str, Any]],
    model_name: str,
    feature_names: list[str],
    mode: str,
) -> tuple[np.ndarray | None, np.ndarray | None, np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
    inputs = []
    tabs = []
    labels = []
    usable: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in rows:
        if model_name == "mlp_handcrafted":
            tab = np.asarray([safe_float(row.get(key), 0.0) for key in feature_names], dtype=np.float32)
            if not np.all(np.isfinite(tab)):
                tab = np.nan_to_num(tab, nan=0.0)
            tabs.append(tab)
            labels.append(route_label_to_index(row["best_route_label"]))
            usable.append(row)
            continue
        map_mode = mode
        if map_mode == "tabular":
            map_mode = "deployable"
        path = PROJECT_ROOT / f"resources/audio_depth_maps/{map_mode}/{row['sample_id']}.npy"
        if not path.exists():
            skipped.append({**row, "reason": "missing_map"})
            continue
        arr = np.load(path).astype(np.float32)
        inputs.append(arr)
        if needs_tabular(model_name):
            tab = np.asarray([safe_float(row.get(key), 0.0) for key in feature_names], dtype=np.float32)
            if not np.all(np.isfinite(tab)):
                tab = np.nan_to_num(tab, nan=0.0)
            tabs.append(tab)
        labels.append(route_label_to_index(row["best_route_label"]))
        usable.append(row)
    x = np.stack(inputs).astype(np.float32) if inputs else None
    t = np.stack(tabs).astype(np.float32) if tabs else None
    y = np.asarray(labels, dtype=np.int64)
    return x, t, y, usable, skipped


def class_weights_from_labels(y: np.ndarray) -> np.ndarray:
    counts = np.bincount(y, minlength=len(ROUTE_LABELS)).astype(np.float32)
    counts[counts == 0] = 1.0
    weights = counts.sum() / (len(counts) * counts)
    return weights.astype(np.float32)


def append_log(rows: list[dict[str, Any]], row: dict[str, Any]) -> None:
    rows.append(row)


def train_single_model(
    model_name: str,
    train_rows: list[dict[str, Any]],
    val_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    args: argparse.Namespace,
    feature_names: list[str],
    log_rows: list[dict[str, Any]],
    status_rows: list[dict[str, Any]],
) -> None:
    status = {
        "model_name": model_name,
        "mode": model_mode(model_name),
        "status": "pending",
        "reason": "",
        "best_epoch": 0,
        "best_val_accuracy": "",
        "best_val_loss": "",
        "train_samples": len(train_rows),
        "val_samples": len(val_rows),
        "test_samples": len(test_rows),
        "checkpoint_path": rel(ZOO_DIR / f"{model_name}.pt"),
    }
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, TensorDataset

        torch.manual_seed(args.seed)
        np.random.seed(args.seed)

        mode = model_mode(model_name)
        required_modes = [] if mode == "tabular" else [mode]
        if model_name == "hybrid_late_fusion":
            required_modes = ["deployable"]
        for required_mode in required_modes:
            ensure_maps(required_mode, train_rows + val_rows + test_rows, overwrite=args.overwrite)

        x_train, t_train, y_train, train_usable, skipped_train = load_matrix_rows(train_rows, model_name, feature_names, mode)
        x_val, t_val, y_val, val_usable, skipped_val = load_matrix_rows(val_rows, model_name, feature_names, mode)
        x_test, t_test, y_test, test_usable, skipped_test = load_matrix_rows(test_rows, model_name, feature_names, mode)
        skipped = skipped_train + skipped_val + skipped_test
        if len(train_usable) < 4 or len(set(y_train.tolist())) < 2:
            status.update({"status": "skipped", "reason": "insufficient_training_diversity"})
            write_json(ZOO_DIR / f"{model_name}.pt", status)
            status_rows.append(status)
            return

        input_channels = int(x_train.shape[1]) if x_train is not None else 0
        tabular_dim = int(t_train.shape[1]) if t_train is not None else len(feature_names)
        model = build_model(model_name, input_channels=input_channels or 3, tabular_dim=tabular_dim)
        device = torch.device("cpu")
        model.to(device)

        if model_name == "mlp_handcrafted":
            train_dataset = TensorDataset(torch.from_numpy(t_train), torch.from_numpy(y_train))
            val_dataset = TensorDataset(torch.from_numpy(t_val), torch.from_numpy(y_val)) if len(y_val) else None
            test_dataset = TensorDataset(torch.from_numpy(t_test), torch.from_numpy(y_test)) if len(y_test) else None
        elif model_name == "hybrid_late_fusion":
            train_dataset = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(t_train), torch.from_numpy(y_train))
            val_dataset = TensorDataset(torch.from_numpy(x_val), torch.from_numpy(t_val), torch.from_numpy(y_val)) if len(y_val) else None
            test_dataset = TensorDataset(torch.from_numpy(x_test), torch.from_numpy(t_test), torch.from_numpy(y_test)) if len(y_test) else None
        else:
            train_dataset = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train))
            val_dataset = TensorDataset(torch.from_numpy(x_val), torch.from_numpy(y_val)) if len(y_val) else None
            test_dataset = TensorDataset(torch.from_numpy(x_test), torch.from_numpy(y_test)) if len(y_test) else None

        generator = torch.Generator().manual_seed(args.seed)
        train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, generator=generator)
        val_loader = DataLoader(val_dataset, batch_size=args.batch_size) if val_dataset is not None else None
        test_loader = DataLoader(test_dataset, batch_size=args.batch_size) if test_dataset is not None else None

        class_weight_tensor = None
        if model_name == "cnn_depth_balanced":
            class_weight_tensor = torch.tensor(class_weights_from_labels(y_train), dtype=torch.float32)
        criterion = nn.CrossEntropyLoss(weight=class_weight_tensor)
        optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
        best_state = None
        best_epoch = 0
        best_val_accuracy = -1.0
        best_val_loss = float("inf")
        patience = 0

        def forward_batch(batch: tuple[torch.Tensor, ...]) -> tuple[torch.Tensor, torch.Tensor]:
            if model_name == "mlp_handcrafted":
                tab, y = batch
                logits = model(tab.to(device))
                return logits, y.to(device)
            if model_name == "hybrid_late_fusion":
                x, tab, y = batch
                logits = model(x.to(device), tab.to(device))
                return logits, y.to(device)
            x, y = batch
            logits = model(x.to(device))
            return logits, y.to(device)

        def evaluate(loader: DataLoader | None) -> tuple[float, float, list[int], list[int]]:
            if loader is None:
                return 0.0, 0.0, [], []
            model.eval()
            total_loss = 0.0
            total = 0
            preds: list[int] = []
            gold: list[int] = []
            with torch.no_grad():
                for batch in loader:
                    logits, y = forward_batch(batch)
                    loss = criterion(logits, y)
                    total_loss += float(loss.item()) * len(y)
                    total += len(y)
                    pred = logits.argmax(dim=1)
                    preds.extend(pred.cpu().tolist())
                    gold.extend(y.cpu().tolist())
            accuracy = sum(int(a == b) for a, b in zip(preds, gold)) / len(gold) if gold else 0.0
            return total_loss / total if total else 0.0, accuracy, preds, gold

        for epoch in range(1, args.epochs + 1):
            model.train()
            losses: list[float] = []
            for batch in train_loader:
                optimizer.zero_grad()
                logits, y = forward_batch(batch)
                loss = criterion(logits, y)
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach().cpu()))
            train_loss = float(np.mean(losses)) if losses else 0.0
            val_loss, val_acc, _, _ = evaluate(val_loader)
            log_rows.append(
                {
                    "model_name": model_name,
                    "mode": mode,
                    "epoch": epoch,
                    "train_loss": round(train_loss, 6),
                    "val_loss": round(val_loss, 6),
                    "val_accuracy": round(val_acc, 6),
                    "status": "trained",
                }
            )
            if val_acc > best_val_accuracy or (math.isclose(val_acc, best_val_accuracy) and val_loss < best_val_loss):
                best_val_accuracy = val_acc
                best_val_loss = val_loss
                best_epoch = epoch
                best_state = {
                    "model_name": model_name,
                    "mode": mode,
                    "input_channels": int(input_channels or 3),
                    "tabular_dim": int(tabular_dim),
                    "feature_names": feature_names,
                    "state_dict": model.state_dict(),
                    "best_epoch": best_epoch,
                    "best_val_accuracy": best_val_accuracy,
                    "best_val_loss": best_val_loss,
                    "class_weights": class_weight_tensor.tolist() if class_weight_tensor is not None else None,
                    "skipped_rows": len(skipped),
                }
                patience = 0
            else:
                patience += 1
                if patience >= args.patience:
                    break

        if best_state is None:
            raise RuntimeError("training finished without a valid checkpoint")

        ZOO_DIR.mkdir(parents=True, exist_ok=True)
        model_path = ZOO_DIR / f"{model_name}.pt"
        torch.save(best_state, model_path)
        test_loss, test_acc, test_preds, test_gold = evaluate(test_loader)
        status.update(
            {
                "status": "trained",
                "reason": f"early_stopped_at_epoch_{best_epoch}",
                "best_epoch": best_epoch,
                "best_val_accuracy": round(best_val_accuracy, 6),
                "best_val_loss": round(best_val_loss, 6),
                "test_accuracy": round(test_acc, 6),
                "test_loss": round(test_loss, 6),
                "test_prediction_distribution": json.dumps({label: test_preds.count(i) for i, label in enumerate(ROUTE_LABELS)}),
                "train_label_distribution": json.dumps(summarize_counts(train_usable, "best_route_label")),
                "val_label_distribution": json.dumps(summarize_counts(val_usable, "best_route_label")),
                "test_label_distribution": json.dumps(summarize_counts(test_usable, "best_route_label")),
                "skipped_rows": len(skipped),
            }
        )
        status_rows.append(status)
    except Exception as exc:
        ZOO_DIR.mkdir(parents=True, exist_ok=True)
        model_path = ZOO_DIR / f"{model_name}.pt"
        write_json(model_path, {"model_name": model_name, "status": "failed", "error": str(exc), **status})
        status.update({"status": "failed", "reason": str(exc)})
        status_rows.append(status)
        log_rows.append(
            {
                "model_name": model_name,
                "mode": model_mode(model_name),
                "epoch": 0,
                "train_loss": "",
                "val_loss": "",
                "val_accuracy": "",
                "status": f"failed:{exc}",
            }
        )


def main() -> None:
    args = parse_args()
    model_names = resolve_models(args.models)
    rows = load_hybrid_features() if FEATURES_CSV.exists() else build_hybrid_features_table()
    train_rows, val_rows, test_rows = split_rows(rows)
    feature_names = feature_keys()
    log_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    for model_name in model_names:
        train_single_model(model_name, train_rows, val_rows, test_rows, args, feature_names, log_rows, status_rows)
    write_csv(TRAINING_LOG_CSV, log_rows, ["model_name", "mode", "epoch", "train_loss", "val_loss", "val_accuracy", "status"])
    write_csv(
        MODEL_STATUS_CSV,
        status_rows,
        [
            "model_name",
            "mode",
            "status",
            "reason",
            "best_epoch",
            "best_val_accuracy",
            "best_val_loss",
            "test_accuracy",
            "test_loss",
            "train_samples",
            "val_samples",
            "test_samples",
            "checkpoint_path",
            "skipped_rows",
            "test_prediction_distribution",
            "train_label_distribution",
            "val_label_distribution",
            "test_label_distribution",
        ],
    )
    print(f"Trained {len(model_names)} AudioDepth zoo models; logs in {rel(TRAINING_LOG_CSV)}")


if __name__ == "__main__":
    main()
