from __future__ import annotations

import json
from collections import defaultdict

import numpy as np

from .audio_depth_router_common import ROUTE_LABELS, read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .balanced_v2_common import BALANCED_COMPARISON, BALANCED_PER_FAMILY, BALANCED_PER_ORACLE_ROUTE, BALANCED_PREDICTIONS, FIGURE_DIR, MODEL_DIR, V2_CER, mean, route_cer
from .controlled_benchmark_common import draw_bar
from .train_balanced_audio_depth_router import features


def router_v2(row: dict[str, str]) -> str:
    ratio = safe_float(row.get("overlap_ratio"))
    if ratio < 0.25:
        return "mixed"
    if ratio > 0.65:
        return "separated"
    return "mixed"


def balanced_prior(row: dict[str, str]) -> str:
    family = row.get("intended_family", "")
    if family.startswith("mixed"):
        return "mixed"
    if family.startswith("separated"):
        return "separated"
    if family.startswith("cleaned"):
        return "cleaned"
    return router_v2(row)


def model_route(row: dict[str, str]) -> str:
    path = MODEL_DIR / "audio_depth_balanced_route_winner_router.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    x = np.asarray(features(row), dtype=np.float32)
    x = (x - np.asarray(payload["mean"], dtype=np.float32)) / np.asarray(payload["std"], dtype=np.float32)
    logits = x @ np.asarray(payload["weights"], dtype=np.float32) + np.asarray(payload["bias"], dtype=np.float32)
    return payload["labels"][int(np.argmax(logits))]


def add_predictions(rows: list[dict[str, str]], out: list[dict], model_name: str, fn) -> None:
    for row in rows:
        route = fn(row)
        out.append(
            {
                "sample_id": row["sample_id"],
                "model_name": model_name,
                "predicted_route": route,
                "oracle_route": row["oracle_route"],
                "predicted_cer": route_cer(row, route),
                "oracle_cer": row["oracle_cer"],
                "route_gap": row["route_gap"],
                "intended_family": row["intended_family"],
            }
        )


def main() -> None:
    rows = read_csv(V2_CER)
    preds: list[dict] = []
    add_predictions(rows, preds, "fixed_mixed", lambda row: "mixed")
    add_predictions(rows, preds, "fixed_separated", lambda row: "separated")
    add_predictions(rows, preds, "fixed_cleaned", lambda row: "cleaned")
    add_predictions(rows, preds, "router_v2", router_v2)
    add_predictions(rows, preds, "balanced_family_prior", balanced_prior)
    add_predictions(rows, preds, "audio_depth_balanced_route_winner_router", model_route)
    add_predictions(rows, preds, "oracle", lambda row: row["oracle_route"])
    comparison = []
    for model_name in sorted({row["model_name"] for row in preds}):
        bucket = [row for row in preds if row["model_name"] == model_name]
        comparison.append(
            {
                "model_name": model_name,
                "average_cer": mean([safe_float(row["predicted_cer"]) for row in bucket]),
                "accuracy_vs_oracle_route": mean([1.0 if row["predicted_route"] == row["oracle_route"] else 0.0 for row in bucket]),
                "sample_count": len(bucket),
                "predicted_mixed_count": sum(1 for row in bucket if row["predicted_route"] == "mixed"),
                "predicted_separated_count": sum(1 for row in bucket if row["predicted_route"] == "separated"),
                "predicted_cleaned_count": sum(1 for row in bucket if row["predicted_route"] == "cleaned"),
            }
        )
    comparison = sorted(comparison, key=lambda row: safe_float(row["average_cer"]))
    write_csv(BALANCED_PREDICTIONS, preds)
    write_csv(BALANCED_COMPARISON, comparison)
    draw_bar(comparison, FIGURE_DIR / "audio_depth_balanced_router_leaderboard.png", "model_name", "average_cer", "Balanced v2 router CER")
    for key, path in [("intended_family", BALANCED_PER_FAMILY), ("oracle_route", BALANCED_PER_ORACLE_ROUTE)]:
        grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
        for row in preds:
            grouped[(row[key], row["model_name"])].append(safe_float(row["predicted_cer"]))
        write_csv(path, [{"group": group, "model_name": model, "average_cer": mean(vals), "sample_count": len(vals)} for (group, model), vals in sorted(grouped.items())])
    print(f"Wrote balanced router comparison to {rel(BALANCED_COMPARISON)}")


if __name__ == "__main__":
    main()
