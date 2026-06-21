from __future__ import annotations

import time
from pathlib import Path

from PIL import Image, ImageDraw

from .generative_audiodepth_common import FIGURE_DIR, MODEL_DIR, TEST_CSV, load_npy, read_rows, unique_samples, write_csv, write_markdown
from .generative_audiodepth_models import build_promptable_prototype, direct_regret_predict, direct_route_classifier_predict


OUT_CSV = Path("results/tables/generative_audiodepth_runtime.csv")
OUT_PNG = FIGURE_DIR / "generative_audiodepth_runtime_pareto.png"
OUT_MD = FIGURE_DIR / "generative_audiodepth_runtime.md"


def time_call(fn, repeats: int = 50) -> float:
    start = time.perf_counter()
    for _ in range(repeats):
        fn()
    return (time.perf_counter() - start) / repeats


def main() -> None:
    train_rows = read_rows(Path("results/tables/generative_audiodepth_train.csv"))
    test_samples = unique_samples(read_rows(TEST_CSV))
    train_samples = unique_samples(train_rows)
    sample = test_samples[0] if test_samples else train_samples[0]
    model = build_promptable_prototype(train_samples, train_rows, load_npy)
    model_path = MODEL_DIR / "generative_audiodepth_promptable_prototype.pt"
    rows = [
        {
            "model_name": "handcrafted_audiodepth_v2",
            "parameter_count": 0,
            "model_file_size_bytes": 0,
            "cpu_inference_ms": round(time_call(lambda: sample.get("overlap_proxy_mean"), 1000) * 1000, 6),
            "map_generation_overhead": "none",
        },
        {
            "model_name": "direct_classifier",
            "parameter_count": 0,
            "model_file_size_bytes": 0,
            "cpu_inference_ms": round(time_call(lambda: direct_route_classifier_predict(sample, train_samples), 200) * 1000, 6),
            "map_generation_overhead": "none",
        },
        {
            "model_name": "promptable_generator_prototype",
            "parameter_count": len(train_samples),
            "model_file_size_bytes": model_path.stat().st_size if model_path.exists() else 0,
            "cpu_inference_ms": round(time_call(lambda: model.predict(sample, "OVERLAP_MAP"), 100) * 1000, 6),
            "map_generation_overhead": "nearest_prototype_map_lookup",
        },
        {
            "model_name": "route_regret_model",
            "parameter_count": len(train_samples),
            "model_file_size_bytes": model_path.stat().st_size if model_path.exists() else 0,
            "cpu_inference_ms": round(time_call(lambda: direct_regret_predict(sample, train_samples), 200) * 1000, 6),
            "map_generation_overhead": "none",
        },
    ]
    write_csv(OUT_CSV, rows)
    width, height = 820, 340
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 18), "Generative AudioDepth runtime proxy", fill=(0, 0, 0))
    max_ms = max(float(row["cpu_inference_ms"]) for row in rows) or 1.0
    for idx, row in enumerate(rows):
        y = 62 + idx * 42
        value = float(row["cpu_inference_ms"])
        draw.text((20, y), str(row["model_name"])[:34], fill=(0, 0, 0))
        draw.rectangle((300, y, 300 + int(420 * value / max_ms), y + 24), fill=(100, 130, 180))
        draw.text((740, y), f"{value:.4f} ms", fill=(0, 0, 0))
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT_PNG)
    lines = [
        "# Generative AudioDepth Runtime",
        "",
        "This first pass benchmarks dependency-light prototypes, not a neural U-Net.",
        "",
        "| model | params/prototypes | file bytes | CPU ms | overhead |",
        "|---|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"| {row['model_name']} | {row['parameter_count']} | {row['model_file_size_bytes']} | {row['cpu_inference_ms']} | {row['map_generation_overhead']} |")
    write_markdown(OUT_MD, lines)
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
