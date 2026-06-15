from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .audio_depth_map import generate_one, load_or_build_dataset
from .audio_depth_router_common import PROJECT_ROOT, normalize01, rel


FIGURE_PATH = PROJECT_ROOT / "results" / "figures" / "audio_depth_map_examples.png"
SUMMARY_PATH = PROJECT_ROOT / "results" / "figures" / "audio_depth_map_examples.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render representative AudioDepth map examples.")
    parser.add_argument("--mode", default="deployable", choices=["deployable", "analysis"])
    parser.add_argument("--sample-limit", type=int, default=5)
    return parser.parse_args()


def select_examples(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    tiers = ["NoOverlap", "LightOverlap", "MidOverlap", "HeavyOverlap", "OppositeOverlap"]
    selected: list[dict[str, str]] = []
    for tier in tiers:
        match = next((row for row in rows if tier in row.get("overlap_tier", row["sample_id"])), None)
        if match:
            selected.append(match)
    return selected[:limit] if limit else selected


def channel_tile(channel: np.ndarray, title: str, size: tuple[int, int] = (180, 110)) -> Image.Image:
    img = Image.fromarray(np.uint8(normalize01(channel) * 255.0), mode="L").convert("RGB").resize(size)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, size[0], 18), fill=(0, 0, 0))
    draw.text((5, 3), title, fill=(255, 255, 255))
    return img


def main() -> None:
    args = parse_args()
    rows = select_examples(load_or_build_dataset(args.mode), args.sample_limit)
    for row in rows:
        map_path = PROJECT_ROOT / f"resources/audio_depth_maps/{args.mode}/{row['sample_id']}.npy"
        if not map_path.exists():
            generate_one(row, args.mode, preview=True)

    width = 760
    row_h = 150
    canvas = Image.new("RGB", (width, 50 + row_h * len(rows)), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((15, 15), f"AudioDepth-Router examples ({args.mode})", fill=(0, 0, 0))
    titles = ["log-mel", "overlap/depth", "uncertainty/dominance"]
    for idx, row in enumerate(rows):
        y = 50 + idx * row_h
        draw.text((12, y + 10), f"{row['sample_id']} | best={row.get('best_route_label', '')}", fill=(0, 0, 0))
        arr = np.load(PROJECT_ROOT / f"resources/audio_depth_maps/{args.mode}/{row['sample_id']}.npy")
        for ch in range(3):
            canvas.paste(channel_tile(arr[ch], titles[ch]), (190 + ch * 185, y + 25))
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(FIGURE_PATH)
    SUMMARY_PATH.write_text(
        "\n".join(
            [
                "# AudioDepth Map Examples",
                "",
                f"Mode: `{args.mode}`.",
                "",
                "Each row shows a fixed-size three-channel representation: log-mel, an overlap/depth channel, and an uncertainty or dominance channel.",
                "",
                f"Figure: `{rel(FIGURE_PATH)}`",
                "",
                "These examples are labeled `experimental/frontier`; synthetic examples remain `synthetic/silver`, not gold evidence.",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {rel(FIGURE_PATH)} and {rel(SUMMARY_PATH)}")


if __name__ == "__main__":
    main()
