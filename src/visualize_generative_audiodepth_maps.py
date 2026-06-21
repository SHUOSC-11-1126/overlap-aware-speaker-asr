from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .generative_audiodepth_common import FIGURE_DIR, MAP_TASKS, TEST_CSV, TRAIN_CSV, load_npy, read_rows, unique_samples, write_markdown
from .generative_audiodepth_models import build_promptable_prototype, direct_regret_predict, select_route_from_regret


EXAMPLES_PNG = FIGURE_DIR / "generative_audiodepth_examples.png"
EXAMPLES_MD = FIGURE_DIR / "generative_audiodepth_examples.md"


def img(arr: np.ndarray, label: str, size: tuple[int, int] = (190, 110)) -> Image.Image:
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr[0]
    lo, hi = float(np.min(arr)), float(np.max(arr))
    norm = (arr - lo) / (hi - lo + 1e-8)
    out = Image.fromarray(np.uint8(norm * 255), mode="L").convert("RGB").resize(size, Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(out)
    draw.rectangle((0, 0, size[0], 18), fill=(0, 0, 0))
    draw.text((5, 4), label, fill=(255, 255, 255))
    return out


def pick_examples(samples: list[dict[str, str]]) -> list[dict[str, str]]:
    buckets = []
    wanted = [
        lambda r: r.get("oracle_route") == "mixed",
        lambda r: r.get("oracle_route") == "separated",
        lambda r: r.get("review_needed") == "True",
        lambda r: float(r.get("route_gap") or 0.0) <= 0.02,
        lambda r: float(r.get("overlap_ratio") or 0.0) >= 0.5,
    ]
    seen = set()
    for pred in wanted:
        for row in samples:
            if row["sample_id"] not in seen and pred(row):
                buckets.append(row)
                seen.add(row["sample_id"])
                break
    for row in samples:
        if len(buckets) >= 6:
            break
        if row["sample_id"] not in seen:
            buckets.append(row)
            seen.add(row["sample_id"])
    return buckets


def main() -> None:
    train_rows = read_rows(TRAIN_CSV)
    test_rows = read_rows(TEST_CSV)
    train_samples = unique_samples(train_rows)
    samples = pick_examples(unique_samples(test_rows))
    model = build_promptable_prototype(train_samples, train_rows, load_npy)
    panels = []
    md = [
        "# Generative AudioDepth Examples",
        "",
        "Examples include mixed-win, separated-win, ambiguous/review, and high-overlap cases when available.",
        "Generated maps are prototype predictions, not production-ready local routing maps.",
        "",
    ]
    task_lookup = {(row["sample_id"], row["target_task"]): row for row in test_rows}
    for row in samples:
        sid = row["sample_id"]
        overlap = task_lookup.get((sid, "OVERLAP_MAP"))
        dominance = task_lookup.get((sid, "DOMINANCE_MAP"))
        uncertainty = task_lookup.get((sid, "UNCERTAINTY_MAP"))
        pred_regret = direct_regret_predict(row, train_samples)
        selected = select_route_from_regret(pred_regret)
        md.append(
            f"- `{sid}`: oracle={row.get('oracle_route')}, selected={selected}, review_needed={row.get('review_needed')}, regrets={np.round(pred_regret, 3).tolist()}"
        )
        for task_row, task in [(overlap, "overlap"), (dominance, "dominance"), (uncertainty, "uncertainty")]:
            if not task_row:
                continue
            target = load_npy(task_row["target_path"])
            pred = model.predict(row, task_row["target_task"])
            panels.extend([img(target, f"{sid} teacher {task}"), img(pred, f"{sid} generated {task}")])
    if not panels:
        panels = [Image.new("RGB", (190, 110), "white")]
    cols = 3
    w, h = panels[0].size
    rows = int(np.ceil(len(panels) / cols))
    canvas = Image.new("RGB", (cols * w, rows * h + 34), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((10, 10), "Generative AudioDepth teacher vs generated maps", fill=(0, 0, 0))
    for idx, panel in enumerate(panels):
        canvas.paste(panel, ((idx % cols) * w, 34 + (idx // cols) * h))
    EXAMPLES_PNG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(EXAMPLES_PNG)
    md.append("")
    md.append(f"Figure: `{EXAMPLES_PNG.as_posix()}`")
    write_markdown(EXAMPLES_MD, md)
    print(f"Wrote {EXAMPLES_PNG}")


if __name__ == "__main__":
    main()
