from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from .audio_depth_router_common import LABEL_TO_METHOD, ROUTE_LABELS, draw_bar_chart, macro_f1, read_csv, rel, route_cer, write_csv
from .audio_depth_zoo_common import CONFIDENCE_CASCADE_CSV, FEATURES_CSV, PERFORMANCE_CSV, PREDICTIONS_CSV


THRESHOLDS = [0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


def load_rows() -> list[dict[str, Any]]:
    if not PREDICTIONS_CSV.exists():
        return []
    feature_lookup = {row["sample_id"]: row for row in read_csv(FEATURES_CSV)} if FEATURES_CSV.exists() else {}
    rows = []
    for row in read_csv(PREDICTIONS_CSV):
        if row.get("split") != "test" or row.get("model_name") not in {"cnn_logmel", "cnn_depth", "cnn_depth_balanced", "resnet_tiny_depth", "crnn_depth", "patch_transformer_depth", "hybrid_late_fusion", "mlp_handcrafted", "analysis_upper_bound_cnn"}:
            continue
        source = feature_lookup.get(row["sample_id"], {})
        rows.append({**source, **row})
    return rows


def load_performance() -> list[dict[str, Any]]:
    return read_csv(PERFORMANCE_CSV) if PERFORMANCE_CSV.exists() else []


def select_best_model(performance: list[dict[str, Any]]) -> str:
    deployable = [row for row in performance if row.get("model_name") in {"mlp_handcrafted", "cnn_logmel", "cnn_depth", "cnn_depth_balanced", "resnet_tiny_depth", "crnn_depth", "patch_transformer_depth", "hybrid_late_fusion"}]
    if not deployable:
        return "cnn_depth"
    deployable.sort(key=lambda row: (float(row.get("routing_average_cer", 99.0)), -float(row.get("macro_f1", 0.0))))
    return str(deployable[0]["model_name"])


def router_v2_for_rows(rows: list[dict[str, Any]]) -> list[str]:
    routing_path = Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/tables/synthetic_split_routing_decisions.csv")
    if not routing_path.exists():
        return ["mixed"] * len(rows)
    lookup = {}
    for row in read_csv(routing_path):
        if row.get("strategy") == "v2_full_features":
            method = row.get("selected_method", "")
            lookup[row["sample_id"]] = "separated" if method == "separated_whisper" else "cleaned" if method == "separated_whisper_cleaned" else "mixed"
    return [lookup.get(row["sample_id"], "mixed") for row in rows]


def evaluate_threshold(rows: list[dict[str, Any]], threshold: float, router_v2_labels: list[str]) -> dict[str, Any]:
    chosen = []
    fallback_count = 0
    confident_gold = []
    confident_pred = []
    for row, router_v2_label in zip(rows, router_v2_labels):
        confidence = float(row.get("predicted_confidence", 0.0))
        audio_pred = row.get("predicted_route_label", "mixed")
        if confidence >= threshold:
            chosen_label = audio_pred
            chosen.append(1)
            confident_gold.append(row["true_route_label"])
            confident_pred.append(audio_pred)
        else:
            chosen_label = router_v2_label
            chosen.append(0)
            fallback_count += 1
        row["_cascade_choice"] = chosen_label
    routing_cers = [route_cer(row, row["_cascade_choice"]) for row in rows]
    confident_macro_f1 = macro_f1(confident_gold, confident_pred) if confident_gold else 0.0
    router_v2_cers = [route_cer(row, router_v2_label) for row, router_v2_label in zip(rows, router_v2_labels)]
    return {
        "threshold": threshold,
        "coverage": round(sum(chosen) / len(rows), 6) if rows else 0.0,
        "fallback_rate": round(fallback_count / len(rows), 6) if rows else 0.0,
        "routing_average_cer": round(float(np.mean(routing_cers)) if routing_cers else 0.0, 6),
        "macro_f1_confident_subset": round(confident_macro_f1, 6),
        "router_v2_average_cer": round(float(np.mean(router_v2_cers)) if router_v2_cers else 0.0, 6),
        "delta_vs_router_v2": round((float(np.mean(routing_cers)) if routing_cers else 0.0) - (float(np.mean(router_v2_cers)) if router_v2_cers else 0.0), 6),
        "confident_sample_count": int(sum(chosen)),
        "fallback_sample_count": int(fallback_count),
        "selected_model": rows[0].get("model_name", ""),
    }


def main() -> None:
    rows = load_rows()
    performance = load_performance()
    if not rows:
        write_csv(CONFIDENCE_CASCADE_CSV, [])
        return
    selected_model = select_best_model(performance)
    rows = [row for row in rows if row.get("model_name") == selected_model]
    router_v2_labels = router_v2_for_rows(rows)
    table = [evaluate_threshold(rows, threshold, router_v2_labels) for threshold in THRESHOLDS]
    write_csv(CONFIDENCE_CASCADE_CSV, table, ["threshold", "selected_model", "coverage", "fallback_rate", "routing_average_cer", "macro_f1_confident_subset", "router_v2_average_cer", "delta_vs_router_v2", "confident_sample_count", "fallback_sample_count"])
    draw_bar_chart(table, Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/figures/audio_depth_zoo_confidence_cascade.png"), "threshold", "routing_average_cer", "AudioDepth confidence cascade")
    print(f"Wrote confidence cascade table to {rel(CONFIDENCE_CASCADE_CSV)}")


if __name__ == "__main__":
    main()
