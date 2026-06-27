"""RQ67: 3-gram KL-divergence detector for Mode S.

REANALYSIS ONLY -- no Whisper / no ASR model / no LLM / no ollama is run. This
script reads the existing AISHELL-4 external-validation results
(``results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json``,
label ``external/sanity-check``, PR #890) and tests whether a character **3-gram**
KL-divergence detector changes the ROC shape and improves detection of
non-Mode-S hallucinations vs RQ58's **2-gram** KL detector (PR #981).

Research question
-----------------
RQ34 (PR #951) introduced a character n-gram KL-divergence anomaly detector. RQ58
(PR #981) plugged the **2-gram** variant into RQ16's corrected router and achieved
cpWER 1.030 with **100% Mode S sensitivity** at 90% specificity -- the first
corrected router to catch Mode S. RQ59 (PR #980) showed the (RQ43) KL detector's
ROC is "flat-topped": sensitivity saturates before 100% on non-Mode-S
hallucinations because of an empty KL band separating the hallucinated floor
from the clean low-KL mass. RQ67 asks: does moving to a **3-gram** KL detector
change the ROC shape (H67a AUC) and the detector's reach on non-Mode-S
hallucinations, while still catching Mode S (H67b) and beating RQ58's cpWER
(H67c)?

Method
------
For each of the 77 AISHELL-4 windows:

  1. Build the reference 3-gram distribution from the 40 non-hallucinated
     tracks' separated text (RQ34's ``build_reference_distribution``, n=3).
     Each track's separated text is the concatenation of per-speaker separated
     transcripts (RQ34's ``separated_concat``).
  2. Compute the MAX-across-speakers 3-gram KL-divergence anomaly score
     (RQ34's ``compute_anomaly_score`` per speaker, MAX -- the RQ12/RQ13
     worst-case-track convention). For the H67a AUC comparison, the 2-gram
     scores are recomputed with the SAME code path (n=2) so the comparison is
     apples-to-apples.
  3. Calibrate the 3-gram threshold at >=90% specificity (RQ34's
     ``calibrate_threshold_at_specificity``) on the 40 non-hallucinated tracks.
     Empirical re-calibration (NOT RQ34's non-reproducible 3.30; RQ40 PR #957).
  4. Compute ROC AUC (Mann-Whitney U with tie correction) for both 3-gram and
     2-gram. Characterise the ROC shape (plateau / saturation point).
  5. Route: if 3-gram KL >= threshold -> MIXED, else -> SEPARATED. The
     3-gram-corrected router's per-window cpWER is the chosen route's stored
     word-level cpWER (``always_mixed_cpwer`` / ``always_separated_cpwer``) --
     matches RQ58 / RQ16 bit-for-bit. The stored cpWER values were produced by
     MeetEval 0.4.3 ``cpwer`` / ``orcwer`` in PR #890; this is pure reanalysis
     so they are read, not recomputed.
  6. Bootstrap (B=10000, seed=42) the 3-gram-corrected cpWER. Report percentile
     + BCa CIs (RQ39 framework). Paired-delta CI vs RQ58's 2-gram cpWER.

Pre-registered hypotheses (KILL criteria)
-----------------------------------------
- H67a: 3-gram KL AUC > 2-gram KL AUC. KILL if <=.
- H67b: 3-gram KL catches Mode S at 100% sensitivity / 90% specificity.
        KILL if < 100%.
- H67c: 3-gram KL corrected router cpWER < 1.030 (RQ58 2-gram baseline).
        KILL if >= 1.030.

This script is pure reanalysis (numpy + scipy + stdlib only; no Whisper / no
LLM / no ollama). The KL detector primitives are imported VERBATIM from
``src.llm_semantic_critic`` (RQ34) so the detector is directly comparable to
RQ58. The BCa CI helpers are reimplemented from RQ39/RQ58 so the CI methodology
matches.

Label: experimental/frontier. Closes #995.

Run:
    /opt/homebrew/bin/python3 results/frontier/three_gram_kl_detector/analysis.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import norm

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = Path(__file__).resolve().parent
OUT_CSV = OUT_DIR / "three_gram_kl_results.csv"
OUT_JSON = OUT_DIR / "three_gram_kl_results.json"
FINDINGS_MD = OUT_DIR / "FINDINGS.md"

# ---------------------------------------------------------- import RQ34 primitives
# KL detector + labelling primitives lifted VERBATIM from src.llm_semantic_critic
# (RQ34, PR #951) so the detector is directly comparable to RQ58.
from src.llm_semantic_critic import (  # noqa: E402
    EPS,
    N_BOOT,
    SEED,
    TARGET_SPECIFICITY,
    build_reference_distribution,
    calibrate_threshold_at_specificity,
    compute_anomaly_score,
    evaluate_at_threshold,
    label_window,
    max_across_speakers,
    separated_concat,
    subgroup_sensitivity,
)

# ------------------------------------------------------------------ config
# 3-gram (trigram) character n-gram, per the RQ67 task spec. RQ58 used n=2.
N_GRAM = 3
N_GRAM_REF = 2  # RQ58's 2-gram, recomputed in-script for the H67a AUC comparison.

# RQ58 2-gram baseline reference values (PR #981).
RQ58_2GRAM_CPWER = 1.030303          # RQ58 KL-corrected router cpWER (n=2)
RQ58_2GRAM_THRESHOLD = 5.418144      # RQ58 empirically-calibrated threshold
RQ58_2GRAM_BCA_CI_95 = [1.0065, 1.0779]
RQ58_2GRAM_PERCENTILE_CI_95 = [1.0043, 1.0671]
RQ16_CORRECTED_CPWER = 1.04329
ALWAYS_MIXED_CPWER = 1.17316
ALWAYS_SEPARATED_CPWER = 1.590909
ROUTER_V2_CPWER = 1.205628
ORACLE_BEST_CPWER = 1.017316

ALPHA = 0.05

# H67c kill threshold (literal criterion from the issue: cpWER >= 1.030 kills).
H67C_KILL_THRESHOLD = 1.030

# Mode S windows (RQ19 verified): monoscript-Chinese near-duplicate
# hallucinations that escape every surface detector.
MODE_S_WINDOW_IDS = {22, 30}


# ===========================================================================
# Part 1: KL detector helpers (reuse RQ34 primitives, parameterised by n)
# ===========================================================================
def build_kl_reference(
    labels: list[dict[str, Any]], n: int = N_GRAM,
) -> dict[str, float]:
    """Build the reference character n-gram distribution from the non-hallucinated
    tracks' separated text.

    Mirrors RQ34/RQ58: the reference is the average n-gram distribution of the 40
    non-hallucinated windows' concatenated separated text (``separated_concat``).
    Each text's distribution is over its own vocabulary; the average is over the
    union vocabulary (RQ34's ``build_reference_distribution``)."""
    neg_texts = [lbl["separated_text"] for lbl in labels if not lbl["hallucinated"]]
    return build_reference_distribution(neg_texts, n=n)


def compute_kl_scores(
    windows: list[dict[str, Any]],
    ref_distribution: dict[str, float],
    n: int = N_GRAM,
    eps: float = EPS,
) -> list[float]:
    """MAX-across-speakers n-gram KL-divergence anomaly score per window.

    For each window, apply RQ34's ``compute_anomaly_score`` to each non-empty
    per-speaker separated transcript, then take the MAX (the RQ12/RQ13
    worst-case-track convention, matching ``max_across_speakers``). A window is
    flagged if ANY speaker track trips the detector. Returns 0.0 for windows
    with no non-empty speaker text."""
    return [
        max_across_speakers(
            w, lambda t: compute_anomaly_score(t, ref_distribution, n=n, eps=eps)
        )
        for w in windows
    ]


def kl_route_decision(kl_score: float, threshold: float, eps: float = EPS) -> str:
    """Route to MIXED if ``kl_score >= threshold`` (flag = hallucination likely),
    else SEPARATED.

    Uses ``>= threshold - eps`` to match RQ34's ``evaluate_at_threshold`` flag
    convention (so the calibrated threshold actually flags the boundary score).
    Identical to RQ58's routing rule."""
    return "mixed" if kl_score >= threshold - eps else "separated"


def cpwer_for(window: dict[str, Any], choice: str) -> float:
    """Stored word-level cpWER for the chosen route (matches RQ58/RQ16 bit-for-bit).

    ``choice`` = "mixed" -> ``always_mixed_cpwer``; "separated" ->
    ``always_separated_cpwer``. These stored values were produced by MeetEval
    0.4.3 ``cpwer`` / ``orcwer`` in PR #890; pure reanalysis reads them."""
    return float(
        window["always_mixed_cpwer"] if choice == "mixed"
        else window["always_separated_cpwer"]
    )


# ===========================================================================
# Part 2: ROC AUC + ROC curve (NEW -- RQ67)
# ===========================================================================
def roc_auc(scores: list[float], labels: list[int]) -> float:
    """ROC AUC via the Mann-Whitney U statistic with average-rank tie handling.

    AUC = P(score_pos > score_neg) + 0.5 * P(score_pos == score_neg), where
    ``pos`` = hallucinated (label 1) and ``neg`` = non-hallucinated (label 0).
    Computed as (sum_of_ranks_of_positives - n_pos*(n_pos+1)/2) / (n_pos*n_neg),
    with ranks assigned by sorting scores ascending (higher score = higher rank)
    and ties broken by average rank. Returns 0.5 when either class is empty."""
    s = np.asarray(scores, dtype=float)
    lab = np.asarray(labels, dtype=int)
    n_pos = int(np.sum(lab == 1))
    n_neg = int(np.sum(lab == 0))
    if n_pos == 0 or n_neg == 0:
        return 0.5
    # average ranks (1-indexed) over ascending sort; ties share the mean rank.
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(s.size, dtype=float)
    sorted_s = s[order]
    i = 0
    while i < s.size:
        j = i
        while j + 1 < s.size and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        avg_rank = (i + 1 + j + 1) / 2.0  # 1-indexed average
        ranks[order[i:j + 1]] = avg_rank
        i = j + 1
    sum_ranks_pos = float(np.sum(ranks[lab == 1]))
    u = sum_ranks_pos - n_pos * (n_pos + 1) / 2.0
    return float(u / (n_pos * n_neg))


def roc_curve(
    scores: list[float], labels: list[int],
) -> dict[str, Any]:
    """ROC curve (FPR, TPR) at every distinct threshold + AUC + shape summary.

    Thresholds are the distinct scores sorted descending; at each threshold t a
    window is flagged if score >= t. The curve starts at (0, 0) (threshold above
    the max -> nothing flagged) and ends at (1, 1) (threshold at/below the min ->
    everything flagged). Also reports the maximum sensitivity achievable at
    >= 90% specificity (the "saturation" point relevant to the flat-topped ROC
    question) and whether the curve has a sensitivity plateau below 1.0 at
    specificity >= 0.9 (i.e. sensitivity cannot reach 1.0 without dropping below
    90% specificity)."""
    s = np.asarray(scores, dtype=float)
    lab = np.asarray(labels, dtype=int)
    n_pos = int(np.sum(lab == 1))
    n_neg = int(np.sum(lab == 0))
    if n_pos == 0 or n_neg == 0:
        return {"fpr": [], "tpr": [], "thresholds": [], "auc": 0.5,
                "max_sens_at_90pct_spec": 0.0, "plateau_below_1_at_90pct_spec": False}
    distinct = np.unique(s)
    # thresholds descending; include +inf so the curve starts at (0,0)
    thr_grid = np.concatenate(([np.inf], distinct[::-1]))
    fpr_list: list[float] = []
    tpr_list: list[float] = []
    for t in thr_grid:
        flagged = s >= t - EPS
        tp = int(np.sum(flagged & (lab == 1)))
        fp = int(np.sum(flagged & (lab == 0)))
        tpr_list.append(tp / n_pos)
        fpr_list.append(fp / n_neg)
    auc = roc_auc(scores, labels)
    # max sensitivity achievable while keeping specificity >= 0.90
    arr_fpr = np.asarray(fpr_list)
    arr_tpr = np.asarray(tpr_list)
    mask = arr_fpr <= (1.0 - 0.90) + EPS
    max_sens = float(np.max(arr_tpr[mask])) if np.any(mask) else 0.0
    # plateau below 1.0: sensitivity cannot reach 1.0 at >=90% specificity
    plateau = max_sens < 1.0 - EPS
    return {
        "fpr": [round(float(x), 6) for x in fpr_list],
        "tpr": [round(float(x), 6) for x in tpr_list],
        "thresholds": [float(x) if np.isfinite(x) else None for x in thr_grid],
        "auc": round(auc, 6),
        "max_sens_at_90pct_spec": round(max_sens, 6),
        "plateau_below_1_at_90pct_spec": bool(plateau),
    }


# ===========================================================================
# Part 3: bootstrap + BCa CI helpers (reimplemented from RQ39/RQ58, PURE)
# ===========================================================================
def bootstrap_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``(n_boot, n)`` int array of resample indices (with replacement).

    Same convention as RQ16/RQ39/RQ58: ``rng.integers(0, n, size=n)`` per
    resample. Deterministic for a fixed ``seed``."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(n_boot, n))


def bootstrap_distribution(values: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``n_boot`` array of bootstrap means of ``values``.

    Resamples ``values`` with replacement (``n`` indices per resample) and takes
    the mean. Deterministic for a fixed ``seed``."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    idx = bootstrap_indices(n, n_boot, seed)
    return values[idx].mean(axis=1)


def percentile_ci(
    boot_dist: np.ndarray, alpha: float = ALPHA,
) -> tuple[float, float]:
    """Percentile CI: ``(100*alpha/2, 100*(1-alpha/2))`` percentiles of the
    bootstrap distribution. Returns ``(lo, hi)``."""
    boot_dist = np.asarray(boot_dist, dtype=float)
    lo = float(np.percentile(boot_dist, 100.0 * (alpha / 2.0)))
    hi = float(np.percentile(boot_dist, 100.0 * (1.0 - alpha / 2.0)))
    return lo, hi


def _jackknife_means(values: np.ndarray) -> np.ndarray:
    """Leave-one-out jackknife means of ``values`` (length-``n`` array).

    O(n) via the identity: mean of n-1 values = (n*mean - x_i) / (n-1)."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < 2:
        return np.array([float(values.mean())])
    total = float(values.sum())
    return (total - values) / (n - 1)


def bca_ci(
    values: np.ndarray, boot_dist: np.ndarray, alpha: float = ALPHA,
) -> tuple[float, float]:
    """BCa (bias-corrected + accelerated) CI for the mean of ``values``.

    Standard Efron & Tibshirani BCa formula. Matches RQ39/RQ58 verbatim."""
    values = np.asarray(values, dtype=float)
    boot_dist = np.asarray(boot_dist, dtype=float)
    n = len(values)
    if n < 2:
        theta = float(values.mean()) if n == 1 else float("nan")
        return theta, theta

    theta_hat = float(values.mean())

    # --- bias correction z0
    prop_less = float(np.mean(boot_dist < theta_hat))
    eps_clip = 0.5 / len(boot_dist)
    prop_less = min(max(prop_less, eps_clip), 1.0 - eps_clip)
    z0 = float(norm.ppf(prop_less))

    # --- acceleration a via jackknife
    jack = _jackknife_means(values)
    jack_mean = float(jack.mean())
    diff = jack_mean - jack
    num = float(np.sum(diff ** 3))
    den = 6.0 * (float(np.sum(diff ** 2)) ** 1.5)
    a = num / den if den > 0 else 0.0

    # --- BCa alpha bounds
    z_lo = float(norm.ppf(alpha / 2.0))
    z_hi = float(norm.ppf(1.0 - alpha / 2.0))

    denom_lo = 1.0 - a * (z0 + z_lo)
    denom_hi = 1.0 - a * (z0 + z_hi)
    if abs(denom_lo) < EPS or abs(denom_hi) < EPS:
        return percentile_ci(boot_dist, alpha)

    alpha1 = float(norm.cdf(z0 + (z0 + z_lo) / denom_lo))
    alpha2 = float(norm.cdf(z0 + (z0 + z_hi) / denom_hi))

    alpha1 = min(max(alpha1, 0.0), 1.0)
    alpha2 = min(max(alpha2, 0.0), 1.0)

    lo = float(np.percentile(boot_dist, 100.0 * alpha1))
    hi = float(np.percentile(boot_dist, 100.0 * alpha2))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def paired_delta_distribution(
    a: np.ndarray, b: np.ndarray, n_boot: int, seed: int,
) -> np.ndarray:
    """Bootstrap distribution of ``mean(a[idx]) - mean(b[idx])`` (paired).

    Same resample indices for both ``a`` and ``b`` (paired design)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.shape != b.shape:
        raise ValueError(
            f"paired_delta_distribution: a and b must have the same shape, got "
            f"{a.shape} vs {b.shape}"
        )
    n = len(a)
    idx = bootstrap_indices(n, n_boot, seed)
    return a[idx].mean(axis=1) - b[idx].mean(axis=1)


def paired_delta_ci(
    a: np.ndarray, b: np.ndarray, n_boot: int, seed: int, alpha: float = ALPHA,
) -> tuple[float, float]:
    """Percentile CI for the paired bootstrap ``mean(a) - mean(b)``."""
    dist = paired_delta_distribution(a, b, n_boot, seed)
    return percentile_ci(dist, alpha)


# ===========================================================================
# Part 4: driver
# ===========================================================================
def _round6(x: float) -> float:
    return round(float(x), 6)


def _ci_pair(ci: tuple[float, float]) -> list[float]:
    return [_round6(ci[0]), _round6(ci[1])]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # --- per-window labels (RQ34 verbatim) + surface features
    labels = [label_window(w) for w in windows]
    n_halluc = sum(1 for l in labels if l["hallucinated"])
    n_nonhalluc = n - n_halluc
    n_mode_s = sum(1 for l in labels if l["mode_s"])
    n_diverse = sum(1 for l in labels if l["diverse_hallucination"])
    mode_s_ids = [l["window_id"] for l in labels if l["mode_s"]]

    # --- build 3-gram reference distribution from 40 non-hallucinated tracks
    ref_dist_3 = build_kl_reference(labels, n=N_GRAM)
    ref_vocab_3 = len(ref_dist_3)
    # --- build 2-gram reference (for the H67a AUC comparison, same code path)
    ref_dist_2 = build_kl_reference(labels, n=N_GRAM_REF)
    ref_vocab_2 = len(ref_dist_2)

    # --- MAX-across-speakers KL scores
    kl_scores_3 = compute_kl_scores(windows, ref_dist_3, n=N_GRAM)
    kl_scores_2 = compute_kl_scores(windows, ref_dist_2, n=N_GRAM_REF)

    # --- calibrate 3-gram threshold at >=90% specificity (EMPIRICAL)
    neg_scores_3 = [s for s, l in zip(kl_scores_3, labels) if not l["hallucinated"]]
    pos_scores_3 = [s for s, l in zip(kl_scores_3, labels) if l["hallucinated"]]
    cal_3 = calibrate_threshold_at_specificity(
        neg_scores_3, pos_scores_3, TARGET_SPECIFICITY,
    )
    threshold_3 = cal_3["threshold"]

    # --- calibrate 2-gram threshold (for comparison; must match RQ58)
    neg_scores_2 = [s for s, l in zip(kl_scores_2, labels) if not l["hallucinated"]]
    pos_scores_2 = [s for s, l in zip(kl_scores_2, labels) if l["hallucinated"]]
    cal_2 = calibrate_threshold_at_specificity(
        neg_scores_2, pos_scores_2, TARGET_SPECIFICITY,
    )
    threshold_2 = cal_2["threshold"]

    # --- detector evaluation at the calibrated thresholds
    halluc_label_ints = [1 if l["hallucinated"] else 0 for l in labels]
    overall_3 = evaluate_at_threshold(kl_scores_3, halluc_label_ints, threshold_3)
    ms_3 = subgroup_sensitivity(
        kl_scores_3, [l["mode_s"] for l in labels], threshold_3)
    div_3 = subgroup_sensitivity(
        kl_scores_3, [l["diverse_hallucination"] for l in labels], threshold_3)
    overall_2 = evaluate_at_threshold(kl_scores_2, halluc_label_ints, threshold_2)
    ms_2 = subgroup_sensitivity(
        kl_scores_2, [l["mode_s"] for l in labels], threshold_2)
    div_2 = subgroup_sensitivity(
        kl_scores_2, [l["diverse_hallucination"] for l in labels], threshold_2)

    # --- ROC AUC + ROC curve for both n-gram orders
    auc_3 = roc_auc(kl_scores_3, halluc_label_ints)
    auc_2 = roc_auc(kl_scores_2, halluc_label_ints)
    roc_3 = roc_curve(kl_scores_3, halluc_label_ints)
    roc_2 = roc_curve(kl_scores_2, halluc_label_ints)

    # --- per-window routing + cpWER (3-gram corrected router)
    rows: list[dict[str, Any]] = []
    for w, lbl, ks3, ks2 in zip(windows, labels, kl_scores_3, kl_scores_2):
        dec3 = kl_route_decision(ks3, threshold_3)
        cp3 = cpwer_for(w, dec3)
        dec2 = kl_route_decision(ks2, threshold_2)
        cp2 = cpwer_for(w, dec2)
        rows.append({
            "window_id": w["window_id"],
            "overlap_label": w["overlap_label"],
            "hallucinated": int(lbl["hallucinated"]),
            "mode_s": int(lbl["mode_s"]),
            "diverse_hallucination": int(lbl["diverse_hallucination"]),
            "kl_score_3gram": _round6(ks3),
            "kl_score_2gram": _round6(ks2),
            "always_mixed_cpwer": _round6(float(w["always_mixed_cpwer"])),
            "always_separated_cpwer": _round6(float(w["always_separated_cpwer"])),
            "router_v2_cpwer": _round6(float(w["router_v2_cpwer"])),
            "oracle_best_cpwer": _round6(float(w["oracle_best_cpwer"])),
            "kl3_flag": int(ks3 >= threshold_3 - EPS),
            "kl3_decision": dec3,
            "kl3_cpwer": _round6(cp3),
            "kl2_flag": int(ks2 >= threshold_2 - EPS),
            "kl2_decision": dec2,
            "kl2_cpwer": _round6(cp2),
        })

    # --- aggregates
    kl3_arr = np.array([r["kl3_cpwer"] for r in rows], dtype=float)
    kl2_arr = np.array([r["kl2_cpwer"] for r in rows], dtype=float)
    mixed_arr = np.array([r["always_mixed_cpwer"] for r in rows], dtype=float)
    sep_arr = np.array([r["always_separated_cpwer"] for r in rows], dtype=float)
    rv2_arr = np.array([r["router_v2_cpwer"] for r in rows], dtype=float)
    oracle_arr = np.array([r["oracle_best_cpwer"] for r in rows], dtype=float)

    kl3_point = float(kl3_arr.mean())
    kl2_point = float(kl2_arr.mean())
    mixed_point = float(mixed_arr.mean())
    sep_point = float(sep_arr.mean())
    rv2_point = float(rv2_arr.mean())
    oracle_point = float(oracle_arr.mean())

    # --- decision counts
    kl3_counts = {
        "mixed": sum(1 for r in rows if r["kl3_decision"] == "mixed"),
        "separated": sum(1 for r in rows if r["kl3_decision"] == "separated"),
    }
    kl2_counts = {
        "mixed": sum(1 for r in rows if r["kl2_decision"] == "mixed"),
        "separated": sum(1 for r in rows if r["kl2_decision"] == "separated"),
    }

    # --- bootstrap CIs (B=10000, seed=42, RQ39 framework) on the 3-gram router
    kl3_boot = bootstrap_distribution(kl3_arr, N_BOOT, SEED)
    kl3_pct_ci = percentile_ci(kl3_boot)
    kl3_bca_ci = bca_ci(kl3_arr, kl3_boot)
    # paired delta: 3-gram minus RQ58's 2-gram (recomputed in-script)
    kl3_minus_kl2 = paired_delta_distribution(kl3_arr, kl2_arr, N_BOOT, SEED)
    kl3_minus_kl2_ci = percentile_ci(kl3_minus_kl2)
    kl3_minus_mixed = paired_delta_distribution(kl3_arr, mixed_arr, N_BOOT, SEED)
    kl3_minus_mixed_ci = percentile_ci(kl3_minus_mixed)

    # --- regret analysis
    regret_kl3_vs_oracle = kl3_point - oracle_point
    regret_kl2_vs_oracle = kl2_point - oracle_point
    regret_mixed_vs_oracle = mixed_point - oracle_point
    recovery_vs_rq58 = (
        (regret_kl2_vs_oracle - regret_kl3_vs_oracle) / regret_kl2_vs_oracle
        if abs(regret_kl2_vs_oracle) > EPS else 0.0
    )
    recovery_vs_mixed = (
        (regret_mixed_vs_oracle - regret_kl3_vs_oracle) / regret_mixed_vs_oracle
        if abs(regret_mixed_vs_oracle) > EPS else 0.0
    )

    # --- Mode S per-window detail
    mode_s_rows = [r for r in rows if r["mode_s"]]
    mode_s_detail = {
        str(r["window_id"]): {
            "kl_score_3gram": r["kl_score_3gram"],
            "kl_score_2gram": r["kl_score_2gram"],
            "kl3_flag": r["kl3_flag"],
            "kl3_decision": r["kl3_decision"],
            "kl3_cpwer": r["kl3_cpwer"],
            "kl2_flag": r["kl2_flag"],
            "kl2_decision": r["kl2_decision"],
            "kl2_cpwer": r["kl2_cpwer"],
            "always_mixed_cpwer": r["always_mixed_cpwer"],
            "always_separated_cpwer": r["always_separated_cpwer"],
        }
        for r in mode_s_rows
    }

    # --- hypothesis verdicts
    # H67a: 3-gram AUC > 2-gram AUC. KILL if <=.
    h67a_supported = auc_3 > auc_2

    # H67b: 3-gram catches Mode S at 100% sensitivity / 90% specificity.
    # KILL if < 100%. Uses the achieved specificity from cal_3 (>= 90%).
    h67b_supported = (
        ms_3["sensitivity"] >= 1.0 and ms_3["n"] == len(MODE_S_WINDOW_IDS)
    )

    # H67c: 3-gram corrected router cpWER < 1.030 (RQ58 2-gram baseline).
    # KILL if >= 1.030. The issue states the literal kill threshold as 1.030.
    h67c_supported = kl3_point < H67C_KILL_THRESHOLD
    h67c_killed_by_rounded = kl3_point >= H67C_KILL_THRESHOLD
    # also report the comparison against the exact RQ58 value (1.030303)
    h67c_vs_exact_rq58 = kl3_point < RQ58_2GRAM_CPWER

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ67: 3-gram KL-divergence detector for Mode S",
        "closes_issue": 995,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "Reanalysis only (no Whisper / no ASR / no LLM / no ollama run). "
            "Builds a character 3-gram KL-divergence anomaly detector (RQ34 "
            "primitives, n=3) in RQ16/RQ58's corrected-router framework. "
            "Reference 3-gram distribution built from the 40 non-hallucinated "
            "tracks' separated text (RQ34 build_reference_distribution, n=3). "
            "Per-window score is the MAX-across-speakers KL (RQ12/RQ13 "
            "worst-case-track convention). Threshold empirically calibrated at "
            ">=90% specificity on the 40 non-hallucinated tracks (NOT RQ34's "
            "non-reproducible 3.30; RQ40 PR #957). The 2-gram detector is "
            "recomputed with the SAME code path (n=2) for the H67a AUC "
            "comparison. ROC AUC via Mann-Whitney U with average-rank ties. "
            "Route: 3-gram KL >= threshold -> MIXED, else SEPARATED. Per-window "
            "cpWER is the chosen route's stored word-level cpWER (always_mixed / "
            "always_separated), produced by MeetEval 0.4.3 cpwer/orcwer in "
            "PR #890; pure reanalysis reads them (matches RQ58/RQ16 bit-for-"
            "bit). Bootstrap 10,000 resamples, seed=42, percentile + BCa CIs "
            "(RQ39 framework)."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated": n_halluc,
        "n_nonhallucinated": n_nonhalluc,
        "n_mode_s": n_mode_s,
        "n_diverse_hallucination": n_diverse,
        "mode_s_window_ids": mode_s_ids,
        "hallucination_label": "always_separated_cpwer > 1.0 (37/40 split, RQ12)",
        "mode_s_definition": (
            "hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0 "
            "AND cr < 2.4 (RQ19 verified windows 22, 30)"
        ),
        "ngram_config": {
            "n_3gram": {
                "n": N_GRAM,
                "reference": (
                    "average 3-gram distribution of 40 non-hallucinated tracks' "
                    "concatenated separated text (RQ34 separated_concat)"
                ),
                "vocab_size": ref_vocab_3,
                "metric": "KL(text || reference), additive smoothing 1e-9",
                "aggregation": "MAX across per-speaker separated tracks (RQ12/RQ13 worst-case)",
            },
            "n_2gram_reference": {
                "n": N_GRAM_REF,
                "vocab_size": ref_vocab_2,
                "note": "Recomputed in-script with the same code path for the H67a AUC comparison (matches RQ58).",
            },
        },
        "threshold_calibration": {
            "n3": {
                "target_specificity": TARGET_SPECIFICITY,
                "threshold": _round6(threshold_3),
                "achieved_specificity": _round6(cal_3["specificity"]),
                "n_neg": cal_3["n_neg"],
                "max_fp": cal_3["max_fp"],
            },
            "n2_recomputed": {
                "target_specificity": TARGET_SPECIFICITY,
                "threshold": _round6(threshold_2),
                "achieved_specificity": _round6(cal_2["specificity"]),
                "n_neg": cal_2["n_neg"],
                "max_fp": cal_2["max_fp"],
                "rq58_reference_threshold": RQ58_2GRAM_THRESHOLD,
                "matches_rq58": abs(threshold_2 - RQ58_2GRAM_THRESHOLD) < 1e-4,
            },
            "note": (
                "Empirically calibrated at >=90% specificity on the 40 "
                "non-hallucinated tracks. RQ40 (PR #957) found RQ34's reported "
                "threshold 3.30 was NON-REPRODUCIBLE on the full corpus; we do "
                "NOT use 3.30. The 2-gram recomputed threshold must match "
                "RQ58's 5.418144 as a sanity check."
            ),
        },
        "detector_evaluation": {
            "n3": {
                "threshold": _round6(threshold_3),
                "specificity": _round6(overall_3["specificity"]),
                "sensitivity_all_hallucinated": _round6(overall_3["sensitivity"]),
                "sensitivity_mode_s": _round6(ms_3["sensitivity"]),
                "sensitivity_diverse": _round6(div_3["sensitivity"]),
                "tp_all": overall_3["tp"], "fp": overall_3["fp"],
                "tn": overall_3["tn"], "fn_all": overall_3["fn"],
                "tp_mode_s": ms_3["tp"], "n_mode_s": ms_3["n"],
                "tp_diverse": div_3["tp"], "n_diverse": div_3["n"],
                "flagged_window_ids": [r["window_id"] for r in rows if r["kl3_flag"]],
            },
            "n2_recomputed": {
                "threshold": _round6(threshold_2),
                "specificity": _round6(overall_2["specificity"]),
                "sensitivity_all_hallucinated": _round6(overall_2["sensitivity"]),
                "sensitivity_mode_s": _round6(ms_2["sensitivity"]),
                "sensitivity_diverse": _round6(div_2["sensitivity"]),
                "tp_all": overall_2["tp"], "fp": overall_2["fp"],
                "tn": overall_2["tn"], "fn_all": overall_2["fn"],
                "tp_mode_s": ms_2["tp"], "n_mode_s": ms_2["n"],
                "tp_diverse": div_2["tp"], "n_diverse": div_2["n"],
                "flagged_window_ids": [r["window_id"] for r in rows if r["kl2_flag"]],
            },
        },
        "roc_analysis": {
            "n3": roc_3,
            "n2": roc_2,
            "auc_n3": round(auc_3, 6),
            "auc_n2": round(auc_2, 6),
            "auc_delta_n3_minus_n2": round(auc_3 - auc_2, 6),
            "note": (
                "ROC AUC via Mann-Whitney U with average-rank ties (AUC = "
                "P(score_pos > score_neg) + 0.5*P(equal)). "
                "max_sens_at_90pct_spec = max sensitivity achievable while "
                "keeping specificity >= 0.90. plateau_below_1_at_90pct_spec = "
                "True when sensitivity cannot reach 1.0 at >=90% specificity "
                "(the 'flat-topped' ROC signature from RQ59)."
            ),
        },
        "baselines": {
            "always_mixed_cpwer": _round6(mixed_point),
            "always_separated_cpwer": _round6(sep_point),
            "router_v2_cpwer": _round6(rv2_point),
            "oracle_best_cpwer": _round6(oracle_point),
        },
        "three_gram_corrected_router_cpwer": _round6(kl3_point),
        "three_gram_corrected_router_ci_95": {
            "percentile": _ci_pair(kl3_pct_ci),
            "bca": _ci_pair(kl3_bca_ci),
        },
        "three_gram_corrected_router_decision_counts": kl3_counts,
        "two_gram_recomputed_router_cpwer": _round6(kl2_point),
        "two_gram_recomputed_router_decision_counts": kl2_counts,
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "alpha": ALPHA,
            "convention": "rng.integers(0, n, size=n) per resample (RQ16/RQ39/RQ58 verbatim)",
        },
        "rq58_reference": {
            "two_gram_corrected_router_cpwer": RQ58_2GRAM_CPWER,
            "percentile_ci_95": RQ58_2GRAM_PERCENTILE_CI_95,
            "bca_ci_95": RQ58_2GRAM_BCA_CI_95,
            "two_gram_threshold": RQ58_2GRAM_THRESHOLD,
            "two_gram_cpwer_recomputed": _round6(kl2_point),
            "note": (
                "RQ58 (PR #981) word-level values. The recomputed 2-gram cpwer "
                "must match RQ58's 1.030303 bit-for-bit (same code path, n=2)."
            ),
        },
        "regret_analysis": {
            "three_gram_regret_vs_oracle": _round6(regret_kl3_vs_oracle),
            "two_gram_regret_vs_oracle": _round6(regret_kl2_vs_oracle),
            "always_mixed_regret_vs_oracle": _round6(regret_mixed_vs_oracle),
            "recovery_fraction_of_rq58_gap": _round6(recovery_vs_rq58),
            "recovery_fraction_of_always_mixed_gap": _round6(recovery_vs_mixed),
        },
        "paired_delta_cis": {
            "three_gram_minus_two_gram_point": _round6(kl3_point - kl2_point),
            "three_gram_minus_two_gram_ci_95": _ci_pair(kl3_minus_kl2_ci),
            "three_gram_minus_always_mixed_point": _round6(kl3_point - mixed_point),
            "three_gram_minus_always_mixed_ci_95": _ci_pair(kl3_minus_mixed_ci),
        },
        "mode_s_detail": mode_s_detail,
        "hypothesis_verdicts": {
            "H67a": {
                "statement": "3-gram KL AUC > 2-gram KL AUC. KILL if <=.",
                "auc_n3": round(auc_3, 6),
                "auc_n2": round(auc_2, 6),
                "delta": round(auc_3 - auc_2, 6),
                "killed_if_le": bool(not h67a_supported),
                "supported": bool(h67a_supported),
                "reason": (
                    f"3-gram AUC = {auc_3:.6f} "
                    f"{'>' if h67a_supported else '<='} 2-gram AUC = {auc_2:.6f} "
                    f"(delta {auc_3 - auc_2:+.6f}). "
                    f"{'3-gram has higher AUC' if h67a_supported else '3-gram does NOT have higher AUC'}."
                ),
            },
            "H67b": {
                "statement": (
                    "3-gram KL catches Mode S at 100% sensitivity / 90% "
                    "specificity. KILL if < 100%."
                ),
                "mode_s_sensitivity": _round6(ms_3["sensitivity"]),
                "tp_mode_s": ms_3["tp"],
                "n_mode_s": ms_3["n"],
                "achieved_specificity": _round6(cal_3["specificity"]),
                "mode_s_window_ids": mode_s_ids,
                "supported": bool(h67b_supported),
                "reason": (
                    f"3-gram Mode S sensitivity = {ms_3['sensitivity']:.0%} "
                    f"({ms_3['tp']}/{ms_3['n']}) at {cal_3['specificity']:.1%} "
                    f"specificity. "
                    f"{'3-gram catches both Mode S windows.' if h67b_supported else '3-gram misses Mode S.'}"
                ),
            },
            "H67c": {
                "statement": (
                    "3-gram KL corrected router cpWER < 1.030 (RQ58 2-gram "
                    "baseline). KILL if >= 1.030."
                ),
                "three_gram_cpwer": _round6(kl3_point),
                "rq58_two_gram_cpwer": RQ58_2GRAM_CPWER,
                "kill_threshold": H67C_KILL_THRESHOLD,
                "delta_vs_rq58": _round6(kl3_point - RQ58_2GRAM_CPWER),
                "killed_if_ge_1_030": bool(h67c_killed_by_rounded),
                "beats_exact_rq58": bool(h67c_vs_exact_rq58),
                "paired_delta_ci_95": _ci_pair(kl3_minus_kl2_ci),
                "supported": bool(h67c_supported),
                "reason": (
                    f"3-gram cpWER = {kl3_point:.6f} "
                    f"{'<' if h67c_supported else '>='} 1.030 "
                    f"(RQ58 2-gram = {RQ58_2GRAM_CPWER:.6f}, "
                    f"delta {kl3_point - RQ58_2GRAM_CPWER:+.6f}). "
                    f"{'3-gram beats RQ58.' if h67c_supported else '3-gram does NOT beat RQ58.'}"
                ),
            },
        },
        "per_window": rows,
    }

    # ----------------------------------------------------------- write CSV
    csv_fields = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow(r)

    # ----------------------------------------------------------- write JSON
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- console
    print(f"=== RQ67: 3-gram KL detector (AISHELL-4, {n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucinated: {n_halluc}  |  non-hallucinated: {n_nonhalluc}  "
          f"|  Mode S: {n_mode_s} ({mode_s_ids})  |  diverse: {n_diverse}")
    print()
    print(f"3-gram reference vocab size: {ref_vocab_3}  (2-gram: {ref_vocab_2})")
    print(f"3-gram threshold (>=90% spec): {threshold_3:.6f}  "
          f"(spec {cal_3['specificity']:.1%}, max_fp {cal_3['max_fp']})")
    print(f"2-gram threshold (recomputed): {threshold_2:.6f}  "
          f"(matches RQ58 {RQ58_2GRAM_THRESHOLD}: "
          f"{abs(threshold_2 - RQ58_2GRAM_THRESHOLD) < 1e-4})")
    print()
    print("ROC AUC comparison:")
    print(f"  3-gram AUC : {auc_3:.6f}")
    print(f"  2-gram AUC : {auc_2:.6f}")
    print(f"  delta      : {auc_3 - auc_2:+.6f}")
    print(f"  3-gram max_sens @ 90% spec: {roc_3['max_sens_at_90pct_spec']:.4f}  "
          f"plateau: {roc_3['plateau_below_1_at_90pct_spec']}")
    print(f"  2-gram max_sens @ 90% spec: {roc_2['max_sens_at_90pct_spec']:.4f}  "
          f"plateau: {roc_2['plateau_below_1_at_90pct_spec']}")
    print()
    print("Detector evaluation at calibrated threshold:")
    print(f"  3-gram sens (all halluc): {overall_3['sensitivity']:.1%} "
          f"({overall_3['tp']}/{n_halluc})  spec {overall_3['specificity']:.1%}")
    print(f"  3-gram sens (Mode S)    : {ms_3['sensitivity']:.0%} "
          f"({ms_3['tp']}/{ms_3['n']})")
    print(f"  3-gram sens (diverse)   : {div_3['sensitivity']:.1%} "
          f"({div_3['tp']}/{div_3['n']})")
    print(f"  2-gram sens (all halluc): {overall_2['sensitivity']:.1%} "
          f"({overall_2['tp']}/{n_halluc})  spec {overall_2['specificity']:.1%}")
    print(f"  2-gram sens (Mode S)    : {ms_2['sensitivity']:.0%} "
          f"({ms_2['tp']}/{ms_2['n']})")
    print()
    print("Baselines (word-level, mean over 77 windows):")
    print(f"  always_mixed     : {mixed_point:.6f}")
    print(f"  always_separated : {sep_point:.6f}")
    print(f"  router_v2        : {rv2_point:.6f}")
    print(f"  oracle_best      : {oracle_point:.6f}")
    print()
    print("Corrected-router cpWER comparison:")
    print(f"  RQ58 2-gram      : {kl2_point:.6f}  (reference: {RQ58_2GRAM_CPWER})")
    print(f"  3-gram (RQ67)    : {kl3_point:.6f}")
    print(f"    percentile CI  : [{kl3_pct_ci[0]:.6f}, {kl3_pct_ci[1]:.6f}]")
    print(f"    BCa CI         : [{kl3_bca_ci[0]:.6f}, {kl3_bca_ci[1]:.6f}]")
    print(f"    paired d(3g-2g) CI : [{kl3_minus_kl2_ci[0]:+.6f}, {kl3_minus_kl2_ci[1]:+.6f}]")
    print(f"    paired d(3g-mix) CI: [{kl3_minus_mixed_ci[0]:+.6f}, {kl3_minus_mixed_ci[1]:+.6f}]")
    print(f"  3-gram decisions: mixed={kl3_counts['mixed']}, separated={kl3_counts['separated']}")
    print(f"  2-gram decisions: mixed={kl2_counts['mixed']}, separated={kl2_counts['separated']}")
    print()
    print("Hypothesis verdicts:")
    print(f"  H67a (3-gram AUC > 2-gram AUC): "
          f"{'SUPPORTED' if h67a_supported else 'KILLED'}  "
          f"(3g={auc_3:.6f}, 2g={auc_2:.6f}, delta={auc_3-auc_2:+.6f})")
    print(f"  H67b (Mode S sens 100% @ 90% spec): "
          f"{'SUPPORTED' if h67b_supported else 'KILLED'}  "
          f"(3g Mode S sens={ms_3['sensitivity']:.0%}, {ms_3['tp']}/{ms_3['n']})")
    print(f"  H67c (3-gram cpWER < 1.030): "
          f"{'SUPPORTED' if h67c_supported else 'KILLED'}  "
          f"(3g={kl3_point:.6f}, RQ58={RQ58_2GRAM_CPWER}, "
          f"delta={kl3_point-RQ58_2GRAM_CPWER:+.6f})")
    print()
    print(f"Mode S per-window: {mode_s_detail}")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
