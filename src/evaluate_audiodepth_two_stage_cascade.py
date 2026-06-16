from __future__ import annotations

import argparse

from .audio_depth_router_common import read_csv, rel, write_csv
from .audio_depth_systematic_common import safe_float
from .audiodepth_centric_common import (
    ABLATION_CSV,
    CASCADE_COST_CSV,
    CASCADE_CSV,
    FIGURE_DIR,
    GATE_PREDICTIONS_CSV,
    ROUTES,
    accuracy,
    draw_bar,
    macro_f1_labels,
    route_cer,
    write_summary,
)
from .balanced_v2_common import BALANCED_PREDICTIONS, V2_CER, mean


COSTS = {"stage1_gate": 0.1, "mixed": 1.0, "separated": 1.8, "cleaned": 1.8, "text_probe": 0.5, "review": 5.0}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate AudioDepth Stage-1 + Stage-2 text cascade.")
    parser.add_argument("--confidence-threshold", type=float, default=0.65)
    return parser.parse_args()


def router_v2(row: dict[str, str]) -> str:
    ratio = safe_float(row.get("overlap_ratio"))
    if ratio < 0.25:
        return "mixed"
    if ratio > 0.65:
        return "separated"
    return "mixed"


def stage27_balanced(row: dict[str, str], lookup: dict[str, str]) -> str:
    return lookup.get(row["sample_id"]) or router_v2(row)


def gate_direct(label: str) -> str | None:
    if label == "easy_mixed":
        return "mixed"
    if label == "likely_separation_helpful":
        return "separated"
    return None


def add_model(rows: list[dict[str, str]], out: list[dict], name: str, fn, review_fn=None) -> None:
    for row in rows:
        route = fn(row)
        review = bool(review_fn(row)) if review_fn else False
        out.append(
            {
                "sample_id": row["sample_id"],
                "model_name": name,
                "selected_route": route,
                "oracle_route": row["oracle_route"],
                "selected_cer": route_cer(row, route),
                "oracle_cer": row["oracle_cer"],
                "route_gap": row["route_gap"],
                "review": "True" if review else "False",
                "stage2_text_probe_called": "False",
                "cost": round(COSTS["stage1_gate"] + COSTS[route] + (COSTS["review"] if review else 0.0), 6),
            }
        )


def main() -> None:
    args = parse_args()
    rows = read_csv(V2_CER)
    gate = {row["sample_id"]: row for row in read_csv(GATE_PREDICTIONS_CSV)}
    balanced_lookup = {
        row["sample_id"]: row["predicted_route"]
        for row in read_csv(BALANCED_PREDICTIONS)
        if row.get("model_name") == "audio_depth_balanced_route_winner_router"
    } if BALANCED_PREDICTIONS.exists() else {}
    rows = [row for row in rows if row["sample_id"] in gate]
    preds: list[dict] = []
    add_model(rows, preds, "fixed_mixed", lambda row: "mixed")
    add_model(rows, preds, "fixed_separated", lambda row: "separated")
    add_model(rows, preds, "router_v2", router_v2)
    add_model(rows, preds, "stage27_balanced_router_if_available", lambda row: stage27_balanced(row, balanced_lookup))
    add_model(rows, preds, "oracle", lambda row: row["oracle_route"])
    for row in rows:
        g = gate[row["sample_id"]]
        direct = gate_direct(g["predicted_gate_label"])
        selected = direct or router_v2(row)
        review = g["predicted_gate_label"] == "review_risk"
        preds.append(
            {
                "sample_id": row["sample_id"],
                "model_name": "audiodepth_stage1_only",
                "selected_route": selected,
                "oracle_route": row["oracle_route"],
                "selected_cer": route_cer(row, selected),
                "oracle_cer": row["oracle_cer"],
                "route_gap": row["route_gap"],
                "review": "True" if review else "False",
                "stage2_text_probe_called": "False",
                "cost": round(COSTS["stage1_gate"] + COSTS[selected] + (COSTS["review"] if review else 0.0), 6),
                "gate_label": g["predicted_gate_label"],
                "gate_confidence": g["confidence"],
            }
        )
        if direct and safe_float(g["confidence"]) >= args.confidence_threshold:
            selected2 = direct
            text_probe = False
        else:
            selected2 = router_v2(row)
            text_probe = True
        review2 = g["predicted_gate_label"] == "review_risk"
        preds.append(
            {
                "sample_id": row["sample_id"],
                "model_name": "audiodepth_stage1_plus_text_stage2",
                "selected_route": selected2,
                "oracle_route": row["oracle_route"],
                "selected_cer": route_cer(row, selected2),
                "oracle_cer": row["oracle_cer"],
                "route_gap": row["route_gap"],
                "review": "True" if review2 else "False",
                "stage2_text_probe_called": "True" if text_probe else "False",
                "cost": round(COSTS["stage1_gate"] + COSTS[selected2] + (COSTS["text_probe"] if text_probe else 0.0) + (COSTS["review"] if review2 else 0.0), 6),
                "gate_label": g["predicted_gate_label"],
                "gate_confidence": g["confidence"],
            }
        )
    comparison = []
    for model in sorted({row["model_name"] for row in preds}):
        bucket = [row for row in preds if row["model_name"] == model]
        y_true = [row["oracle_route"] for row in bucket]
        y_pred = [row["selected_route"] for row in bucket]
        direct = sum(1 for row in bucket if row.get("stage2_text_probe_called") == "False")
        sep_calls = sum(1 for row in bucket if row["selected_route"] in {"separated", "cleaned"})
        false_safe = sum(1 for row in bucket if row["selected_route"] == "mixed" and safe_float(row["selected_cer"]) > 0.6)
        comparison.append(
            {
                "model_name": model,
                "selected_route_cer": mean([safe_float(row["selected_cer"]) for row in bucket]),
                "route_accuracy": accuracy(y_true, y_pred),
                "macro_f1": macro_f1_labels(y_true, y_pred, ROUTES),
                "asr_text_probe_reduction_rate": round(direct / max(len(bucket), 1), 6),
                "separation_call_rate": round(sep_calls / max(len(bucket), 1), 6),
                "false_safe_rate": round(false_safe / max(len(bucket), 1), 6),
                "review_rate": round(sum(1 for row in bucket if row["review"] == "True") / max(len(bucket), 1), 6),
                "average_cost": mean([safe_float(row["cost"]) for row in bucket]),
                "sample_count": len(bucket),
            }
        )
    comparison = sorted(comparison, key=lambda row: (safe_float(row["selected_route_cer"]), safe_float(row["average_cost"])))
    write_csv(CASCADE_CSV, preds)
    write_csv(CASCADE_COST_CSV, comparison)
    draw_bar(comparison, FIGURE_DIR / "audiodepth_two_stage_pareto.png", "model_name", "selected_route_cer", "AudioDepth two-stage CER/cost frontier")
    best = comparison[0] if comparison else {}
    two = next((row for row in comparison if row["model_name"] == "audiodepth_stage1_plus_text_stage2"), {})
    write_summary(
        FIGURE_DIR / "audiodepth_two_stage_summary.md",
        "AudioDepth Two-Stage Cascade",
        [
            f"- evaluated samples: `{len(rows)}`",
            f"- best CER row: `{best.get('model_name', '')}` `{best.get('selected_route_cer', '')}`",
            f"- two-stage CER: `{two.get('selected_route_cer', '')}`",
            f"- two-stage text-probe reduction: `{two.get('asr_text_probe_reduction_rate', '')}`",
            f"- two-stage false-safe rate: `{two.get('false_safe_rate', '')}`",
            "- Interpretation: AudioDepth is evaluated as a pre-ASR acoustic gate, not as a replacement for text instability features.",
        ],
    )
    print(f"Wrote two-stage cascade to {rel(CASCADE_COST_CSV)}")


if __name__ == "__main__":
    main()
