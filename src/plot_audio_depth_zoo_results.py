from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from .audio_depth_router_common import draw_bar_chart, read_csv, rel
from .audio_depth_zoo_common import PERFORMANCE_CSV, SUMMARY_MD


def load_perf() -> list[dict[str, Any]]:
    return read_csv(PERFORMANCE_CSV) if PERFORMANCE_CSV.exists() else []


def model_family(model_name: str) -> str:
    if model_name == "mlp_handcrafted":
        return "handcrafted"
    if model_name == "cnn_logmel":
        return "logmel"
    if model_name in {"cnn_depth", "cnn_depth_balanced", "analysis_upper_bound_cnn"}:
        return "depth-cnn"
    if model_name == "resnet_tiny_depth":
        return "resnet"
    if model_name == "crnn_depth":
        return "crnn"
    if model_name == "patch_transformer_depth":
        return "transformer"
    if model_name == "hybrid_late_fusion":
        return "hybrid"
    return "baseline"


def draw_matrix(rows: list[dict[str, Any]], output_path: Path) -> None:
    headers = ["model", "family", "CER", "macro-F1", "status"]
    width = 1120
    row_h = 42
    canvas = Image.new("RGB", (width, 60 + row_h * (len(rows) + 1)), "white")
    draw = ImageDraw.Draw(canvas)
    col_x = [20, 280, 460, 620, 820]
    for x, header in zip(col_x, headers):
        draw.text((x, 18), header, fill=(0, 0, 0))
    for idx, row in enumerate(rows):
        y = 60 + idx * row_h
        draw.text((col_x[0], y), str(row["model_name"]), fill=(0, 0, 0))
        draw.text((col_x[1], y), model_family(str(row["model_name"])), fill=(0, 0, 0))
        draw.text((col_x[2], y), f"{float(row['routing_average_cer']):.6f}", fill=(0, 0, 0))
        draw.text((col_x[3], y), f"{float(row.get('macro_f1', 0.0)):.6f}", fill=(0, 0, 0))
        draw.text((col_x[4], y), str(row.get("model_status", "")), fill=(0, 0, 0))
    canvas.save(output_path)


def family_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        if row["model_name"] in {"fixed_mixed_whisper", "fixed_separated_whisper", "fixed_separated_whisper_cleaned", "majority_route_baseline", "router_v1", "router_v2", "oracle_best"}:
            grouped["baseline"].append(float(row["routing_average_cer"]))
        else:
            grouped[model_family(str(row["model_name"]))].append(float(row["routing_average_cer"]))
    return [{"family": family, "routing_average_cer": round(float(np.mean(values)), 6), "sample_count": len(values)} for family, values in sorted(grouped.items()) if values]


def build_summary(rows: list[dict[str, Any]]) -> str:
    frontier_rows = [row for row in rows if row.get("label") == "experimental/frontier"]
    best = min(frontier_rows, key=lambda r: float(r["routing_average_cer"])) if frontier_rows else {}
    oracle = next((row for row in rows if row["model_name"] == "oracle_best"), None)
    router_v2 = next((row for row in rows if row["model_name"] == "router_v2"), None)
    hybrid = next((row for row in rows if row["model_name"] == "hybrid_late_fusion"), None)
    cascade = read_csv(Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/tables/audio_depth_zoo_confidence_cascade.csv")) if Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/tables/audio_depth_zoo_confidence_cascade.csv").exists() else []
    lines = [
        "# AudioDepth Zoo Plot Summary",
        "",
        "The ablation matrix and family comparison are meant to keep the frontier story honest: what helped, what barely moved, and what still needs hybrid signal.",
        "",
        f"Best frontier model: `{best.get('model_name', '')}` with CER `{best.get('routing_average_cer', '')}`.",
        "",
    ]
    if router_v2:
        lines.append(f"Matched router_v2 CER: `{router_v2.get('routing_average_cer', '')}`.")
    if oracle:
        lines.append(f"Oracle upper bound CER: `{oracle.get('routing_average_cer', '')}`.")
    if hybrid:
        lines.append(f"Hybrid late fusion CER: `{hybrid.get('routing_average_cer', '')}`.")
    if cascade:
        best_cascade = min(cascade, key=lambda row: float(row["routing_average_cer"]))
        lines.append(f"Best confidence cascade threshold: `{best_cascade.get('threshold', '')}` with CER `{best_cascade.get('routing_average_cer', '')}`.")
    lines.extend(
        [
            "",
            "If the hybrid rows do not beat the pure depth CNNs, that still tells us something useful: transcript-instability features may be necessary at routing time, not just helpful as a late add-on.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    rows = load_perf()
    if not rows:
        return
    rows = sorted(rows, key=lambda row: float(row["routing_average_cer"]))
    draw_matrix(rows, Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/figures/audio_depth_zoo_ablation_matrix.png"))
    family = family_rows(rows)
    draw_bar_chart(family, Path("/Users/ark/Documents/机器学习/overlap-aware-speaker-asr/results/figures/audio_depth_zoo_model_family_comparison.png"), "family", "routing_average_cer", "AudioDepth family comparison")
    SUMMARY_MD.write_text(build_summary(rows), encoding="utf-8")
    print("Wrote AudioDepth zoo plot summaries")


if __name__ == "__main__":
    main()
