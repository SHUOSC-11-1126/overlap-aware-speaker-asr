"""Curing separation-induced Whisper hallucination: decoder-native vs preprocessing (frontier).

Research question (extends Separation Tax RQ3):
  RQ3 showed that on silence-padded separated tracks, Whisper's temperature fallback does NOT
  cure the catastrophic hallucination tail, but manual energy-based silence-trim does. RQ3 did
  not test Whisper's PURPOSE-BUILT anti-hallucination feature, `hallucination_silence_threshold`
  (skips silent periods > threshold, requires word_timestamps=True), nor beam search. This
  module runs a head-to-head of cures on the separated tracks:

    greedy_baseline      temperature=0, condition_on_previous_text=False  (the repo default)
    silence_trim         greedy + energy-based leading/trailing silence trim  (proven RQ3 cure)
    halluc_silence       greedy + word_timestamps + hallucination_silence_threshold=2.0  (native)
    halluc_silence_trim  native cure + trim (combined)
    beam5                beam_size=5 (decoding robustness)

  Question: does Whisper's native hallucination_silence_threshold match/beat manual trimming at
  killing the catastrophic tail (CER > 1.0)? Is beam search a cheap partial cure?

Labels: experimental/frontier; references synthetic/silver; Whisper-tiny. CER post-hoc only,
never a routing input. No gold tables touched; outputs to results/frontier/hallucination_cure/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer, repetition_count_from_text
from .generate_synthetic_overlap import build_mixture, read_mono_audio
from .separation_tax_phase import (
    DEFAULT_RATIOS,
    _rel,
    load_snippet_reference,
    select_pairs,
    tail_rate,
    trim_silence,
)

SR = 16000
SNIPPETS_DIR = PROJECT_ROOT / "resources" / "snippets"
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "hallucination_cure"

BASE = dict(language="zh", verbose=False, fp16=False)
# Each cure: decode kwargs + whether to silence-trim the audio first.
CURES: dict[str, dict[str, Any]] = {
    "greedy_baseline": {"kwargs": {"temperature": 0.0, "condition_on_previous_text": False}, "trim": False},
    "silence_trim": {"kwargs": {"temperature": 0.0, "condition_on_previous_text": False}, "trim": True},
    "halluc_silence": {"kwargs": {"temperature": 0.0, "condition_on_previous_text": False,
                                   "word_timestamps": True, "hallucination_silence_threshold": 2.0}, "trim": False},
    "halluc_silence_trim": {"kwargs": {"temperature": 0.0, "condition_on_previous_text": False,
                                        "word_timestamps": True, "hallucination_silence_threshold": 2.0}, "trim": True},
    "beam5": {"kwargs": {"temperature": 0.0, "beam_size": 5, "condition_on_previous_text": False}, "trim": False},
}
CURE_NAMES = list(CURES)
CATASTROPHIC_CER = 1.0

# The exact catastrophic separated tracks found in the Separation Tax sweep (spk2 = leading-silence).
KNOWN_CATASTROPHIC = [
    ("con_006.wav", "pro_006.wav", 0.05),
    ("con_006.wav", "pro_006.wav", 0.10),
    ("con_001.wav", "pro_003.wav", 0.10),
    ("con_001.wav", "pro_003.wav", 0.00),
    ("con_003.wav", "pro_002.wav", 0.15),
]


# --------------------------------------------------------------------------------------
# Pure aggregation (unit-tested)
# --------------------------------------------------------------------------------------
def aggregate_by_cure(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-cure mean/median CER and catastrophic-tail rate over all (track) samples."""
    out: list[dict[str, Any]] = []
    for cure in CURE_NAMES:
        cers = [float(r["cer"]) for r in rows if r["cure"] == cure]
        if not cers:
            continue
        out.append({
            "cure": cure,
            "n": len(cers),
            "mean_cer": round(float(np.mean(cers)), 6),
            "median_cer": round(float(np.median(cers)), 6),
            "tail_rate": round(tail_rate(cers, CATASTROPHIC_CER), 6),
            "max_cer": round(float(np.max(cers)), 6),
        })
    return out


# --------------------------------------------------------------------------------------
# Whisper-dependent driver
# --------------------------------------------------------------------------------------
def transcribe_cure(model: Any, audio: np.ndarray, cure: str) -> dict[str, Any]:
    spec = CURES[cure]
    a = trim_silence(audio) if spec["trim"] else audio
    a = np.ascontiguousarray(np.asarray(a, dtype=np.float32))
    result = model.transcribe(a, **BASE, **spec["kwargs"])
    segs = result.get("segments", [])
    text = str(result.get("text", "")).strip()
    return {
        "text": text,
        "n_segments": len(segs),
        "max_compression_ratio": float(max((s.get("compression_ratio", 0.0) for s in segs), default=0.0)),
        "repetition": repetition_count_from_text(text),
    }


def _eval_track(model: Any, con: str, pro: str, ratio: float, which: int) -> list[dict[str, Any]]:
    s1 = read_mono_audio(SNIPPETS_DIR / con)
    s2 = read_mono_audio(SNIPPETS_DIR / pro)
    _, t1, t2, _ = build_mixture(s1, s2, ratio)
    track = t1 if which == 1 else t2
    ref = load_snippet_reference(SNIPPETS_DIR / (con if which == 1 else pro))
    rows: list[dict[str, Any]] = []
    for cure in CURE_NAMES:
        o = transcribe_cure(model, track, cure)
        rows.append({
            "con": con, "pro": pro, "overlap_ratio": ratio, "track": f"spk{which}", "cure": cure,
            "cer": round(compute_cer(ref, o["text"])["cer"], 6),
            "max_compression_ratio": round(o["max_compression_ratio"], 4),
            "repetition": o["repetition"], "n_segments": o["n_segments"],
        })
    return rows


def run_smoke(out_dir: Path) -> list[dict[str, Any]]:
    import whisper
    model = whisper.load_model("tiny")
    print(f"[cure] smoke on {len(KNOWN_CATASTROPHIC)} known-catastrophic tracks x {len(CURE_NAMES)} cures", flush=True)
    rows: list[dict[str, Any]] = []
    for con, pro, ratio in KNOWN_CATASTROPHIC:
        rows.extend(_eval_track(model, con, pro, ratio, which=2))  # spk2 = leading-silence catastrophic
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cure_smoke.csv").write_text(
        _rows_to_csv(rows), encoding="utf-8-sig")
    return rows


def run_sweep(out_dir: Path, num_pairs: int, ratios: list[float]) -> list[dict[str, Any]]:
    import whisper
    model = whisper.load_model("tiny")
    plans = select_pairs(num_pairs)
    print(f"[cure] sweep pairs={len(plans)} ratios={len(ratios)} cures={len(CURE_NAMES)}", flush=True)
    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        for ratio in ratios:
            for which in (1, 2):
                rows.extend(_eval_track(model, plan.con_path.name, plan.pro_path.name, ratio, which))
        print(f"[cure] pair {pi + 1}/{len(plans)}", flush=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cure_curve.csv").write_text(_rows_to_csv(rows), encoding="utf-8-sig")
    agg = aggregate_by_cure(rows)
    (out_dir / "cure_summary.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[cure] wrote {_rel(out_dir / 'cure_curve.csv')} + cure_summary.json", flush=True)
    return rows


def analyze_relative(out_dir: Path) -> list[dict[str, Any]]:
    """Pair each cure against greedy on the SAME track and split groups into catastrophic
    (greedy CER > 1.0) vs normal. Answers: does the cure fix the tail WITHOUT hurting the
    non-catastrophic majority? Reads cure_curve.csv; writes cure_relative.csv/json."""
    from collections import defaultdict
    with (out_dir / "cure_curve.csv").open("r", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    by_group: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(dict)
    for r in rows:
        by_group[(r["con"], r["pro"], r["overlap_ratio"], r["track"])][r["cure"]] = float(r["cer"])
    tail = [g for g, d in by_group.items() if d.get("greedy_baseline", 0.0) > CATASTROPHIC_CER]
    normal = [g for g, d in by_group.items() if 0.0 <= d.get("greedy_baseline", 0.0) <= CATASTROPHIC_CER]
    base_norm = float(np.mean([by_group[g]["greedy_baseline"] for g in normal])) if normal else 0.0
    out: list[dict[str, Any]] = []
    for cure in CURE_NAMES:
        tail_cers = [by_group[g][cure] for g in tail if cure in by_group[g]]
        norm_cers = [by_group[g][cure] for g in normal if cure in by_group[g]]
        mean_norm = float(np.mean(norm_cers)) if norm_cers else 0.0
        out.append({
            "cure": cure,
            "n_catastrophic_groups": len(tail),
            "mean_cer_on_catastrophic": round(float(np.mean(tail_cers)), 6) if tail_cers else 0.0,
            "n_normal_groups": len(normal),
            "mean_cer_on_normal": round(mean_norm, 6),
            "normal_delta_vs_greedy": round(mean_norm - base_norm, 6),  # >0 means the cure HURTS normal clips
        })
    (out_dir / "cure_relative.csv").write_text(_rows_to_csv(out), encoding="utf-8-sig")
    (out_dir / "cure_relative.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[cure] wrote {_rel(out_dir / 'cure_relative.csv')} (tail groups={len(tail)}, normal={len(normal)})", flush=True)
    return out


def _rows_to_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Whisper hallucination cure head-to-head (frontier).")
    p.add_argument("--smoke", action="store_true", help="Run only on known-catastrophic tracks.")
    p.add_argument("--analyze-relative", action="store_true", help="Re-analyze existing cure_curve.csv (tail vs normal).")
    p.add_argument("--pairs", type=int, default=20)
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if args.analyze_relative:
        analyze_relative(out_dir)
    elif args.smoke:
        run_smoke(out_dir)
    else:
        run_sweep(out_dir, args.pairs, DEFAULT_RATIOS)
        analyze_relative(out_dir)


if __name__ == "__main__":
    main()
