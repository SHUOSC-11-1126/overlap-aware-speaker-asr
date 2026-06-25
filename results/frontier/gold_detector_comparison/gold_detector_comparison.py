"""RQ21: Gold-benchmark detector comparison — CR vs language-id entropy.

Does language-id entropy help or hurt on repetitive hallucination?

RQ13 (PR #906) built language-id entropy for AISHELL-4's *diverse* hallucination
(94.6% sensitivity vs CR's 2.7%). But on the gold benchmark, hallucination is
*repetitive* (Mode R, CR > 2.4): a single Chinese phrase looped many times —
monoscript Han, so language-id entropy ~ 0. CR achieves AUC ~ 1.0 on gold. This
study tests whether lang-id entropy is complementary (neutral on gold, strong on
AISHELL-4) or competitive (hurts on gold), and establishes a dataset-aware
switching criterion.

Hypotheses
----------
- H21a: Language-id entropy achieves < 50% sensitivity on gold's repetitive
  hallucination (vs CR's ~100%).
- H21b: CR achieves > 90% sensitivity on gold's repetitive hallucination at 90%
  specificity.
- H21c: A dataset-aware switch (CR on gold, lang-id on AISHELL-4) achieves > 90%
  sensitivity on both datasets.

Method
------
Gold benchmark: 300 greedy conditions (20 con x pro pairings x 15 overlap ratios)
x 2 oracle-separated tracks (sep1=con, sep2=pro) = 600 tracks. Per-track separated
text is decoded once by ``decode_gold_tracks.py`` (Whisper-tiny, greedy, matching
``separation_tax_phase``) and cached in ``gold_track_texts.json``. CER per track
comes from ``separation_tax/phase_curve.csv`` (read-only). Hallucination label:
``cer_sepN > 5.0 OR cr_sepN_phase > 2.4`` (the catastrophic-repetitive tail).

AISHELL-4: 77 windows from ``rq1_aishell4_validation_results.json``. Per-speaker
separated text is aggregated by MAX across speakers (same convention as RQ13).
Hallucination label: ``always_separated_cpwer > 1.0`` (37 hallucinated / 40 clean).

Detectors (both reference-free, higher = more hallucinated):
  - CR: len(utf8) / len(zlib.compress(utf8)) on the track text.
  - Language-id entropy: Shannon entropy over Unicode script categories.

Each detector is calibrated to >= 90% specificity on the non-hallucinated tracks of
its own dataset; sensitivity is measured on the hallucinated tracks. The
dataset-aware switch uses CR on gold tracks and lang-id entropy on AISHELL-4 tracks
(each calibrated on its own dataset). Bootstrap 95% CIs use 10,000 resamples
(seed=42) with the full-sample-fixed threshold.

This script is pure reanalysis (numpy + stdlib only; no scipy, no sklearn, no
Whisper, no audio). Label: experimental/frontier. Closes #916.
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
import zlib
from pathlib import Path
from typing import Any

import numpy as np

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "gold_detector_comparison"
GOLD_TEXT_JSON = OUT_DIR / "gold_track_texts.json"
GOLD_CURVE_CSV = PROJECT_ROOT / "results" / "frontier" / "separation_tax" / "phase_curve.csv"
AISHELL4_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_CSV = OUT_DIR / "comparison_results.csv"
OUT_JSON = OUT_DIR / "comparison_results.json"

# ------------------------------------------------------------------ thresholds
GOLD_CER_CATASTROPHIC = 5.0     # CER > 5.0 => catastrophic hallucination (gold)
GOLD_CR_REPETITIVE = 2.4        # Whisper's compression_ratio_threshold (repetition)
AISHELL4_CPWER_HALLUC = 1.0     # cpWER > 1.0 => insertions dominate (AISHELL-4)
TARGET_SPECIFICITY = 0.90       # calibrate each detector to >= 90% specificity
N_BOOT = 10000
SEED = 42
EPS = 1e-9


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches RQ13's ``compression_ratio`` and Whisper's ``compression_ratio``. Returns
    0.0 for empty/whitespace text. High CR (>~2.4) = repetitive loop."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


# ------------------------------------------------------------- script detection
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (same as RQ13)."""
    if ch.isspace():
        return "Space"
    name = unicodedata.name(ch, "")
    if not name:
        return "Other"
    first = name.split()[0]
    if first == "CJK":
        return "Han"
    if first == "LATIN" or "LATIN" in name:
        return "Latin"
    if first == "HIRAGANA":
        return "Hiragana"
    if first == "KATAKANA":
        return "Katakana"
    if first == "HANGUL":
        return "Hangul"
    if first == "CYRILLIC":
        return "Cyrillic"
    if first == "ARABIC":
        return "Arabic"
    if first == "GREEK":
        return "Greek"
    if first == "DIGIT":
        return "Digit"
    cat = unicodedata.category(ch)
    if cat.startswith("P") or cat.startswith("S"):
        return "Punct"
    return "Other"


# --------------------------------------------------------------- lang-id entropy
def language_id_entropy(text: str) -> float:
    """Shannon entropy (bits) over the script-category distribution of the text.

    Clean Chinese (near-monoscript Han) -> entropy ~ 0. Diverse multilingual
    gibberish mixing Han+Latin+Katakana+Hangul -> high entropy (up to log2(k)).
    Repetitive Chinese loops are also monoscript -> entropy ~ 0 (non-discriminative
    on gold's repetitive hallucination)."""
    if not text or not text.strip():
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        sc = script_category(ch)
        counts[sc] = counts.get(sc, 0) + 1
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            h -= p * math.log2(p)
    return h


# --------------------------------------------------------- threshold calibration
def roc_operating_point(
    neg_scores: list[float], pos_scores: list[float], target_spec: float = TARGET_SPECIFICITY
) -> dict[str, float]:
    """Pick the threshold with specificity >= target_spec and maximal sensitivity.

    Candidate thresholds = all unique scores. Flag = score >= threshold. Returns the
    threshold, achieved specificity, and sensitivity. If no threshold meets the
    specificity target (degenerate), returns the highest threshold (flag nothing)."""
    n_neg = len(neg_scores)
    n_pos = len(pos_scores)
    candidates = sorted(set(neg_scores) | set(pos_scores))
    best: dict[str, float] | None = None
    for t in candidates:
        fp = sum(1 for s in neg_scores if s >= t - EPS)
        tp = sum(1 for s in pos_scores if s >= t - EPS)
        spec = 1.0 - (fp / n_neg) if n_neg else 1.0
        sens = (tp / n_pos) if n_pos else 0.0
        if spec >= target_spec - EPS:
            if best is None or sens > best["sensitivity"] + EPS or (
                abs(sens - best["sensitivity"]) <= EPS and spec > best["specificity"]
            ):
                best = {
                    "threshold": float(t),
                    "specificity": float(spec),
                    "sensitivity": float(sens),
                    "tp": float(tp),
                    "fp": float(fp),
                    "tn": float(n_neg - fp),
                    "fn": float(n_pos - tp),
                }
    if best is None:
        t = (max(neg_scores + pos_scores) + 1.0) if (neg_scores or pos_scores) else 0.0
        best = {
            "threshold": float(t),
            "specificity": 1.0,
            "sensitivity": 0.0,
            "tp": 0.0, "fp": 0.0,
            "tn": float(n_neg), "fn": float(n_pos),
        }
    return best


# --------------------------------------------------------------------- bootstrap
def bootstrap_sensitivity_ci(
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for sensitivity = P(score >= threshold | label==1).

    Resamples the tracks with replacement and recomputes sensitivity with the
    FIXED full-sample threshold (threshold uncertainty is not included). Resamples
    with no hallucinated track are skipped."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    sens: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        s = scores[idx]
        lab = labels[idx]
        n_pos = int(lab.sum())
        if n_pos <= 0:
            continue
        tp = int(((s >= threshold - EPS) & (lab == 1)).sum())
        sens.append(tp / n_pos)
    if not sens:
        return 0.0, 0.0
    return float(np.percentile(sens, 2.5)), float(np.percentile(sens, 97.5))


def bootstrap_specificity_ci(
    scores: np.ndarray,
    labels: np.ndarray,
    threshold: float,
    n_boot: int = N_BOOT,
    seed: int = SEED + 1,
) -> tuple[float, float]:
    """Bootstrap 95% CI for specificity = P(score < threshold | label==0)."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    spec: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        s = scores[idx]
        lab = labels[idx]
        n_neg = int((lab == 0).sum())
        if n_neg <= 0:
            continue
        tn = int(((s < threshold - EPS) & (lab == 0)).sum())
        spec.append(tn / n_neg)
    if not spec:
        return 0.0, 0.0
    return float(np.percentile(spec, 2.5)), float(np.percentile(spec, 97.5))


# --------------------------------------------------------------- AUC (Mann-Whitney)
def rank_auc(scores: list[float], labels: list[int]) -> float:
    """AUC via Mann-Whitney U. 0.5 if either class is empty."""
    pos = [s for s, l in zip(scores, labels) if l == 1]
    neg = [s for s, l in zip(scores, labels) if l == 0]
    if not pos or not neg:
        return 0.5
    wins = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    return wins / (len(pos) * len(neg))


# --------------------------------------------------------------- load gold tracks
def load_gold_tracks() -> list[dict[str, Any]]:
    """Load the 600 gold tracks (300 conditions x sep1/sep2) with text, CER, CR.

    Matches each decoded condition to its CER in phase_curve.csv (greedy config).
    Hallucination label: cer_sepN > 5.0 OR cr_sepN_phase > 2.4."""
    cache = json.loads(GOLD_TEXT_JSON.read_text(encoding="utf-8"))
    # index phase_curve greedy rows by (con, pro, overlap_ratio)
    curve_rows: dict[tuple[str, str, float], dict[str, str]] = {}
    with GOLD_CURVE_CSV.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["config"] != "greedy":
                continue
            key = (r["con"], r["pro"], float(r["overlap_ratio"]))
            curve_rows[key] = r

    tracks: list[dict[str, Any]] = []
    for t in cache["tracks"]:
        key = (t["con"], t["pro"], float(t["overlap_ratio"]))
        row = curve_rows.get(key)
        if row is None:
            continue
        for arm, text_key, cer_key, cr_key, label_speaker in [
            ("sep1", "sep1_text", "cer_sep1", "cr_sep1", "con"),
            ("sep2", "sep2_text", "cer_sep2", "cr_sep2", "pro"),
        ]:
            text = t[text_key]
            cer = float(row[cer_key])
            cr_phase = float(row[cr_key])
            halluc = (cer > GOLD_CER_CATASTROPHIC) or (cr_phase > GOLD_CR_REPETITIVE)
            track_id = f"{Path(t['con']).stem}_{Path(t['pro']).stem}_r{t['overlap_ratio']}_{arm}"
            tracks.append({
                "dataset": "gold",
                "track_id": track_id,
                "con": t["con"],
                "pro": t["pro"],
                "overlap_ratio": float(t["overlap_ratio"]),
                "arm": arm,
                "speaker": label_speaker,
                "text": text,
                "cer": cer,
                "cr_phase_curve": cr_phase,
                "cr": compression_ratio(text),
                "lang_id_entropy": language_id_entropy(text),
                "hallucinated": bool(halluc),
            })
    return tracks


# ------------------------------------------------------------ load AISHELL-4 tracks
def load_aishell4_tracks() -> list[dict[str, Any]]:
    """Load the 77 AISHELL-4 windows with max-across-speakers CR and lang-id entropy.

    Same convention as RQ13: a window is flagged if ANY speaker track trips the
    detector (max aggregation). Hallucination label: always_separated_cpwer > 1.0."""
    data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
    tracks: list[dict[str, Any]] = []
    for w in data["windows"]:
        sep_cpwer = float(w["always_separated_cpwer"])
        sep_texts = w.get("separated_text_per_speaker", {})
        # max across non-empty speaker tracks
        cr_vals = [compression_ratio(str(t)) for t in sep_texts.values()
                   if t is not None and str(t).strip()]
        ent_vals = [language_id_entropy(str(t)) for t in sep_texts.values()
                    if t is not None and str(t).strip()]
        cr = max(cr_vals) if cr_vals else 0.0
        ent = max(ent_vals) if ent_vals else 0.0
        halluc = sep_cpwer > AISHELL4_CPWER_HALLUC
        tracks.append({
            "dataset": "aishell4",
            "track_id": w["window_id"],
            "con": "",
            "pro": "",
            "overlap_ratio": float(w.get("overlap_ratio", 0.0)),
            "arm": "window",
            "speaker": "",
            "text": " | ".join(str(t) for t in sep_texts.values() if t),
            "cer": sep_cpwer,  # cpWER stored in cer field for uniformity
            "cr_phase_curve": 0.0,
            "cr": cr,
            "lang_id_entropy": ent,
            "hallucinated": bool(halluc),
        })
    return tracks


# ------------------------------------------------------- per-dataset detector eval
def evaluate_detector(
    tracks: list[dict[str, Any]], score_key: str, dataset_name: str, detector_name: str
) -> dict[str, Any]:
    """Calibrate a detector at >= 90% specificity on non-hallucinated tracks,
    measure sensitivity on hallucinated tracks, bootstrap CIs."""
    scores = np.array([t[score_key] for t in tracks], dtype=float)
    labels = np.array([1 if t["hallucinated"] else 0 for t in tracks], dtype=float)
    neg = [float(s) for s, l in zip(scores, labels) if l == 0]
    pos = [float(s) for s, l in zip(scores, labels) if l == 1]
    op = roc_operating_point(neg, pos, TARGET_SPECIFICITY)
    ci_lo, ci_hi = bootstrap_sensitivity_ci(scores, labels, op["threshold"])
    sp_lo, sp_hi = bootstrap_specificity_ci(scores, labels, op["threshold"])
    auc = rank_auc([float(s) for s in scores], [int(l) for l in labels])
    n_pos = int(labels.sum())
    n_neg = len(labels) - n_pos
    return {
        "dataset": dataset_name,
        "detector": detector_name,
        "score_key": score_key,
        "threshold": round(op["threshold"], 6),
        "threshold_exact": float(op["threshold"]),
        "specificity": round(op["specificity"], 6),
        "specificity_ci_95": [round(sp_lo, 6), round(sp_hi, 6)],
        "sensitivity": round(op["sensitivity"], 6),
        "sensitivity_ci_95": [round(ci_lo, 6), round(ci_hi, 6)],
        "auc": round(auc, 6),
        "tp": int(op["tp"]),
        "fp": int(op["fp"]),
        "tn": int(op["tn"]),
        "fn": int(op["fn"]),
        "n_pos": n_pos,
        "n_neg": n_neg,
    }


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gold_tracks = load_gold_tracks()
    aishell4_tracks = load_aishell4_tracks()
    all_tracks = gold_tracks + aishell4_tracks

    gold_n = len(gold_tracks)
    gold_pos = sum(1 for t in gold_tracks if t["hallucinated"])
    a4_n = len(aishell4_tracks)
    a4_pos = sum(1 for t in aishell4_tracks if t["hallucinated"])

    # --- Per-dataset detector evaluation.
    gold_cr = evaluate_detector(gold_tracks, "cr", "gold", "compression_ratio")
    gold_ent = evaluate_detector(gold_tracks, "lang_id_entropy", "gold", "language_id_entropy")
    a4_cr = evaluate_detector(aishell4_tracks, "cr", "aishell4", "compression_ratio")
    a4_ent = evaluate_detector(aishell4_tracks, "lang_id_entropy", "aishell4", "language_id_entropy")

    # --- Dataset-aware switch: CR on gold, lang-id entropy on AISHELL-4.
    # Each detector uses its own dataset-calibrated threshold (exact, unrounded to
    # avoid a boundary track being missed by floating-point rounding of the threshold).
    gold_cr_thresh = gold_cr["threshold_exact"]
    a4_ent_thresh = a4_ent["threshold_exact"]

    # Gold switch performance (CR detector on gold).
    switch_gold_tp = sum(1 for t in gold_tracks if t["hallucinated"] and t["cr"] >= gold_cr_thresh - EPS)
    switch_gold_fp = sum(1 for t in gold_tracks if not t["hallucinated"] and t["cr"] >= gold_cr_thresh - EPS)
    switch_gold_tn = gold_n - gold_pos - switch_gold_fp
    switch_gold_fn = gold_pos - switch_gold_tp
    # AISHELL-4 switch performance (lang-id entropy on AISHELL-4).
    switch_a4_tp = sum(1 for t in aishell4_tracks if t["hallucinated"] and t["lang_id_entropy"] >= a4_ent_thresh - EPS)
    switch_a4_fp = sum(1 for t in aishell4_tracks if not t["hallucinated"] and t["lang_id_entropy"] >= a4_ent_thresh - EPS)
    switch_a4_tn = a4_n - a4_pos - switch_a4_fp
    switch_a4_fn = a4_pos - switch_a4_tp

    # Combined sensitivity across both datasets.
    combined_tp = switch_gold_tp + switch_a4_tp
    combined_pos = gold_pos + a4_pos
    combined_sensitivity = combined_tp / combined_pos if combined_pos else 0.0

    switch_result = {
        "policy": "dataset-aware switch (CR on gold, lang-id entropy on AISHELL-4)",
        "gold_threshold_cr": round(gold_cr_thresh, 6),
        "aishell4_threshold_lang_id": round(a4_ent_thresh, 6),
        "gold_sensitivity": round(switch_gold_tp / gold_pos, 6) if gold_pos else 0.0,
        "gold_specificity": round(switch_gold_tn / (gold_n - gold_pos), 6) if (gold_n - gold_pos) else 0.0,
        "gold_tp": switch_gold_tp, "gold_fp": switch_gold_fp,
        "gold_tn": switch_gold_tn, "gold_fn": switch_gold_fn,
        "aishell4_sensitivity": round(switch_a4_tp / a4_pos, 6) if a4_pos else 0.0,
        "aishell4_specificity": round(switch_a4_tn / (a4_n - a4_pos), 6) if (a4_n - a4_pos) else 0.0,
        "aishell4_tp": switch_a4_tp, "aishell4_fp": switch_a4_fp,
        "aishell4_tn": switch_a4_tn, "aishell4_fn": switch_a4_fn,
        "combined_sensitivity": round(combined_sensitivity, 6),
        "combined_tp": combined_tp,
        "combined_n_pos": combined_pos,
    }

    # --- Bootstrap the combined sensitivity of the dataset-aware switch.
    gold_scores_cr = np.array([t["cr"] for t in gold_tracks], dtype=float)
    gold_labels = np.array([1 if t["hallucinated"] else 0 for t in gold_tracks], dtype=float)
    a4_scores_ent = np.array([t["lang_id_entropy"] for t in aishell4_tracks], dtype=float)
    a4_labels = np.array([1 if t["hallucinated"] else 0 for t in aishell4_tracks], dtype=float)
    rng = np.random.default_rng(SEED)
    combined_sens_boot: list[float] = []
    for _ in range(N_BOOT):
        g_idx = rng.integers(0, len(gold_scores_cr), size=len(gold_scores_cr))
        a_idx = rng.integers(0, len(a4_scores_ent), size=len(a4_scores_ent))
        g_tp = int(((gold_scores_cr[g_idx] >= gold_cr_thresh - EPS) & (gold_labels[g_idx] == 1)).sum())
        g_pos = int(gold_labels[g_idx].sum())
        a_tp = int(((a4_scores_ent[a_idx] >= a4_ent_thresh - EPS) & (a4_labels[a_idx] == 1)).sum())
        a_pos = int(a4_labels[a_idx].sum())
        tot_pos = g_pos + a_pos
        if tot_pos <= 0:
            continue
        combined_sens_boot.append((g_tp + a_tp) / tot_pos)
    if combined_sens_boot:
        combined_ci = [round(float(np.percentile(combined_sens_boot, 2.5)), 6),
                       round(float(np.percentile(combined_sens_boot, 97.5)), 6)]
    else:
        combined_ci = [0.0, 0.0]
    switch_result["combined_sensitivity_ci_95"] = combined_ci

    # --- Hypothesis verdicts.
    h21a_supported = gold_ent["sensitivity"] < 0.50
    h21b_supported = gold_cr["sensitivity"] > 0.90 and gold_cr["specificity"] >= 0.90 - EPS
    h21c_supported = (
        switch_result["gold_sensitivity"] > 0.90
        and switch_result["aishell4_sensitivity"] > 0.90
    )

    # --- Distribution stats for the findings writeup.
    def dist_stats(tracks: list[dict[str, Any]], key: str, label: bool) -> dict[str, float]:
        vals = [t[key] for t in tracks if t["hallucinated"] == label]
        if not vals:
            return {"n": 0, "median": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}
        arr = np.array(vals, dtype=float)
        return {
            "n": len(vals),
            "median": round(float(np.median(arr)), 6),
            "mean": round(float(np.mean(arr)), 6),
            "min": round(float(np.min(arr)), 6),
            "max": round(float(np.max(arr)), 6),
        }

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ21: Gold-benchmark detector comparison — CR vs language-id entropy",
        "closes_issue": 916,
        "method": (
            "reanalysis only (no Whisper / no ASR run by this script); gold per-track text "
            "decoded once by decode_gold_tracks.py (Whisper-tiny greedy, matching "
            "separation_tax_phase) and cached; AISHELL-4 text read from existing JSON"
        ),
        "gold_source_text": str(GOLD_TEXT_JSON.relative_to(PROJECT_ROOT)),
        "gold_source_cer": str(GOLD_CURVE_CSV.relative_to(PROJECT_ROOT)),
        "aishell4_source": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
        "gold_hallucination_label": f"cer_sepN > {GOLD_CER_CATASTROPHIC} OR cr_sepN_phase > {GOLD_CR_REPETITIVE}",
        "aishell4_hallucination_label": f"always_separated_cpwer > {AISHELL4_CPWER_HALLUC}",
        "target_specificity": TARGET_SPECIFICITY,
        "aggregation_gold": "per-track (sep1 + sep2, 600 tracks); CR and lang-id computed from decoded text",
        "aggregation_aishell4": "max across per-speaker separated transcripts (worst-case track), same as RQ13",
        "gold_n_tracks": gold_n,
        "gold_n_hallucinated": gold_pos,
        "gold_n_nonhallucinated": gold_n - gold_pos,
        "aishell4_n_tracks": a4_n,
        "aishell4_n_hallucinated": a4_pos,
        "aishell4_n_nonhallucinated": a4_n - a4_pos,
        "detectors": {
            "gold_cr": gold_cr,
            "gold_lang_id_entropy": gold_ent,
            "aishell4_cr": a4_cr,
            "aishell4_lang_id_entropy": a4_ent,
        },
        "dataset_aware_switch": switch_result,
        "distribution_stats": {
            "gold_cr_hallucinated": dist_stats(gold_tracks, "cr", True),
            "gold_cr_nonhallucinated": dist_stats(gold_tracks, "cr", False),
            "gold_lang_id_hallucinated": dist_stats(gold_tracks, "lang_id_entropy", True),
            "gold_lang_id_nonhallucinated": dist_stats(gold_tracks, "lang_id_entropy", False),
            "aishell4_cr_hallucinated": dist_stats(aishell4_tracks, "cr", True),
            "aishell4_cr_nonhallucinated": dist_stats(aishell4_tracks, "cr", False),
            "aishell4_lang_id_hallucinated": dist_stats(aishell4_tracks, "lang_id_entropy", True),
            "aishell4_lang_id_nonhallucinated": dist_stats(aishell4_tracks, "lang_id_entropy", False),
        },
        "hypothesis_verdicts": {
            "H21a": {
                "statement": "language-id entropy achieves < 50% sensitivity on gold's repetitive hallucination",
                "sensitivity": gold_ent["sensitivity"],
                "specificity": gold_ent["specificity"],
                "bootstrap_ci_95": gold_ent["sensitivity_ci_95"],
                "supported": bool(h21a_supported),
            },
            "H21b": {
                "statement": "CR achieves > 90% sensitivity on gold's repetitive hallucination at 90% specificity",
                "sensitivity": gold_cr["sensitivity"],
                "specificity": gold_cr["specificity"],
                "bootstrap_ci_95": gold_cr["sensitivity_ci_95"],
                "supported": bool(h21b_supported),
            },
            "H21c": {
                "statement": "dataset-aware switch (CR on gold, lang-id on AISHELL-4) achieves > 90% sensitivity on both",
                "gold_sensitivity": switch_result["gold_sensitivity"],
                "aishell4_sensitivity": switch_result["aishell4_sensitivity"],
                "combined_sensitivity": switch_result["combined_sensitivity"],
                "combined_ci_95": combined_ci,
                "supported": bool(h21c_supported),
            },
        },
    }

    # --- Write CSV (per-track).
    csv_fields = [
        "dataset", "track_id", "hallucinated", "cr", "lang_id_entropy",
        "cr_flag", "lang_id_flag", "cer", "cr_phase_curve",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for t in all_tracks:
            cr_flag = t["cr"] >= (gold_cr["threshold_exact"] if t["dataset"] == "gold" else a4_cr["threshold_exact"]) - EPS
            ent_flag = t["lang_id_entropy"] >= (a4_ent["threshold_exact"] if t["dataset"] == "aishell4" else gold_ent["threshold_exact"]) - EPS
            wr.writerow({
                "dataset": t["dataset"],
                "track_id": t["track_id"],
                "hallucinated": int(t["hallucinated"]),
                "cr": round(t["cr"], 6),
                "lang_id_entropy": round(t["lang_id_entropy"], 6),
                "cr_flag": int(cr_flag),
                "lang_id_flag": int(ent_flag),
                "cer": round(t["cer"], 6),
                "cr_phase_curve": round(t["cr_phase_curve"], 6),
            })

    # --- Write JSON.
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- Console summary.
    print(f"=== RQ21: Gold-benchmark detector comparison ===")
    print(f"Label: experimental/frontier  |  Closes #916")
    print(f"Gold: {gold_n} tracks ({gold_pos} hallucinated, {gold_n - gold_pos} clean)")
    print(f"AISHELL-4: {a4_n} tracks ({a4_pos} hallucinated, {a4_n - a4_pos} clean)")
    print(f"Target specificity: {TARGET_SPECIFICITY:.0%}")
    print()
    print(f"{'dataset':10s} {'detector':24s} {'thresh':>9s} {'spec':>6s} {'sens':>6s} {'auc':>6s} {'CI95':>16s}")
    for d in [gold_cr, gold_ent, a4_cr, a4_ent]:
        ci = d["sensitivity_ci_95"]
        print(f"{d['dataset']:10s} {d['detector']:24s} {d['threshold']:9.4f} "
              f"{d['specificity']:6.1%} {d['sensitivity']:6.1%} {d['auc']:6.3f} "
              f"[{ci[0]:5.1%},{ci[1]:5.1%}]")
    print()
    print(f"Dataset-aware switch: gold sens={switch_result['gold_sensitivity']:.1%} "
          f"(CR), aishell4 sens={switch_result['aishell4_sensitivity']:.1%} (lang-id), "
          f"combined={switch_result['combined_sensitivity']:.1%} "
          f"CI=[{combined_ci[0]:.1%},{combined_ci[1]:.1%}]")
    print()
    print("Hypothesis verdicts:")
    print(f"  H21a (lang-id < 50% sens on gold): {'SUPPORTED' if h21a_supported else 'NOT SUPPORTED'} "
          f"(sens={gold_ent['sensitivity']:.1%})")
    print(f"  H21b (CR > 90% sens on gold at 90% spec): {'SUPPORTED' if h21b_supported else 'NOT SUPPORTED'} "
          f"(sens={gold_cr['sensitivity']:.1%}, spec={gold_cr['specificity']:.1%})")
    print(f"  H21c (switch > 90% sens on both): {'SUPPORTED' if h21c_supported else 'NOT SUPPORTED'} "
          f"(gold={switch_result['gold_sensitivity']:.1%}, aishell4={switch_result['aishell4_sensitivity']:.1%})")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
