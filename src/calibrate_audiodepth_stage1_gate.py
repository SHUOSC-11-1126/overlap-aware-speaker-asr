from __future__ import annotations

import argparse

import numpy as np
import torch
from PIL import Image, ImageDraw
from torch import nn

from .audio_depth_router_common import rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import (
    FIGURE_DIR,
    MODEL_DIR,
    feature_vector,
    labelled_metadata,
    macro_f1_labels,
    route_cer,
    split_train_test,
    write_summary,
)
from .balanced_v2_common import V2_CER, mean
from .evaluate_audiodepth_two_stage_cascade import router_v2


LABELS = ["easy_mixed", "likely_separation_helpful", "ambiguous_needs_text_probe", "review_risk"]
TABLE_DIR = FIGURE_DIR.parent / "tables"
PRED_CSV = TABLE_DIR / "audiodepth_gate_calibrated_predictions.csv"
SWEEP_CSV = TABLE_DIR / "audiodepth_gate_calibrated_threshold_sweep.csv"
PERF_CSV = TABLE_DIR / "audiodepth_gate_calibrated_performance.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate AudioDepth Stage-1 gate labels and confidence thresholds.")
    parser.add_argument("--epochs", type=int, default=80)
    return parser.parse_args()


def calibrated_label(row: dict[str, str]) -> str:
    gap = safe_float(row.get("route_gap"))
    min_cer = min(safe_float(row.get("mixed_cer")), safe_float(row.get("separated_cer")), safe_float(row.get("cleaned_cer")))
    oracle = row.get("oracle_route", "")
    separation_gain = safe_float(row.get("mixed_cer")) - min(safe_float(row.get("separated_cer")), safe_float(row.get("cleaned_cer")))
    if oracle == "mixed":
        if gap < 0.02:
            return "ambiguous_needs_text_probe"
        return "easy_mixed"
    if oracle == "separated" or separation_gain >= 0.02:
        return "likely_separation_helpful"
    if gap < 0.02:
        return "ambiguous_needs_text_probe"
    if min_cer > 0.75:
        return "review_risk"
    return "ambiguous_needs_text_probe"


def risk_flag(row: dict[str, str]) -> bool:
    min_cer = min(safe_float(row.get("mixed_cer")), safe_float(row.get("separated_cer")), safe_float(row.get("cleaned_cer")))
    return min_cer > 0.6 or safe_float(row.get("route_gap")) < 0.02


class Gate(nn.Module):
    def __init__(self, input_dim: int):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(input_dim, 32), nn.ReLU(), nn.Linear(32, 16), nn.ReLU(), nn.Linear(16, len(LABELS)))

    def forward(self, x):
        return self.net(x)


def recall(y_true: list[str], y_pred: list[str], label: str) -> float:
    denom = sum(1 for value in y_true if value == label)
    return round(sum(1 for a, b in zip(y_true, y_pred) if a == label and b == label) / denom, 6) if denom else 0.0


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    return round(float(np.mean([a == b for a, b in zip(y_true, y_pred)])), 6) if y_true else 0.0


def train(rows: list[dict[str, str]], epochs: int):
    train_rows, test_rows = split_train_test(rows)
    x_train = torch.tensor([feature_vector(row) for row in train_rows], dtype=torch.float32)
    y_train = torch.tensor([LABELS.index(row["_calibrated_label"]) for row in train_rows], dtype=torch.long)
    mean_v = x_train.mean(dim=0, keepdim=True)
    std_v = x_train.std(dim=0, keepdim=True)
    std_v[std_v == 0] = 1.0
    counts = torch.bincount(y_train, minlength=len(LABELS)).float()
    weights = counts.sum() / torch.clamp(counts, min=1.0)
    weights = weights / weights.mean()
    model = Gate(x_train.shape[1])
    opt = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_fn = nn.CrossEntropyLoss(weight=weights)
    for _ in range(epochs):
        opt.zero_grad()
        loss = loss_fn(model((x_train - mean_v) / std_v), y_train)
        loss.backward()
        opt.step()
    return model, mean_v, std_v, train_rows, test_rows


def predict_rows(model, mean_v, std_v, rows: list[dict[str, str]], test_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    x = torch.tensor([feature_vector(row) for row in rows], dtype=torch.float32)
    probs = torch.softmax(model((x - mean_v) / std_v), dim=1).detach().numpy()
    out = []
    for row, prob in zip(rows, probs):
        pred = LABELS[int(np.argmax(prob))]
        out.append(
            {
                "sample_id": row["sample_id"],
                "source": row.get("source", ""),
                "eval_split": "heldout" if row in test_rows else "train",
                "true_gate_label": row["_calibrated_label"],
                "predicted_gate_label": pred,
                "confidence": round(float(np.max(prob)), 6),
                "risk_flag": "True" if risk_flag(row) else "False",
                "oracle_route": row.get("oracle_route", ""),
                "route_gap": row.get("route_gap", ""),
                "mixed_cer": row.get("mixed_cer", ""),
                "separated_cer": row.get("separated_cer", ""),
                "cleaned_cer": row.get("cleaned_cer", ""),
                "intended_family": row.get("intended_family", ""),
                **{f"p_{label}": round(float(prob[idx]), 6) for idx, label in enumerate(LABELS)},
            }
        )
    return out


def selected_route(row: dict[str, str], threshold: float) -> tuple[str, bool]:
    label = row["predicted_gate_label"]
    if safe_float(row["confidence"]) >= threshold and label == "easy_mixed":
        return "mixed", False
    if safe_float(row["confidence"]) >= threshold and label == "likely_separation_helpful":
        return "separated", False
    return router_v2(row), True


def sweep_thresholds(preds: list[dict[str, object]]) -> list[dict[str, object]]:
    cer_rows = {row["sample_id"]: row for row in __import__("src.audio_depth_router_common", fromlist=["read_csv"]).read_csv(V2_CER)}
    rows = [row for row in preds if row["sample_id"] in cer_rows]
    out = []
    for threshold in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        selected = []
        text_probe = []
        false_safe = 0
        for pred in rows:
            cer = cer_rows[pred["sample_id"]]
            merged = {**cer, **pred}
            route, probe = selected_route(merged, threshold)
            selected.append(route_cer(cer, route))
            text_probe.append(probe)
            if route == "mixed" and min(safe_float(cer["mixed_cer"]), safe_float(cer["separated_cer"]), safe_float(cer["cleaned_cer"])) > 0.6:
                false_safe += 1
        out.append(
            {
                "threshold": threshold,
                "selected_route_cer": mean(selected),
                "text_probe_reduction_rate": round(1.0 - (sum(text_probe) / max(len(text_probe), 1)), 6),
                "false_safe_rate": round(false_safe / max(len(rows), 1), 6),
                "sample_count": len(rows),
            }
        )
    return out


def draw_sweep(rows: list[dict[str, object]]) -> None:
    img = Image.new("RGB", (900, 480), "white")
    draw = ImageDraw.Draw(img)
    draw.text((24, 18), "AudioDepth calibrated gate threshold sweep", fill=(0, 0, 0))
    xs = [safe_float(row["threshold"]) for row in rows]
    ys = [safe_float(row["selected_route_cer"]) for row in rows]
    zs = [safe_float(row["text_probe_reduction_rate"]) for row in rows]
    min_y, max_y = min(ys + [0.0]), max(ys + [1e-6])
    for idx, row in enumerate(rows):
        x = 70 + int(740 * (xs[idx] - min(xs)) / max(max(xs) - min(xs), 1e-6))
        y = 360 - int(260 * (ys[idx] - min_y) / max(max_y - min_y, 1e-6))
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(40, 100, 170))
        draw.text((x - 18, y - 24), f"{zs[idx]:.2f}", fill=(0, 0, 0))
    draw.line((70, 360, 810, 360), fill=(0, 0, 0))
    draw.line((70, 100, 70, 360), fill=(0, 0, 0))
    out = FIGURE_DIR / "audiodepth_gate_calibrated_threshold_sweep.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def main() -> None:
    args = parse_args()
    rows = labelled_metadata()
    for row in rows:
        row["_calibrated_label"] = calibrated_label(row)
    model, mean_v, std_v, _train_rows, test_rows = train(rows, args.epochs)
    preds = predict_rows(model, mean_v, std_v, rows, test_rows)
    heldout = [row for row in preds if row["eval_split"] == "heldout"]
    true = [row["true_gate_label"] for row in heldout]
    pred = [row["predicted_gate_label"] for row in heldout]
    perf = [
        {
            "model_name": "audiodepth_stage1_gate_calibrated",
            "gate_accuracy": accuracy(true, pred),
            "macro_f1": macro_f1_labels(true, pred, LABELS),
            "easy_mixed_recall": recall(true, pred, "easy_mixed"),
            "separation_helpful_recall": recall(true, pred, "likely_separation_helpful"),
            "ambiguous_recall": recall(true, pred, "ambiguous_needs_text_probe"),
            "review_risk_recall": recall(true, pred, "review_risk"),
            "heldout_samples": len(heldout),
            "prediction_rows": len(preds),
        }
    ]
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "audiodepth_gate_calibrated.pt"
    torch.save({"model_state": model.state_dict(), "mean": mean_v.numpy().tolist(), "std": std_v.numpy().tolist(), "labels": LABELS}, model_path)
    sweep = sweep_thresholds(preds)
    write_csv(PRED_CSV, preds)
    write_csv(PERF_CSV, perf)
    write_csv(SWEEP_CSV, sweep)
    draw_sweep(sweep)
    best = sorted(sweep, key=lambda row: (safe_float(row["selected_route_cer"]), -safe_float(row["text_probe_reduction_rate"])))[0]
    write_summary(
        FIGURE_DIR / "audiodepth_gate_calibrated_summary.md",
        "AudioDepth Gate Calibration",
        [
            f"- model path: `{rel(model_path)}`",
            f"- held-out accuracy: `{perf[0]['gate_accuracy']}`",
            f"- held-out macro-F1: `{perf[0]['macro_f1']}`",
            f"- easy_mixed recall: `{perf[0]['easy_mixed_recall']}`",
            f"- separation_helpful recall: `{perf[0]['separation_helpful_recall']}`",
            f"- best threshold by CER: `{best['threshold']}` CER `{best['selected_route_cer']}` text-probe reduction `{best['text_probe_reduction_rate']}`",
            "- Calibration separates route-action labels from risk flags, so review risk no longer swallows every high-CER separated-helpful case.",
        ],
    )
    print(f"Wrote calibrated AudioDepth gate to {rel(PERF_CSV)}")


if __name__ == "__main__":
    main()
