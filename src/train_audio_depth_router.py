from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_map import generate_one, load_or_build_dataset
from .audio_depth_router_common import PROJECT_ROOT, ROUTE_LABELS, rel, summarize_counts, write_csv, write_json


LOG_PATH = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_training_log.csv"
DIAGNOSTIC_PATH = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_training_diagnostic.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a lightweight AudioDepth-Router CNN.")
    parser.add_argument("--mode", default="deployable", choices=["deployable", "analysis", "logmel"])
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def ensure_maps(rows: list[dict[str, str]], mode: str) -> None:
    source_mode = "deployable" if mode == "logmel" else mode
    for row in rows:
        path = PROJECT_ROOT / f"resources/audio_depth_maps/{source_mode}/{row['sample_id']}.npy"
        if not path.exists():
            generate_one(row, source_mode, preview=False)


def load_arrays(rows: list[dict[str, str]], mode: str) -> tuple[np.ndarray, np.ndarray, list[dict[str, str]]]:
    source_mode = "deployable" if mode == "logmel" else mode
    usable = []
    arrays = []
    labels = []
    for row in rows:
        path = PROJECT_ROOT / f"resources/audio_depth_maps/{source_mode}/{row['sample_id']}.npy"
        if not path.exists():
            continue
        arr = np.load(path).astype(np.float32)
        if mode == "logmel":
            arr = arr[:1]
        arrays.append(arr)
        labels.append(ROUTE_LABELS.index(row["best_route_label"]))
        usable.append(row)
    if not arrays:
        return np.empty((0, 3, 64, 96), dtype=np.float32), np.empty((0,), dtype=np.int64), []
    return np.stack(arrays), np.asarray(labels, dtype=np.int64), usable


def split_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    train = [row for row in rows if row.get("split") == "dev"]
    eval_rows = [row for row in rows if row.get("split") == "test"]
    if not train or not eval_rows:
        train = [row for row in rows if row.get("split") == "train"]
        eval_rows = [row for row in rows if row.get("split") in {"dev", "test"}]
    return train, eval_rows


def write_missing_torch_diagnostic(mode: str, rows: list[dict[str, str]], error: Exception) -> None:
    model_path = PROJECT_ROOT / "models" / f"audio_depth_router_{mode}.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "mode": mode,
        "training_status": "diagnostic_only",
        "reason": "torch_unavailable",
        "error": str(error),
        "sample_count": len(rows),
        "label_counts": summarize_counts(rows, "best_route_label"),
        "note": "PyTorch is required for the requested CNN. Maps and labels were generated; install torch to train the CNN.",
    }
    model_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_json(DIAGNOSTIC_PATH, payload)
    write_csv(
        LOG_PATH,
        [{"mode": mode, "epoch": 0, "train_loss": "", "eval_accuracy": "", "status": "diagnostic_only"}],
        ["mode", "epoch", "train_loss", "eval_accuracy", "status"],
    )


def train_torch(args: argparse.Namespace, x_train: np.ndarray, y_train: np.ndarray, x_eval: np.ndarray, y_eval: np.ndarray) -> list[dict[str, Any]]:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset

    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)

    class AudioDepthCNN(nn.Module):
        def __init__(self, channels: int) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Conv2d(channels, 8, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(2),
                nn.Conv2d(8, 16, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.AdaptiveAvgPool2d((4, 4)),
                nn.Flatten(),
                nn.Linear(16 * 4 * 4, len(ROUTE_LABELS)),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x)

    device = torch.device("cpu")
    model = AudioDepthCNN(x_train.shape[1]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()
    dataset = TensorDataset(torch.from_numpy(x_train), torch.from_numpy(y_train))
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    x_eval_t = torch.from_numpy(x_eval).to(device)
    y_eval_t = torch.from_numpy(y_eval).to(device)
    logs: list[dict[str, Any]] = []
    for epoch in range(1, args.epochs + 1):
        model.train()
        losses = []
        for batch_x, batch_y in loader:
            optimizer.zero_grad()
            logits = model(batch_x.to(device))
            loss = loss_fn(logits, batch_y.to(device))
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        model.eval()
        with torch.no_grad():
            pred = model(x_eval_t).argmax(dim=1)
            accuracy = float((pred == y_eval_t).float().mean().cpu()) if len(y_eval_t) else 0.0
        logs.append(
            {
                "mode": args.mode,
                "epoch": epoch,
                "train_loss": round(float(np.mean(losses)), 6) if losses else "",
                "eval_accuracy": round(accuracy, 6),
                "status": "trained",
            }
        )
    model_path = PROJECT_ROOT / "models" / f"audio_depth_router_{args.mode}.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "mode": args.mode,
            "state_dict": model.state_dict(),
            "input_channels": int(x_train.shape[1]),
            "labels": ROUTE_LABELS,
        },
        model_path,
    )
    return logs


def main() -> None:
    args = parse_args()
    rows = load_or_build_dataset("deployable" if args.mode == "logmel" else args.mode)
    rows = [row for row in rows if row.get("split") in {"dev", "test", "train"}]
    train_rows, eval_rows = split_rows(rows)
    ensure_maps(train_rows + eval_rows, args.mode)
    x_train, y_train, train_rows = load_arrays(train_rows, args.mode)
    x_eval, y_eval, eval_rows = load_arrays(eval_rows, args.mode)
    if len(train_rows) < 3 or len(set(y_train.tolist())) < 2:
        write_missing_torch_diagnostic(args.mode, rows, RuntimeError("insufficient labeled training diversity"))
        print(f"Training diagnostic written for {args.mode}: insufficient samples")
        return
    try:
        logs = train_torch(args, x_train, y_train, x_eval, y_eval)
        write_csv(LOG_PATH, logs, ["mode", "epoch", "train_loss", "eval_accuracy", "status"])
        write_csv(
            PROJECT_ROOT / "results" / "tables" / f"audio_depth_router_training_log_{args.mode}.csv",
            logs,
            ["mode", "epoch", "train_loss", "eval_accuracy", "status"],
        )
        print(f"Trained {args.mode} CNN and wrote {rel(LOG_PATH)}")
    except Exception as exc:
        write_missing_torch_diagnostic(args.mode, rows, exc)
        print(f"Training diagnostic written for {args.mode}: {exc}")


if __name__ == "__main__":
    main()
