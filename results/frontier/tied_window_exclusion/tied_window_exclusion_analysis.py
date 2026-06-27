"""RQ50: Tied-window exclusion corrected-router.

REANALYSIS ONLY — no Whisper / no ASR / no MeetEval run. Reads the existing
AISHELL-4 external-validation results
(``results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json``,
label ``external/sanity-check``, PR #890; 77 windows).

RQ47 (PR #967) found that 35 of the 77 AISHELL-4 windows are "tied" —
``abs(always_mixed_cpwer - always_separated_cpwer) < 1e-6`` — silence /
single-speaker no-ops where the mixed and separated ASR passes give identical
cpWER. On a tied window the corrected router cannot improve over always-mixed
no matter which route it picks (both routes give the same cpWER).

RQ39 (PR #960) found that the corrected router's word-level BCa CI
[1.012987, 1.097403] *includes* the oracle cpWER (1.017316): the corrected
router is statistically indistinguishable from oracle on the 77-window set
(H39b NOT SUPPORTED). RQ50 asks: **does excluding the 35 tied no-op windows
change this conclusion?**

The pre-registered intuition is that tied windows inflate both the corrected
router's cpWER and oracle's cpWER equally (both get cpWER = 1.0 on tied
windows), so excluding them might (a) tighten the CI, (b) change whether the
CI includes oracle, or (c) reveal that the corrected router's advantage is
concentrated on the actionable (non-tied) windows.

Hypotheses (pre-registered)
---------------------------
- H50a: Excluding tied windows, the corrected router's BCa CI lower bound >
  oracle cpWER on non-tied windows (the corrected router BEATS oracle on
  actionable windows). Kill: CI includes oracle (lower <= oracle).
- H50b: Excluding tied windows, the BCa CI width < RQ39's word-level width
  (0.0844 = 1.0974 - 1.0130). Kill: width >= 0.0844.
- H50c: The corrected router's cpWER improvement over always-mixed is larger
  on non-tied windows than on all windows (the advantage is concentrated on
  actionable windows). Kill: non-tied improvement <= all-windows improvement.

Method
------
1. Load the 77 AISHELL-4 windows (read-only).
2. Mark a window "tied" iff ``abs(always_mixed_cpwer - always_separated_cpwer)
   < 1e-6`` (RQ47's operational definition).
3. Compute the corrected router's per-window cpWER using the lang-id entropy
   detector (RQ13/RQ16) at threshold 0.38: route MIXED if
   ``max_across_speakers(separated, language_id_entropy) >= 0.38``, else
   SEPARATED. On this dataset the threshold-0.38 decisions coincide with
   RQ16's threshold-0.409 decisions (no window has entropy in [0.38, 0.409)),
   so the corrected-router point estimate reproduces RQ16's 1.043290.
4. Exclude the 35 tied windows. On the remaining 42 non-tied windows:
   - corrected router cpWER = mean of per-window corrected cpWER
   - always-mixed cpWER    = mean of per-window mixed cpWER
   - oracle cpWER           = mean of per-window oracle cpWER
5. Bootstrap (B=10,000, seed=42) the corrected router's cpWER on non-tied
   windows. Report percentile + BCa CI [2.5%, 97.5%]. BCa uses the standard
   Efron & Tibshirani formula with bias correction ``z0`` and jackknife
   acceleration ``a`` (lifted verbatim from RQ39's ``bca_ci``).
6. Compare to RQ39's all-windows BCa CI [1.012987, 1.097403]
   (width 0.084416).
7. Compute the improvement ``always_mixed - corrected`` on non-tied vs all
   windows.

Label: experimental/frontier. Closes the RQ50 issue.

Run:
    /opt/homebrew/bin/python3 results/frontier/tied_window_exclusion/tied_window_exclusion_analysis.py
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import norm

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SOURCE_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = Path(__file__).resolve().parent
CSV_PATH = OUT_DIR / "tied_window_exclusion_results.csv"
JSON_PATH = OUT_DIR / "tied_window_exclusion_results.json"

# ----------------------------------------------------------------- thresholds
# Task directive: lang-id entropy threshold 0.38 (route MIXED if >= 0.38,
# else SEPARATED). On this AISHELL-4 file the threshold-0.38 decisions
# coincide bit-for-bit with RQ16's threshold-0.409 decisions (no window has
# entropy in the half-open interval [0.38, 0.409)), so the corrected-router
# point estimate reproduces RQ16's 1.043290 and RQ39's word-level 1.043290.
LANG_ID_ENTROPY_THRESHOLD = 0.38
TIE_TOL = 1e-6
N_BOOT = 10000
SEED = 42
ALPHA = 0.05
EPS = 1e-9
LABEL = "experimental/frontier"

# RQ39's all-windows BCa CI on the corrected-router cpWER, word-level.
# Used as the comparison anchor for H50b.
RQ39_WORD_LEVEL_BCA_CI = (1.012987, 1.097403)
RQ39_WORD_LEVEL_BCA_WIDTH = RQ39_WORD_LEVEL_BCA_CI[1] - RQ39_WORD_LEVEL_BCA_CI[0]

# RQ39's all-windows corrected-router point estimate and oracle cpWER
# (word-level), for the all-windows improvement comparison in H50c.
RQ39_WORD_LEVEL_CORRECTED_CPWER = 1.04329
RQ39_WORD_LEVEL_ALWAYS_MIXED_CPWER = 1.17316
RQ39_WORD_LEVEL_ORACLE_CPWER = 1.017316

# Linguistic-content script categories (exclude Space / Punct / Other noise).
# Verbatim from RQ13/RQ16.
CONTENT_SCRIPTS = {
    "Han", "Latin", "Hiragana", "Katakana", "Hangul",
    "Cyrillic", "Arabic", "Greek", "Digit",
}


# ===========================================================================
# Part 1: detector primitives (lifted VERBATIM from RQ16/RQ13)
# ===========================================================================

def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13 verbatim).

    Uses ``unicodedata.name``. Whitespace -> "Space"; punctuation/symbols ->
    "Punct"; control/unknown -> "Other". Sufficient to separate Han / Latin /
    Hiragana / Katakana / Hangul / Cyrillic / Arabic / Greek / Digit, which are
    exactly the scripts RQ12/RQ13 observed in AISHELL-4 hallucination."""
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
    """Shannon entropy (bits) over the script-category distribution (RQ13).

    Clean Chinese (near-monoscript Han) -> entropy ~ 0. Diverse multilingual
    gibberish mixing Han+Latin+Katakana+Hangul -> high entropy."""
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


def max_across_speakers(window: dict[str, Any], fn: Callable[[str], float]) -> float:
    """Max of fn(text) over the per-speaker separated transcripts (RQ13 verbatim).

    A window is flagged if ANY speaker track trips the detector. Empty /
    whitespace speaker texts are effectively skipped."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def corrected_router_decision(window: dict[str, Any]) -> str:
    """RQ50's corrected-router decision using lang-id entropy at threshold 0.38.

    Route to MIXED if ``max_across_speakers(separated, language_id_entropy)
    >= 0.38`` bits, else SEPARATED. On this AISHELL-4 file the decisions
    coincide with RQ16's threshold-0.409 rule (no window has entropy in
    [0.38, 0.409))."""
    ent = max_across_speakers(window, language_id_entropy)
    return "mixed" if ent >= LANG_ID_ENTROPY_THRESHOLD else "separated"


# ===========================================================================
# Part 2: tied-window identification (RQ47 operational definition)
# ===========================================================================

def is_tied_window(window: dict[str, Any], tol: float = TIE_TOL) -> bool:
    """RQ47's tied-window test: ``abs(mixed - sep) < tol``.

    On a tied window both routes give the same cpWER, so the corrected
    router cannot improve over always-mixed no matter which route it picks."""
    mixed = float(window["always_mixed_cpwer"])
    sep = float(window["always_separated_cpwer"])
    return abs(mixed - sep) < tol


def identify_tied_windows(
    windows: list[dict[str, Any]], tol: float = TIE_TOL
) -> list[int]:
    """Return the window_ids of the tied windows (RQ47 operational definition)."""
    return [
        w["window_id"]
        for w in windows
        if is_tied_window(w, tol=tol)
    ]


def identify_nontied_windows(
    windows: list[dict[str, Any]], tol: float = TIE_TOL
) -> list[int]:
    """Return the window_ids of the non-tied (actionable) windows."""
    tied = set(identify_tied_windows(windows, tol=tol))
    return [w["window_id"] for w in windows if w["window_id"] not in tied]


# ===========================================================================
# Part 3: per-window corrected cpWER (RQ16/RQ50)
# ===========================================================================

def per_window_corrected_cpwer(window: dict[str, Any]) -> float:
    """Corrected-router per-window cpWER using threshold 0.38.

    MIXED route contributes ``always_mixed_cpwer``; SEPARATED route
    contributes ``always_separated_cpwer``. Reproduces RQ16/RQ39's
    ``word_corrected_cpwer`` on every window (decisions coincide)."""
    decision = corrected_router_decision(window)
    if decision == "mixed":
        return float(window["always_mixed_cpwer"])
    return float(window["always_separated_cpwer"])


def build_per_window_rows(
    windows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build per-window rows with all fields needed for the analysis.

    Each row carries: ``window_id``, the tie flag, the corrected decision,
    the per-window mixed / separated / corrected / oracle cpWER, and the
    lang-id entropy."""
    rows: list[dict[str, Any]] = []
    for w in windows:
        ent = max_across_speakers(w, language_id_entropy)
        decision = corrected_router_decision(w)
        mixed = float(w["always_mixed_cpwer"])
        sep = float(w["always_separated_cpwer"])
        corrected = mixed if decision == "mixed" else sep
        oracle = float(w["oracle_best_cpwer"])
        rows.append({
            "window_id": w["window_id"],
            "overlap_label": w["overlap_label"],
            "num_speakers": w["num_speakers"],
            "lang_id_entropy": round(float(ent), 6),
            "corrected_decision": decision,
            "always_mixed_cpwer": round(mixed, 6),
            "always_separated_cpwer": round(sep, 6),
            "corrected_cpwer": round(corrected, 6),
            "oracle_best_cpwer": round(oracle, 6),
            "is_tied": bool(is_tied_window(w)),
        })
    return rows


# ===========================================================================
# Part 4: bootstrap helpers (BCa, lifted VERBATIM from RQ39)
# ===========================================================================

def bootstrap_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``(n_boot, n)`` int array of resample indices (with replacement).

    Same convention as RQ16: ``rng.integers(0, n, size=n)`` per resample.
    Deterministic for a fixed ``seed``. Pure helper — no I/O, no global state.
    """
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(n_boot, n))


def bootstrap_distribution(values: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``n_boot`` array of bootstrap means of ``values``.

    Resamples ``values`` with replacement (``n`` indices per resample) and
    takes the mean. Deterministic for a fixed ``seed``.
    """
    values = np.asarray(values, dtype=float)
    n = len(values)
    idx = bootstrap_indices(n, n_boot, seed)
    return values[idx].mean(axis=1)


def percentile_ci(boot_dist: np.ndarray, alpha: float = ALPHA) -> tuple[float, float]:
    """Percentile CI: ``(100*alpha/2, 100*(1-alpha/2))`` percentiles of the
    bootstrap distribution. Pure helper; returns ``(lo, hi)``."""
    boot_dist = np.asarray(boot_dist, dtype=float)
    lo = float(np.percentile(boot_dist, 100.0 * (alpha / 2.0)))
    hi = float(np.percentile(boot_dist, 100.0 * (1.0 - alpha / 2.0)))
    return lo, hi


def _jackknife_means(values: np.ndarray) -> np.ndarray:
    """Leave-one-out jackknife means of ``values`` (length-``n`` array).

    Pure helper used by ``bca_ci`` to compute the acceleration ``a``.
    O(n) via the identity: mean of n-1 values = (n*mean - x_i) / (n-1).
    """
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < 2:
        return np.array([float(values.mean())])
    total = float(values.sum())
    return (total - values) / (n - 1)


def bca_ci(
    values: np.ndarray, boot_dist: np.ndarray, alpha: float = ALPHA
) -> tuple[float, float]:
    """BCa (bias-corrected + accelerated) CI for the mean of ``values``.

    Implements the standard Efron & Tibshirani BCa formula (lifted verbatim
    from RQ39's ``bca_ci``):

      * ``z0 = Phi^-1(P(boot < theta_hat))``  — bias correction
      * ``a`` via jackknife: ``a = sum((theta_bar - theta_i)^3) /
        (6 * (sum((theta_bar - theta_i)^2))^1.5)``
      * BCa alphas:
          ``alpha1 = Phi(z0 + (z0 + z_{alpha/2}) / (1 - a*(z0 + z_{alpha/2})))``
          ``alpha2 = Phi(z0 + (z0 + z_{1-alpha/2}) / (1 - a*(z0 + z_{1-alpha/2})))``
      * BCa CI = ``(percentile(boot, 100*alpha1), percentile(boot, 100*alpha2))``

    Edge cases (constant data, zero denominator, ``P(boot < theta_hat)`` of 0/1)
    are handled by clipping to a small epsilon and falling back to the
    percentile CI when the acceleration is undefined. Pure helper.
    """
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
    a: np.ndarray, b: np.ndarray, n_boot: int, seed: int
) -> np.ndarray:
    """Bootstrap distribution of ``mean(a[idx]) - mean(b[idx])`` (paired).

    Same resample indices for both ``a`` and ``b`` (paired design). Returns an
    ``n_boot`` array. Deterministic for a fixed ``seed``.
    """
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
    a: np.ndarray, b: np.ndarray, n_boot: int, seed: int, alpha: float = ALPHA
) -> tuple[float, float]:
    """Percentile CI for the paired bootstrap ``mean(a) - mean(b)``."""
    dist = paired_delta_distribution(a, b, n_boot, seed)
    return percentile_ci(dist, alpha)


# ===========================================================================
# Part 5: driver
# ===========================================================================

def _round6(x: float) -> float:
    return round(float(x), 6)


def _ci_pair(ci: tuple[float, float]) -> list[float]:
    return [_round6(ci[0]), _round6(ci[1])]


def run() -> dict[str, Any]:
    """Run the full RQ50 analysis. Returns the summary dict (also writes CSV/JSON)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n_all = len(windows)

    # --- per-window rows (with corrected decision at threshold 0.38)
    rows = build_per_window_rows(windows)

    tied_ids = [r["window_id"] for r in rows if r["is_tied"]]
    nontied_ids = [r["window_id"] for r in rows if not r["is_tied"]]
    n_tied = len(tied_ids)
    n_nontied = len(nontied_ids)

    # --- ALL-windows aggregates (sanity: must reproduce RQ39's word-level)
    all_corrected = np.array(
        [r["corrected_cpwer"] for r in rows], dtype=float
    )
    all_mixed = np.array(
        [r["always_mixed_cpwer"] for r in rows], dtype=float
    )
    all_separated = np.array(
        [r["always_separated_cpwer"] for r in rows], dtype=float
    )
    all_oracle = np.array(
        [r["oracle_best_cpwer"] for r in rows], dtype=float
    )
    all_corrected_point = float(all_corrected.mean())
    all_mixed_point = float(all_mixed.mean())
    all_separated_point = float(all_separated.mean())
    all_oracle_point = float(all_oracle.mean())
    all_decision_counts = {
        "mixed": sum(1 for r in rows if r["corrected_decision"] == "mixed"),
        "separated": sum(1 for r in rows if r["corrected_decision"] == "separated"),
    }
    # all-windows improvement (always_mixed - corrected)
    all_improvement = all_mixed_point - all_corrected_point

    # --- NON-TIED windows: the actionable subset
    nontied_rows = [r for r in rows if not r["is_tied"]]
    nt_corrected = np.array(
        [r["corrected_cpwer"] for r in nontied_rows], dtype=float
    )
    nt_mixed = np.array(
        [r["always_mixed_cpwer"] for r in nontied_rows], dtype=float
    )
    nt_sep = np.array(
        [r["always_separated_cpwer"] for r in nontied_rows], dtype=float
    )
    nt_oracle = np.array(
        [r["oracle_best_cpwer"] for r in nontied_rows], dtype=float
    )
    nt_corrected_point = float(nt_corrected.mean())
    nt_mixed_point = float(nt_mixed.mean())
    nt_sep_point = float(nt_sep.mean())
    nt_oracle_point = float(nt_oracle.mean())
    nt_decision_counts = {
        "mixed": sum(1 for r in nontied_rows if r["corrected_decision"] == "mixed"),
        "separated": sum(1 for r in nontied_rows if r["corrected_decision"] == "separated"),
    }
    # non-tied improvement (always_mixed - corrected)
    nt_improvement = nt_mixed_point - nt_corrected_point

    # --- bootstrap on non-tied corrected cpWER
    nt_boot = bootstrap_distribution(nt_corrected, N_BOOT, SEED)
    nt_pct_ci = percentile_ci(nt_boot)
    nt_bca_ci = bca_ci(nt_corrected, nt_boot)

    # paired delta (corrected - mixed) on non-tied, for context
    nt_paired = paired_delta_distribution(nt_corrected, nt_mixed, N_BOOT, SEED)
    nt_paired_ci = percentile_ci(nt_paired)
    nt_paired_point = nt_corrected_point - nt_mixed_point

    # all-windows bootstrap (recomputed for direct apples-to-apples width
    # comparison; should reproduce RQ39's word-level CI bit-for-bit)
    all_boot = bootstrap_distribution(all_corrected, N_BOOT, SEED)
    all_pct_ci = percentile_ci(all_boot)
    all_bca_ci = bca_ci(all_corrected, all_boot)
    all_paired = paired_delta_distribution(all_corrected, all_mixed, N_BOOT, SEED)
    all_paired_ci = percentile_ci(all_paired)
    all_paired_point = all_corrected_point - all_mixed_point

    nt_bca_width = nt_bca_ci[1] - nt_bca_ci[0]
    all_bca_width = all_bca_ci[1] - all_bca_ci[0]
    rq39_bca_width = RQ39_WORD_LEVEL_BCA_WIDTH

    # --- hypothesis verdicts
    # H50a: corrected BEATS oracle on non-tied windows.
    # Success: BCa lower bound > non-tied oracle cpWER.
    h50a_supported = nt_bca_ci[0] > nt_oracle_point

    # H50b: non-tied BCa CI width < RQ39's word-level width (0.084416).
    h50b_supported = nt_bca_width < RQ39_WORD_LEVEL_BCA_WIDTH

    # H50c: non-tied improvement > all-windows improvement.
    h50c_supported = nt_improvement > all_improvement

    summary: dict[str, Any] = {
        "label": LABEL,
        "rq": "RQ50: Tied-window exclusion corrected-router",
        "source_data": str(SOURCE_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "meeting_id": data["meeting_id"],
        "n_windows": n_all,
        "n_tied": n_tied,
        "n_nontied": n_nontied,
        "tied_window_ids": tied_ids,
        "nontied_window_ids": nontied_ids,
        "tie_definition": f"abs(always_mixed_cpwer - always_separated_cpwer) < {TIE_TOL}",
        "method": (
            "Reanalysis only (no Whisper / no ASR / no MeetEval run). RQ47's "
            "tied-window definition (abs(mixed - sep) < 1e-6) identifies 35 "
            "tied windows; the remaining 42 non-tied windows are the "
            "actionable subset. RQ16's corrected router (lang-id entropy >= "
            "0.38 bits -> MIXED, else SEPARATED) is applied per window. On "
            "this AISHELL-4 file the threshold-0.38 decisions coincide with "
            "RQ16's threshold-0.409 decisions (no window has entropy in "
            "[0.38, 0.409)), so the corrected-router point estimate reproduces "
            "RQ16's 1.043290 and RQ39's word-level 1.043290. Bootstrap "
            "10,000 resamples, seed=42, with percentile CI and BCa CI "
            "(jackknife acceleration) on the non-tied subset."
        ),
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "tie_tolerance": TIE_TOL,
            "note": (
                "Task directive: route MIXED if lang_id_entropy >= 0.38, else "
                "SEPARATED. On this AISHELL-4 file the decisions coincide "
                "bit-for-bit with RQ16's threshold-0.409 rule (no window has "
                "entropy in [0.38, 0.409))."
            ),
        },
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "alpha": ALPHA,
            "convention": "rng.integers(0, n, size=n) per resample (RQ16 verbatim)",
        },
        "decision_counts": {
            "all_windows": all_decision_counts,
            "nontied": nt_decision_counts,
        },
        "rq39_reference": {
            "word_level_bca_ci_95": list(RQ39_WORD_LEVEL_BCA_CI),
            "word_level_bca_width": round(RQ39_WORD_LEVEL_BCA_WIDTH, 6),
            "word_level_corrected_router_cpwer": RQ39_WORD_LEVEL_CORRECTED_CPWER,
            "word_level_always_mixed_cpwer": RQ39_WORD_LEVEL_ALWAYS_MIXED_CPWER,
            "word_level_oracle_best_cpwer": RQ39_WORD_LEVEL_ORACLE_CPWER,
            "note": (
                "RQ39 (PR #960) reported the all-windows word-level BCa CI "
                "[1.012987, 1.097403] (width 0.084416) on the corrected "
                "router (cpWER 1.043290), oracle 1.017316. The CI lower bound "
                "(1.0130) is below oracle, so H39b (CI excludes oracle) was "
                "NOT SUPPORTED — the corrected router is statistically "
                "indistinguishable from oracle."
            ),
        },
        "all_windows": {
            "n": n_all,
            "corrected_router_cpwer": _round6(all_corrected_point),
            "always_mixed_cpwer": _round6(all_mixed_point),
            "always_separated_cpwer": _round6(all_separated_point),
            "oracle_best_cpwer": _round6(all_oracle_point),
            "improvement_mixed_minus_corrected": _round6(all_improvement),
            "percentile_ci_95": _ci_pair(all_pct_ci),
            "bca_ci_95": _ci_pair(all_bca_ci),
            "bca_ci_width": _round6(all_bca_width),
            "paired_delta_corrected_minus_mixed_ci_95": _ci_pair(all_paired_ci),
            "paired_delta_corrected_minus_mixed_point": _round6(all_paired_point),
        },
        "nontied": {
            "n": n_nontied,
            "corrected_router_cpwer": _round6(nt_corrected_point),
            "always_mixed_cpwer": _round6(nt_mixed_point),
            "always_separated_cpwer": _round6(nt_sep_point),
            "oracle_best_cpwer": _round6(nt_oracle_point),
            "improvement_mixed_minus_corrected": _round6(nt_improvement),
            "percentile_ci_95": _ci_pair(nt_pct_ci),
            "bca_ci_95": _ci_pair(nt_bca_ci),
            "bca_ci_width": _round6(nt_bca_width),
            "paired_delta_corrected_minus_mixed_ci_95": _ci_pair(nt_paired_ci),
            "paired_delta_corrected_minus_mixed_point": _round6(nt_paired_point),
        },
        "hypothesis_verdicts": {
            "H50a": {
                "statement": (
                    "Excluding tied windows, the corrected router's BCa CI "
                    "lower bound > oracle cpWER on non-tied windows (the "
                    "corrected router BEATS oracle on actionable windows)."
                ),
                "kill_condition": "CI includes oracle (BCa lower <= oracle)",
                "nontied_bca_ci_95": _ci_pair(nt_bca_ci),
                "nontied_oracle_cpwer": _round6(nt_oracle_point),
                "nontied_corrected_cpwer": _round6(nt_corrected_point),
                "bca_lower_above_oracle": bool(h50a_supported),
                "supported": bool(h50a_supported),
            },
            "H50b": {
                "statement": (
                    "Excluding tied windows, the BCa CI width < RQ39's "
                    "word-level width (0.084416)."
                ),
                "kill_condition": "width >= 0.084416",
                "nontied_bca_width": _round6(nt_bca_width),
                "rq39_word_level_bca_width": _round6(RQ39_WORD_LEVEL_BCA_WIDTH),
                "width_shrunk": bool(h50b_supported),
                "supported": bool(h50b_supported),
            },
            "H50c": {
                "statement": (
                    "The corrected router's cpWER improvement over "
                    "always-mixed is larger on non-tied windows than on all "
                    "windows (the advantage is concentrated on actionable "
                    "windows)."
                ),
                "kill_condition": "non-tied improvement <= all-windows improvement",
                "nontied_improvement": _round6(nt_improvement),
                "all_windows_improvement": _round6(all_improvement),
                "nontied_larger": bool(h50c_supported),
                "supported": bool(h50c_supported),
            },
        },
    }

    # --- write CSV
    csv_fields = list(rows[0].keys())
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow(r)

    # --- write JSON
    summary_with_rows = dict(summary)
    summary_with_rows["per_window"] = rows
    JSON_PATH.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- console
    print(f"=== RQ50: Tied-window exclusion corrected-router ({n_all} windows) ===")
    print(f"Label: {LABEL}  |  Source: {SOURCE_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Tie definition: abs(mixed - sep) < {TIE_TOL}  ->  {n_tied} tied / {n_nontied} non-tied")
    print(f"Bootstrap: {N_BOOT} resamples, seed={SEED}  |  lang-id threshold: {LANG_ID_ENTROPY_THRESHOLD}")
    print()
    print("Corrected-router decisions (lang-id alone, threshold 0.38):")
    print(f"  all-windows : mixed={all_decision_counts['mixed']}, separated={all_decision_counts['separated']}")
    print(f"  non-tied    : mixed={nt_decision_counts['mixed']}, separated={nt_decision_counts['separated']}")
    print()
    print("ALL-windows (sanity, should reproduce RQ39's word-level):")
    print(f"  always_mixed     : {all_mixed_point:.6f}  (RQ39: 1.173160)")
    print(f"  oracle_best      : {all_oracle_point:.6f}  (RQ39: 1.017316)")
    print(f"  corrected_router : {all_corrected_point:.6f}  (RQ39: 1.043290)")
    print(f"    percentile CI  : [{all_pct_ci[0]:.6f}, {all_pct_ci[1]:.6f}]")
    print(f"    BCa CI         : [{all_bca_ci[0]:.6f}, {all_bca_ci[1]:.6f}]  (RQ39: [1.012987, 1.097403])")
    print(f"    BCa width      : {all_bca_width:.6f}  (RQ39: 0.084416)")
    print(f"    improvement    : {all_improvement:.6f}  (mixed - corrected)")
    print()
    print("NON-TIED windows (the actionable subset, n=42):")
    print(f"  always_mixed     : {nt_mixed_point:.6f}")
    print(f"  always_separated : {nt_sep_point:.6f}")
    print(f"  oracle_best      : {nt_oracle_point:.6f}")
    print(f"  corrected_router : {nt_corrected_point:.6f}")
    print(f"    percentile CI  : [{nt_pct_ci[0]:.6f}, {nt_pct_ci[1]:.6f}]")
    print(f"    BCa CI         : [{nt_bca_ci[0]:.6f}, {nt_bca_ci[1]:.6f}]")
    print(f"    BCa width      : {nt_bca_width:.6f}")
    print(f"    improvement    : {nt_improvement:.6f}  (mixed - corrected)")
    print(f"    paired delta CI (corrected - mixed): [{nt_paired_ci[0]:+.6f}, {nt_paired_ci[1]:+.6f}]")
    print()
    print("Hypothesis verdicts:")
    print(f"  H50a (BCa lower > non-tied oracle):")
    print(f"    {'SUPPORTED' if h50a_supported else 'NOT SUPPORTED'}  "
          f"(BCa lower={nt_bca_ci[0]:.4f} vs oracle={nt_oracle_point:.4f})")
    print(f"  H50b (non-tied BCa width < RQ39 width 0.0844):")
    print(f"    {'SUPPORTED' if h50b_supported else 'NOT SUPPORTED'}  "
          f"(non-tied width={nt_bca_width:.4f} vs RQ39 width={RQ39_WORD_LEVEL_BCA_WIDTH:.4f})")
    print(f"  H50c (non-tied improvement > all-windows improvement):")
    print(f"    {'SUPPORTED' if h50c_supported else 'NOT SUPPORTED'}  "
          f"(non-tied={nt_improvement:.4f} vs all={all_improvement:.4f})")
    print()
    print(f"Wrote: {CSV_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {JSON_PATH.relative_to(PROJECT_ROOT)}")

    return summary


if __name__ == "__main__":
    run()
