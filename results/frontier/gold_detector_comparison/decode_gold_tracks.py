"""Decode helper for RQ21: regenerate per-track separated text for the gold benchmark.

This is a ONE-TIME decode helper (NOT the analysis script). It reproduces the
``separation_tax`` oracle-separation sweep (20 con x pro pairings x 15 overlap ratios =
300 greedy conditions, identical to ``src/separation_tax_phase.py::run_sweep``) and caches
the per-track separated transcripts so that ``gold_detector_comparison.py`` (numpy + stdlib
only) can compute language-id entropy without re-running Whisper.

ASR = Whisper-tiny (the only cached model, matching separation_tax / causal_hallucination_probe).
Greedy decoding (temperature=0.0, condition_on_previous_text=False) matches the "greedy"
config of separation_tax. The fallback config is NOT reproduced here (RQ21 only needs the
greedy tracks that carry the repetitive-hallucination signal).

Label: experimental/frontier. Reads only snippet audio (read-only); writes a single JSON
cache. No references / gold tables are modified.

Run:  python3 results/frontier/gold_detector_comparison/decode_gold_tracks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

# Make the project src importable when run from the worktree root.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.generate_synthetic_overlap import AudioClip, build_mixture, read_mono_audio  # noqa: E402

SNIPPETS_DIR = PROJECT_ROOT / "resources" / "snippets"
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "gold_detector_comparison"
OUT_JSON = OUT_DIR / "gold_track_texts.json"

# Must match separation_tax_phase.select_pairs (stride=7) and DEFAULT_RATIOS.
RATIOS = [
    0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.70, 0.80, 0.90,
]
NUM_PAIRS = 20
STRIDE = 7
TARGET_SR = 16000


def select_pairs() -> list[tuple[Path, Path]]:
    con_files = sorted(SNIPPETS_DIR.glob("con_*.wav"))
    pro_files = sorted(SNIPPETS_DIR.glob("pro_*.wav"))
    pairs: list[tuple[Path, Path]] = []
    for i in range(NUM_PAIRS):
        con_path = con_files[i % len(con_files)]
        pro_path = pro_files[(i * STRIDE) % len(pro_files)]
        pairs.append((con_path, pro_path))
    return pairs


def main() -> None:
    import whisper

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs = select_pairs()
    model = whisper.load_model("tiny")
    print(f"[rq21-decode] model=tiny pairs={len(pairs)} ratios={len(RATIOS)} "
          f"conditions={len(pairs) * len(RATIOS)}", flush=True)

    cache: list[dict] = []
    done = 0
    total = len(pairs) * len(RATIOS)
    for pi, (con_path, pro_path) in enumerate(pairs):
        s1 = read_mono_audio(con_path)
        s2 = read_mono_audio(pro_path)
        for ratio in RATIOS:
            mixed, track1, track2, _scale = build_mixture(s1, s2, ratio)
            # greedy config (matches separation_tax WHISPER_CONFIGS["greedy"])
            t1 = np.ascontiguousarray(track1, dtype=np.float32)
            t2 = np.ascontiguousarray(track2, dtype=np.float32)
            r1 = model.transcribe(t1, language="zh", verbose=False, fp16=False,
                                  temperature=0.0, condition_on_previous_text=False)
            r2 = model.transcribe(t2, language="zh", verbose=False, fp16=False,
                                  temperature=0.0, condition_on_previous_text=False)
            cache.append({
                "pair_id": pi,
                "con": con_path.name,
                "pro": pro_path.name,
                "overlap_ratio": ratio,
                "config": "greedy",
                "sep1_text": str(r1.get("text", "")).strip(),
                "sep2_text": str(r2.get("text", "")).strip(),
            })
            done += 1
            if done % 30 == 0 or done == total:
                print(f"[rq21-decode] {done}/{total} "
                      f"({con_path.name} x {pro_path.name} r={ratio})", flush=True)

    OUT_JSON.write_text(
        json.dumps({"label": "experimental/frontier", "asr_model": "whisper-tiny",
                    "config": "greedy", "n_conditions": len(cache), "tracks": cache},
                   ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[rq21-decode] wrote {OUT_JSON.relative_to(PROJECT_ROOT)} ({len(cache)} conditions)")


if __name__ == "__main__":
    main()
