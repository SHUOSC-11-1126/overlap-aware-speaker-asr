from __future__ import annotations

import argparse

import numpy as np
import torch
from torch import nn

from .audio_depth_router_common import PROJECT_ROOT, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import (
    FIGURE_DIR,
    GATE_LABELS,
    GATE_PERFORMANCE_CSV,
    GATE_PER_FAMILY_CSV,
    GATE_PREDICTIONS_CSV,
    MODEL_DIR,
    accuracy,
    draw_confusion,
    feature_vector,
    gate_label,
    labelled_metadata,
    macro_f1_labels,
    split_train_test,
    write_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train AudioDepth Stage-1 acoustic gate.")
    parser.add_argument("--epochs", type=int, default=40)
    return parser.parse_args()


class GateMLP(nn.Module):
    def __init__(self, input_dim: int, out_dim: int):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(input_dim, 24), nn.ReLU(), nn.Linear(24, out_dim))

    def forward(self, x):
        return self.net(x)


def main() -> None:
    args = parse_args()
    rows = labelled_metadata()
    if not rows:
        raise SystemExit("No labelled AudioDepth metadata found.")
    for row in rows:
        row["_gate_label"] = gate_label(row)
    train, test = split_train_test(rows)
    x_train = torch.tensor([feature_vector(row) for row in train], dtype=torch.float32)
    y_train = torch.tensor([GATE_LABELS.index(row["_gate_label"]) for row in train], dtype=torch.long)
    mean = x_train.mean(dim=0, keepdim=True)
    std = x_train.std(dim=0, keepdim=True)
    std[std == 0] = 1.0
    model = GateMLP(x_train.shape[1], len(GATE_LABELS))
    opt = torch.optim.Adam(model.parameters(), lr=0.02)
    loss_fn = nn.CrossEntropyLoss()
    for _ in range(args.epochs):
        opt.zero_grad()
        loss = loss_fn(model((x_train - mean) / std), y_train)
        loss.backward()
        opt.step()
    x_test = torch.tensor([feature_vector(row) for row in test], dtype=torch.float32)
    probs = torch.softmax(model((x_test - mean) / std), dim=1).detach().numpy()
    pred_idx = probs.argmax(axis=1)
    preds = [GATE_LABELS[int(idx)] for idx in pred_idx]
    true = [row["_gate_label"] for row in test]
    pred_rows = []
    all_x = torch.tensor([feature_vector(row) for row in rows], dtype=torch.float32)
    all_probs = torch.softmax(model((all_x - mean) / std), dim=1).detach().numpy()
    all_preds = [GATE_LABELS[int(idx)] for idx in all_probs.argmax(axis=1)]
    for row, pred, prob_vec in zip(rows, all_preds, all_probs):
        split = "heldout" if row in test else "train"
        pred_rows.append(
            {
                "sample_id": row["sample_id"],
                "source": row.get("source", ""),
                "eval_split": split,
                "true_gate_label": row["_gate_label"],
                "predicted_gate_label": pred,
                "confidence": round(float(max(prob_vec)), 6),
                "oracle_route": row.get("oracle_route", ""),
                "route_gap": row.get("route_gap", ""),
                "min_route_cer": min(safe_float(row.get("mixed_cer")), safe_float(row.get("separated_cer")), safe_float(row.get("cleaned_cer"))),
                "intended_family": row.get("intended_family", ""),
                **{f"p_{label}": round(float(prob_vec[idx]), 6) for idx, label in enumerate(GATE_LABELS)},
            }
        )
    eval_rows = [row for row in pred_rows if row["eval_split"] == "heldout"]
    false_safe = [
        row
        for row in eval_rows
        if row["predicted_gate_label"] == "easy_mixed" and (row["true_gate_label"] in {"review_risk", "ambiguous_needs_text_probe"} or safe_float(row["min_route_cer"]) > 0.6)
    ]
    text_probe_needed = {"ambiguous_needs_text_probe", "review_risk"}
    performance = [
        {
            "model_name": "audiodepth_stage1_gate",
            "gate_accuracy": accuracy(true, preds),
            "macro_f1": macro_f1_labels(true, preds, GATE_LABELS),
            "easy_mixed_recall": recall(true, preds, "easy_mixed"),
            "separation_helpful_recall": recall(true, preds, "likely_separation_helpful"),
            "ambiguous_review_recall": recall_binary(true, preds, text_probe_needed),
            "false_safe_rate": round(len(false_safe) / max(len(eval_rows), 1), 6),
            "text_probe_reduction_rate": round(sum(1 for row in eval_rows if row["predicted_gate_label"] not in text_probe_needed) / max(len(eval_rows), 1), 6),
            "test_samples": len(eval_rows),
            "prediction_rows": len(pred_rows),
        }
    ]
    family_rows = []
    for family in sorted({row.get("intended_family", "") for row in pred_rows}):
        bucket = [row for row in pred_rows if row.get("intended_family", "") == family]
        family_rows.append(
            {
                "intended_family": family,
                "sample_count": len(bucket),
                "gate_accuracy": accuracy([row["true_gate_label"] for row in bucket], [row["predicted_gate_label"] for row in bucket]),
                "false_safe_count": sum(1 for row in bucket if row in false_safe),
            }
        )
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_DIR / "audiodepth_stage1_gate.pt"
    torch.save({"model_state": model.state_dict(), "mean": mean.numpy().tolist(), "std": std.numpy().tolist(), "labels": GATE_LABELS}, model_path)
    write_csv(GATE_PREDICTIONS_CSV, pred_rows)
    write_csv(GATE_PERFORMANCE_CSV, performance)
    write_csv(GATE_PER_FAMILY_CSV, family_rows)
    draw_confusion(true, preds, GATE_LABELS, FIGURE_DIR / "audiodepth_gate_confusion_matrix.png", "AudioDepth Stage-1 gate confusion")
    write_summary(
        FIGURE_DIR / "audiodepth_gate_summary.md",
        "AudioDepth Stage-1 Gate",
        [
            f"- model path: `{rel(model_path)}`",
            f"- gate accuracy: `{performance[0]['gate_accuracy']}`",
            f"- macro-F1: `{performance[0]['macro_f1']}`",
            f"- easy_mixed recall: `{performance[0]['easy_mixed_recall']}`",
            f"- separation_helpful recall: `{performance[0]['separation_helpful_recall']}`",
            f"- false-safe rate: `{performance[0]['false_safe_rate']}`",
            f"- text-probe reduction rate: `{performance[0]['text_probe_reduction_rate']}`",
        ],
    )
    print(f"Wrote AudioDepth gate predictions to {rel(GATE_PREDICTIONS_CSV)}")


def recall(y_true: list[str], y_pred: list[str], label: str) -> float:
    denom = sum(1 for value in y_true if value == label)
    return round(sum(1 for a, b in zip(y_true, y_pred) if a == label and b == label) / denom, 6) if denom else 0.0


def recall_binary(y_true: list[str], y_pred: list[str], labels: set[str]) -> float:
    denom = sum(1 for value in y_true if value in labels)
    return round(sum(1 for a, b in zip(y_true, y_pred) if a in labels and b in labels) / denom, 6) if denom else 0.0


if __name__ == "__main__":
    main()
