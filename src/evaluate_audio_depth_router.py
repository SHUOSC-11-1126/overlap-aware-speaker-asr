from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_map import generate_one, load_or_build_dataset
from .audio_depth_router_common import (
    LABEL_TO_METHOD,
    PROJECT_ROOT,
    ROUTE_LABELS,
    confusion_counts,
    draw_bar_chart,
    draw_confusion_matrix,
    macro_f1,
    read_csv,
    rel,
    route_cer,
    write_csv,
    write_json,
)


PREDICTIONS_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_predictions.csv"
PERFORMANCE_CSV = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_performance.csv"
PERFORMANCE_JSON = PROJECT_ROOT / "results" / "tables" / "audio_depth_router_performance.json"
SUMMARY_MD = PROJECT_ROOT / "results" / "figures" / "audio_depth_router_summary.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate AudioDepth-Router predictions and routing CER.")
    parser.add_argument("--mode", default="deployable", choices=["deployable", "analysis", "logmel"])
    return parser.parse_args()


def load_model_predict(mode: str, arrays: np.ndarray) -> tuple[list[str], str]:
    model_path = PROJECT_ROOT / "models" / f"audio_depth_router_{mode}.pt"
    if not model_path.exists():
        return ["cleaned"] * len(arrays), "missing_model_cleaned_fallback"
    try:
        import torch
        from torch import nn

        checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
        if isinstance(checkpoint, dict) and checkpoint.get("training_status") == "diagnostic_only":
            return ["cleaned"] * len(arrays), "diagnostic_model_cleaned_fallback"

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

        model = AudioDepthCNN(int(checkpoint["input_channels"]))
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        with torch.no_grad():
            logits = model(torch.from_numpy(arrays.astype(np.float32)))
            pred = logits.argmax(dim=1).cpu().numpy().tolist()
        return [ROUTE_LABELS[idx] for idx in pred], "cnn"
    except Exception:
        try:
            payload = json.loads(model_path.read_text(encoding="utf-8"))
            if payload.get("training_status") == "diagnostic_only":
                return ["cleaned"] * len(arrays), "diagnostic_model_cleaned_fallback"
        except Exception:
            pass
        return ["cleaned"] * len(arrays), "unreadable_model_cleaned_fallback"


def load_eval_arrays(rows: list[dict[str, str]], mode: str) -> tuple[np.ndarray, list[dict[str, str]]]:
    source_mode = "deployable" if mode == "logmel" else mode
    arrays = []
    usable = []
    for row in rows:
        path = PROJECT_ROOT / f"resources/audio_depth_maps/{source_mode}/{row['sample_id']}.npy"
        if not path.exists():
            generate_one(row, source_mode, preview=False)
        arr = np.load(path).astype(np.float32)
        if mode == "logmel":
            arr = arr[:1]
        arrays.append(arr)
        usable.append(row)
    return np.stack(arrays), usable


def baseline_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    baselines = [
        ("fixed_mixed", "mixed"),
        ("fixed_separated", "separated"),
        ("fixed_cleaned", "cleaned"),
        ("oracle_best", "oracle"),
    ]
    output = []
    for name, route in baselines:
        if route == "oracle":
            avg = float(np.mean([min(float(row["mixed_cer"]), float(row["separated_cer"]), float(row["cleaned_cer"])) for row in rows]))
        else:
            avg = float(np.mean([route_cer(row, route) for row in rows]))
        output.append({"strategy": name, "routing_average_cer": round(avg, 6), "sample_count": len(rows)})
    routing_path = PROJECT_ROOT / "results" / "tables" / "synthetic_split_routing_performance.csv"
    if routing_path.exists():
        for row in read_csv(routing_path):
            if row.get("scope") == "TEST" and row.get("strategy") in {"v1_overlap_only", "v2_full_features"}:
                output.append(
                    {
                        "strategy": row["strategy"],
                        "routing_average_cer": row["average_cer"],
                        "sample_count": row["sample_count"],
                    }
                )
    return output


def main() -> None:
    args = parse_args()
    rows = [row for row in load_or_build_dataset("deployable" if args.mode == "logmel" else args.mode) if row.get("split") == "test"]
    arrays, rows = load_eval_arrays(rows, args.mode)
    predictions, model_status = load_model_predict(args.mode, arrays)
    y_true = [row["best_route_label"] for row in rows]
    pred_rows: list[dict[str, Any]] = []
    for row, pred in zip(rows, predictions):
        pred_rows.append(
            {
                **row,
                "predicted_route": pred,
                "predicted_method": LABEL_TO_METHOD[pred],
                "predicted_cer": route_cer(row, pred),
                "model_status": model_status,
            }
        )
    accuracy = sum(1 for t, p in zip(y_true, predictions) if t == p) / len(rows) if rows else 0.0
    avg_cer = float(np.mean([float(row["predicted_cer"]) for row in pred_rows])) if pred_rows else 0.0
    performance = [
        {
            "strategy": f"audio_depth_cnn_{args.mode}",
            "mode": args.mode,
            "classification_accuracy": round(accuracy, 6),
            "macro_f1": round(macro_f1(y_true, predictions), 6),
            "routing_average_cer": round(avg_cer, 6),
            "sample_count": len(rows),
            "model_status": model_status,
            "label": "experimental/frontier",
        }
    ] + baseline_rows(rows)
    write_csv(PREDICTIONS_CSV, pred_rows)
    write_csv(PERFORMANCE_CSV, performance)
    write_json(PERFORMANCE_JSON, performance)
    write_csv(PROJECT_ROOT / "results" / "tables" / f"audio_depth_router_predictions_{args.mode}.csv", pred_rows)
    write_csv(PROJECT_ROOT / "results" / "tables" / f"audio_depth_router_performance_{args.mode}.csv", performance)
    write_json(PROJECT_ROOT / "results" / "tables" / f"audio_depth_router_performance_{args.mode}.json", performance)
    matrix = confusion_counts(y_true, predictions)
    draw_confusion_matrix(matrix, PROJECT_ROOT / "results" / "figures" / "audio_depth_router_confusion_matrix.png", args.mode)
    draw_bar_chart(
        performance,
        PROJECT_ROOT / "results" / "figures" / "audio_depth_router_cer_comparison.png",
        "strategy",
        "routing_average_cer",
        "AudioDepth routing CER comparison",
    )
    router_v2 = next((row for row in performance if row["strategy"] == "v2_full_features"), None)
    router_v2_note = (
        f"v2_full_features routing_average_cer `{router_v2['routing_average_cer']}` on the matched TEST scope."
        if router_v2
        else "router_v2 comparable row was not found in this evaluator."
    )
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# AudioDepth-Router Summary",
                "",
                "## What was attempted",
                "AudioDepth-Router tests whether a lightweight learned router can choose between mixed, separated, and cleaned ASR outputs from depth-augmented spectrogram maps.",
                "",
                "## RGB-D inspiration",
                "The experiment treats overlapping speech as time-frequency occlusion. A log-mel spectrogram is augmented with overlap/depth and uncertainty/dominance channels, mirroring RGB-D image recognition where depth helps explain occluded structure.",
                "",
                "## Dataset used",
                "The run uses the synthetic split CER table as `synthetic/silver` evidence. Gold cases remain sanity-only and are not used as training data.",
                "",
                "## Deployable vs analysis-only",
                "`deployable` maps use only mixed audio. `analysis` maps may use separated tracks and must be read as `analysis_only`, not a deployable claim.",
                "",
                "## Classification result",
                f"Mode `{args.mode}` achieved accuracy `{accuracy:.4f}` and macro-F1 `{macro_f1(y_true, predictions):.4f}` on the held-out synthetic test split. Model status: `{model_status}`.",
                "",
                "## Routing CER result",
                f"AudioDepth routing average CER was `{avg_cer:.6f}` on `{len(rows)}` test samples.",
                "",
                "## Comparison",
                *[f"- `{row['strategy']}`: routing_average_cer `{row['routing_average_cer']}`" for row in performance],
                f"- router_v2: {router_v2_note}",
                "",
                "## Did AudioDepth help?",
                "This first frontier pass is useful even when it underperforms: it isolates how much local audio-visual structure can explain route labels without text-level instability features.",
                "",
                "## Failure modes",
                "- small synthetic data may be insufficient",
                "- overlap proxy may be too weak",
                "- oracle labels may be noisy",
                "- text-level instability features remain important",
                "- audio visual features alone may not capture ASR hallucination risk",
                "",
                "## What should happen next",
                "Run the same pipeline with a larger synthetic sweep, add explicit log-mel-only comparison, and compare against router_v2 on exactly matched synthetic split rows.",
            ]
        ),
        encoding="utf-8",
    )
    (PROJECT_ROOT / "results" / "figures" / f"audio_depth_router_summary_{args.mode}.md").write_text(
        SUMMARY_MD.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    print(f"Wrote {rel(PREDICTIONS_CSV)}, {rel(PERFORMANCE_CSV)}, and {rel(SUMMARY_MD)}")


if __name__ == "__main__":
    main()
