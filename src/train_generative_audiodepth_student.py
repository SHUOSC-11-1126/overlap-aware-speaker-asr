from __future__ import annotations

from pathlib import Path

import numpy as np

from .generative_audiodepth_common import FIGURE_DIR, MAP_TASKS, TEST_CSV, TRAIN_CSV, load_npy, read_rows, unique_samples, write_csv, write_markdown
from .generative_audiodepth_models import build_promptable_prototype


DISTILLATION_CSV = Path("results/tables/generative_audiodepth_distillation.csv")
GAP_MD = FIGURE_DIR / "generative_audiodepth_teacher_student_gap.md"


def main() -> None:
    train_rows = read_rows(TRAIN_CSV)
    test_rows = read_rows(TEST_CSV)
    model = build_promptable_prototype(unique_samples(train_rows), train_rows, load_npy)
    rows = []
    for task in sorted(MAP_TASKS):
        errors = []
        for row in test_rows:
            if row["target_task"] != task:
                continue
            teacher = load_npy(row["target_path"])
            student = model.predict(row, task)
            errors.append(float(np.mean(np.abs(student - teacher))))
        rows.append(
            {
                "task": task,
                "teacher_source": "analysis_only_source_track_map" if task != "UNCERTAINTY_MAP" else "weak_uncertainty_target",
                "student_input": "mixed_only_deployable_audiodepth_metadata",
                "test_samples": len(errors),
                "student_teacher_mae": round(float(np.mean(errors)), 6) if errors else 0.0,
                "gap_interpretation": "prototype_student_recovers_partial_structure_only",
            }
        )
    write_csv(DISTILLATION_CSV, rows)
    lines = [
        "# Generative AudioDepth Teacher-Student Gap",
        "",
        "Teacher maps may use source tracks. The first-pass student/prototype uses only mixed-only deployable AudioDepth metadata.",
        "",
        "| task | test samples | student-teacher MAE | interpretation |",
        "|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row['task']} | {row['test_samples']} | {row['student_teacher_mae']} | {row['gap_interpretation']} |")
    write_markdown(GAP_MD, lines)
    print(f"Wrote {DISTILLATION_CSV}")


if __name__ == "__main__":
    main()
