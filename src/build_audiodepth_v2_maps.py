from __future__ import annotations

import numpy as np

from .audio_depth_router_common import PROJECT_ROOT, analysis_channels, read_csv, read_wav_mono, rel, save_map_preview, write_csv
from .balanced_v2_common import AUDIO_DEPTH_V2_MAP_DIR, AUDIO_DEPTH_V2_MAP_METADATA, FIGURE_DIR, V2_CER, V2_MANIFEST


def main() -> None:
    cer_ids = {row["sample_id"] for row in read_csv(V2_CER)} if V2_CER.exists() else set()
    rows = [row for row in read_csv(V2_MANIFEST) if not cer_ids or row["sample_id"] in cer_ids]
    AUDIO_DEPTH_V2_MAP_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    previews = []
    for row in rows:
        mixed, sr = read_wav_mono(PROJECT_ROOT / row["mixed_path"])
        spk1, _ = read_wav_mono(PROJECT_ROOT / row["spk1_path"])
        spk2, _ = read_wav_mono(PROJECT_ROOT / row["spk2_path"])
        arr = analysis_channels(mixed, sr, spk1, spk2)
        path = AUDIO_DEPTH_V2_MAP_DIR / f"{row['sample_id']}.npy"
        np.save(path, arr)
        if len(previews) < 4:
            preview = AUDIO_DEPTH_V2_MAP_DIR / f"{row['sample_id']}.png"
            save_map_preview(arr, preview, f"{row['sample_id']} analysis_only_irm_proxy")
            previews.append(rel(preview))
        out.append(
            {
                "sample_id": row["sample_id"],
                "map_path": rel(path),
                "mode": "analysis_only_irm_proxy",
                "shape": "3x64x96",
                "channel_1": "mixed_pseudo_logmel",
                "channel_2": "source_energy_overlap_proxy",
                "channel_3": "source_energy_dominance_proxy",
                "deployable": "False",
                "intended_family": row["intended_family"],
            }
        )
    write_csv(AUDIO_DEPTH_V2_MAP_METADATA, out)
    if rows:
        first = AUDIO_DEPTH_V2_MAP_DIR / f"{rows[0]['sample_id']}.npy"
        save_map_preview(np.load(first), FIGURE_DIR / "audio_depth_v2_map_examples.png", "AudioDepth v2 analysis-only IRM proxy")
    print(f"Wrote {len(out)} AudioDepth v2 maps to {rel(AUDIO_DEPTH_V2_MAP_METADATA)}")


if __name__ == "__main__":
    main()
