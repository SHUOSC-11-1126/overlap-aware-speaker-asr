from __future__ import annotations

import argparse
from collections import defaultdict

import numpy as np
from PIL import Image

from .audio_depth_router_common import PROJECT_ROOT, rel, write_csv
from .audiodepth_centric_common import (
    FIGURE_DIR,
    MAP_DIR,
    METADATA_CSV,
    deployable_audiodepth_v2,
    map_stats,
    read_wav_mono,
    save_preview,
    source_rows,
    target_family,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deployable mixed-only AudioDepth v2 maps.")
    parser.add_argument("--source", choices=["controlled_v2", "controlled_v1", "synthetic_split"], default="controlled_v2")
    parser.add_argument("--all", action="store_true", help="Build all available rows for the source.")
    parser.add_argument("--limit", type=int, default=60)
    return parser.parse_args()


def append_metadata(new_rows: list[dict[str, object]], source: str) -> None:
    old = []
    if METADATA_CSV.exists():
        from .audio_depth_router_common import read_csv

        old = [row for row in read_csv(METADATA_CSV) if row.get("source") != source]
    write_csv(METADATA_CSV, old + new_rows)


def preview_grid(preview_paths: list[str]) -> None:
    if not preview_paths:
        return
    imgs = [Image.open(PROJECT_ROOT / path).convert("RGB") for path in preview_paths[:4]]
    width = max(img.width for img in imgs)
    height = sum(img.height for img in imgs)
    canvas = Image.new("RGB", (width, height), "white")
    y = 0
    for img in imgs:
        canvas.paste(img, (0, y))
        y += img.height
    out = FIGURE_DIR / "audiodepth_v2_examples.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)


def main() -> None:
    args = parse_args()
    manifest, labels = source_rows(args.source)
    if args.source == "synthetic_split":
        manifest, labels = [], {}
    if not manifest:
        note = FIGURE_DIR / "audiodepth_v2_examples.md"
        note.write_text(f"# AudioDepth v2 Examples\n\nSource `{args.source}` not available; skipped.\n", encoding="utf-8")
        print(f"Skipped missing source {args.source}")
        return
    rows = manifest if args.all else manifest[: args.limit]
    out_rows = []
    previews = []
    source_dir = MAP_DIR / args.source
    source_dir.mkdir(parents=True, exist_ok=True)
    counts = defaultdict(int)
    for row in rows:
        sid = row["sample_id"]
        audio, sr = read_wav_mono(PROJECT_ROOT / row["mixed_path"])
        arr = deployable_audiodepth_v2(audio, sr)
        map_path = source_dir / f"{sid}.npy"
        np.save(map_path, arr)
        preview_path = source_dir / f"{sid}.png"
        if len(previews) < 4:
            save_preview(arr, preview_path, f"{args.source} {sid} deployable mixed-only")
            previews.append(rel(preview_path))
        label = labels.get(sid, {})
        stats = map_stats(arr)
        family = target_family({**row, **label})
        counts[family] += 1
        out_rows.append(
            {
                "source": args.source,
                "sample_id": sid,
                "map_path": rel(map_path),
                "preview_path": rel(preview_path) if preview_path.exists() else "",
                "mixed_path": row["mixed_path"],
                "mode": "deployable_mixed_only",
                "shape": "3x128x256",
                "channel_1": "mixed_logmel",
                "channel_2": "mixed_only_overlap_proxy",
                "channel_3": "mixed_only_uncertainty_proxy",
                "uses_source_tracks": "False",
                "oracle_route": label.get("oracle_route", ""),
                "route_gap": label.get("route_gap", ""),
                "mixed_cer": label.get("mixed_cer", ""),
                "separated_cer": label.get("separated_cer", ""),
                "cleaned_cer": label.get("cleaned_cer", ""),
                "intended_family": family,
                **stats,
            }
        )
    append_metadata(out_rows, args.source)
    preview_grid(previews)
    md = [
        "# Deployable AudioDepth v2 Examples",
        "",
        f"- source: `{args.source}`",
        f"- maps built: `{len(out_rows)}`",
        "- channels are mixed-only: `True`",
        "- C1: mixed logmel",
        "- C2: mixed-only overlap proxy from energy variation, spectral entropy/flatness, band density, and zero-crossing density",
        "- C3: mixed-only uncertainty proxy from spectral flux, entropy movement, energy variance, and band conflict",
        "",
        "Family counts:",
        *[f"- `{key}`: `{value}`" for key, value in sorted(counts.items())],
    ]
    (FIGURE_DIR / "audiodepth_v2_examples.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Wrote {len(out_rows)} deployable AudioDepth v2 maps to {rel(METADATA_CSV)}")


if __name__ == "__main__":
    main()
