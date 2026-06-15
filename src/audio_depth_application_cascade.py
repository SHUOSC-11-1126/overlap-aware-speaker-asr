from __future__ import annotations

import numpy as np

from .audio_depth_router_common import draw_bar_chart, read_csv, rel, write_csv
from .audio_depth_systematic_common import COST_CASCADE_CSV, PREDICTIONS_CSV, ROUTE_COSTS, SYSTEMATIC_FIGURE_PREFIX, safe_float


def main() -> None:
    rows = [row for row in read_csv(PREDICTIONS_CSV) if row["model_name"] == "calibrated_confidence_router"]
    output = []
    for threshold in [0.45, 0.55, 0.65, 0.75, 0.85]:
        selected = []
        costs = []
        review = 0
        for row in rows:
            confidence = safe_float(row.get("confidence"), 0.0)
            route = row["predicted_route_label"]
            cost = ROUTE_COSTS[route]
            cer = safe_float(row["predicted_cer"])
            if confidence < threshold:
                review += 1
                cost = ROUTE_COSTS["llm_critic"] if confidence >= threshold - 0.15 else ROUTE_COSTS["strong_asr"]
            selected.append(cer)
            costs.append(cost)
        output.append(
            {
                "policy": f"confidence_threshold_{threshold}",
                "average_cer": round(float(np.mean(selected)), 6) if selected else 0.0,
                "average_cost": round(float(np.mean(costs)), 6) if costs else 0.0,
                "review_rate": round(review / len(rows), 6) if rows else 0.0,
                "saved_cost_vs_all_strong": round(1.0 - (float(np.mean(costs)) / ROUTE_COSTS["strong_asr"]), 6) if costs else 0.0,
                "evidence_type": "simulated_cost_extension",
            }
        )
    write_csv(COST_CASCADE_CSV, output)
    draw_bar_chart(output, SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_cer_cost_pareto.png", "policy", "average_cer", "Systematic cost cascade CER")
    (SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_application_cascade.md").write_text(
        "# AudioDepth Application Cascade\n\nThis simulated application layer uses router confidence to trade routing CER, compute cost, and review burden. Costs for `strong_asr`, `llm_critic`, and `manual_review` are simulated and are not hardware measurements.\n",
        encoding="utf-8",
    )
    print(f"Wrote application cascade to {rel(COST_CASCADE_CSV)}")


if __name__ == "__main__":
    main()
