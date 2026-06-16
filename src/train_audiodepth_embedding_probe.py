from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw
from torch import nn
from torch.utils.data import DataLoader, Dataset

from .audio_depth_router_common import PROJECT_ROOT, ROUTE_LABELS, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import (
    FIGURE_DIR,
    MODEL_DIR,
    PROBE_EMBEDDINGS_CSV,
    PROBE_PERFORMANCE_CSV,
    accuracy,
    labelled_metadata,
    macro_f1_labels,
    split_train_test,
    write_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train lightweight AudioDepth embedding probes.")
    parser.add_argument("--models", default="cnn,resnet")
    parser.add_argument("--epochs", type=int, default=40)
    return parser.parse_args()


def gap_bucket(row: dict[str, str]) -> str:
    gap = safe_float(row.get("route_gap"))
    if gap < 0.02:
        return "tiny_gap"
    if gap < 0.15:
        return "medium_gap"
    return "large_gap"


def sep_helpful(row: dict[str, str]) -> str:
    return "separation_helpful" if row.get("oracle_route") == "separated" else "not_separation_helpful"


class MapDataset(Dataset):
    def __init__(self, rows: list[dict[str, str]], labels: list[str]):
        self.rows = rows
        self.label_to_idx = {label: idx for idx, label in enumerate(labels)}

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int):
        row = self.rows[idx]
        arr = np.load(PROJECT_ROOT / row["map_path"]).astype(np.float32)
        arr = arr[:, ::2, ::2]
        y = self.label_to_idx[row["_label"]]
        return torch.from_numpy(arr), torch.tensor(y, dtype=torch.long)


class TinyCNN(nn.Module):
    def __init__(self, out_dim: int):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(3, 12, 5, stride=2, padding=2),
            nn.ReLU(),
            nn.Conv2d(12, 24, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((4, 4)),
            nn.Flatten(),
            nn.Linear(24 * 4 * 4, 64),
            nn.ReLU(),
        )
        self.head = nn.Linear(64, out_dim)

    def forward(self, x):
        emb = self.encoder(x)
        return self.head(emb), emb


class TinyResNet(nn.Module):
    def __init__(self, out_dim: int):
        super().__init__()
        self.stem = nn.Sequential(nn.Conv2d(3, 16, 3, stride=2, padding=1), nn.ReLU())
        self.block = nn.Sequential(nn.Conv2d(16, 16, 3, padding=1), nn.ReLU(), nn.Conv2d(16, 16, 3, padding=1))
        self.pool = nn.AdaptiveAvgPool2d((4, 4))
        self.fc = nn.Sequential(nn.Flatten(), nn.Linear(16 * 4 * 4, 64), nn.ReLU())
        self.head = nn.Linear(64, out_dim)

    def forward(self, x):
        h = self.stem(x)
        h = torch.relu(h + self.block(h))
        emb = self.fc(self.pool(h))
        return self.head(emb), emb


def train_model(name: str, rows: list[dict[str, str]], labels: list[str], epochs: int):
    train_rows, test_rows = split_train_test(rows)
    model = TinyResNet(len(labels)) if name == "resnet" else TinyCNN(len(labels))
    opt = torch.optim.Adam(model.parameters(), lr=0.003)
    loss_fn = nn.CrossEntropyLoss()
    loader = DataLoader(MapDataset(train_rows, labels), batch_size=12, shuffle=True)
    model.train()
    for _ in range(epochs):
        for x, y in loader:
            opt.zero_grad()
            logits, _ = model(x)
            loss = loss_fn(logits, y)
            loss.backward()
            opt.step()
    y_true, y_pred, embeddings = [], [], []
    model.eval()
    with torch.no_grad():
        for row in test_rows:
            arr = torch.from_numpy(np.load(PROJECT_ROOT / row["map_path"]).astype(np.float32)[:, ::2, ::2]).unsqueeze(0)
            logits, emb = model(arr)
            y_true.append(row["_label"])
            y_pred.append(labels[int(torch.argmax(logits, dim=1).item())])
            embeddings.append((row, emb.squeeze(0).numpy()))
    return model, test_rows, y_true, y_pred, embeddings


def pca2(xs: np.ndarray) -> np.ndarray:
    xs = xs - xs.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(xs, full_matrices=False)
    return xs @ vt[:2].T


def silhouette_like(points: np.ndarray, labels: list[str]) -> float:
    if len(points) < 3 or len(set(labels)) < 2:
        return 0.0
    vals = []
    for idx, point in enumerate(points):
        same = [np.linalg.norm(point - points[j]) for j, label in enumerate(labels) if label == labels[idx] and j != idx]
        other = [np.linalg.norm(point - points[j]) for j, label in enumerate(labels) if label != labels[idx]]
        if same and other:
            a = float(np.mean(same))
            b = float(np.mean(other))
            vals.append((b - a) / max(a, b, 1e-6))
    return round(float(np.mean(vals)), 6) if vals else 0.0


def scatter(rows: list[dict[str, object]], path: Path, title: str) -> None:
    width, height = 820, 520
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    draw.text((18, 18), title, fill=(0, 0, 0))
    xs = [float(row["x"]) for row in rows]
    ys = [float(row["y"]) for row in rows]
    colors = {"mixed": (30, 120, 180), "separated": (200, 80, 55), "cleaned": (80, 150, 80)}
    for row, x, y in zip(rows, xs, ys):
        px = 60 + int(700 * (x - min(xs)) / max(max(xs) - min(xs), 1e-6))
        py = 450 - int(360 * (y - min(ys)) / max(max(ys) - min(ys), 1e-6))
        color = colors.get(str(row.get("oracle_route")), (80, 80, 80))
        draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=color)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def task_rows(base_rows: list[dict[str, str]], task: str) -> tuple[list[dict[str, str]], list[str]]:
    rows = []
    for row in base_rows:
        row = dict(row)
        if task == "oracle_route":
            row["_label"] = row["oracle_route"]
        elif task == "target_family":
            row["_label"] = row.get("intended_family") or "unknown"
        elif task == "route_gap_bucket":
            row["_label"] = gap_bucket(row)
        else:
            row["_label"] = sep_helpful(row)
        rows.append(row)
    labels = sorted({row["_label"] for row in rows})
    return rows, labels


def main() -> None:
    args = parse_args()
    base_rows = labelled_metadata()
    if not base_rows:
        raise SystemExit("No labelled AudioDepth v2 maps found.")
    perf = []
    embedding_rows = []
    best_embeddings = None
    best_labels = None
    for model_name in [name.strip() for name in args.models.split(",") if name.strip()]:
        for task in ["oracle_route", "target_family", "route_gap_bucket", "separation_helpful"]:
            rows, labels = task_rows(base_rows, task)
            model, test_rows, y_true, y_pred, embeddings = train_model(model_name, rows, labels, args.epochs)
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            model_path = MODEL_DIR / f"audiodepth_centric_probe_{model_name}_{task}.pt"
            torch.save({"model_state": model.state_dict(), "labels": labels, "task": task, "model_name": model_name}, model_path)
            emb_matrix = np.asarray([emb for _, emb in embeddings], dtype=np.float32)
            sil = silhouette_like(emb_matrix, y_true) if len(emb_matrix) else 0.0
            perf.append(
                {
                    "model_name": model_name,
                    "task": task,
                    "accuracy": accuracy(y_true, y_pred),
                    "macro_f1": macro_f1_labels(y_true, y_pred, labels),
                    "route_separability_score": sil,
                    "test_samples": len(test_rows),
                    "model_path": rel(model_path),
                }
            )
            if task == "oracle_route" and (best_embeddings is None or model_name == "resnet"):
                best_embeddings = embeddings
                best_labels = y_true
            for row, emb in embeddings:
                embedding_rows.append(
                    {
                        "model_name": model_name,
                        "task": task,
                        "sample_id": row["sample_id"],
                        "oracle_route": row.get("oracle_route", ""),
                        "target_label": row["_label"],
                        **{f"e{i:02d}": round(float(v), 6) for i, v in enumerate(emb[:16])},
                    }
                )
    write_csv(PROBE_PERFORMANCE_CSV, perf)
    write_csv(PROBE_EMBEDDINGS_CSV, embedding_rows)
    if best_embeddings:
        matrix = np.asarray([emb for _, emb in best_embeddings], dtype=np.float32)
        points = pca2(matrix)
        plot_rows = [
            {"sample_id": row["sample_id"], "oracle_route": row.get("oracle_route", ""), "x": points[idx, 0], "y": points[idx, 1]}
            for idx, (row, _) in enumerate(best_embeddings)
        ]
        scatter(plot_rows, FIGURE_DIR / "audiodepth_centric_embedding_pca.png", "AudioDepth embedding PCA")
        scatter(plot_rows, FIGURE_DIR / "audiodepth_centric_embedding_tsne.png", "AudioDepth embedding t-SNE fallback (PCA projection)")
    best = sorted(perf, key=lambda row: safe_float(row["accuracy"]), reverse=True)[:4]
    write_summary(
        FIGURE_DIR / "audiodepth_centric_probe_summary.md",
        "AudioDepth-Centric Embedding Probe",
        [
            f"- labelled maps: `{len(base_rows)}`",
            f"- models: `{args.models}`",
            "- no large AST dependency was used in this stage",
            "",
            "Best rows:",
            *[f"- `{row['model_name']}` `{row['task']}` accuracy `{row['accuracy']}` macro-F1 `{row['macro_f1']}` separability `{row['route_separability_score']}`" for row in best],
        ],
    )
    print(f"Wrote embedding probe performance to {rel(PROBE_PERFORMANCE_CSV)}")


if __name__ == "__main__":
    main()
