"""Noise robustness: does background noise change when separation helps? (experimental/frontier)

Research question:
  Every prior experiment varied OVERLAP under clean conditions. Real meetings are noisy. This
  maps the separation decision over a 2-D grid of (overlap ratio × input SNR) and asks:

  RQ-N1: As SNR drops (clean → 0 dB), does the separation gain ΔCER = CER(mixed) − CER(sep)
     grow or shrink, and does the crossover overlap r* move? (Separation removes the competing
     talker but NOT the environmental noise, which is present in both inputs.)
  RQ-N2: Does noise DEFEAT the silence-trim cure? The trim is energy-based; under noise the
     "silent" region the separation leaves behind is no longer silent, so the trim may stop
     firing — re-exposing the hallucination tail. We compare sep vs sep_trim across SNR.

Modeling choice: each ASR input is presented at the stated SNR w.r.t. its own speech power
(additive white Gaussian noise). Oracle separation removes the other speaker; the per-speaker
track still carries noise (separation is not denoising). This isolates "at input SNR X, is
mixed or separated(+trim) better for ASR?".

Labels: experimental/frontier; references synthetic/silver; Whisper-tiny; CER post-hoc only,
never a routing input. No gold tables touched; outputs to results/frontier/noise_robustness/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .evaluate_cer import compute_cer
from .generate_synthetic_overlap import build_mixture, read_mono_audio
from .separation_tax_phase import (
    _rel,
    load_snippet_reference,
    nonzero_speech_span,
    select_pairs,
    tail_rate,
    transcribe_with_signals,
    trim_silence,
)

SR = 16000
SNIPPETS_DIR = PROJECT_ROOT / "resources" / "snippets"
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "noise_robustness"
SNR_LEVELS: list[float | None] = [None, 20.0, 10.0, 5.0, 0.0]  # None = clean
OVERLAPS = [0.0, 0.1, 0.2, 0.4, 0.6, 0.9]
CATASTROPHIC_CER = 1.0


# --------------------------------------------------------------------------------------
# Pure helpers (unit-tested)
# --------------------------------------------------------------------------------------
def speech_power(x: np.ndarray) -> float:
    s, e = nonzero_speech_span(x)
    seg = x[s:e] if e > s else x
    return float(np.mean(seg ** 2)) + 1e-12 if seg.size else 1e-12


def add_noise(x: np.ndarray, snr_db: float | None, seed: int) -> np.ndarray:
    """Add white Gaussian noise so the signal-to-noise ratio over the speech region equals
    snr_db. snr_db=None returns the clean signal. Peak-limited to avoid clipping."""
    x = np.asarray(x, dtype=np.float32)
    if snr_db is None or x.size == 0:
        return x
    rng = np.random.default_rng(seed)
    sp = speech_power(x)
    noise = rng.standard_normal(x.size).astype(np.float32)
    noise *= float(np.sqrt(sp / (10.0 ** (snr_db / 10.0)) / (float(np.mean(noise ** 2)) + 1e-12)))
    y = (x + noise).astype(np.float32)
    peak = float(np.max(np.abs(y)))
    return (y * (0.98 / peak)).astype(np.float32) if peak > 0.98 else y


def measured_snr_db(clean: np.ndarray, noisy: np.ndarray) -> float:
    s, e = nonzero_speech_span(clean)
    if e <= s:
        s, e = 0, clean.size
    sig = clean[s:e]
    noise = noisy[s:e] - sig
    sp = float(np.mean(sig ** 2)) + 1e-12
    npow = float(np.mean(noise ** 2)) + 1e-12
    return float(10.0 * np.log10(sp / npow))


def _seed(pi: int, overlap: float, snr_db: float | None, which: int) -> int:
    s = -1 if snr_db is None else int(snr_db)
    return (pi * 97 + int(round(overlap * 100)) + (s + 1) * 7 + which * 3) % (2 ** 31)


def aggregate_grid(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per (snr) aggregate: mean ΔCER(mixed−sep_trim), mean CERs, sep tail rate, and the
    sep-vs-sep_trim gap (does trimming still help under this SNR?)."""
    out: list[dict[str, Any]] = []
    snrs = sorted({(-1.0 if r["snr_db"] in ("", "None", None) else float(r["snr_db"])) for r in rows})
    for snr in snrs:
        at = [r for r in rows if (-1.0 if r["snr_db"] in ("", "None", None) else float(r["snr_db"])) == snr]
        cm = [float(r["cer_mixed"]) for r in at]
        cs = [float(r["cer_sep"]) for r in at]
        ct = [float(r["cer_sep_trim"]) for r in at]
        deltas = [m - t for m, t in zip(cm, ct)]
        out.append({
            "snr_db": "clean" if snr == -1.0 else snr,
            "n": len(at),
            "mean_cer_mixed": round(float(np.mean(cm)), 6),
            "mean_cer_sep": round(float(np.mean(cs)), 6),
            "mean_cer_sep_trim": round(float(np.mean(ct)), 6),
            "mean_delta_mixed_minus_septrim": round(float(np.mean(deltas)), 6),
            "septrim_helps_frac": round(sum(1 for d in deltas if d > 0) / len(deltas), 6) if deltas else 0.0,
            "tail_rate_sep": round(tail_rate(cs, CATASTROPHIC_CER), 6),
            "tail_rate_sep_trim": round(tail_rate(ct, CATASTROPHIC_CER), 6),
            "trim_gain_vs_sep": round(float(np.mean(cs)) - float(np.mean(ct)), 6),  # >0 => trim helps
        })
    return out


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------
def run(out_dir: Path, num_pairs: int) -> dict[str, Any]:
    import whisper

    out_dir.mkdir(parents=True, exist_ok=True)
    plans = select_pairs(num_pairs)
    model = whisper.load_model("tiny")
    print(f"[noise] pairs={len(plans)} overlaps={len(OVERLAPS)} snr={len(SNR_LEVELS)}", flush=True)
    rows: list[dict[str, Any]] = []
    for pi, plan in enumerate(plans):
        s1, s2 = read_mono_audio(plan.con_path), read_mono_audio(plan.pro_path)
        ref = plan.con_text + plan.pro_text
        for overlap in OVERLAPS:
            mixed, t1, t2, _ = build_mixture(s1, s2, overlap)
            for snr in SNR_LEVELS:
                mx = add_noise(mixed, snr, _seed(pi, overlap, snr, 0))
                n1 = add_noise(t1, snr, _seed(pi, overlap, snr, 1))
                n2 = add_noise(t2, snr, _seed(pi, overlap, snr, 2))
                o_mx = transcribe_with_signals(model, mx, "greedy")
                o1 = transcribe_with_signals(model, n1, "greedy")
                o2 = transcribe_with_signals(model, n2, "greedy")
                ot1 = transcribe_with_signals(model, trim_silence(n1), "greedy")
                ot2 = transcribe_with_signals(model, trim_silence(n2), "greedy")
                rows.append({
                    "pair_id": pi, "overlap_ratio": overlap,
                    "snr_db": "None" if snr is None else snr,
                    "cer_mixed": round(compute_cer(ref, o_mx["text"])["cer"], 6),
                    "cer_sep": round(compute_cer(ref, o1["text"] + o2["text"])["cer"], 6),
                    "cer_sep_trim": round(compute_cer(ref, ot1["text"] + ot2["text"])["cer"], 6),
                    "cr_sep1": round(o1["max_compression_ratio"], 4),
                    "cr_sep1_trim": round(ot1["max_compression_ratio"], 4),
                })
        print(f"[noise] pair {pi + 1}/{len(plans)}", flush=True)
    with (out_dir / "noise_curve.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    grid = aggregate_grid(rows)
    (out_dir / "noise_summary.json").write_text(json.dumps(grid, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[noise] wrote {_rel(out_dir / 'noise_curve.csv')} + noise_summary.json", flush=True)
    return {"grid": grid}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Overlap x SNR noise-robustness map (frontier).")
    p.add_argument("--pairs", type=int, default=10)
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    run(Path(args.out_dir), args.pairs)


if __name__ == "__main__":
    main()
