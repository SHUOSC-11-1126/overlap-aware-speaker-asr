from __future__ import annotations

from collections import defaultdict

import numpy as np

from .generative_audiodepth_common import FIGURE_DIR, TABLE_DIR, load_npy, read_rows, safe_float, write_csv, write_markdown
from .generative_audiodepth_reliability_common import RELIABILITY_TEST, RELIABILITY_TRAIN, draw_bar_chart, generated_map_features, map_task_row


OUT_CSV = TABLE_DIR / "generative_audiodepth_teacher_student_gap.csv"
OUT_PNG = FIGURE_DIR / "generative_audiodepth_teacher_student_gap.png"
OUT_MD = FIGURE_DIR / "generative_audiodepth_teacher_student_gap.md"


def nearest_train(row: dict[str, str], train_rows: list[dict[str, str]]) -> dict[str, str]:
    from .generative_audiodepth_common import feature_vector

    train_x = np.stack([feature_vector(r) for r in train_rows])
    query = feature_vector(row)
    return train_rows[int(np.argmin(np.sum((train_x - query[None, :]) ** 2, axis=1)))]


def main() -> None:
    dataset_rows = read_rows(TABLE_DIR / "generative_audiodepth_dataset.csv")
    train_rows = sorted({row["sample_id"]: row for row in read_rows(RELIABILITY_TRAIN)}.values(), key=lambda r: r["sample_id"])
    test_rows = sorted({row["sample_id"]: row for row in read_rows(RELIABILITY_TEST)}.values(), key=lambda r: r["sample_id"])
    rows = []
    for row in test_rows:
        neighbor = nearest_train(row, train_rows)
        for task in ["OVERLAP_MAP", "DOMINANCE_MAP", "UNCERTAINTY_MAP"]:
            teacher_row = map_task_row(row["sample_id"], task, dataset_rows)
            student_row = map_task_row(neighbor["sample_id"], task, dataset_rows)
            teacher = load_npy(teacher_row["target_path"])
            student = load_npy(student_row["target_path"])
            rows.append(
                {
                    "sample_id": row["sample_id"],
                    "target_task": task,
                    "student_source_sample_id": neighbor["sample_id"],
                    "mae": round(float(np.mean(np.abs(teacher - student))), 6),
                    "teacher_mean": round(float(np.mean(teacher)), 6),
                    "student_mean": round(float(np.mean(student)), 6),
                    "overlap_ratio": row.get("overlap_ratio", ""),
                    "dominance_type": row.get("dominance_type", ""),
                    "target_family": row.get("target_family", ""),
                    "oracle_route": row.get("oracle_route", ""),
                    "route_gap": row.get("route_gap", ""),
                    "review_needed": row.get("review_needed", ""),
                    "high_error_mixed": str(safe_float(row.get("mixed_cer"), 0.0) >= 0.6),
                }
            )
    write_csv(OUT_CSV, rows)
    task_rows = []
    for task in ["OVERLAP_MAP", "DOMINANCE_MAP", "UNCERTAINTY_MAP"]:
        vals = [safe_float(row["mae"]) for row in rows if row["target_task"] == task]
        task_rows.append({"target_task": task, "mae": round(float(np.mean(vals)), 6) if vals else 0.0})
    draw_bar_chart(OUT_PNG, "Teacher-student gap by map task", task_rows, "target_task", "mae")
    easiest = min(task_rows, key=lambda r: r["mae"])
    hardest = max(task_rows, key=lambda r: r["mae"])
    lines = [
        "# Generative AudioDepth Teacher-Student Gap",
        "",
        "| task | MAE |",
        "|---|---:|",
    ]
    for row in task_rows:
        lines.append(f"| {row['target_task']} | {row['mae']} |")
    lines.extend(
        [
            "",
            f"- easiest map: `{easiest['target_task']}`",
            f"- hardest map: `{hardest['target_task']}`",
        ]
    )
    if hardest["target_task"] == "UNCERTAINTY_MAP":
        lines.append("- The uncertainty target is too weakly supervised and should be removed or redesigned.")
    write_markdown(OUT_MD, lines)
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
