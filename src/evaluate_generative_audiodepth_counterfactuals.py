from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .generative_audiodepth_common import DATASET_CSV, FIGURE_DIR, read_rows, safe_float, unique_samples, write_csv, write_markdown


PAIRS_CSV = Path("results/tables/generative_audiodepth_counterfactual_pairs.csv")
OUT_CSV = Path("results/tables/generative_audiodepth_counterfactuals.csv")
OUT_PNG = FIGURE_DIR / "generative_audiodepth_counterfactual_curves.png"
OUT_MD = FIGURE_DIR / "generative_audiodepth_counterfactual_summary.md"


def main() -> None:
    samples = {row["sample_id"]: row for row in unique_samples(read_rows(DATASET_CSV))}
    pairs = read_rows(PAIRS_CSV)
    rows = []
    for pair in pairs:
        low = samples.get(pair["low_sample_id"])
        high = samples.get(pair["high_sample_id"])
        if not low or not high:
            continue
        low_signal = safe_float(low.get("overlap_proxy_mean"))
        high_signal = safe_float(high.get("overlap_proxy_mean"))
        rows.append(
            {
                **pair,
                "low_mixed_only_overlap_proxy_mean": low_signal,
                "high_mixed_only_overlap_proxy_mean": high_signal,
                "overlap_proxy_monotonic": str(high_signal >= low_signal),
                "dominance_changed": str(low.get("dominance_type") != high.get("dominance_type")),
                "interpretation": "exact_counterfactual" if pair["pair_type"].startswith("source") else "proxy_pair_only",
            }
        )
    write_csv(OUT_CSV, rows)
    width, height = 860, 360
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 18), "Generative AudioDepth counterfactual/proxy monotonicity", fill=(0, 0, 0))
    for idx, row in enumerate(rows[:8]):
        y = 60 + idx * 32
        x1 = 220 + int(450 * safe_float(row["low_mixed_only_overlap_proxy_mean"]))
        x2 = 220 + int(450 * safe_float(row["high_mixed_only_overlap_proxy_mean"]))
        color = (60, 150, 90) if row["overlap_proxy_monotonic"] == "True" else (190, 80, 70)
        draw.text((20, y), row["pair_type"][:24], fill=(0, 0, 0))
        draw.line((x1, y + 10, x2, y + 10), fill=color, width=4)
        draw.ellipse((x1 - 4, y + 6, x1 + 4, y + 14), fill=color)
        draw.ellipse((x2 - 4, y + 6, x2 + 4, y + 14), fill=color)
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT_PNG)
    monotonic = sum(1 for row in rows if row["overlap_proxy_monotonic"] == "True")
    lines = [
        "# Generative AudioDepth Counterfactual Summary",
        "",
        "Exact same-source counterfactuals are preferred. If unavailable, this script labels pairs as proxy-only.",
        "",
        f"- pairs evaluated: {len(rows)}",
        f"- monotonic overlap proxy pairs: {monotonic}",
        f"- proxy-only pairs: {sum(1 for row in rows if row['interpretation'] == 'proxy_pair_only')}",
        "",
        f"Figure: `{OUT_PNG.as_posix()}`",
    ]
    write_markdown(OUT_MD, lines)
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
