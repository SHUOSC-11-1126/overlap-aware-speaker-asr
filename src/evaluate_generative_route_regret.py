from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from .generative_audiodepth_common import ROUTES, TEST_CSV, TRAIN_CSV, read_rows, safe_float, spearman, unique_samples, write_csv, write_markdown, FIGURE_DIR
from .generative_audiodepth_models import direct_regret_predict, select_route_from_regret


PREDICTIONS_CSV = Path("results/tables/generative_route_regret_predictions.csv")
PERFORMANCE_CSV = Path("results/tables/generative_route_regret_performance.csv")
SUMMARY_MD = FIGURE_DIR / "generative_route_regret_summary.md"
CALIBRATION_PNG = FIGURE_DIR / "generative_route_regret_calibration.png"


def cer_for_route(row: dict[str, Any], route: str) -> float:
    return safe_float(row.get(f"{route}_cer"), 1.0)


def true_regret_vector(row: dict[str, Any]) -> np.ndarray:
    return np.asarray([safe_float(row.get(f"{route}_regret"), 0.0) for route in ROUTES], dtype=np.float32)


def evaluate_policy(rows: list[dict[str, Any]], policy_name: str, cost_weight: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    train_samples = unique_samples(read_rows(TRAIN_CSV))
    pred_rows: list[dict[str, Any]] = []
    true_all: list[float] = []
    pred_all: list[float] = []
    selected_cers = []
    oracle_cers = []
    review_needed_count = 0
    review_recalled = 0
    false_safe = 0
    correct = 0
    for row in rows:
        pred = direct_regret_predict(row, train_samples)
        true = true_regret_vector(row)
        route = select_route_from_regret(pred, cost_weight=cost_weight)
        oracle = row.get("oracle_route", "")
        selected_cer = cer_for_route(row, route)
        oracle_cer = min(cer_for_route(row, r) for r in ROUTES)
        review_needed = row.get("review_needed") == "True"
        predicted_review = bool(np.min(pred) > 0.18 or safe_float(row.get("route_gap"), 1.0) <= 0.02)
        if review_needed:
            review_needed_count += 1
            if predicted_review:
                review_recalled += 1
        if safe_float(row.get("mixed_cer"), 0.0) >= 0.6 and route == "mixed":
            false_safe += 1
        if route == oracle:
            correct += 1
        selected_cers.append(selected_cer)
        oracle_cers.append(oracle_cer)
        true_all.extend(true.tolist())
        pred_all.extend(pred.tolist())
        pred_rows.append(
            {
                "sample_id": row["sample_id"],
                "policy_name": policy_name,
                "predicted_mixed_regret": round(float(pred[0]), 6),
                "predicted_separated_regret": round(float(pred[1]), 6),
                "predicted_cleaned_regret": round(float(pred[2]), 6),
                "true_mixed_regret": round(float(true[0]), 6),
                "true_separated_regret": round(float(true[1]), 6),
                "true_cleaned_regret": round(float(true[2]), 6),
                "predicted_route": route,
                "oracle_route": oracle,
                "selected_route_cer": round(float(selected_cer), 6),
                "oracle_cer": round(float(oracle_cer), 6),
                "review_needed": row.get("review_needed", ""),
                "predicted_review": str(predicted_review),
            }
        )
    perf = {
        "policy_name": policy_name,
        "cost_weight": cost_weight,
        "sample_count": len(rows),
        "regret_mae": round(float(np.mean(np.abs(np.asarray(pred_all) - np.asarray(true_all)))), 6) if pred_all else 0.0,
        "regret_spearman": spearman(pred_all, true_all),
        "route_accuracy": round(correct / len(rows), 6) if rows else 0.0,
        "selected_route_cer": round(float(np.mean(selected_cers)), 6) if selected_cers else 0.0,
        "average_realized_regret": round(float(np.mean(np.asarray(selected_cers) - np.asarray(oracle_cers))), 6) if selected_cers else 0.0,
        "oracle_gap": round(float(np.mean(np.asarray(selected_cers) - np.asarray(oracle_cers))), 6) if selected_cers else 0.0,
        "false_safe_count": false_safe,
        "review_recall": round(review_recalled / review_needed_count, 6) if review_needed_count else 0.0,
    }
    return pred_rows, perf


def draw_calibration(pred_rows: list[dict[str, Any]]) -> None:
    no_cost_rows = [row for row in pred_rows if row["policy_name"] == "generative_regret_no_cost"]
    points = []
    for row in no_cost_rows:
        for route in ROUTES:
            points.append(
                (
                    safe_float(row.get(f"predicted_{route}_regret"), 0.0),
                    safe_float(row.get(f"true_{route}_regret"), 0.0),
                    route,
                )
            )
    width, height = 720, 560
    margin_left, margin_top, plot_size = 82, 56, 420
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "Generative route-regret calibration", fill=(0, 0, 0))
    draw.text((margin_left + 88, height - 42), "Predicted regret", fill=(0, 0, 0))
    draw.text((18, margin_top + 190), "True regret", fill=(0, 0, 0))
    max_value = max([0.25] + [value for point in points for value in point[:2]])
    max_value = min(max_value * 1.15, 1.0)
    x0, y0 = margin_left, margin_top + plot_size
    x1, y1 = margin_left + plot_size, margin_top
    draw.rectangle((x0, y1, x1, y0), outline=(120, 120, 120), width=1)
    for frac in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x = x0 + int(plot_size * frac)
        y = y0 - int(plot_size * frac)
        draw.line((x, y0, x, y0 + 5), fill=(90, 90, 90))
        draw.line((x0 - 5, y, x0, y), fill=(90, 90, 90))
        label = f"{max_value * frac:.2f}"
        draw.text((x - 14, y0 + 10), label, fill=(70, 70, 70))
        draw.text((x0 - 52, y - 7), label, fill=(70, 70, 70))
        if frac not in [0.0, 1.0]:
            draw.line((x, y0, x, y1), fill=(230, 230, 230))
            draw.line((x0, y, x1, y), fill=(230, 230, 230))
    draw.line((x0, y0, x1, y1), fill=(60, 60, 60), width=2)
    colors = {"mixed": (46, 105, 172), "separated": (33, 145, 89), "cleaned": (197, 88, 38)}
    for pred, true, route in points:
        x = x0 + int(plot_size * max(0.0, min(pred / max_value, 1.0)))
        y = y0 - int(plot_size * max(0.0, min(true / max_value, 1.0)))
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=colors[route], outline="white")
    legend_x, legend_y = x1 + 34, y1 + 36
    draw.text((legend_x, legend_y - 24), "Route channel", fill=(0, 0, 0))
    for idx, route in enumerate(ROUTES):
        y = legend_y + idx * 28
        draw.rectangle((legend_x, y, legend_x + 18, y + 18), fill=colors[route])
        draw.text((legend_x + 28, y + 2), route, fill=(0, 0, 0))
    draw.text((legend_x, legend_y + 106), "Diagonal is ideal.", fill=(80, 80, 80))
    draw.text((legend_x, legend_y + 128), "Targets are sample-level", fill=(80, 80, 80))
    draw.text((legend_x, legend_y + 146), "regrets, not CER maps.", fill=(80, 80, 80))
    CALIBRATION_PNG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(CALIBRATION_PNG)


def main() -> None:
    rows = unique_samples(read_rows(TEST_CSV))
    pred_no_cost, perf_no_cost = evaluate_policy(rows, "generative_regret_no_cost", 0.0)
    pred_cost, perf_cost = evaluate_policy(rows, "generative_regret_cost_aware", 0.04)
    pred_rows = pred_no_cost + pred_cost
    write_csv(PREDICTIONS_CSV, pred_rows)
    write_csv(PERFORMANCE_CSV, [perf_no_cost, perf_cost])
    draw_calibration(pred_rows)
    lines = [
        "# Generative Route-Regret Summary",
        "",
        "This evaluation treats route regret as a sample-level vector. It does not claim local CER maps.",
        "",
        "| policy | regret MAE | Spearman | route accuracy | selected CER | false-safe | review recall |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in [perf_no_cost, perf_cost]:
        lines.append(
            f"| {row['policy_name']} | {row['regret_mae']} | {row['regret_spearman']} | {row['route_accuracy']} | {row['selected_route_cer']} | {row['false_safe_count']} | {row['review_recall']} |"
        )
    write_markdown(SUMMARY_MD, lines)
    print(f"Wrote route-regret evaluation for {len(rows)} samples")


if __name__ == "__main__":
    main()
