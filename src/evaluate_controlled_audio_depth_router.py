from __future__ import annotations

from .audio_depth_router_common import PROJECT_ROOT, ROUTE_LABELS, read_csv, rel, write_csv
from .audio_depth_systematic_common import ROUTE_COSTS, safe_float
import json
from pathlib import Path

import numpy as np

from .controlled_benchmark_common import CER_CSV, FIGURE_DIR, MODEL_DIR, ROUTER_COMPARISON_CSV, ROUTER_PREDICTIONS_CSV, draw_bar
from .train_controlled_audio_depth_router import features


def avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 6) if values else 0.0


def router_v2(row: dict[str, str]) -> str:
    ratio = safe_float(row.get("overlap_ratio"), 0.0)
    if ratio < 0.25:
        return "mixed"
    if ratio > 0.65:
        return "separated"
    return "mixed"


def heuristic_hybrid(row: dict[str, str]) -> str:
    ratio = safe_float(row.get("overlap_ratio"), 0.0)
    dom = row.get("dominance_type", "")
    if ratio < 0.2:
        return "mixed"
    if ratio >= 0.6 and dom == "balanced":
        return "separated"
    if ratio >= 0.7:
        return "separated"
    if ratio >= 0.4:
        return "cleaned"
    return "mixed"


def route_cer(row: dict[str, str], route: str) -> float:
    return safe_float(row[f"{route}_cer"])


def add_predictions(rows: list[dict[str, str]], out: list[dict], model: str, fn) -> None:
    for row in rows:
        pred = fn(row)
        out.append(
            {
                "sample_id": row["sample_id"],
                "model_name": model,
                "predicted_route": pred,
                "oracle_route": row["oracle_route"],
                "predicted_cer": route_cer(row, pred),
                "oracle_cer": row["oracle_cer"],
                "route_gap": row["route_gap"],
                "expected_cost": ROUTE_COSTS.get(pred, 1.0),
            }
        )


def add_trained_model_predictions(rows: list[dict[str, str]], out: list[dict]) -> None:
    for path in sorted(MODEL_DIR.glob("audio_depth_controlled_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        labels = payload["labels"]
        w = np.asarray(payload["weights"], dtype=np.float32)
        b = np.asarray(payload["bias"], dtype=np.float32)
        mean = np.asarray(payload["mean"], dtype=np.float32)
        std = np.asarray(payload["std"], dtype=np.float32)
        model_name = Path(path).stem.replace("audio_depth_controlled_", "")
        for row in rows:
            x = (np.asarray(features(row), dtype=np.float32) - mean) / std
            route = labels[int(np.argmax(x @ w + b))]
            out.append(
                {
                    "sample_id": row["sample_id"],
                    "model_name": model_name,
                    "predicted_route": route,
                    "oracle_route": row["oracle_route"],
                    "predicted_cer": route_cer(row, route),
                    "oracle_cer": row["oracle_cer"],
                    "route_gap": row["route_gap"],
                    "expected_cost": ROUTE_COSTS.get(route, 1.0),
                }
            )


def main() -> None:
    rows = read_csv(CER_CSV)
    preds: list[dict] = []
    add_predictions(rows, preds, "fixed_mixed", lambda row: "mixed")
    add_predictions(rows, preds, "fixed_separated", lambda row: "separated")
    add_predictions(rows, preds, "fixed_cleaned", lambda row: "cleaned")
    add_predictions(rows, preds, "router_v2", router_v2)
    add_predictions(rows, preds, "stage22_model_zoo_best_blocked_feature_mismatch", lambda row: "separated")
    add_predictions(rows, preds, "stage23_systematic_heuristic", heuristic_hybrid)
    add_predictions(rows, preds, "confidence_cascade_controlled", lambda row: heuristic_hybrid(row) if safe_float(row["route_gap"]) >= 0.03 else router_v2(row))
    add_predictions(rows, preds, "oracle", lambda row: row["oracle_route"])
    add_trained_model_predictions(rows, preds)
    comparison = []
    for model in sorted({row["model_name"] for row in preds}):
        bucket = [row for row in preds if row["model_name"] == model]
        comparison.append(
            {
                "model_name": model,
                "average_cer": avg([safe_float(row["predicted_cer"]) for row in bucket]),
                "accuracy_vs_oracle_route": avg([1.0 if row["predicted_route"] == row["oracle_route"] else 0.0 for row in bucket]),
                "sample_count": len(bucket),
                "status": "blocked_old_model_feature_mismatch" if "blocked" in model else "evaluated",
            }
        )
    comparison = sorted(comparison, key=lambda row: safe_float(row["average_cer"]))
    write_csv(ROUTER_PREDICTIONS_CSV, preds)
    write_csv(ROUTER_COMPARISON_CSV, comparison)
    draw_bar(comparison, FIGURE_DIR / "controlled_audio_depth_router_leaderboard.png", "model_name", "average_cer", "Controlled router leaderboard")
    best = comparison[0] if comparison else {}
    (FIGURE_DIR / "controlled_audio_depth_router_summary.md").write_text(
        "\n".join(
            [
                "# Controlled AudioDepth Router Summary",
                "",
                f"- Samples: `{len(rows)}`",
                f"- Best row: `{best.get('model_name', '')}` CER `{best.get('average_cer', '')}`",
                "- Old Stage 22 model is marked blocked/feature-mismatch rather than forced into an incompatible feature space.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote controlled router comparison to {rel(ROUTER_COMPARISON_CSV)}")


if __name__ == "__main__":
    main()
