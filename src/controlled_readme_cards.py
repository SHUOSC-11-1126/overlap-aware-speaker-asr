from __future__ import annotations

from PIL import Image, ImageDraw

from .audio_depth_router_common import PROJECT_ROOT, read_csv, rel
from .audio_depth_systematic_common import safe_float
from .controlled_benchmark_common import FIGURE_DIR


def card(path, title: str, lines: list[str]) -> None:
    im = Image.new("RGB", (1000, 560), "white")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1000, 90), fill=(32, 72, 110))
    d.text((36, 32), title, fill=(255, 255, 255))
    y = 130
    for line in lines:
        d.text((48, y), line, fill=(20, 20, 20))
        y += 48
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def main() -> None:
    sens = read_csv(PROJECT_ROOT / "results" / "tables" / "controlled_route_sensitivity_summary.csv")
    comp = read_csv(PROJECT_ROOT / "results" / "tables" / "controlled_audio_depth_router_comparison.csv")
    all_row = sens[0]
    best = comp[0]
    card(
        FIGURE_DIR / "controlled_benchmark_overview.png",
        "Controlled Route-Sensitive Benchmark",
        [
            "source utterances -> controlled overlap generation",
            "mixed / speaker-track WAVs -> real Whisper routes",
            "route CER -> oracle gap -> router evaluation",
            f"samples evaluated: {all_row['sample_count']}",
        ],
    )
    card(
        FIGURE_DIR / "controlled_main_result_card.png",
        "Controlled Main Result",
        [f"{row['model_name']}: CER {row['average_cer']}" for row in comp[:6]] + [f"best: {best['model_name']}"],
    )
    card(
        FIGURE_DIR / "controlled_separation_phase_card.png",
        "Controlled Separation Phase",
        [
            f"mean separation gain: {all_row['mean_separation_gain']}",
            f"mean route gap: {all_row['mean_route_gap']}",
            f"oracle CER: {all_row['oracle_cer']}",
            f"fixed mixed CER: {all_row['mixed_cer']}",
        ],
    )
    print(f"Wrote README cards to {rel(FIGURE_DIR / 'controlled_main_result_card.png')}")


if __name__ == "__main__":
    main()
