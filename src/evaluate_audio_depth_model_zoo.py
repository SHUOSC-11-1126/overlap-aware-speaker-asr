from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_router_common import LABEL_TO_METHOD, ROUTE_LABELS, confusion_counts, draw_bar_chart, draw_confusion_matrix, macro_f1, read_csv, rel, route_cer, write_csv, write_json
from .audio_depth_zoo_common import (
    COMPARE_TO_ROUTER_V2_CSV,
    FEATURES_CSV,
    MODEL_NAMES,
    PER_CLASS_CSV,
    PER_TIER_CSV,
    PERFORMANCE_CSV,
    PREDICTIONS_CSV,
    SUMMARY_MD,
    build_hybrid_features_table,
    feature_keys,
    load_hybrid_features,
    majority_label,
    map_channels_for_mode,
    route_label_to_index,
    safe_float,
    sample_map_path,
)
from .audio_depth_zoo_models import build_model


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the AudioDepth model zoo.")
    parser.add_argument("--models", default="all")
    return parser.parse_args()


def resolve_models(spec: str) -> list[str]:
    if spec == "all":
        return MODEL_NAMES
    models = [item.strip() for item in spec.split(",") if item.strip()]
    unknown = [item for item in models if item not in MODEL_NAMES]
    if unknown:
        raise KeyError(f"Unknown zoo model(s): {', '.join(unknown)}")
    return models


def load_rows() -> list[dict[str, Any]]:
    rows = load_hybrid_features() if FEATURES_CSV.exists() else build_hybrid_features_table()
    return [row for row in rows if row.get("split") == "test"]


def load_checkpoint(model_name: str) -> dict[str, Any] | None:
    path = Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/models/audio_depth_zoo") / f"{model_name}.pt"
    if not path.exists():
        return None
    try:
        import torch

        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        if isinstance(checkpoint, dict) and checkpoint.get("status") == "failed":
            return checkpoint
        return checkpoint
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None


def model_mode(model_name: str) -> str:
    if model_name == "mlp_handcrafted":
        return "tabular"
    if model_name == "cnn_logmel":
        return "logmel"
    if model_name == "analysis_upper_bound_cnn":
        return "analysis"
    return "deployable"


def predict_for_model(model_name: str, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    checkpoint = load_checkpoint(model_name)
    feature_names = feature_keys()
    mode = model_mode(model_name)
    predictions: list[dict[str, Any]] = []
    model_status = "missing_model"
    if checkpoint is None:
        for row in rows:
            predictions.append(
                {
                    "sample_id": row["sample_id"],
                    "split": row["split"],
                    "model_name": model_name,
                    "true_route_label": row["best_route_label"],
                    "predicted_route_label": majority_label(rows),
                    "predicted_confidence": 0.0,
                    "predicted_method": LABEL_TO_METHOD[majority_label(rows)],
                    "predicted_cer": route_cer(row, majority_label(rows)),
                    "model_status": model_status,
                }
            )
        return predictions, {"status": model_status}
    if checkpoint.get("status") == "failed":
        model_status = "failed"
        fallback = majority_label(rows)
        for row in rows:
            predictions.append(
                {
                    "sample_id": row["sample_id"],
                    "split": row["split"],
                    "model_name": model_name,
                    "true_route_label": row["best_route_label"],
                    "predicted_route_label": fallback,
                    "predicted_confidence": 0.0,
                    "predicted_method": LABEL_TO_METHOD[fallback],
                    "predicted_cer": route_cer(row, fallback),
                    "model_status": model_status,
                }
            )
        return predictions, checkpoint
    try:
        import torch

        model = build_model(model_name, input_channels=int(checkpoint.get("input_channels", 3)), tabular_dim=int(checkpoint.get("tabular_dim", len(feature_names))))
        model.load_state_dict(checkpoint["state_dict"])
        model.eval()
        model_status = "trained"
        for row in rows:
            if model_name == "mlp_handcrafted":
                tab = np.asarray([safe_float(row.get(key), 0.0) for key in feature_names], dtype=np.float32)[None, :]
                logits = model(torch.from_numpy(tab))
            else:
                map_mode = mode
                arr = np.load(sample_map_path(str(row["sample_id"]), map_mode)).astype(np.float32)
                if model_name == "hybrid_late_fusion":
                    tab = np.asarray([safe_float(row.get(key), 0.0) for key in feature_names], dtype=np.float32)[None, :]
                    logits = model(torch.from_numpy(arr[None, ...]), torch.from_numpy(tab))
                else:
                    logits = model(torch.from_numpy(arr[None, ...]))
            probs = torch.softmax(logits, dim=1).detach().cpu().numpy()[0]
            idx = int(np.argmax(probs))
            label = ROUTE_LABELS[idx]
            predictions.append(
                {
                    "sample_id": row["sample_id"],
                    "split": row["split"],
                    "model_name": model_name,
                    "true_route_label": row["best_route_label"],
                    "predicted_route_label": label,
                    "predicted_confidence": float(probs[idx]),
                    "predicted_method": LABEL_TO_METHOD[label],
                    "predicted_cer": route_cer(row, label),
                    "model_status": model_status,
                }
            )
        return predictions, checkpoint
    except Exception as exc:
        fallback = majority_label(rows)
        for row in rows:
            predictions.append(
                {
                    "sample_id": row["sample_id"],
                    "split": row["split"],
                    "model_name": model_name,
                    "true_route_label": row["best_route_label"],
                    "predicted_route_label": fallback,
                    "predicted_confidence": 0.0,
                    "predicted_method": LABEL_TO_METHOD[fallback],
                    "predicted_cer": route_cer(row, fallback),
                    "model_status": f"fallback:{exc}",
                }
            )
        return predictions, {"status": f"fallback:{exc}"}


def baseline_predictions(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    output: list[dict[str, Any]] = []
    majority = majority_label(rows)
    for baseline_name, route in [
        ("fixed_mixed_whisper", "mixed"),
        ("fixed_separated_whisper", "separated"),
        ("fixed_separated_whisper_cleaned", "cleaned"),
        ("majority_route_baseline", majority),
        ("oracle_best", "oracle"),
    ]:
        if route == "oracle":
            cer_values = [min(route_cer(row, "mixed"), route_cer(row, "separated"), route_cer(row, "cleaned")) for row in rows]
        else:
            cer_values = [route_cer(row, route) for row in rows]
        output.append(
            {
                "strategy": baseline_name,
                "model_name": baseline_name,
                "classification_accuracy": "",
                "macro_f1": "",
                "routing_average_cer": round(float(np.mean(cer_values)), 6) if cer_values else 0.0,
                "sample_count": len(rows),
                "model_status": "baseline",
                "label": "baseline",
            }
        )
    return output, [], []


def route_label_distribution(labels: list[str]) -> dict[str, int]:
    counts = {label: 0 for label in ROUTE_LABELS}
    for label in labels:
        counts[label] = counts.get(label, 0) + 1
    return counts


def metrics_for_predictions(model_name: str, preds: list[dict[str, Any]]) -> dict[str, Any]:
    y_true = [row["true_route_label"] for row in preds]
    y_pred = [row["predicted_route_label"] for row in preds]
    avg_cer = float(np.mean([float(row["predicted_cer"]) for row in preds])) if preds else 0.0
    acc = sum(1 for a, b in zip(y_true, y_pred) if a == b) / len(preds) if preds else 0.0
    return {
        "model_name": model_name,
        "classification_accuracy": round(acc, 6),
        "macro_f1": round(macro_f1(y_true, y_pred), 6),
        "routing_average_cer": round(avg_cer, 6),
        "sample_count": len(preds),
        "prediction_distribution": json.dumps(route_label_distribution(y_pred)),
        "model_status": preds[0]["model_status"] if preds else "",
        "label": "experimental/frontier" if model_name in MODEL_NAMES else "baseline",
    }


def per_class_rows(model_name: str, preds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    y_true = [row["true_route_label"] for row in preds]
    y_pred = [row["predicted_route_label"] for row in preds]
    for label in ROUTE_LABELS:
        tp = sum(1 for a, b in zip(y_true, y_pred) if a == label and b == label)
        fp = sum(1 for a, b in zip(y_true, y_pred) if a != label and b == label)
        fn = sum(1 for a, b in zip(y_true, y_pred) if a == label and b != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "model_name": model_name,
                "route_label": label,
                "precision": round(precision, 6),
                "recall": round(recall, 6),
                "f1": round(f1, 6),
                "support": sum(1 for a in y_true if a == label),
            }
        )
    return rows


def per_tier_rows(model_name: str, preds: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = {}
    for row in preds:
        source = next((item for item in rows if item["sample_id"] == row["sample_id"]), None)
        tier = source.get("overlap_tier", source.get("tier", "")) if source else ""
        grouped.setdefault(tier, []).append(float(row["predicted_cer"]))
    return [
        {
            "model_name": model_name,
            "overlap_tier": tier,
            "routing_average_cer": round(float(np.mean(values)), 6) if values else 0.0,
            "sample_count": len(values),
        }
        for tier, values in sorted(grouped.items())
    ]


def router_v2_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    routing_path = Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/tables/synthetic_split_routing_decisions.csv")
    if not routing_path.exists():
        return []
    route_map: dict[str, str] = {}
    for row in read_csv(routing_path):
        if row.get("strategy") == "v2_full_features":
            route_map[row["sample_id"]] = row.get("selected_method", "")
    output = []
    for row in rows:
        method = route_map.get(row["sample_id"], "mixed_whisper")
        label = "mixed"
        if method in {"separated_whisper", "separated_whisper_cleaned", "mixed_whisper"}:
            label = "separated" if method == "separated_whisper" else "cleaned" if method == "separated_whisper_cleaned" else "mixed"
        output.append(
            {
                "sample_id": row["sample_id"],
                "model_name": "router_v2",
                "true_route_label": row["best_route_label"],
                "predicted_route_label": label,
                "predicted_confidence": 1.0,
                "predicted_method": method or LABEL_TO_METHOD[label],
                "predicted_cer": route_cer(row, label),
                "model_status": "baseline",
                "split": row["split"],
            }
        )
    return output


def router_v1_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    routing_path = Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/tables/synthetic_split_routing_decisions.csv")
    if not routing_path.exists():
        return []
    route_map: dict[str, str] = {}
    for row in read_csv(routing_path):
        if row.get("strategy") == "v1_overlap_only":
            route_map[row["sample_id"]] = row.get("selected_method", "")
    output = []
    for row in rows:
        method = route_map.get(row["sample_id"], "mixed_whisper")
        label = "mixed"
        if method == "separated_whisper":
            label = "separated"
        elif method == "separated_whisper_cleaned":
            label = "cleaned"
        output.append(
            {
                "sample_id": row["sample_id"],
                "model_name": "router_v1",
                "true_route_label": row["best_route_label"],
                "predicted_route_label": label,
                "predicted_confidence": 1.0,
                "predicted_method": method or LABEL_TO_METHOD[label],
                "predicted_cer": route_cer(row, label),
                "model_status": "baseline",
                "split": row["split"],
            }
        )
    return output


def synthetic_majority_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    label = majority_label(rows)
    return [
        {
            "sample_id": row["sample_id"],
            "model_name": "majority_route_baseline",
            "true_route_label": row["best_route_label"],
            "predicted_route_label": label,
            "predicted_confidence": 1.0,
            "predicted_method": LABEL_TO_METHOD[label],
            "predicted_cer": route_cer(row, label),
            "model_status": "baseline",
            "split": row["split"],
        }
        for row in rows
    ]


def fixed_route_rows(rows: list[dict[str, Any]], model_name: str, route_label: str) -> list[dict[str, Any]]:
    return [
        {
            "sample_id": row["sample_id"],
            "split": row["split"],
            "model_name": model_name,
            "true_route_label": row["best_route_label"],
            "predicted_route_label": route_label,
            "predicted_confidence": 1.0,
            "predicted_method": LABEL_TO_METHOD[route_label],
            "predicted_cer": route_cer(row, route_label),
            "model_status": "baseline",
        }
        for row in rows
    ]


def compare_to_router_v2(metrics_rows: list[dict[str, Any]], router_v2_metric: dict[str, Any] | None) -> list[dict[str, Any]]:
    if router_v2_metric is None:
        return []
    output = []
    for row in metrics_rows:
        output.append(
            {
                "model_name": row["model_name"],
                "routing_average_cer": row["routing_average_cer"],
                "delta_vs_router_v2": round(float(row["routing_average_cer"]) - float(router_v2_metric["routing_average_cer"]), 6),
                "macro_f1": row.get("macro_f1", ""),
                "delta_macro_f1_vs_router_v2": round(float(row.get("macro_f1", 0.0)) - float(router_v2_metric.get("macro_f1", 0.0)), 6),
                "model_status": row.get("model_status", ""),
            }
        )
    return output


def build_summary_md(sorted_rows: list[dict[str, Any]], router_v2_metric: dict[str, Any] | None, rows: list[dict[str, Any]]) -> str:
    best = sorted_rows[0] if sorted_rows else {}
    router_note = (
        f"router_v2 routing CER on the matched test rows is `{router_v2_metric['routing_average_cer']}`."
        if router_v2_metric
        else "router_v2 comparable rows were not available."
    )
    lines = [
        "# AudioDepth Model Zoo Summary",
        "",
        "## What this frontier study asks",
        "Can richer audio-depth models and hybrid audio-text routers better predict when separation helps or hurts ASR?",
        "",
        "## Interpretation",
        "The first AudioDepth MVP was weak, which motivated this broader model-zoo exploration. The point is not to force a win, but to see whether richer architectures, class balancing, hybrid features, or confidence cascades recover more signal than the small frontier CNN.",
        "",
        "## Best observed model",
        f"`{best.get('model_name', '')}` with routing CER `{best.get('routing_average_cer', '')}` and macro-F1 `{best.get('macro_f1', '')}`.",
        "",
        "## Baselines",
        *[f"- `{row['model_name']}`: CER `{row['routing_average_cer']}`" for row in sorted_rows if row["model_name"] in {"fixed_mixed_whisper", "fixed_separated_whisper", "fixed_separated_whisper_cleaned", "majority_route_baseline", "router_v1", "router_v2", "oracle_best"}],
        "",
        "## Router comparison",
        router_note,
        "",
        "## Reminder",
        "Synthetic results are informative but not gold. If a model does not beat router_v2, that is still a boundary finding, especially if the hybrid and cascade views explain why.",
    ]
    return "\n".join(lines) + "\n"


def leaderboard_sort_key(row: dict[str, Any]) -> tuple[float, float, int]:
    deployable_priority = 0 if row.get("model_name") != "analysis_upper_bound_cnn" else 1
    return (float(row["routing_average_cer"]), -float(row.get("macro_f1", 0.0)), deployable_priority)


def main() -> None:
    args = parse_args()
    rows = load_rows()
    model_names = resolve_models(args.models)

    predictions_all: list[dict[str, Any]] = []
    performance_rows: list[dict[str, Any]] = []
    per_class_all: list[dict[str, Any]] = []
    per_tier_all: list[dict[str, Any]] = []

    for model_name in model_names:
        preds, checkpoint = predict_for_model(model_name, rows)
        predictions_all.extend(preds)
        perf = metrics_for_predictions(model_name, preds)
        performance_rows.append(perf)
        per_class_all.extend(per_class_rows(model_name, preds))
        per_tier_all.extend(per_tier_rows(model_name, preds, rows))

    baseline_sets = []
    baseline_sets.append(fixed_route_rows(rows, "fixed_mixed_whisper", "mixed"))
    baseline_sets.append(fixed_route_rows(rows, "fixed_separated_whisper", "separated"))
    baseline_sets.append(fixed_route_rows(rows, "fixed_separated_whisper_cleaned", "cleaned"))
    baseline_sets.append(synthetic_majority_rows(rows))
    baseline_sets.append(router_v1_rows(rows))
    baseline_sets.append(router_v2_rows(rows))
    for baseline_rows in baseline_sets:
        if not baseline_rows:
            continue
        name = baseline_rows[0]["model_name"]
        predictions_all.extend(baseline_rows)
        perf = metrics_for_predictions(name, baseline_rows)
        performance_rows.append(perf)
        per_class_all.extend(per_class_rows(name, baseline_rows))
        per_tier_all.extend(per_tier_rows(name, baseline_rows, rows))

    oracle_rows = [
        {
            "sample_id": row["sample_id"],
            "split": row["split"],
            "model_name": "oracle_best",
            "true_route_label": row["best_route_label"],
            "predicted_route_label": min(
                ["mixed", "separated", "cleaned"],
                key=lambda label: route_cer(row, label),
            ),
            "predicted_confidence": 1.0,
            "predicted_method": "",
            "predicted_cer": min(route_cer(row, "mixed"), route_cer(row, "separated"), route_cer(row, "cleaned")),
            "model_status": "baseline",
        }
        for row in rows
    ]
    predictions_all.extend(oracle_rows)
    performance_rows.append(metrics_for_predictions("oracle_best", oracle_rows))
    per_class_all.extend(per_class_rows("oracle_best", oracle_rows))
    per_tier_all.extend(per_tier_rows("oracle_best", oracle_rows, rows))

    performance_rows = sorted(performance_rows, key=leaderboard_sort_key)
    router_v2_metric = next((row for row in performance_rows if row["model_name"] == "router_v2"), None)
    compare_rows = compare_to_router_v2(performance_rows, router_v2_metric)

    write_csv(PREDICTIONS_CSV, predictions_all)
    write_csv(PERFORMANCE_CSV, performance_rows)
    write_csv(PER_CLASS_CSV, per_class_all)
    write_csv(PER_TIER_CSV, per_tier_all)
    write_csv(COMPARE_TO_ROUTER_V2_CSV, compare_rows)

    top_rows = performance_rows[: min(8, len(performance_rows))]
    draw_bar_chart(top_rows, Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/figures/audio_depth_zoo_leaderboard.png"), "model_name", "routing_average_cer", "AudioDepth model zoo leaderboard")

    confusion_paths = []
    for row in performance_rows:
        if row["model_name"] in model_names:
            preds = [item for item in predictions_all if item["model_name"] == row["model_name"]]
            if preds:
                matrix = confusion_counts([item["true_route_label"] for item in preds], [item["predicted_route_label"] for item in preds])
                path = Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/figures") / f"audio_depth_zoo_confusion_{row['model_name']}.png"
                draw_confusion_matrix(matrix, path, row["model_name"])
                confusion_paths.append((row["model_name"], path))
    if confusion_paths:
        from PIL import Image, ImageDraw

        thumbs = []
        for name, path in confusion_paths[:6]:
            img = Image.open(path).convert("RGB").resize((320, 260))
            canvas = Image.new("RGB", (320, 290), "white")
            canvas.paste(img, (0, 20))
            draw = ImageDraw.Draw(canvas)
            draw.text((8, 2), name, fill=(0, 0, 0))
            thumbs.append(canvas)
        cols = 2
        rows_n = math.ceil(len(thumbs) / cols)
        sheet = Image.new("RGB", (cols * 320, rows_n * 290), "white")
        for idx, thumb in enumerate(thumbs):
            sheet.paste(thumb, ((idx % cols) * 320, (idx // cols) * 290))
        sheet.save(Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/figures/audio_depth_zoo_confusion_matrices.png"))
    SUMMARY_MD.write_text(build_summary_md(performance_rows, router_v2_metric, rows), encoding="utf-8")
    print(f"Wrote model zoo evaluation outputs to {rel(PERFORMANCE_CSV)}")


if __name__ == "__main__":
    main()
