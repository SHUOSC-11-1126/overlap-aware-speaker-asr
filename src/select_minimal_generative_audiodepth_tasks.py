from __future__ import annotations

from .generative_audiodepth_common import FIGURE_DIR, TABLE_DIR, read_rows, safe_float, write_csv, write_markdown
from .generative_audiodepth_reliability_common import draw_bar_chart


OUT_CSV = TABLE_DIR / "generative_audiodepth_task_selection.csv"
OUT_PNG = FIGURE_DIR / "generative_audiodepth_task_selection.png"
OUT_MD = FIGURE_DIR / "generative_audiodepth_task_selection.md"


COMBOS = {
    "overlap_only": ["OVERLAP_MAP"],
    "dominance_only": ["DOMINANCE_MAP"],
    "overlap_plus_dominance": ["OVERLAP_MAP", "DOMINANCE_MAP"],
    "overlap_plus_regret": ["OVERLAP_MAP", "ROUTE_REGRET"],
    "dominance_plus_regret": ["DOMINANCE_MAP", "ROUTE_REGRET"],
    "overlap_dominance_regret": ["OVERLAP_MAP", "DOMINANCE_MAP", "ROUTE_REGRET"],
    "all_five_tasks": ["OVERLAP_MAP", "DOMINANCE_MAP", "UNCERTAINTY_MAP", "ROUTE_REGRET", "REVIEW_RISK"],
    "all_excluding_uncertainty": ["OVERLAP_MAP", "DOMINANCE_MAP", "ROUTE_REGRET", "REVIEW_RISK"],
    "all_excluding_review_map": ["OVERLAP_MAP", "DOMINANCE_MAP", "UNCERTAINTY_MAP", "ROUTE_REGRET"],
}


def main() -> None:
    gap_rows = read_rows(TABLE_DIR / "generative_audiodepth_teacher_student_gap.csv")
    rank_rows = read_rows(TABLE_DIR / "generative_regret_calibration_performance.csv")
    safe_rows = read_rows(TABLE_DIR / "generative_safe_fusion_comparison.csv")
    task_mae = {}
    for task in ["OVERLAP_MAP", "DOMINANCE_MAP", "UNCERTAINTY_MAP"]:
        vals = [safe_float(row.get("mae")) for row in gap_rows if row.get("target_task") == task]
        task_mae[task] = sum(vals) / len(vals) if vals else 0.5
    rank_best = max((safe_float(row.get("pairwise_ranking_accuracy")) for row in rank_rows), default=0.0)
    safety_best = min((safe_float(row.get("false_safe_count"), 9.0) for row in safe_rows if row.get("policy_name", "").startswith("F")), default=9.0)
    rows = []
    for name, tasks in COMBOS.items():
        map_tasks = [task for task in tasks if task.endswith("_MAP")]
        map_mae = sum(task_mae.get(task, 0.0) for task in map_tasks) / len(map_tasks) if map_tasks else 0.0
        regret_score = rank_best if "ROUTE_REGRET" in tasks else 0.0
        safety_score = max(0.0, 1.0 - safety_best / 4.0) if "REVIEW_RISK" in tasks or "ROUTE_REGRET" in tasks else 0.0
        runtime_units = len(tasks)
        utility = (1.0 - map_mae) * 0.35 + regret_score * 0.35 + safety_score * 0.30 - runtime_units * 0.015
        rows.append(
            {
                "task_combo": name,
                "tasks": "|".join(tasks),
                "map_mae_proxy": round(map_mae, 6),
                "regret_ranking_score": round(regret_score, 6),
                "safety_score": round(safety_score, 6),
                "runtime_units": runtime_units,
                "utility_score": round(utility, 6),
            }
        )
    rows = sorted(rows, key=lambda r: safe_float(r["utility_score"]), reverse=True)
    write_csv(OUT_CSV, rows)
    draw_bar_chart(OUT_PNG, "Generative AudioDepth task selection utility", rows, "task_combo", "utility_score")
    best = rows[0]
    lines = [
        "# Generative AudioDepth Task Selection",
        "",
        f"Recommended minimum task set: `{best['task_combo']}`.",
        "",
        "| combo | utility | map MAE proxy | runtime units |",
        "|---|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(f"| {row['task_combo']} | {row['utility_score']} | {row['map_mae_proxy']} | {row['runtime_units']} |")
    lines.extend(["", "Task count is penalized lightly so the selection does not default to all tasks."])
    write_markdown(OUT_MD, lines)
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
