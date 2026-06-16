"""Reference-free quality estimation for overlapping-speech ASR (experimental/frontier).

Research question:
  The Separation Tax study (RQ4) showed Whisper's compression ratio flags *catastrophic*
  hallucinations (CER > 1.0) at AUC 1.0. This module asks the graded question: across all
  600 collected conditions, how well do purely reference-free signals — segment
  compression ratio, n-gram repetition count, max no-speech probability — predict the
  *actual CER* of a transcript, not just the binary tail? A good reference-free CER proxy
  is the foundation for risk-aware routing, confidence display, and active-learning sample
  selection (which utterances to send to human review).

  This is a deeper analysis of the data already produced by
  results/frontier/separation_tax/phase_curve.csv (no new ASR run); it extends RQ4 from
  catastrophe detection to graded quality estimation. Honest limitation: it reuses the same
  transcripts that produced RQ4, so it is a richer read of that evidence, not an independent
  replication.

Labels: experimental/frontier. CER is the prediction *target* for this analysis only and is
never fed back as a routing input anywhere in the pipeline. Stable tables untouched; outputs
go to results/frontier/reference_free_qe/.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .separation_tax_phase import _to_float, rank_auc

PHASE_CURVE = PROJECT_ROOT / "results" / "frontier" / "separation_tax" / "phase_curve.csv"
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "reference_free_qe"
CER_THRESHOLDS = [0.3, 0.5, 1.0]
SIGNALS = ["compression_ratio", "repetition", "no_speech_prob"]


# --------------------------------------------------------------------------------------
# Pure statistics (unit-tested)
# --------------------------------------------------------------------------------------
def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n < 2:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return 0.0
    return cov / ((va ** 0.5) * (vb ** 0.5))


def spearman_corr(xs: list[float], ys: list[float]) -> float:
    """Rank correlation: Pearson on average ranks (handles ties)."""
    if len(xs) < 2:
        return 0.0
    return round(pearson(_average_ranks(xs), _average_ranks(ys)), 4)


def detection_auc(scores: list[float], cers: list[float], threshold: float) -> float:
    """Ranking AUC for flagging CER > threshold using a reference-free score."""
    labels = [1 if c > threshold else 0 for c in cers]
    return round(rank_auc(scores, labels), 4)


def decile_calibration(scores: list[float], cers: list[float], n_bins: int = 5) -> list[dict[str, float]]:
    """Sort by score, split into n_bins equal-count buckets; report mean score & mean CER
    per bucket. Monotone increasing mean CER => the signal tracks quality."""
    pairs = sorted(zip(scores, cers), key=lambda p: p[0])
    n = len(pairs)
    if n == 0:
        return []
    out: list[dict[str, float]] = []
    for b in range(n_bins):
        lo = b * n // n_bins
        hi = (b + 1) * n // n_bins
        chunk = pairs[lo:hi]
        if not chunk:
            continue
        out.append(
            {
                "bin": b + 1,
                "n": len(chunk),
                "mean_score": round(sum(s for s, _ in chunk) / len(chunk), 4),
                "mean_cer": round(sum(c for _, c in chunk) / len(chunk), 4),
            }
        )
    return out


def is_monotone_increasing(values: list[float]) -> bool:
    return all(b >= a for a, b in zip(values, values[1:]))


# --------------------------------------------------------------------------------------
# Driver (reads existing phase_curve.csv — no ASR)
# --------------------------------------------------------------------------------------
def pool_separated_samples(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    """Per-track samples from greedy rows: each separated track contributes one (signals, CER)."""
    cr: list[float] = []
    rep: list[float] = []
    nsp: list[float] = []
    cer: list[float] = []
    for r in rows:
        if r.get("config") != "greedy":
            continue
        for cr_k, rep_k, nsp_k, cer_k in (
            ("cr_sep1", "rep_sep1", "nsp_sep1", "cer_sep1"),
            ("cr_sep2", "rep_sep2", "nsp_sep2", "cer_sep2"),
        ):
            c = _to_float(r.get(cer_k))
            if c != c:  # NaN
                continue
            cr.append(_to_float(r.get(cr_k)))
            rep.append(_to_float(r.get(rep_k)))
            nsp.append(_to_float(r.get(nsp_k)))
            cer.append(c)
    return {"compression_ratio": cr, "repetition": rep, "no_speech_prob": nsp, "cer": cer}


def analyze(out_dir: Path) -> dict[str, Any]:
    with PHASE_CURVE.open("r", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    pool = pool_separated_samples(rows)
    cer = pool["cer"]
    n = len(cer)
    per_signal: dict[str, Any] = {}
    for sig in SIGNALS:
        scores = pool[sig]
        per_signal[sig] = {
            "spearman_vs_cer": spearman_corr(scores, cer),
            "detection_auc": {str(t): detection_auc(scores, cer, t) for t in CER_THRESHOLDS},
        }
    # calibration for the strongest single signal (by |spearman|)
    best = max(SIGNALS, key=lambda s: abs(per_signal[s]["spearman_vs_cer"]))
    calib = decile_calibration(pool[best], cer, n_bins=5)
    summary = {
        "n_separated_track_samples": n,
        "signals": per_signal,
        "best_single_signal": best,
        "calibration_best_signal": {"signal": best, "bins": calib,
                                    "monotone": is_monotone_increasing([b["mean_cer"] for b in calib])},
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qe_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    # flat table
    with (out_dir / "qe_signal_table.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["signal", "spearman_vs_cer", "auc_cer>0.3", "auc_cer>0.5", "auc_cer>1.0"])
        for sig in SIGNALS:
            a = per_signal[sig]["detection_auc"]
            w.writerow([sig, per_signal[sig]["spearman_vs_cer"], a["0.3"], a["0.5"], a["1.0"]])
    print(f"[qe] n={n} best={best} wrote qe_summary.json + qe_signal_table.csv", flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reference-free quality estimation for overlap ASR (frontier).")
    parser.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    analyze(Path(parse_args().out_dir))


if __name__ == "__main__":
    main()
