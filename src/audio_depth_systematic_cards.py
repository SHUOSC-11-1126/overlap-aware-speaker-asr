from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .audio_depth_router_common import read_csv, rel
from .audio_depth_systematic_common import COST_CASCADE_CSV, PERFORMANCE_CSV, SYSTEMATIC_FIGURE_PREFIX, safe_float


def card(path: Path, title: str, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1100, 620), (248, 250, 252))
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, 1060, 580), fill=(255, 255, 255), outline=(30, 60, 90), width=3)
    draw.text((80, 80), title, fill=(0, 0, 0))
    y = 150
    for line in lines:
        draw.text((90, y), line, fill=(20, 30, 40))
        y += 48
    img.save(path)


def main() -> None:
    perf = read_csv(PERFORMANCE_CSV) if PERFORMANCE_CSV.exists() else []
    cost = read_csv(COST_CASCADE_CSV) if COST_CASCADE_CSV.exists() else []
    lookup = {row["model_name"]: row for row in perf}
    best = next((row for row in perf if row.get("label") == "experimental/frontier"), {})
    card(
        SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_overview.png",
        "AudioDepth-Hybrid Router System",
        [
            "AudioDepth maps + transcript instability + confidence cascade",
            "Outputs: route decision, confidence, risk level, fallback strategy",
            "Routes: mixed / separated / cleaned now; strong ASR and review are designed extensions",
            "Evidence label: synthetic/silver plus stress proxy validation",
        ],
    )
    card(
        SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_main_result_card.png",
        "Main Result Card",
        [
            "AudioDepth MVP CER: 0.436666",
            "matched router_v2 CER: 0.335326",
            "model zoo best CER: 0.166381",
            f"systematic best CER: {best.get('routing_average_cer', 'NA')} ({best.get('model_name', 'NA')})",
            "oracle CER: 0.115181",
        ],
    )
    lines = [f"{row['policy']}: CER {row['average_cer']}, cost {row['average_cost']}, review {row['review_rate']}" for row in cost[:6]]
    card(SYSTEMATIC_FIGURE_PREFIX / "audio_depth_systematic_pareto_card.png", "CER vs Cost Policy Card", lines or ["Run audio_depth_application_cascade first."])
    print("Wrote systematic README cards")


if __name__ == "__main__":
    main()
