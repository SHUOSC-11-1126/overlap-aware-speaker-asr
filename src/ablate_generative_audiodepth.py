from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .generative_audiodepth_common import FIGURE_DIR, read_rows, safe_float, write_csv, write_markdown


ABLATION_CSV = Path("results/tables/generative_audiodepth_ablation.csv")
ABLATION_PNG = FIGURE_DIR / "generative_audiodepth_ablation.png"
ABLATION_MD = FIGURE_DIR / "generative_audiodepth_ablation.md"


def main() -> None:
    baseline = read_rows(Path("results/tables/generative_audiodepth_baseline_performance.csv"))
    regret = read_rows(Path("results/tables/generative_route_regret_performance.csv"))
    rows = []
    for row in baseline:
        rows.append(
            {
                "ablation": row["model_name"],
                "route_accuracy": row.get("route_accuracy", ""),
                "selected_route_cer": row.get("selected_route_cer", ""),
                "regret_mae": row.get("regret_mae", ""),
                "map_mae": row.get("map_mae", ""),
                "interpretation": "first-pass deterministic baseline",
            }
        )
    for row in regret:
        rows.append(
            {
                "ablation": row["policy_name"],
                "route_accuracy": row.get("route_accuracy", ""),
                "selected_route_cer": row.get("selected_route_cer", ""),
                "regret_mae": row.get("regret_mae", ""),
                "map_mae": "",
                "interpretation": "route-regret selection policy",
            }
        )
    write_csv(ABLATION_CSV, rows)
    width, height = 900, 360
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 18), "Generative AudioDepth first-pass ablation", fill=(0, 0, 0))
    numeric = [r for r in rows if r.get("selected_route_cer") not in {"", None}]
    max_val = max([safe_float(r.get("selected_route_cer"), 0.0) for r in numeric] + [1.0])
    for idx, row in enumerate(numeric[:8]):
        y = 60 + idx * 34
        val = safe_float(row.get("selected_route_cer"), 0.0)
        draw.text((20, y), row["ablation"][:34], fill=(0, 0, 0))
        draw.rectangle((300, y, 300 + int(500 * val / max_val), y + 20), fill=(90, 140, 190))
        draw.text((810, y), f"{val:.3f}", fill=(0, 0, 0))
    ABLATION_PNG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(ABLATION_PNG)
    lines = [
        "# Generative AudioDepth Ablation",
        "",
        "This first pass compares dependency-light baselines. It is not yet a neural U-Net result.",
        "",
        "| ablation | route accuracy | selected CER | regret MAE | map MAE | interpretation |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['ablation']} | {row.get('route_accuracy','')} | {row.get('selected_route_cer','')} | {row.get('regret_mae','')} | {row.get('map_mae','')} | {row.get('interpretation','')} |"
        )
    write_markdown(ABLATION_MD, lines)
    print(f"Wrote {ABLATION_CSV}")


if __name__ == "__main__":
    main()
