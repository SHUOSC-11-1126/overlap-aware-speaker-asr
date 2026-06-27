"""RQ58: Corrected router with n-gram KL-divergence detector.

REANALYSIS ONLY — no Whisper / no ASR model / no LLM is run. This script reads
the existing AISHELL-4 external-validation results
(``results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json``,
label ``external/sanity-check``, PR #890) and simulates a *KL-corrected router*
that replaces RQ16's language-id-entropy detector with a character 2-gram
KL-divergence anomaly detector (RQ34, PR #951).

RQ34 found the n-gram KL detector is the FIRST detector to catch Mode S
(monoscript-Chinese near-duplicate hallucinations, windows 22 and 30) at 90%
specificity — every prior surface detector (RQ19/22/23/28, including RQ16's
lang-id entropy) gets 0% Mode S sensitivity. RQ16's lang-id corrected router
plateaus at cpWER 1.043 (BCa CI [1.013, 1.097], RQ39) precisely because it
cannot catch Mode S — the 2 Mode S windows are the entirety of RQ16's losses
vs always-mixed. RQ58 asks: does replacing lang-id entropy with n-gram KL
divergence in RQ16's corrected router improve cpWER below 1.043?

Method
------
For each of the 77 AISHELL-4 windows:

  1. Build the reference 2-gram distribution from the 40 non-hallucinated
     tracks' separated text (RQ34's ``build_reference_distribution``, n=2).
     Each track's separated text is the concatenation of per-speaker separated
     transcripts (RQ34's ``separated_concat``).
  2. Compute the MAX-across-speakers 2-gram KL-divergence anomaly score
     (RQ34's ``compute_anomaly_score`` applied per speaker track, MAX — the
     RQ12/RQ13 worst-case-track convention).
  3. Calibrate the KL threshold at >=90% specificity (RQ34's
     ``calibrate_threshold_at_specificity``) on the 40 non-hallucinated tracks.

     IMPORTANT: RQ40 (PR #957) found RQ34's reported threshold 3.30 was
     NON-REPRODUCIBLE on the full corpus (gives 32.5% specificity, not 90%).
     We therefore empirically re-calibrate at 90% specificity here and do NOT
     use RQ34's 3.30 value.
  4. Route: if KL >= threshold -> MIXED, else -> SEPARATED. The KL-corrected
     router's per-window cpWER is the chosen route's stored word-level cpWER
     (``always_mixed_cpwer`` / ``always_separated_cpwer``) — matches RQ16
     bit-for-bit.
  5. Bootstrap (B=10000, seed=42) the KL-corrected cpWER. Report percentile +
     BCa CIs (RQ39's framework).

Hypotheses
----------
- H58a: KL-corrected router cpWER < 1.043 (beats RQ16's lang-id corrected
  router). KILLED if cpWER >= 1.043.
- H58b: KL-corrected router catches both Mode S windows (Mode S sensitivity
  0% -> 100%). KILLED if < 100%.
- H58c: KL-corrected router BCa CI excludes oracle (1.017). KILLED if CI
  includes oracle.

This script is pure reanalysis (numpy + scipy + stdlib only; no Whisper / no
LLM / no ollama). The KL detector primitives are imported VERBATIM from
``src.llm_semantic_critic`` (RQ34) so the detector is directly comparable. The
BCa CI helpers are reimplemented from RQ39
(``results/frontier/bootstrap_ci_corrected_router/bootstrap_ci_analysis.py``)
so the CI methodology matches.

Label: experimental/frontier. Closes #974.

Run:
    /opt/homebrew/bin/python3 results/frontier/kl_corrected_router/kl_corrected_router_analysis.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

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
OUT_CSV = OUT_DIR / "kl_corrected_router_results.csv"
OUT_JSON = OUT_DIR / "kl_corrected_router_results.json"
FINDINGS_MD = OUT_DIR / "FINDINGS.md"

# ---------------------------------------------------------- import RQ34 primitives
# KL detector + labelling primitives lifted VERBATIM from src.llm_semantic_critic
# (RQ34, PR #951) so the detector is directly comparable.
from src.llm_semantic_critic import (  # noqa: E402
    CATASTROPHIC_CPWER,
    CR_THRESHOLD,
    EPS,
    LANG_ID_ENTROPY_THRESHOLD,
    LENGTH_RATIO_THRESHOLD,
    N_BOOT,
    SEED,
    TARGET_SPECIFICITY,
    average_distributions,
    build_reference_distribution,
    calibrate_threshold_at_specificity,
    char_distribution,
    char_ngrams,
    compute_anomaly_score,
    evaluate_at_threshold,
    kl_divergence,
    label_window,
    language_id_entropy,
    max_across_speakers,
    separated_concat,
    subgroup_sensitivity,
)

# ------------------------------------------------------------------ config
# 2-gram (bigram) character n-gram, per the RQ58 task spec. RQ34 used n=3;
# RQ58 deliberately uses n=2.
N_GRAM = 2

# RQ16 / RQ39 reference values for hypothesis comparison (word-level).
RQ16_CORRECTED_CPWER = 1.04329
RQ16_BCA_CI_95 = [1.0130, 1.0974]
RQ16_PERCENTILE_CI_95 = [1.008658, 1.088745]
ALWAYS_MIXED_CPWER = 1.17316
ALWAYS_SEPARATED_CPWER = 1.590909
ROUTER_V2_CPWER = 1.205628
ORACLE_BEST_CPWER = 1.017316

ALPHA = 0.05

# Mode S windows (RQ19 verified): monoscript-Chinese near-duplicate
# hallucinations that escape every surface detector.
MODE_S_WINDOW_IDS = {22, 30}


# ===========================================================================
# Part 1: KL-corrected router primitives (NEW — RQ58)
# ===========================================================================
def build_kl_reference(
    labels: list[dict[str, Any]], n: int = N_GRAM,
) -> dict[str, float]:
    """Build the reference character n-gram distribution from the non-hallucinated
    tracks' separated text.

    Mirrors RQ34's ``run_ngram_fallback``: the reference is the average n-gram
    distribution of the 40 non-hallucinated windows' concatenated separated
    text (``separated_concat``). Each text's distribution is over its own
    vocabulary; the average is over the union vocabulary (RQ34's
    ``build_reference_distribution``)."""
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
    This is the KL analogue of RQ16's ``lang_id_entropy > 0.409 -> MIXED``."""
    return "mixed" if kl_score >= threshold - eps else "separated"


def cpwer_for(window: dict[str, Any], choice: str) -> float:
    """Stored word-level cpWER for the chosen route (matches RQ16 bit-for-bit).

    ``choice`` = "mixed" -> ``always_mixed_cpwer``; "separated" ->
    ``always_separated_cpwer``."""
    return float(
        window["always_mixed_cpwer"] if choice == "mixed"
        else window["always_separated_cpwer"]
    )


def lang_id_route_decision(window: dict[str, Any]) -> str:
    """RQ16's lang-id corrected-router decision (for comparison / sanity check).

    Route to MIXED if ``max_across_speakers(separated, language_id_entropy) >
    0.409`` bits, else SEPARATED. RQ39 verified lang-id alone is cpWER-identical
    to RQ16's full three-guard corrected router on AISHELL-4 (1.04329)."""
    ent = max_across_speakers(window, language_id_entropy)
    return "mixed" if ent > LANG_ID_ENTROPY_THRESHOLD else "separated"


# ===========================================================================
# Part 2: bootstrap + BCa CI helpers (reimplemented from RQ39, PURE)
# ===========================================================================
# These are reimplemented verbatim from
# ``results/frontier/bootstrap_ci_corrected_router/bootstrap_ci_analysis.py``
# (RQ39, PR #955) so the CI methodology matches bit-for-bit. Pure helpers — no
# I/O, no global state.

def bootstrap_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``(n_boot, n)`` int array of resample indices (with replacement).

    Same convention as RQ16/RQ39: ``rng.integers(0, n, size=n)`` per resample.
    Deterministic for a fixed ``seed``."""
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

    O(n) via the identity: mean of n-1 values = (n*mean - x_i) / (n-1).
    Used by ``bca_ci`` to compute the acceleration ``a``."""
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

    Standard Efron & Tibshirani BCa formula:
      * ``z0 = Phi^-1(P(boot < theta_hat))`` — bias correction
      * ``a`` via jackknife: ``a = sum((theta_bar - theta_i)^3) /
        (6 * (sum((theta_bar - theta_i)^2))^1.5)``
      * BCa alphas:
          ``alpha1 = Phi(z0 + (z0 + z_{alpha/2}) / (1 - a*(z0 + z_{alpha/2})))``
          ``alpha2 = Phi(z0 + (z0 + z_{1-alpha/2}) / (1 - a*(z0 + z_{1-alpha/2})))``
      * BCa CI = ``(percentile(boot, 100*alpha1), percentile(boot, 100*alpha2))``

    Edge cases (constant data, zero denominator, ``P(boot < theta_hat)`` of 0/1)
    are handled by clipping to a small epsilon and falling back to the
    percentile CI when the acceleration is undefined. Matches RQ39 verbatim."""
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

    Same resample indices for both ``a`` and ``b`` (paired design). Returns an
    ``n_boot`` array. Deterministic for a fixed ``seed``."""
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
# Part 3: driver
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

    # --- build 2-gram reference distribution from 40 non-hallucinated tracks
    ref_dist = build_kl_reference(labels, n=N_GRAM)
    ref_vocab_size = len(ref_dist)

    # --- MAX-across-speakers 2-gram KL scores
    kl_scores = compute_kl_scores(windows, ref_dist, n=N_GRAM)

    # --- calibrate threshold at >=90% specificity (EMPIRICAL, not RQ34's 3.30)
    neg_scores = [s for s, l in zip(kl_scores, labels) if not l["hallucinated"]]
    pos_scores = [s for s, l in zip(kl_scores, labels) if l["hallucinated"]]
    cal = calibrate_threshold_at_specificity(
        neg_scores, pos_scores, TARGET_SPECIFICITY,
    )
    threshold = cal["threshold"]

    # --- detector evaluation at the calibrated threshold
    halluc_label_ints = [1 if l["hallucinated"] else 0 for l in labels]
    overall = evaluate_at_threshold(kl_scores, halluc_label_ints, threshold)
    ms = subgroup_sensitivity(
        kl_scores, [l["mode_s"] for l in labels], threshold)
    div = subgroup_sensitivity(
        kl_scores, [l["diverse_hallucination"] for l in labels], threshold)

    # --- per-window routing + cpWER
    rows: list[dict[str, Any]] = []
    for w, lbl, ks in zip(windows, labels, kl_scores):
        kl_dec = kl_route_decision(ks, threshold)
        kl_cpwer = cpwer_for(w, kl_dec)
        lang_dec = lang_id_route_decision(w)
        lang_cpwer = cpwer_for(w, lang_dec)
        rows.append({
            "window_id": w["window_id"],
            "overlap_label": w["overlap_label"],
            "hallucinated": int(lbl["hallucinated"]),
            "mode_s": int(lbl["mode_s"]),
            "diverse_hallucination": int(lbl["diverse_hallucination"]),
            "lang_id_entropy": _round6(lbl["lang_id_entropy"]),
            "kl_score": _round6(ks),
            "always_mixed_cpwer": _round6(float(w["always_mixed_cpwer"])),
            "always_separated_cpwer": _round6(float(w["always_separated_cpwer"])),
            "router_v2_cpwer": _round6(float(w["router_v2_cpwer"])),
            "oracle_best_cpwer": _round6(float(w["oracle_best_cpwer"])),
            "kl_flag": int(ks >= threshold - EPS),
            "kl_decision": kl_dec,
            "kl_cpwer": _round6(kl_cpwer),
            "rq16_lang_id_decision": lang_dec,
            "rq16_lang_id_cpwer": _round6(lang_cpwer),
        })

    # --- aggregates
    kl_arr = np.array([r["kl_cpwer"] for r in rows], dtype=float)
    lang_arr = np.array([r["rq16_lang_id_cpwer"] for r in rows], dtype=float)
    mixed_arr = np.array([r["always_mixed_cpwer"] for r in rows], dtype=float)
    sep_arr = np.array([r["always_separated_cpwer"] for r in rows], dtype=float)
    rv2_arr = np.array([r["router_v2_cpwer"] for r in rows], dtype=float)
    oracle_arr = np.array([r["oracle_best_cpwer"] for r in rows], dtype=float)

    kl_point = float(kl_arr.mean())
    lang_point = float(lang_arr.mean())
    mixed_point = float(mixed_arr.mean())
    sep_point = float(sep_arr.mean())
    rv2_point = float(rv2_arr.mean())
    oracle_point = float(oracle_arr.mean())

    # --- decision counts
    kl_counts = {
        "mixed": sum(1 for r in rows if r["kl_decision"] == "mixed"),
        "separated": sum(1 for r in rows if r["kl_decision"] == "separated"),
    }
    lang_counts = {
        "mixed": sum(1 for r in rows if r["rq16_lang_id_decision"] == "mixed"),
        "separated": sum(1 for r in rows if r["rq16_lang_id_decision"] == "separated"),
    }

    # --- bootstrap CIs (B=10000, seed=42, RQ39 framework)
    kl_boot = bootstrap_distribution(kl_arr, N_BOOT, SEED)
    kl_pct_ci = percentile_ci(kl_boot)
    kl_bca_ci = bca_ci(kl_arr, kl_boot)
    # paired deltas: KL vs RQ16, KL vs always-mixed, KL vs oracle
    kl_minus_lang = paired_delta_distribution(kl_arr, lang_arr, N_BOOT, SEED)
    kl_minus_mixed = paired_delta_distribution(kl_arr, mixed_arr, N_BOOT, SEED)
    kl_minus_lang_ci = percentile_ci(kl_minus_lang)
    kl_minus_mixed_ci = percentile_ci(kl_minus_mixed)

    # --- regret analysis
    regret_kl_vs_oracle = kl_point - oracle_point
    regret_lang_vs_oracle = lang_point - oracle_point
    regret_mixed_vs_oracle = mixed_point - oracle_point
    regret_rv2_vs_oracle = rv2_point - oracle_point
    # recovery fraction of RQ16's gap to oracle recovered by KL
    recovery_vs_lang = (
        (regret_lang_vs_oracle - regret_kl_vs_oracle) / regret_lang_vs_oracle
        if regret_lang_vs_oracle > EPS else 0.0
    )
    # recovery fraction of always-mixed's gap to oracle recovered by KL
    recovery_vs_mixed = (
        (regret_mixed_vs_oracle - regret_kl_vs_oracle) / regret_mixed_vs_oracle
        if regret_mixed_vs_oracle > EPS else 0.0
    )

    # --- Mode S per-window detail
    mode_s_rows = [r for r in rows if r["mode_s"]]
    mode_s_detail = {
        str(r["window_id"]): {
            "kl_score": r["kl_score"],
            "kl_flag": r["kl_flag"],
            "kl_decision": r["kl_decision"],
            "kl_cpwer": r["kl_cpwer"],
            "always_mixed_cpwer": r["always_mixed_cpwer"],
            "always_separated_cpwer": r["always_separated_cpwer"],
            "rq16_lang_id_decision": r["rq16_lang_id_decision"],
            "rq16_lang_id_cpwer": r["rq16_lang_id_cpwer"],
        }
        for r in mode_s_rows
    }

    # --- hypothesis verdicts
    # H58a: KL-corrected router cpWER < 1.043 (beats RQ16's lang-id corrected
    # router). KILLED if cpWER >= 1.043. We compare against RQ16's exact value
    # 1.04329 (the task's "1.043" is the rounded form); killed if KL cpWER
    # >= 1.04329.
    h58a_supported = kl_point < RQ16_CORRECTED_CPWER
    h58a_killed_by_rounded = kl_point >= 1.043

    # H58b: KL-corrected router catches both Mode S windows (Mode S sensitivity
    # 0% -> 100%). KILLED if < 100%.
    h58b_supported = ms["sensitivity"] >= 1.0 and ms["n"] == len(MODE_S_WINDOW_IDS)

    # H58c: KL-corrected router BCa CI excludes oracle (1.017). KILLED if CI
    # includes oracle. "Excludes" = entire CI above OR below oracle. Since the
    # corrected router cannot beat the oracle, the relevant case is lower CI >
    # oracle (CI entirely above oracle).
    h58c_supported = (kl_bca_ci[1] < oracle_point) or (kl_bca_ci[0] > oracle_point)
    h58c_ci_above_oracle = kl_bca_ci[0] > oracle_point

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ58: Corrected router with n-gram KL-divergence detector",
        "closes_issue": 974,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "Reanalysis only (no Whisper / no ASR / no LLM run). Replaces RQ16's "
            "language-id-entropy detector with a character 2-gram KL-divergence "
            "anomaly detector (RQ34) in the corrected router. Reference 2-gram "
            "distribution built from the 40 non-hallucinated tracks' separated "
            "text (RQ34 build_reference_distribution, n=2). Per-window score is "
            "the MAX-across-speakers KL (RQ12/RQ13 worst-case-track convention). "
            "Threshold empirically calibrated at >=90% specificity on the 40 "
            "non-hallucinated tracks (NOT RQ34's non-reproducible 3.30; RQ40 "
            "PR #957 showed 3.30 gives 32.5% specificity). Route: KL >= "
            "threshold -> MIXED, else SEPARATED. Per-window cpWER is the chosen "
            "route's stored word-level cpWER (matches RQ16 bit-for-bit). "
            "Bootstrap 10,000 resamples, seed=42, percentile + BCa CIs (RQ39 "
            "framework)."
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
            "n": N_GRAM,
            "reference": (
                "average 2-gram distribution of 40 non-hallucinated tracks' "
                "concatenated separated text (RQ34 separated_concat)"
            ),
            "vocab_size": ref_vocab_size,
            "metric": "KL(text || reference), additive smoothing 1e-9",
            "aggregation": "MAX across per-speaker separated tracks (RQ12/RQ13 worst-case)",
        },
        "threshold_calibration": {
            "target_specificity": TARGET_SPECIFICITY,
            "threshold": _round6(threshold),
            "achieved_specificity": _round6(cal["specificity"]),
            "n_neg": cal["n_neg"],
            "max_fp": cal["max_fp"],
            "note": (
                "Empirically calibrated at >=90% specificity on the 40 "
                "non-hallucinated tracks. RQ40 (PR #957) found RQ34's reported "
                "threshold 3.30 was NON-REPRODUCIBLE on the full corpus (gives "
                "32.5% specificity, not 90%); we do NOT use 3.30."
            ),
        },
        "detector_evaluation": {
            "threshold": _round6(threshold),
            "specificity": _round6(overall["specificity"]),
            "sensitivity_all_hallucinated": _round6(overall["sensitivity"]),
            "sensitivity_mode_s": _round6(ms["sensitivity"]),
            "sensitivity_diverse": _round6(div["sensitivity"]),
            "tp_all": overall["tp"], "fp": overall["fp"],
            "tn": overall["tn"], "fn_all": overall["fn"],
            "tp_mode_s": ms["tp"], "n_mode_s": ms["n"],
            "tp_diverse": div["tp"], "n_diverse": div["n"],
            "flagged_window_ids": [r["window_id"] for r in rows if r["kl_flag"]],
        },
        "baselines": {
            "always_mixed_cpwer": _round6(mixed_point),
            "always_separated_cpwer": _round6(sep_point),
            "router_v2_cpwer": _round6(rv2_point),
            "oracle_best_cpwer": _round6(oracle_point),
        },
        "kl_corrected_router_cpwer": _round6(kl_point),
        "kl_corrected_router_ci_95": {
            "percentile": _ci_pair(kl_pct_ci),
            "bca": _ci_pair(kl_bca_ci),
        },
        "kl_corrected_router_decision_counts": kl_counts,
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "alpha": ALPHA,
            "convention": "rng.integers(0, n, size=n) per resample (RQ16/RQ39 verbatim)",
        },
        "rq16_reference": {
            "corrected_router_cpwer": RQ16_CORRECTED_CPWER,
            "percentile_ci_95": RQ16_PERCENTILE_CI_95,
            "bca_ci_95": RQ16_BCA_CI_95,
            "always_mixed_cpwer": ALWAYS_MIXED_CPWER,
            "always_separated_cpwer": ALWAYS_SEPARATED_CPWER,
            "router_v2_cpwer": ROUTER_V2_CPWER,
            "oracle_best_cpwer": ORACLE_BEST_CPWER,
            "lang_id_decision_counts": lang_counts,
            "lang_id_cpwer_recomputed": _round6(lang_point),
            "note": (
                "RQ16 (PR #909) / RQ39 (PR #955) word-level values. lang-id "
                "alone is cpWER-identical to RQ16's full three-guard corrected "
                "router on AISHELL-4 (1.04329). Recomputed here as a sanity "
                "check and must match 1.04329 bit-for-bit."
            ),
        },
        "regret_analysis": {
            "kl_regret_vs_oracle": _round6(regret_kl_vs_oracle),
            "rq16_lang_id_regret_vs_oracle": _round6(regret_lang_vs_oracle),
            "always_mixed_regret_vs_oracle": _round6(regret_mixed_vs_oracle),
            "router_v2_regret_vs_oracle": _round6(regret_rv2_vs_oracle),
            "recovery_fraction_of_rq16_gap": _round6(recovery_vs_lang),
            "recovery_fraction_of_always_mixed_gap": _round6(recovery_vs_mixed),
        },
        "paired_delta_cis": {
            "kl_minus_rq16_lang_id_point": _round6(kl_point - lang_point),
            "kl_minus_rq16_lang_id_ci_95": _ci_pair(kl_minus_lang_ci),
            "kl_minus_always_mixed_point": _round6(kl_point - mixed_point),
            "kl_minus_always_mixed_ci_95": _ci_pair(kl_minus_mixed_ci),
        },
        "mode_s_detail": mode_s_detail,
        "hypothesis_verdicts": {
            "H58a": {
                "statement": (
                    "KL-corrected router cpWER < 1.043 (beats RQ16's lang-id "
                    "corrected router). KILLED if cpWER >= 1.043."
                ),
                "kl_corrected_cpwer": _round6(kl_point),
                "rq16_lang_id_cpwer": RQ16_CORRECTED_CPWER,
                "delta_kl_minus_rq16": _round6(kl_point - RQ16_CORRECTED_CPWER),
                "paired_delta_ci_95": _ci_pair(kl_minus_lang_ci),
                "killed_if_ge_1_043": bool(h58a_killed_by_rounded),
                "supported": bool(h58a_supported),
                "reason": (
                    f"KL-corrected cpWER = {kl_point:.6f} "
                    f"{'<' if h58a_supported else '>='} RQ16's "
                    f"{RQ16_CORRECTED_CPWER:.6f}. "
                    f"{'KL beats RQ16' if h58a_supported else 'KL does NOT beat RQ16'}."
                ),
            },
            "H58b": {
                "statement": (
                    "KL-corrected router catches both Mode S windows (Mode S "
                    "sensitivity 0% -> 100%). KILLED if < 100%."
                ),
                "mode_s_sensitivity": _round6(ms["sensitivity"]),
                "tp_mode_s": ms["tp"],
                "n_mode_s": ms["n"],
                "mode_s_window_ids": mode_s_ids,
                "rq16_lang_id_mode_s_sensitivity": 0.0,
                "supported": bool(h58b_supported),
                "reason": (
                    f"KL Mode S sensitivity = {ms['sensitivity']:.0%} "
                    f"({ms['tp']}/{ms['n']}) at {overall['specificity']:.1%} "
                    f"specificity. RQ16's lang-id gets 0% on Mode S. "
                    f"{'KL catches both Mode S windows.' if h58b_supported else 'KL misses Mode S.'}"
                ),
            },
            "H58c": {
                "statement": (
                    "KL-corrected router BCa CI excludes oracle (1.017). KILLED "
                    "if CI includes oracle."
                ),
                "kl_corrected_cpwer": _round6(kl_point),
                "oracle_best_cpwer": _round6(oracle_point),
                "bca_ci_95": _ci_pair(kl_bca_ci),
                "percentile_ci_95": _ci_pair(kl_pct_ci),
                "ci_entirely_above_oracle": bool(h58c_ci_above_oracle),
                "ci_entirely_below_oracle": bool(kl_bca_ci[1] < oracle_point),
                "supported": bool(h58c_supported),
                "reason": (
                    f"BCa CI [{kl_bca_ci[0]:.6f}, {kl_bca_ci[1]:.6f}] "
                    f"{'excludes' if h58c_supported else 'includes'} oracle "
                    f"{oracle_point:.6f}. "
                    f"{'Lower CI > oracle.' if h58c_ci_above_oracle else ''}"
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
    print(f"=== RQ58: KL-corrected router (AISHELL-4, {n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucinated: {n_halluc}  |  non-hallucinated: {n_nonhalluc}  "
          f"|  Mode S: {n_mode_s} ({mode_s_ids})  |  diverse: {n_diverse}")
    print()
    print(f"2-gram KL reference vocab size: {ref_vocab_size}")
    print(f"Empirically-calibrated threshold (>=90% specificity): "
          f"{threshold:.6f}  (specificity {cal['specificity']:.1%}, max_fp {cal['max_fp']})")
    print(f"  NOTE: RQ34's reported 3.30 is NON-REPRODUCIBLE (RQ40 PR #957); not used.")
    print()
    print("Detector evaluation at calibrated threshold:")
    print(f"  sensitivity (all halluc) : {overall['sensitivity']:.1%} "
          f"({overall['tp']}/{n_halluc})")
    print(f"  sensitivity (Mode S)     : {ms['sensitivity']:.0%} "
          f"({ms['tp']}/{ms['n']})  [RQ16 lang-id: 0%]")
    print(f"  sensitivity (diverse)    : {div['sensitivity']:.1%} "
          f"({div['tp']}/{div['n']})")
    print(f"  specificity              : {overall['specificity']:.1%} "
          f"(fp {overall['fp']}/{n_nonhalluc})")
    print()
    print("Baselines (word-level, mean over 77 windows):")
    print(f"  always_mixed     : {mixed_point:.6f}")
    print(f"  always_separated : {sep_point:.6f}")
    print(f"  router_v2        : {rv2_point:.6f}")
    print(f"  oracle_best      : {oracle_point:.6f}")
    print()
    print("Corrected-router cpWER comparison:")
    print(f"  RQ16 lang-id     : {lang_point:.6f}  (reference: {RQ16_CORRECTED_CPWER})")
    print(f"  KL-corrected     : {kl_point:.6f}")
    print(f"    percentile CI  : [{kl_pct_ci[0]:.6f}, {kl_pct_ci[1]:.6f}]")
    print(f"    BCa CI         : [{kl_bca_ci[0]:.6f}, {kl_bca_ci[1]:.6f}]")
    print(f"    paired d(KL-RQ16) CI : [{kl_minus_lang_ci[0]:+.6f}, {kl_minus_lang_ci[1]:+.6f}]")
    print(f"    paired d(KL-mixed) CI: [{kl_minus_mixed_ci[0]:+.6f}, {kl_minus_mixed_ci[1]:+.6f}]")
    print(f"  KL decisions: mixed={kl_counts['mixed']}, separated={kl_counts['separated']}")
    print(f"  RQ16 decisions: mixed={lang_counts['mixed']}, separated={lang_counts['separated']}")
    print()
    print("Hypothesis verdicts:")
    print(f"  H58a (KL cpWER < 1.043, beats RQ16): "
          f"{'SUPPORTED' if h58a_supported else 'KILLED'}  "
          f"(KL={kl_point:.6f}, RQ16={RQ16_CORRECTED_CPWER}, "
          f"delta={kl_point-RQ16_CORRECTED_CPWER:+.6f})")
    print(f"  H58b (Mode S sens 0%->100%): "
          f"{'SUPPORTED' if h58b_supported else 'KILLED'}  "
          f"(KL Mode S sens={ms['sensitivity']:.0%}, {ms['tp']}/{ms['n']})")
    print(f"  H58c (BCa CI excludes oracle 1.017): "
          f"{'SUPPORTED' if h58c_supported else 'KILLED'}  "
          f"(BCa=[{kl_bca_ci[0]:.6f}, {kl_bca_ci[1]:.6f}], oracle={oracle_point:.6f})")
    print()
    print(f"Mode S per-window KL scores: {mode_s_detail}")
    print(f"Regret recovery: {recovery_vs_lang:.1%} of RQ16's gap, "
          f"{recovery_vs_mixed:.1%} of always-mixed's gap")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
