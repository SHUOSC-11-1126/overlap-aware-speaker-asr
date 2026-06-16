"""Does acoustic speaker (dis)similarity predict the separation benefit? (experimental/frontier)

Research question:
  A natural alternative explanation for "when does separation help overlapping-speech ASR"
  is *who* is talking: acoustically similar talkers should be harder for Whisper to
  disentangle in the mixture, so separation should pay off more for similar speakers. This
  module tests that falsifiably by correlating a per-snippet MFCC speaker embedding distance
  with each (con × pro) pair's measured separation benefit (ΔCER), reusing the 600-condition
  sweep in results/frontier/separation_tax/phase_curve.csv.

Result (see FINDINGS): the hypothesis is NOT supported in this corpus — and, importantly,
the apparent moderate correlation under a tail-sensitive *mean* benefit (Pearson ≈ +0.49) is
an artifact of the catastrophic hallucination tail; under the tail-robust *median* benefit it
collapses to ≈ +0.08. This rules out speaker similarity as a strong driver here and reinforces
the Separation Tax thesis (the benefit is governed by the hallucination tail, not the talkers),
while flagging a methodological caution: use tail-robust statistics when CER has heavy tails.

Labels: experimental/frontier. Honest limitations: a coarse clip-level MFCC descriptor on an
acoustically homogeneous debate corpus (within-side cosine 0.973 vs cross-side 0.956 — little
speaker structure), n = 20 pairs, Whisper-tiny. CER is the analysis target only, never a
routing input. Reuses committed data; no gold tables touched.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT
from .generate_synthetic_overlap import read_mono_audio
from .reference_free_qe import pearson, spearman_corr

SR = 16000
SNIPPETS_DIR = PROJECT_ROOT / "resources" / "snippets"
PHASE_CURVE = PROJECT_ROOT / "results" / "frontier" / "separation_tax" / "phase_curve.csv"
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "speaker_similarity_probe"


# --------------------------------------------------------------------------------------
# Acoustic speaker embedding (MFCC mean+std) and pure stats
# --------------------------------------------------------------------------------------
def _hz_to_mel(f: float) -> float:
    return 2595.0 * np.log10(1.0 + f / 700.0)


def _mel_to_hz(m: np.ndarray) -> np.ndarray:
    return 700.0 * (10.0 ** (m / 2595.0) - 1.0)


def mel_filterbank(sr: int, nfft: int, n_mels: int) -> np.ndarray:
    pts = _mel_to_hz(np.linspace(0.0, _hz_to_mel(sr / 2), n_mels + 2))
    b = np.floor((nfft + 1) * pts / sr).astype(int)
    fb = np.zeros((n_mels, nfft // 2 + 1))
    for m in range(1, n_mels + 1):
        lo, ce, hi = b[m - 1], b[m], b[m + 1]
        for k in range(lo, ce):
            fb[m - 1, k] = (k - lo) / max(1, ce - lo)
        for k in range(ce, hi):
            fb[m - 1, k] = (hi - k) / max(1, hi - ce)
    return fb


def mfcc_embedding(samples: np.ndarray, sr: int = SR, n_mels: int = 26, n_mfcc: int = 13,
                   frame: int = 400, hop: int = 160) -> np.ndarray | None:
    """A coarse clip-level speaker/timbre descriptor: per-frame MFCCs, summarized by their
    mean and std over time. Returns a (2*n_mfcc,) L2-normalized vector, or None if too short."""
    from scipy.fft import dct

    x = np.asarray(samples, dtype=np.float64)
    if x.size < frame:
        return None
    n = 1 + (x.size - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n)[:, None]
    frames = x[idx] * np.hanning(frame)[None, :]
    power = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    log_mel = np.log(power @ mel_filterbank(sr, frame, n_mels).T + 1e-8)
    mfccs = dct(log_mel, type=2, axis=1, norm="ortho")[:, :n_mfcc]
    emb = np.concatenate([mfccs.mean(axis=0), mfccs.std(axis=0)])
    norm = float(np.linalg.norm(emb))
    return emb / norm if norm > 0 else emb


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if na <= 0 or nb <= 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def per_pair_benefit(rows: list[dict[str, Any]], config: str = "greedy") -> dict[tuple[str, str], dict[str, float]]:
    """Aggregate per-(con,pro) separation benefit (ΔCER) three ways: tail-sensitive mean,
    tail-robust median, and capped-to-[-1,1] mean."""
    by_pair: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        if r.get("config") != config:
            continue
        try:
            d = float(r["delta_cer"])
        except (TypeError, ValueError, KeyError):
            continue
        by_pair[(str(r["con"]), str(r["pro"]))].append(d)
    out: dict[tuple[str, str], dict[str, float]] = {}
    for key, ds in by_pair.items():
        arr = np.asarray(ds)
        out[key] = {
            "mean": float(arr.mean()),
            "median": float(np.median(arr)),
            "capped": float(np.clip(arr, -1.0, 1.0).mean()),
        }
    return out


def correlate(dissimilarity: list[float], benefit: list[float]) -> dict[str, float]:
    return {"spearman": spearman_corr(dissimilarity, benefit), "pearson": round(pearson(dissimilarity, benefit), 4)}


# --------------------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------------------
def embed_snippets() -> dict[str, np.ndarray]:
    emb: dict[str, np.ndarray] = {}
    for p in sorted(SNIPPETS_DIR.glob("*.wav")):
        e = mfcc_embedding(read_mono_audio(p).samples)
        if e is not None:
            emb[p.name] = e
    return emb


def _structure_gap(emb: dict[str, np.ndarray]) -> dict[str, float]:
    con = [k for k in emb if k.startswith("con_")]
    pro = [k for k in emb if k.startswith("pro_")]

    def avg(a: list[str], b: list[str], same: bool) -> float:
        vals = [cosine_sim(emb[x], emb[y]) for i, x in enumerate(a) for j, y in enumerate(b) if not (same and j <= i)]
        return float(np.mean(vals)) if vals else 0.0

    within = (avg(con, con, True) + avg(pro, pro, True)) / 2.0
    cross = avg(con, pro, False)
    return {"within_side_cos": round(within, 4), "cross_side_cos": round(cross, 4), "structure_gap": round(within - cross, 4)}


def analyze(out_dir: Path) -> dict[str, Any]:
    emb = embed_snippets()
    with PHASE_CURVE.open("r", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    benefit = per_pair_benefit(rows)
    dis: list[float] = []
    means: list[float] = []
    medians: list[float] = []
    capped: list[float] = []
    for (c, p), b in benefit.items():
        if c in emb and p in emb:
            dis.append(1.0 - cosine_sim(emb[c], emb[p]))
            means.append(b["mean"])
            medians.append(b["median"])
            capped.append(b["capped"])
    summary = {
        "n_pairs": len(dis),
        "speaker_structure": _structure_gap(emb),
        "dissimilarity_var": round(float(np.var(dis)), 5) if dis else 0.0,
        "corr_mean_benefit_tail_sensitive": correlate(dis, means),
        "corr_median_benefit_tail_robust": correlate(dis, medians),
        "corr_capped_benefit": correlate(dis, capped),
        "verdict": "",
    }
    sp_mean = summary["corr_mean_benefit_tail_sensitive"]["pearson"]
    sp_med = summary["corr_median_benefit_tail_robust"]["pearson"]
    summary["verdict"] = (
        "speaker_similarity_not_predictive_tail_artifact"
        if abs(sp_med) < 0.2 and sp_mean - sp_med > 0.2
        else "speaker_similarity_signal_survives_tail_control"
        if abs(sp_med) >= 0.2
        else "no_clear_signal"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "speaker_similarity_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[spk-sim] n={summary['n_pairs']} verdict={summary['verdict']} "
          f"mean_pearson={sp_mean} median_pearson={sp_med}", flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Speaker-similarity vs separation-benefit probe (frontier).")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    analyze(Path(parse_args().out_dir))


if __name__ == "__main__":
    main()
