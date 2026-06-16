from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .audio_depth_router_common import read_csv
from .audio_depth_systematic_common import safe_float
from .balanced_v2_common import BALANCED_CASE_STUDIES, BALANCED_COMPARISON, FIGURE_DIR, V2_DISTRIBUTION


def card(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1100, 620), (250, 251, 252))
    draw = ImageDraw.Draw(img)
    draw.rectangle((36, 36, 1064, 584), fill=(255, 255, 255), outline=(38, 70, 83), width=3)
    draw.text((72, 72), title, fill=(0, 0, 0))
    y = 150
    for line in lines[:9]:
        draw.text((84, y), line[:120], fill=(25, 34, 42))
        y += 48
    img.save(path)


def main() -> None:
    comp = read_csv(BALANCED_COMPARISON) if BALANCED_COMPARISON.exists() else []
    dist = read_csv(V2_DISTRIBUTION) if V2_DISTRIBUTION.exists() else []
    best = comp[0] if comp else {}
    dist_lines = [f"{row['oracle_route']}: {row['count']} ({row['fraction']})" for row in dist[:4]]
    result_lines = [f"{row['model_name']}: CER {row['average_cer']} acc {row['accuracy_vs_oracle_route']}" for row in comp[:6]]
    card(
        FIGURE_DIR / "audio_depth_balanced_overview.png",
        "Balanced Route-Sensitive Benchmark v2",
        [
            "Purpose: test whether routing changes with route winners, not only separation strength.",
            "Routes: mixed / separated / cleaned plus review-needed flags.",
            "Evidence: real Whisper on silver-plus-unverified references.",
            "AudioDepth v2 maps are analysis-only IRM/source-energy proxies.",
        ],
    )
    card(FIGURE_DIR / "audio_depth_balanced_route_distribution_card.png", "Oracle Route Distribution", dist_lines)
    card(FIGURE_DIR / "audio_depth_balanced_main_result_card.png", "Balanced Router Result", [f"best: {best.get('model_name', 'NA')} CER {best.get('average_cer', 'NA')}", *result_lines])
    cases = read_csv(BALANCED_CASE_STUDIES) if BALANCED_CASE_STUDIES.exists() else []
    case_lines = [f"{row['sample_id']}: oracle {row['oracle_route']} balanced {row['balanced_router_prediction']}" for row in cases[:8]]
    card(FIGURE_DIR / "audio_depth_balanced_case_grid.png", "Representative Cases", case_lines)
    print("Wrote balanced README cards")


if __name__ == "__main__":
    main()
