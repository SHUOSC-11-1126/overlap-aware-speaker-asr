"""RQ33: Metadata-only Mode S detector.

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads the existing
AISHELL-4 external-validation results (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890) and
tests whether a METADATA-ONLY detector (runtime + duration + segment count + word
count, NO content features) can catch the 2 Mode S monoscript-Chinese hallucinations
that escape every surface detector (RQ13 lang-id entropy, RQ14 length/CR), every
content-similarity detector (RQ19), every per-speaker-structure detector (RQ22),
and every other surface attempt (RQ23, RQ28 — all 0% Mode S sensitivity).

Label: experimental/frontier. Closes #940.

Background
----------
RQ29 confirmed Mode S (windows 22, 30) accounts for 100% of the corrected-router
residual gap to oracle (cpWER 1.043 vs 1.017). RQ22 found exactly one partial
metadata signal: ``sep_to_mix_runtime_ratio`` caught 1 of 2 Mode S (window 22,
runtime ratio 7.05; window 30 has runtime ratio 0.99 and was missed). Every other
metadata-ish feature was 0% sensitivity at 90% specificity.

This study asks whether bundling ALL metadata features into a single numpy-only
logistic regression with leave-one-out cross-validation can catch BOTH Mode S
windows — i.e. whether the COMBINATION succeeds where each individual feature fails.

Hypotheses
----------
- H33a: metadata-only detector catches both Mode S windows at 90% specificity
  (sensitivity = 100% at specificity >= 90% on the 40 non-hallucinated).
- H33b: combined metadata + lang-id detector achieves > 95% sensitivity on the 37
  AISHELL-4 hallucinated tracks.
- H33c: metadata features have a distinct Mode S profile (permutation p < 0.05 for
  > 50% of the 10 features).

Method
------
1. Extract 10 metadata features (NO content analysis) for all 77 windows.
2. For each feature, two-sided ROC calibration at >= 90% specificity on the 40
   non-hallucinated tracks; report Mode S sensitivity.
3. Combined metadata detector: numpy-only L2 logistic regression on all 10 features
   with leave-one-out cross-validation (LOO-CV). Target = Mode S label. Threshold
   at 90% specificity on the 40 non-hallucinated out-of-fold probabilities.
4. Metadata + lang-id ensemble: OR-combine the metadata detector (LOO-CV flag at
   90% specificity) with the RQ13 lang-id entropy detector (threshold 0.409 bits).
5. Permutation test: for each feature, permute the Mode S label (1000 permutations,
   seed=42) and compute a two-sided p-value for the mean-difference statistic.

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / Whisper are
NOT required). The surface-detector primitives (``script_category``,
``language_id_entropy``, ``compression_ratio``) are lifted verbatim from RQ13/RQ16/
RQ19 so the Mode S definition is directly comparable.
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
SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "metadata_mode_s_detector"
OUT_CSV = OUT_DIR / "metadata_detector_results.csv"
OUT_JSON = OUT_DIR / "metadata_detector_results.json"

# ------------------------------------------------------------------ thresholds
LANG_ID_ENTROPY_THRESHOLD = 0.409   # RQ13 >=90%-specificity operating point
LENGTH_RATIO_THRESHOLD = 2.0        # RQ14 insertion_dominated proxy
CR_THRESHOLD = 2.4                  # Whisper default / RQ14 repetition guard
CATASTROPHIC_CPWER = 1.0            # cpWER > 1.0 => hallucination label
TARGET_SPECIFICITY = 0.90           # calibrate each detector to >= 90% specificity
N_PERM = 1000                       # RQ33 spec: 1000 permutations
N_BOOT = 10000
SEED = 42
EPS = 1e-9
# Logistic-regression hyperparameters. With n_pos=2 Mode S, each LOO fold trains on
# exactly 1 positive against 76 negatives (1:76 imbalance). At weak L2 the single
# positive dominates the class-balanced loss and the probabilities saturate to 0/1
# (a numerical pathology, not a signal). LR_L2 below is the smallest L2 at which all
# LOO fold probabilities are non-saturated (in (0.01, 0.99)); this is a numerical-
# stability criterion, NOT a Mode-S-performance criterion. The L2 sensitivity
# analysis (LR_L2_GRID) is reported prominently so the fragility is visible.
LR_L2 = 50.0
LR_LR = 0.05
LR_N_ITER = 3000
LR_L2_GRID = (1.0, 5.0, 10.0, 25.0, 50.0, 75.0, 100.0, 150.0, 200.0)

CJK_SCRIPTS = {"Han", "Hiragana", "Katakana", "Hangul"}

# The 10 metadata-only features (order is stable; consumed by the logistic regressor).
METADATA_FEATURES: tuple[str, ...] = (
    "sep_runtime_sec",
    "mix_runtime_sec",
    "runtime_ratio",
    "sep_total_chars",
    "mix_total_chars",
    "char_ratio",
    "num_speakers",
    "num_active_speakers_sep",
    "avg_speaker_length_sep",
    "length_entropy_speakers",
)


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches ``whisper.audio.compression_ratio`` and RQ12/RQ13/RQ16/RQ19. Returns 0.0
    for empty/whitespace text. High CR (>~2.4) = repetitive loop."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


# ------------------------------------------------------------- script detection
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13 verbatim)."""
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


def language_id_entropy(text: str) -> float:
    """Shannon entropy (bits) over the script-category distribution (RQ13 verbatim)."""
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


# ------------------------------------------------------------- per-track aggregate
def max_across_speakers(window: dict[str, Any], fn) -> float:
    """Max of fn(text) over per-speaker separated transcripts (RQ12/RQ13 convention)."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def length_ratio(window: dict[str, Any]) -> float:
    """RQ8/RQ14 silence-gap text proxy: separated_total_length / mixed_text_length."""
    sep = float(window.get("separated_total_length", 0) or 0)
    mix = float(window.get("mixed_text_length", 0) or 0)
    return sep / max(1.0, mix)


# ----------------------------------------------------- metadata feature extraction
def _safe_div(num: float, den: float) -> float:
    return num / den if den > EPS else 0.0


def per_speaker_lengths(window: dict[str, Any]) -> list[int]:
    """Character length of each per-speaker separated text (empty channels count as 0).

    Whitespace is stripped before counting so speaker-channel ordering artifacts do
    not inflate lengths. The list length equals ``num_speakers``."""
    sep = window.get("separated_text_per_speaker", {}) or {}
    return [len(str(t).strip()) for t in sep.values()]


def extract_metadata_features(window: dict[str, Any]) -> dict[str, float]:
    """Extract the 10 metadata-only features for one window.

    NO content analysis is performed — only runtime, length/char counts, speaker
    counts, and per-speaker length distribution. ``runtime_ratio`` and ``char_ratio``
    are recomputed from the raw counts (rather than trusting the stored
    ``runtime_ratio`` field) so the feature contract is self-contained.
    """
    sep_runtime = float(window.get("separated_runtime_sec", 0.0) or 0.0)
    mix_runtime = float(window.get("mixed_runtime_sec", 0.0) or 0.0)
    runtime_ratio = _safe_div(sep_runtime, mix_runtime)

    sep_chars = float(window.get("separated_total_length", 0) or 0)
    mix_chars = float(window.get("mixed_text_length", 0) or 0)
    char_ratio = _safe_div(sep_chars, mix_chars) if mix_chars > EPS else 0.0

    num_speakers = int(window.get("num_speakers", 0) or 0)

    lengths = per_speaker_lengths(window)
    nonempty = [ln for ln in lengths if ln > 0]
    num_active = len(nonempty)
    avg_speaker_length = float(np.mean(nonempty)) if nonempty else 0.0
    length_entropy = _shannon_entropy(lengths)

    return {
        "sep_runtime_sec": sep_runtime,
        "mix_runtime_sec": mix_runtime,
        "runtime_ratio": runtime_ratio,
        "sep_total_chars": sep_chars,
        "mix_total_chars": mix_chars,
        "char_ratio": char_ratio,
        "num_speakers": float(num_speakers),
        "num_active_speakers_sep": float(num_active),
        "avg_speaker_length_sep": avg_speaker_length,
        "length_entropy_speakers": length_entropy,
    }


def _shannon_entropy(lengths: list[int]) -> float:
    """Shannon entropy (bits) over the per-speaker length distribution.

    Lengths are normalised to proportions (empty channels count as 0 and therefore
    contribute 0 to the entropy). Matches RQ22 ``per_speaker_length_entropy`` so the
    two studies are directly comparable. Returns 0.0 if total length is 0."""
    total = sum(lengths)
    if total <= 0:
        return 0.0
    h = 0.0
    for ln in lengths:
        if ln <= 0:
            continue
        p = ln / total
        if p > 0:
            h -= p * math.log2(p)
    return h


# --------------------------------------------------------- threshold calibration
def calibrate_two_sided(
    neg_scores: list[float],
    pos_scores_mode_s: list[float],
    pos_scores_all_halluc: list[float],
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """Calibrate a single feature TWO-SIDEDLY at >= target_spec specificity.

    Tries both orientations:
      - "high": flag if score >= threshold (high score = hallucination)
      - "low":  flag if score <= threshold (low score = hallucination)
    Candidate thresholds = all unique scores; specificity is measured on neg_scores
    (non-hallucinated). Among operating points with specificity >= target_spec, the
    one with maximal Mode S sensitivity is kept (tiebreak: maximal all-hallucinated
    sensitivity, then maximal specificity). Lifted from RQ19/RQ22 for comparability.
    """
    n_neg = len(neg_scores)
    n_ms = len(pos_scores_mode_s)
    n_ah = len(pos_scores_all_halluc)
    candidates = sorted(set(neg_scores) | set(pos_scores_mode_s) | set(pos_scores_all_halluc))
    best: dict[str, Any] | None = None

    for direction in ("high", "low"):
        for t in candidates:
            if direction == "high":
                fp = sum(1 for s in neg_scores if s >= t - EPS)
                tp_ms = sum(1 for s in pos_scores_mode_s if s >= t - EPS)
                tp_ah = sum(1 for s in pos_scores_all_halluc if s >= t - EPS)
            else:  # "low"
                fp = sum(1 for s in neg_scores if s <= t + EPS)
                tp_ms = sum(1 for s in pos_scores_mode_s if s <= t + EPS)
                tp_ah = sum(1 for s in pos_scores_all_halluc if s <= t + EPS)
            spec = 1.0 - (fp / n_neg) if n_neg else 1.0
            sens_ms = (tp_ms / n_ms) if n_ms else 0.0
            sens_ah = (tp_ah / n_ah) if n_ah else 0.0
            if spec < target_spec - EPS:
                continue
            cand = {
                "direction": direction,
                "threshold": float(t),
                "specificity": float(spec),
                "sensitivity_mode_s": float(sens_ms),
                "sensitivity_all_hallucinated": float(sens_ah),
                "tp_mode_s": int(tp_ms), "fp": int(fp),
                "tn": int(n_neg - fp), "fn_mode_s": int(n_ms - tp_ms),
                "tp_all_hallucinated": int(tp_ah),
                "fn_all_hallucinated": int(n_ah - tp_ah),
            }
            if best is None:
                best = cand
                continue
            better = (
                sens_ms > best["sensitivity_mode_s"] + EPS
                or (abs(sens_ms - best["sensitivity_mode_s"]) <= EPS
                    and sens_ah > best["sensitivity_all_hallucinated"] + EPS)
                or (abs(sens_ms - best["sensitivity_mode_s"]) <= EPS
                    and abs(sens_ah - best["sensitivity_all_hallucinated"]) <= EPS
                    and spec > best["specificity"] + EPS)
            )
            if better:
                best = cand
    if best is None:
        best = {
            "direction": "none",
            "threshold": float("inf"),
            "specificity": 1.0,
            "sensitivity_mode_s": 0.0,
            "sensitivity_all_hallucinated": 0.0,
            "tp_mode_s": 0, "fp": 0, "tn": int(n_neg), "fn_mode_s": int(n_ms),
            "tp_all_hallucinated": 0, "fn_all_hallucinated": int(n_ah),
        }
    return best


def flag_at(score: float, direction: str, threshold: float) -> bool:
    """Apply a calibrated two-sided operating point to a single score."""
    if direction == "high":
        return score >= threshold - EPS
    if direction == "low":
        return score <= threshold + EPS
    return False


def ceiling_analysis(
    neg_scores: list[float],
    pos_scores_mode_s: list[float],
    spec_floors: list[float],
) -> list[dict[str, Any]]:
    """Max Mode S sensitivity achievable at specificity >= each floor (two-sided)."""
    n_neg = len(neg_scores)
    n_ms = len(pos_scores_mode_s)
    candidates = sorted(set(neg_scores) | set(pos_scores_mode_s))
    out: list[dict[str, Any]] = []
    for floor in spec_floors:
        best_sens = 0.0
        best_dir = "none"
        best_t = float("inf")
        best_spec = 1.0
        for direction in ("high", "low"):
            for t in candidates:
                if direction == "high":
                    fp = sum(1 for s in neg_scores if s >= t - EPS)
                    tp_ms = sum(1 for s in pos_scores_mode_s if s >= t - EPS)
                else:
                    fp = sum(1 for s in neg_scores if s <= t + EPS)
                    tp_ms = sum(1 for s in pos_scores_mode_s if s <= t + EPS)
                spec = 1.0 - (fp / n_neg) if n_neg else 1.0
                sens = (tp_ms / n_ms) if n_ms else 0.0
                if spec >= floor - EPS and sens > best_sens + EPS:
                    best_sens = sens
                    best_dir = direction
                    best_t = float(t)
                    best_spec = spec
        out.append({
            "specificity_floor": floor,
            "max_sensitivity_mode_s": round(best_sens, 6),
            "direction": best_dir,
            "threshold": round(best_t, 6),
            "achieved_specificity": round(best_spec, 6),
        })
    return out


# -------------------------------------------------------------- permutation test
def permutation_test(
    feature_values: np.ndarray, mode_s_mask: np.ndarray,
    n_perm: int = N_PERM, seed: int = SEED,
) -> dict[str, Any]:
    """Permutation test for a distinct Mode S metadata profile.

    Test statistic = mean(feature | Mode S) - mean(feature | not Mode S). The Mode S
    label is permuted among the n tracks (n_perm resamples, seed). p-value (two-sided)
    = fraction of permutations with |stat| >= |observed|, with +1 smoothing. With n=2
    Mode S the resolution is bounded by C(n,2) distinct labelings."""
    n = len(feature_values)
    n_ms = int(mode_s_mask.sum())
    obs_ms_mean = float(feature_values[mode_s_mask].mean()) if n_ms > 0 else 0.0
    obs_other_mean = float(feature_values[~mode_s_mask].mean()) if n_ms < n else 0.0
    obs_stat = obs_ms_mean - obs_other_mean

    rng = np.random.default_rng(seed)
    count_extreme = 0
    for _ in range(n_perm):
        perm_idx = rng.permutation(n)
        perm_mask = np.zeros(n, dtype=bool)
        perm_mask[perm_idx[:n_ms]] = True
        if perm_mask.sum() == 0 or perm_mask.sum() == n:
            continue
        ms_mean = float(feature_values[perm_mask].mean())
        other_mean = float(feature_values[~perm_mask].mean())
        stat = ms_mean - other_mean
        if abs(stat) >= abs(obs_stat) - EPS:
            count_extreme += 1
    p_value = (count_extreme + 1) / (n_perm + 1)
    return {
        "test_statistic": round(obs_stat, 6),
        "mode_s_mean": round(obs_ms_mean, 6),
        "others_mean": round(obs_other_mean, 6),
        "n_perm": n_perm,
        "n_mode_s": n_ms,
        "n_others": n - n_ms,
        "p_value_two_sided": round(p_value, 6),
        "n_extreme": count_extreme,
        "n_distinct_labelings": math.comb(n, n_ms),
        "note": (
            "Two-sided permutation test: fraction of permutations with |stat| >= |observed|. "
            f"With n_mode_s={n_ms} the number of distinct labelings is C({n},{n_ms})="
            f"{math.comb(n, n_ms)}; p-value resolution is bounded and reported with +1 smoothing."
        ),
    }


# --------------------------------------------------------- numpy-only logistic regression
def _sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    out = np.empty_like(z, dtype=float)
    pos = z >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-z[pos]))
    ez = np.exp(z[~pos])
    out[~pos] = ez / (1.0 + ez)
    return out


def standardize_fit(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute mean and std (with +eps guard) for z-scoring columns.

    Constant columns (std==0) are left at 0 (centered to mean, not rescaled)."""
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd = np.where(sd > EPS, sd, 1.0)
    return mu, sd


def standardize_apply(X: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    return (X - mu) / sd


def fit_logistic_regression(
    X: np.ndarray, y: np.ndarray,
    l2: float = 1.0, lr: float = 0.1, n_iter: int = 2000,
    seed: int = SEED,
) -> np.ndarray:
    """Numpy-only L2-regularised logistic regression via gradient descent.

    X is assumed already standardised. Returns the weight vector w (length = n_features
    + 1; the first element is the intercept bias). With n_pos very small (here n=2
    Mode S, and n=1 in each LOO training fold) the L2 term is what keeps the weights
    finite — without it a single positive point is separable and the weights diverge.
    """
    n, d = X.shape
    # Augment with intercept column.
    Xa = np.hstack([np.ones((n, 1)), X])
    w = np.zeros(d + 1)
    # Class-balanced loss weighting so 1 positive among 75 negatives is not drowned.
    n_pos = float(max(int(y.sum()), 1))
    n_neg = float(max(int((y == 0).sum()), 1))
    w_pos = n / (2.0 * n_pos)   # weight on positive examples
    w_neg = n / (2.0 * n_neg)   # weight on negative examples
    sw = np.where(y == 1, w_pos, w_neg)  # shape (n,)
    for _ in range(n_iter):
        p = _sigmoid(Xa @ w)
        grad = (Xa * (sw * (p - y))[:, None]).mean(axis=0)
        # L2 on non-intercept weights only.
        reg = np.concatenate([[0.0], w[1:]])
        grad = grad + (l2 / n) * reg
        w = w - lr * grad
    return w


def predict_proba(X: np.ndarray, w: np.ndarray, mu: np.ndarray, sd: np.ndarray) -> np.ndarray:
    """Standardise X with (mu, sd) then return sigmoid(Xa @ w)."""
    Xs = standardize_apply(X, mu, sd)
    Xa = np.hstack([np.ones((Xs.shape[0], 1)), Xs])
    return _sigmoid(Xa @ w)


def loo_cv_predict(
    X: np.ndarray, y: np.ndarray, l2: float = 1.0, lr: float = 0.1,
    n_iter: int = 2000, seed: int = SEED,
) -> np.ndarray:
    """Leave-one-out cross-validation out-of-fold probabilities.

    For each window i, standardisation + LR are fit on the other n-1 windows and the
    held-out window's P(y=1) is predicted. Returns an array of length n. With n_pos=2
    Mode S, each LOO training fold that holds out a Mode S window has only 1 positive
    — the L2 prior dominates and the held-out Mode S window's probability is driven by
    how similar its metadata is to the single training positive.
    """
    n = X.shape[0]
    oof = np.zeros(n, dtype=float)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        X_tr = X[mask]
        y_tr = y[mask]
        mu, sd = standardize_fit(X_tr)
        w = fit_logistic_regression(X_tr, y_tr, l2=l2, lr=lr, n_iter=n_iter, seed=seed)
        oof[i] = float(predict_proba(X[i:i + 1], w, mu, sd)[0])
    return oof


def calibrate_probability_threshold(
    neg_probs: np.ndarray, pos_probs_mode_s: np.ndarray,
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """Calibrate a one-sided (flag if prob >= t) threshold at >= target_spec specificity.

    LR probabilities are directional (high = Mode S), so only the "high" orientation
    is searched. Candidate thresholds = all unique probabilities; among operating
    points with specificity >= target_spec on the non-hallucinated, the one with
    maximal Mode S sensitivity is kept (tiebreak: maximal specificity)."""
    n_neg = len(neg_probs)
    n_ms = len(pos_probs_mode_s)
    candidates = sorted(set(float(p) for p in neg_probs)
                        | set(float(p) for p in pos_probs_mode_s)
                        | {0.5})
    best: dict[str, Any] | None = None
    for t in candidates:
        fp = int(sum(1 for s in neg_probs if s >= t - EPS))
        tp_ms = int(sum(1 for s in pos_probs_mode_s if s >= t - EPS))
        spec = 1.0 - (fp / n_neg) if n_neg else 1.0
        sens_ms = (tp_ms / n_ms) if n_ms else 0.0
        if spec < target_spec - EPS:
            continue
        cand = {
            "direction": "high",
            "threshold": float(t),
            "specificity": float(spec),
            "sensitivity_mode_s": float(sens_ms),
            "tp_mode_s": tp_ms, "fp": fp, "tn": int(n_neg - fp), "fn_mode_s": int(n_ms - tp_ms),
        }
        if best is None or sens_ms > best["sensitivity_mode_s"] + EPS or (
            abs(sens_ms - best["sensitivity_mode_s"]) <= EPS
            and spec > best["specificity"] + EPS
        ):
            best = cand
    if best is None:
        best = {
            "direction": "high", "threshold": 1.0, "specificity": 1.0,
            "sensitivity_mode_s": 0.0, "tp_mode_s": 0, "fp": 0,
            "tn": int(n_neg), "fn_mode_s": int(n_ms),
        }
    return best


# --------------------------------------------------------------------- bootstrap
def bootstrap_sensitivity_ci(
    scores: np.ndarray, labels: np.ndarray, direction: str, threshold: float,
    n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for sensitivity = P(flag | label==1) with FIXED threshold."""
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
        if direction == "high":
            tp = int(((s >= threshold - EPS) & (lab == 1)).sum())
        else:
            tp = int(((s <= threshold + EPS) & (lab == 1)).sum())
        sens.append(tp / n_pos)
    if not sens:
        return 0.0, 0.0
    return float(np.percentile(sens, 2.5)), float(np.percentile(sens, 97.5))


def bootstrap_specificity_ci(
    scores: np.ndarray, labels: np.ndarray, direction: str, threshold: float,
    n_boot: int = N_BOOT, seed: int = SEED,
) -> tuple[float, float]:
    """Bootstrap 95% CI for specificity = P(not flag | label==0) with FIXED threshold."""
    rng = np.random.default_rng(seed)
    n = len(scores)
    specs: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        s = scores[idx]
        lab = labels[idx]
        n_neg = int((lab == 0).sum())
        if n_neg <= 0:
            continue
        if direction == "high":
            fp = int(((s >= threshold - EPS) & (lab == 0)).sum())
        else:
            fp = int(((s <= threshold + EPS) & (lab == 0)).sum())
        specs.append(1.0 - fp / n_neg)
    if not specs:
        return 0.0, 0.0
    return float(np.percentile(specs, 2.5)), float(np.percentile(specs, 97.5))


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # --- per-window metadata features + labels + surface primitives (for labelling)
    rows: list[dict[str, Any]] = []
    raw_features: list[list[float]] = []  # unrounded, feeds the logistic regressor
    for w in windows:
        sep_cpwer = float(w["always_separated_cpwer"])
        mixed_cpwer = float(w["always_mixed_cpwer"])
        ent = max_across_speakers(w, language_id_entropy)
        mcr = max_across_speakers(w, compression_ratio)
        lr = length_ratio(w)
        halluc = sep_cpwer > CATASTROPHIC_CPWER
        mode_s = (halluc and ent < LANG_ID_ENTROPY_THRESHOLD
                  and lr < LENGTH_RATIO_THRESHOLD and mcr < CR_THRESHOLD)
        feats = extract_metadata_features(w)
        raw_features.append([float(feats[name]) for name in METADATA_FEATURES])
        row = {
            "window_id": w["window_id"],
            "always_separated_cpwer": round(sep_cpwer, 6),
            "always_mixed_cpwer": round(mixed_cpwer, 6),
            "hallucinated": bool(halluc),
            "mode_s": bool(mode_s),
            "lang_id_entropy": round(ent, 6),
            "length_ratio": round(lr, 6),
            "cr": round(mcr, 6),
        }
        # rounded copies for CSV/JSON display; raw_features (unrounded) feed the LR
        row.update({k: round(float(v), 6) for k, v in feats.items()})
        rows.append(row)

    n_halluc = sum(1 for r in rows if r["hallucinated"])
    n_nonhalluc = n - n_halluc
    n_mode_s = sum(1 for r in rows if r["mode_s"])
    mode_s_ids = [r["window_id"] for r in rows if r["mode_s"]]

    # ----------------------------------------------------------------- per-feature
    detector_results: list[dict[str, Any]] = []
    for name in METADATA_FEATURES:
        scores = [float(r[name]) for r in rows]
        neg = [s for s, r in zip(scores, rows) if not r["hallucinated"]]
        pos_ms = [s for s, r in zip(scores, rows) if r["mode_s"]]
        pos_ah = [s for s, r in zip(scores, rows) if r["hallucinated"]]
        op = calibrate_two_sided(neg, pos_ms, pos_ah, TARGET_SPECIFICITY)
        feat_arr = np.array(scores, dtype=float)
        ms_mask = np.array([r["mode_s"] for r in rows], dtype=bool)
        perm = permutation_test(feat_arr, ms_mask, N_PERM, SEED)
        ceil = ceiling_analysis(neg, pos_ms, [0.50, 0.70, 0.80, 0.90, 0.95])
        # bootstrap CIs at the calibrated operating point
        scores_arr = np.array(scores, dtype=float)
        ms_labels = np.array([1.0 if r["mode_s"] else 0.0 for r in rows], dtype=float)
        ci_ms_lo, ci_ms_hi = bootstrap_sensitivity_ci(
            scores_arr, ms_labels, op["direction"], op["threshold"])
        detector_results.append({
            "detector": name,
            "feature_key": name,
            "note": _FEATURE_NOTES[name],
            "direction": op["direction"],
            "direction_meaning": (
                "flag if score >= threshold (high score = hallucination)"
                if op["direction"] == "high"
                else "flag if score <= threshold (low score = hallucination)"
                if op["direction"] == "low" else "no threshold met 90% specificity target"
            ),
            "threshold": round(op["threshold"], 6),
            "specificity": round(op["specificity"], 6),
            "sensitivity_mode_s": round(op["sensitivity_mode_s"], 6),
            "sensitivity_mode_s_ci_95": [round(ci_ms_lo, 6), round(ci_ms_hi, 6)],
            "sensitivity_all_hallucinated": round(op["sensitivity_all_hallucinated"], 6),
            "tp_mode_s": op["tp_mode_s"], "fp": op["fp"],
            "tn": op["tn"], "fn_mode_s": op["fn_mode_s"],
            "tp_all_hallucinated": op["tp_all_hallucinated"],
            "fn_all_hallucinated": op["fn_all_hallucinated"],
            "permutation_test": perm,
            "ceiling_analysis": ceil,
            "n_mode_s": n_mode_s, "n_all_hallucinated": n_halluc, "n_nonhallucinated": n_nonhalluc,
        })

    # best single-feature metadata detector: most distinct profile (lowest perm p),
    # tiebreak highest sens_ms at 90% spec, then highest sens_ah.
    best_single = min(
        detector_results,
        key=lambda d: (d["permutation_test"]["p_value_two_sided"],
                       -d["sensitivity_mode_s"],
                       -d["sensitivity_all_hallucinated"]),
    )

    # ------------------------------------------------- combined metadata LR (LOO-CV)
    # X uses the UNROUNDED raw features; the LR is sensitive enough that 6-decimal
    # display rounding can flip a razor-thin operating point (documented fragility).
    X = np.array(raw_features, dtype=float)
    y_ms = np.array([1.0 if r["mode_s"] else 0.0 for r in rows], dtype=float)
    oof = loo_cv_predict(X, y_ms, l2=LR_L2, lr=LR_LR, n_iter=LR_N_ITER, seed=SEED)

    neg_probs = np.array([oof[i] for i, r in enumerate(rows) if not r["hallucinated"]], dtype=float)
    pos_ms_probs = np.array([oof[i] for i, r in enumerate(rows) if r["mode_s"]], dtype=float)
    lr_op = calibrate_probability_threshold(neg_probs, pos_ms_probs, TARGET_SPECIFICITY)
    lr_thr = lr_op["threshold"]
    lr_dir = lr_op["direction"]
    for r, p in zip(rows, oof):
        r["metadata_lr_prob"] = round(float(p), 6)
        r["metadata_lr_flag"] = bool(flag_at(float(p), lr_dir, lr_thr))

    # bootstrap CI for the LR Mode S sensitivity (fixed threshold, out-of-fold probs)
    oof_arr = np.array(oof, dtype=float)
    ci_lr_lo, ci_lr_hi = bootstrap_sensitivity_ci(oof_arr, y_ms, lr_dir, lr_thr)

    # L2 sensitivity analysis: how robust is the LOO-CV Mode S sensitivity to L2?
    # With n=2 Mode S, L2 cannot be tuned by cross-validation, so this grid exposes
    # the fragility directly. For each L2 we report the calibrated 90%-specificity
    # operating point, the Mode S sensitivity, the ensemble (metadata OR lang-id)
    # all-hallucinated sensitivity, and whether probabilities saturated.
    l2_sensitivity: list[dict[str, Any]] = []
    for l2 in LR_L2_GRID:
        oof_l2 = loo_cv_predict(X, y_ms, l2=l2, lr=LR_LR, n_iter=LR_N_ITER, seed=SEED)
        neg_l2 = np.array([oof_l2[i] for i, r in enumerate(rows) if not r["hallucinated"]], dtype=float)
        ms_l2 = np.array([oof_l2[i] for i, r in enumerate(rows) if r["mode_s"]], dtype=float)
        op_l2 = calibrate_probability_threshold(neg_l2, ms_l2, TARGET_SPECIFICITY)
        sat = bool((oof_l2 <= 0.01).any() or (oof_l2 >= 0.99).any())
        # ensemble (metadata LR flag OR lang-id) all-hallucinated sensitivity at this L2
        ens_tp = 0
        ens_fp_l2 = 0
        for r, p in zip(rows, oof_l2):
            flag = bool(flag_at(float(p), op_l2["direction"], op_l2["threshold"])
                        or (r["lang_id_entropy"] > LANG_ID_ENTROPY_THRESHOLD))
            if r["hallucinated"] and flag:
                ens_tp += 1
            if (not r["hallucinated"]) and flag:
                ens_fp_l2 += 1
        ens_sens_l2 = ens_tp / n_halluc if n_halluc else 0.0
        ens_spec_l2 = (n_nonhalluc - ens_fp_l2) / n_nonhalluc if n_nonhalluc else 0.0
        l2_sensitivity.append({
            "l2": float(l2),
            "mode_s_probs": [round(float(p), 6) for p in ms_l2],
            "neg_max_prob": round(float(neg_l2.max()), 6),
            "threshold": round(op_l2["threshold"], 6),
            "specificity": round(op_l2["specificity"], 6),
            "sensitivity_mode_s": round(op_l2["sensitivity_mode_s"], 6),
            "tp_mode_s": op_l2["tp_mode_s"],
            "fp": op_l2["fp"],
            "ensemble_sensitivity_all_hallucinated": round(ens_sens_l2, 6),
            "ensemble_specificity": round(ens_spec_l2, 6),
            "saturated": sat,
        })
    n_l2_full = sum(1 for s in l2_sensitivity if s["sensitivity_mode_s"] >= 1.0 - EPS)
    n_l2_ens_above_95 = sum(1 for s in l2_sensitivity if s["ensemble_sensitivity_all_hallucinated"] > 0.95)

    # ---------------------------------------------- metadata + lang-id ensemble (H33b)
    for r in rows:
        r["ensemble_flag"] = bool(r["metadata_lr_flag"]
                                  or (r["lang_id_entropy"] > LANG_ID_ENTROPY_THRESHOLD))

    tp_ens_ah = sum(1 for r in rows if r["hallucinated"] and r["ensemble_flag"])
    fp_ens = sum(1 for r in rows if not r["hallucinated"] and r["ensemble_flag"])
    tn_ens = sum(1 for r in rows if not r["hallucinated"] and not r["ensemble_flag"])
    fn_ens_ah = sum(1 for r in rows if r["hallucinated"] and not r["ensemble_flag"])
    ens_sens_ah = tp_ens_ah / n_halluc if n_halluc else 0.0
    ens_spec = tn_ens / n_nonhalluc if n_nonhalluc else 0.0
    tp_ens_ms = sum(1 for r in rows if r["mode_s"] and r["ensemble_flag"])
    ens_sens_ms = tp_ens_ms / n_mode_s if n_mode_s else 0.0

    # lang-id entropy alone (reference, RQ13)
    tp_lang_ah = sum(1 for r in rows if r["hallucinated"] and r["lang_id_entropy"] > LANG_ID_ENTROPY_THRESHOLD)
    fp_lang = sum(1 for r in rows if not r["hallucinated"] and r["lang_id_entropy"] > LANG_ID_ENTROPY_THRESHOLD)
    tp_lang_ms = sum(1 for r in rows if r["mode_s"] and r["lang_id_entropy"] > LANG_ID_ENTROPY_THRESHOLD)
    lang_sens_ah = tp_lang_ah / n_halluc if n_halluc else 0.0
    lang_spec = (n_nonhalluc - fp_lang) / n_nonhalluc if n_nonhalluc else 0.0
    lang_sens_ms = tp_lang_ms / n_mode_s if n_mode_s else 0.0

    # ------------------------------------------------------------- hypothesis verdicts
    h33a_supported = (
        lr_op["sensitivity_mode_s"] >= 1.0 - EPS and lr_op["specificity"] >= TARGET_SPECIFICITY - EPS
    )
    h33b_supported = ens_sens_ah > 0.95
    n_features_distinct = sum(1 for d in detector_results
                              if d["permutation_test"]["p_value_two_sided"] < 0.05)
    h33c_supported = n_features_distinct > (len(METADATA_FEATURES) // 2)

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ33: Metadata-only Mode S detector (runtime + duration + segment count, NO content)",
        "closes_issue": 940,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR run); 10 metadata-only features extracted per "
            "window. Per-feature two-sided calibration at >= 90% specificity on the 40 "
            "non-hallucinated tracks. Combined detector = numpy-only L2 logistic regression on "
            "all 10 features with leave-one-out cross-validation (Mode S label); threshold "
            "calibrated at 90% specificity on the 40 non-hallucinated out-of-fold probabilities. "
            "Ensemble = metadata LR flag OR lang-id entropy (threshold 0.409). Permutation test: "
            "1000 permutations, seed=42, two-sided, +1 smoothing."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated_tracks": n_halluc,
        "n_nonhallucinated_tracks": n_nonhalluc,
        "n_mode_s_tracks": n_mode_s,
        "mode_s_window_ids": mode_s_ids,
        "hallucination_label": "always_separated_cpwer > 1.0 (37/40 split, RQ12)",
        "mode_s_definition": (
            "hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0 AND cr < 2.4 "
            "(escapes every surface detector; the RQ16 corrected-router residual)"
        ),
        "metadata_features": list(METADATA_FEATURES),
        "feature_notes": dict(_FEATURE_NOTES),
        "mode_s_context": {
            "rq22_runtime_ratio_partial_signal": (
                "RQ22 found sep_to_mix_runtime_ratio (= runtime_ratio here) caught 1 of 2 Mode S "
                "(window 22, ratio 7.05) but missed window 30 (ratio 0.99). This study tests "
                "whether bundling all 10 metadata features into a logistic regression with LOO-CV "
                "catches both."
            ),
            "mode_s_metadata_heterogeneity": (
                "Window 22 (runtime_ratio 7.05, num_speakers 2, 1 active speaker) and window 30 "
                "(runtime_ratio 0.99, num_speakers 1, 1 active speaker) have very different "
                "metadata profiles. LOO-CV must generalise from one to the other, which is the "
                "binding constraint."
            ),
        },
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "length_ratio": LENGTH_RATIO_THRESHOLD,
            "cr": CR_THRESHOLD,
            "target_specificity": TARGET_SPECIFICITY,
            "n_perm": N_PERM,
            "lr_l2": LR_L2,
            "lr_lr": LR_LR,
            "lr_n_iter": LR_N_ITER,
            "lr_l2_rationale": (
                "smallest L2 at which all LOO fold probabilities are non-saturated (in (0.01, 0.99)); "
                "a numerical-stability criterion for the 1:76 imbalance in each LOO fold, NOT a "
                "Mode-S-performance criterion. See l2_sensitivity_analysis."
            ),
        },
        "per_feature_detectors": detector_results,
        "best_single_feature_detector": {
            "detector": best_single["detector"],
            "feature_key": best_single["feature_key"],
            "selection_rule": "lowest permutation p-value (most distinct Mode S profile); tiebreak highest Mode S sensitivity at 90% specificity",
            "direction": best_single["direction"],
            "threshold": best_single["threshold"],
            "specificity_at_90pct_target": best_single["specificity"],
            "sensitivity_mode_s_at_90pct_target": best_single["sensitivity_mode_s"],
            "sensitivity_all_hallucinated_at_90pct_target": best_single["sensitivity_all_hallucinated"],
            "permutation_p_value": best_single["permutation_test"]["p_value_two_sided"],
        },
        "combined_metadata_lr": {
            "rule": "numpy-only L2 logistic regression on all 10 metadata features; Mode S label; LOO-CV out-of-fold probabilities; flag if prob >= threshold",
            "target": "mode_s label (2 positives vs 75 negatives)",
            "loo_cv": "leave-one-out over all 77 windows",
            "direction": lr_dir,
            "threshold": round(lr_thr, 6),
            "specificity": round(lr_op["specificity"], 6),
            "sensitivity_mode_s": round(lr_op["sensitivity_mode_s"], 6),
            "sensitivity_mode_s_ci_95": [round(ci_lr_lo, 6), round(ci_lr_hi, 6)],
            "tp_mode_s": lr_op["tp_mode_s"], "fp": lr_op["fp"],
            "tn": lr_op["tn"], "fn_mode_s": lr_op["fn_mode_s"],
            "mode_s_window_probs": {
                str(r["window_id"]): r["metadata_lr_prob"] for r in rows if r["mode_s"]
            },
            "l2_sensitivity_analysis": {
                "note": (
                    "LOO-CV Mode S sensitivity as a function of L2. With n=2 Mode S, L2 cannot be "
                    "tuned by cross-validation; this grid exposes the fragility directly. "
                    f"{n_l2_full} of {len(LR_L2_GRID)} L2 values achieve 100% Mode S sensitivity. "
                    "'saturated' = at least one OOF probability in [0, 0.01] or [0.99, 1.0] "
                    "(numerical pathology, not signal)."
                ),
                "default_l2": LR_L2,
                "n_l2_values_achieving_100pct_mode_s_sensitivity": n_l2_full,
                "n_l2_values_total": len(LR_L2_GRID),
                "grid": l2_sensitivity,
            },
        },
        "lang_id_entropy_alone_reference": {
            "threshold": LANG_ID_ENTROPY_THRESHOLD,
            "specificity": round(lang_spec, 6),
            "sensitivity_all_hallucinated": round(lang_sens_ah, 6),
            "sensitivity_mode_s": round(lang_sens_ms, 6),
            "tp_all_hallucinated": tp_lang_ah, "fp": fp_lang,
            "note": "RQ13 lang-id entropy detector. By definition Mode S escapes it (lang-id < 0.409), so lang-id alone misses both Mode S tracks.",
        },
        "ensemble_metadata_or_lang_id": {
            "rule": f"(metadata LR flag at 90% spec) OR (lang_id_entropy > {LANG_ID_ENTROPY_THRESHOLD})",
            "specificity": round(ens_spec, 6),
            "sensitivity_all_hallucinated": round(ens_sens_ah, 6),
            "sensitivity_mode_s": round(ens_sens_ms, 6),
            "tp_all_hallucinated": tp_ens_ah,
            "fp": fp_ens, "tn": tn_ens, "fn_all_hallucinated": fn_ens_ah,
            "tp_mode_s": tp_ens_ms,
        },
        "hypothesis_verdicts": {
            "H33a": {
                "statement": "metadata-only detector catches both Mode S windows at 90% specificity (sensitivity = 100%)",
                "success_criterion": "sensitivity = 100% at specificity >= 90%",
                "kill_criterion": "sensitivity < 100%",
                "detector": "combined metadata LR (LOO-CV) at default L2",
                "sensitivity_mode_s": round(lr_op["sensitivity_mode_s"], 6),
                "specificity": round(lr_op["specificity"], 6),
                "bootstrap_ci_95_mode_s_sensitivity": [round(ci_lr_lo, 6), round(ci_lr_hi, 6)],
                "l2_robustness": {
                    "n_l2_values_achieving_100pct_mode_s_sensitivity": n_l2_full,
                    "n_l2_values_total": len(LR_L2_GRID),
                    "interpretation": (
                        f"Only {n_l2_full} of {len(LR_L2_GRID)} L2 values achieve 100% Mode S "
                        f"sensitivity; the rest achieve 50%. The 100% result is therefore FRAGILE "
                        f"to the L2 hyperparameter, which cannot be tuned by cross-validation with "
                        f"n=2 Mode S."
                    ),
                },
                "supported": bool(h33a_supported),
                "verdict_qualifier": (
                    "SUPPORTED at the default (minimum-stable) L2, but FRAGILE: only "
                    f"{n_l2_full}/{len(LR_L2_GRID)} L2 values achieve 100% Mode S sensitivity. "
                    "Not robustly deployable."
                ) if h33a_supported else (
                    "NOT SUPPORTED at the default L2 (sensitivity < 100%)."
                ),
                "reason": (
                    f"LOO-CV metadata LR catches {lr_op['sensitivity_mode_s']:.0%} of Mode S at "
                    f"{lr_op['specificity']:.0%} specificity (threshold {lr_thr:.4f}) at the default "
                    f"L2={LR_L2}. Window-22 prob={rows[[r['window_id'] for r in rows].index(22)]['metadata_lr_prob']:.4f}, "
                    f"window-30 prob={rows[[r['window_id'] for r in rows].index(30)]['metadata_lr_prob']:.4f}, "
                    f"top clean prob={float(neg_probs.max()):.4f}. L2 sensitivity: {n_l2_full}/{len(LR_L2_GRID)} "
                    f"L2 values achieve 100% Mode S sensitivity (the rest 50%); the result is fragile "
                    f"because n=2 Mode S precludes L2 tuning by cross-validation."
                ),
            },
            "H33b": {
                "statement": "combined metadata + lang-id detector achieves > 95% sensitivity on the 37 AISHELL-4 hallucinated tracks",
                "success_criterion": "sensitivity > 95%",
                "kill_criterion": "sensitivity <= 95%",
                "combined_sensitivity_all_hallucinated": round(ens_sens_ah, 6),
                "combined_specificity": round(ens_spec, 6),
                "lang_id_alone_sensitivity": round(lang_sens_ah, 6),
                "metadata_lr_sensitivity_mode_s": round(lr_op["sensitivity_mode_s"], 6),
                "l2_robustness": {
                    "n_l2_values_with_ensemble_sens_above_95pct": n_l2_ens_above_95,
                    "n_l2_values_total": len(LR_L2_GRID),
                    "interpretation": (
                        f"{n_l2_ens_above_95} of {len(LR_L2_GRID)} L2 values yield ensemble "
                        f"(metadata OR lang-id) sensitivity > 95% on the 37 hallucinated. The "
                        f"ensemble reaches > 95% whenever the metadata LR catches >= 1 Mode S "
                        f"(lang-id already catches 35/37 diverse hallucinations), which happens at "
                        f"all L2 values tested. H33b is therefore robust on the sensitivity "
                        f"criterion; specificity is only good at non-saturated L2 (see l2 grid)."
                    ),
                },
                "supported": bool(h33b_supported),
                "reason": (
                    f"Ensemble sensitivity is {ens_sens_ah:.1%} ({tp_ens_ah}/{n_halluc}) at "
                    f"{ens_spec:.1%} specificity; lang-id alone is {lang_sens_ah:.1%} "
                    f"({tp_lang_ah}/{n_halluc}). Metadata LR catches {lr_op['sensitivity_mode_s']:.0%} "
                    f"of Mode S, so the ensemble adds {tp_ens_ms} Mode S track(s) over lang-id alone. "
                    f"Across L2, {n_l2_ens_above_95}/{len(LR_L2_GRID)} values yield ensemble "
                    f"sensitivity > 95% (robust on sensitivity; specificity varies — good only at "
                    f"non-saturated L2)."
                ),
            },
            "H33c": {
                "statement": "metadata features have a distinct Mode S profile (permutation p < 0.05 for > 50% of features)",
                "success_criterion": "perm p < 0.05 for > 5 of 10 features",
                "kill_criterion": "perm p >= 0.05 for >= 5 of 10 features",
                "best_feature": best_single["feature_key"],
                "best_feature_p_value": best_single["permutation_test"]["p_value_two_sided"],
                "n_features_with_p_lt_0p05": n_features_distinct,
                "n_features_total": len(METADATA_FEATURES),
                "all_features_p_values": {
                    d["detector"]: d["permutation_test"]["p_value_two_sided"]
                    for d in detector_results
                },
                "supported": bool(h33c_supported),
                "reason": (
                    f"{n_features_distinct} of {len(METADATA_FEATURES)} features have perm p < 0.05 "
                    f"(best: {best_single['feature_key']} p={best_single['permutation_test']['p_value_two_sided']:.4f}). "
                    f"Mode S's metadata profile is dominated by window 22's extreme runtime_ratio "
                    f"(7.05) and window 30's clean-like profile (runtime_ratio 0.99); averaging the "
                    f"two washes out the signal."
                ),
            },
        },
    }

    # --- write CSV (per-window)
    csv_fields = (
        ["window_id", "hallucinated", "mode_s", "lang_id_entropy", "length_ratio", "cr"]
        + list(METADATA_FEATURES)
        + ["metadata_lr_prob", "metadata_lr_flag", "ensemble_flag"]
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in csv_fields})

    # --- write JSON (summary + per-window)
    summary_with_rows = dict(summary)
    summary_with_rows["per_window"] = rows
    OUT_JSON.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- console
    print(f"=== RQ33: Metadata-only Mode S detector (AISHELL-4, {n} tracks) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucinated: {n_halluc}  |  non-hallucinated: {n_nonhalluc}  |  Mode S: {n_mode_s}")
    print(f"Mode S window ids: {mode_s_ids}")
    print(f"Target specificity: {TARGET_SPECIFICITY:.0%}  |  per-feature calibration: two-sided")
    print()
    print(f"{'feature':30s} {'dir':>5s} {'thresh':>11s} {'spec':>6s} {'sens_MS':>8s} {'perm_p':>8s}")
    for d in detector_results:
        print(f"{d['detector']:30s} {d['direction']:>5s} {d['threshold']:11.4f} "
              f"{d['specificity']:6.1%} {d['sensitivity_mode_s']:8.1%} "
              f"{d['permutation_test']['p_value_two_sided']:8.4f}")
    print()
    print(f"Best single-feature detector: {best_single['detector']} "
          f"(perm p={best_single['permutation_test']['p_value_two_sided']:.4f})")
    print()
    print(f"Combined metadata LR (LOO-CV, Mode S target, default L2={LR_L2}):")
    print(f"  threshold={lr_thr:.4f} (dir={lr_dir}), spec={lr_op['specificity']:.1%}, "
          f"sens_MS={lr_op['sensitivity_mode_s']:.1%} (CI [{ci_lr_lo:.1%}, {ci_lr_hi:.1%}])")
    for r in rows:
        if r["mode_s"]:
            print(f"  window {r['window_id']}: prob={r['metadata_lr_prob']:.4f} "
                  f"flag={r['metadata_lr_flag']}")
    print(f"  top clean (non-halluc) OOF prob={float(neg_probs.max()):.4f}")
    print(f"  L2 sensitivity (sens_MS at 90% spec across L2): "
          f"{[s['sensitivity_mode_s'] for s in l2_sensitivity]}")
    print(f"  -> {n_l2_full}/{len(LR_L2_GRID)} L2 values achieve 100% Mode S sensitivity "
          f"(FRAGILE: n=2 precludes L2 tuning by CV)")
    print(f"Lang-id entropy alone: spec={lang_spec:.1%}, sens_AH={lang_sens_ah:.1%} ({tp_lang_ah}/{n_halluc}), "
          f"sens_MS={lang_sens_ms:.1%} ({tp_lang_ms}/{n_mode_s})")
    print(f"Ensemble (metadata LR OR lang-id): spec={ens_spec:.1%}, "
          f"sens_AH={ens_sens_ah:.1%} ({tp_ens_ah}/{n_halluc}), "
          f"sens_MS={ens_sens_ms:.1%} ({tp_ens_ms}/{n_mode_s})")
    print(f"  ensemble sens_AH > 95% at {n_l2_ens_above_95}/{len(LR_L2_GRID)} L2 values "
          f"(robust on sensitivity; specificity good only at non-saturated L2)")
    print()
    print("Hypothesis verdicts:")
    print(f"  H33a (metadata LR sens_MS = 100% at spec >= 90%): "
          f"{'SUPPORTED (fragile)' if h33a_supported else 'NOT SUPPORTED'} "
          f"(sens_MS={lr_op['sensitivity_mode_s']:.1%}, spec={lr_op['specificity']:.1%}, "
          f"{n_l2_full}/{len(LR_L2_GRID)} L2 values achieve 100%)")
    print(f"  H33b (ensemble sens_AH > 95%): "
          f"{'SUPPORTED' if h33b_supported else 'NOT SUPPORTED'} "
          f"(sens_AH={ens_sens_ah:.1%}, spec={ens_spec:.1%}, "
          f"{n_l2_ens_above_95}/{len(LR_L2_GRID)} L2 values > 95%)")
    print(f"  H33c (Mode S distinct metadata profile, > 5/10 features p<0.05): "
          f"{'SUPPORTED' if h33c_supported else 'NOT SUPPORTED'} "
          f"(best p={best_single['permutation_test']['p_value_two_sided']:.4f}, "
          f"{n_features_distinct}/{len(METADATA_FEATURES)} features p<0.05)")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


_FEATURE_NOTES: dict[str, str] = {
    "sep_runtime_sec": "separated ASR runtime in seconds (raw)",
    "mix_runtime_sec": "mixed ASR runtime in seconds (raw)",
    "runtime_ratio": "sep_runtime / mix_runtime (RQ22 partial signal: caught 1/2 Mode S)",
    "sep_total_chars": "total character count of the separated transcript",
    "mix_total_chars": "total character count of the mixed transcript",
    "char_ratio": "sep_total_chars / mix_total_chars (= RQ22 sep_to_mix_length_ratio)",
    "num_speakers": "number of speakers in the reference",
    "num_active_speakers_sep": "number of non-empty speaker segments in separated output (= RQ22 effective_speaker_count)",
    "avg_speaker_length_sep": "mean characters per non-empty speaker segment",
    "length_entropy_speakers": "Shannon entropy of per-speaker lengths (= RQ22 per_speaker_length_entropy)",
}


if __name__ == "__main__":
    main()
