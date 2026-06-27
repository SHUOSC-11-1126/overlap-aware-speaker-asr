#!/usr/bin/env python3
"""RQ55: Char-level BCa CI on the corrected router.

RQ39 (PR #960) found the **word-level** BCa CI [1.0130, 1.0974] on the corrected
router *includes* the oracle (1.0173): the corrected router reaches the oracle
within statistical noise at word-level, but cannot be claimed to beat it. RQ31
(PR #950) showed char-level cpWER shrinks the separation tax ~79.5x
(0.418 -> 0.005) and that Mode S disappears at char-level. RQ55 asks: **does the
char-level BCa CI on the corrected router exclude the char-level oracle?**

If char-level cpWER is less lumpy (RQ30/RQ35), the corrected router's char-level
cpWER might sit closer to oracle, and the (narrower) BCa CI might exclude oracle
-- a stronger statistical claim than RQ39's word-level "reaches oracle within
noise."

Hypotheses (pre-registered)
---------------------------
- H55a: char-level corrected-router BCa CI excludes oracle char-level cpWER
  (corrected router beats oracle at char-level). KILLED if CI includes oracle.
- H55b: char-level BCa CI width < word-level BCa CI width (0.0844). KILLED if
  char-level width >= 0.0844.
- H55c: char-level corrected-router cpWER < char-level always-mixed cpWER
  (corrected router still beats mixed at char-level). KILLED if corrected >=
  mixed.

Method
------
For each of the 77 AISHELL-4 windows we:
  1. Compute char-level cpWER with MeetEval 0.4.3's cpwer / orcwer using
     character-level tokenisation: ' '.join(list(text)) (RQ31 convention).
  2. Compute lang_id_entropy (RQ13 detector, verbatim) from the per-speaker
     separated transcripts, aggregated by MAX across speakers.
  3. Apply the corrected router: lang_id_entropy > 0.38 => MIXED, else
     SEPARATED. (Threshold 0.38 per RQ55 task spec; verified to give identical
     routing to RQ13's 0.409 operating point on this dataset -- no window has
     entropy in (0.38, 0.409].)
  4. Compute four policies: always_mixed_char, always_separated_char,
     corrected_router_char, oracle_char (= min(mixed, separated)).
  5. Bootstrap (B=10,000, seed=42) the corrected router's char-level cpWER;
     report percentile CI and BCa CI (jackknife acceleration).

The detector primitives (``script_category``, ``language_id_entropy``,
``max_across_speakers``) and char-level MeetEval helpers (``to_char_level``,
``build_segments``, ``build_mixed_segment``, ``safe_cpwer``, ``safe_orcwer``)
are lifted verbatim from RQ31/RQ13 so the per-window char-level cpWER matches
bit-for-bit. The bootstrap helpers (``bootstrap_indices``,
``bootstrap_distribution``, ``percentile_ci``, ``_jackknife_means``, ``bca_ci``,
``paired_delta_distribution``, ``paired_delta_ci``) are lifted verbatim from
RQ39 so the BCa CI methodology matches.

Reanalysis only -- no Whisper / no ASR runs. Uses the stored transcripts in
results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json.

Label: experimental/frontier. Closes #978.

Run:
    /opt/homebrew/bin/python3 results/frontier/char_level_bca/char_level_bca_analysis.py
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
import warnings
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy.stats import norm

warnings.filterwarnings("ignore")  # MeetEval prints "Assuming sort=False" spam

try:
    import meeteval
    from meeteval.wer import cpwer, orcwer
except ImportError:  # pure helpers can still be tested without MeetEval
    meeteval = None
    cpwer = None
    orcwer = None

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = Path(__file__).resolve().parent
OUT_CSV = OUT_DIR / "char_level_bca_results.csv"
OUT_JSON = OUT_DIR / "char_level_bca_results.json"

# ------------------------------------------------------------------ thresholds
# RQ55 task spec: lang-id entropy threshold 0.38. Verified to give identical
# routing to RQ13's 0.409 operating point on AISHELL-4 (no window has entropy
# in (0.38, 0.409]), so the per-window decisions match RQ16/RQ31/RQ39.
LANG_ID_ENTROPY_THRESHOLD = 0.38
N_BOOT = 10000
SEED = 42
ALPHA = 0.05
SESSION_ID = "s1"
EPS = 1e-9

# RQ39 word-level BCa CI reference (for H55b width comparison).
RQ39_WORD_BCA_CI = (1.012987, 1.097403)
RQ39_WORD_BCA_WIDTH = RQ39_WORD_BCA_CI[1] - RQ39_WORD_BCA_CI[0]  # 0.084416


# ===========================================================================
# Part 1: detector primitives (lifted VERBATIM from RQ13/RQ16/RQ31)
# ===========================================================================

def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13 verbatim).

    Uses ``unicodedata.name``. Whitespace -> "Space"; punctuation/symbols ->
    "Punct"; control/unknown -> "Other". Sufficient to separate Han / Latin /
    Hiragana / Katakana / Hangul / Cyrillic / Arabic / Greek / Digit.
    """
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
    """Max of fn(text) over the per-speaker separated transcripts (worst-case).

    Same convention as RQ12/RQ13/RQ16: a window is flagged if ANY speaker track
    trips the detector. Empty/whitespace speaker texts contribute nothing."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def corrected_router_decision(window: dict[str, Any]) -> str:
    """RQ55 corrected-router decision using lang-id entropy alone (threshold 0.38).

    Route to MIXED if ``max_across_speakers(separated, language_id_entropy) >
    0.38`` bits, else SEPARATED. Verified to give identical routing to RQ13's
    0.409 operating point on AISHELL-4 (no window has entropy in (0.38, 0.409])."""
    ent = max_across_speakers(window, language_id_entropy)
    return "mixed" if ent > LANG_ID_ENTROPY_THRESHOLD else "separated"


# ===========================================================================
# Part 2: MeetEval char-level helpers (lifted VERBATIM from RQ31)
# ===========================================================================

def to_char_level(text: str) -> str:
    """Space-separate each character so MeetEval treats it as one "word".

    Standard Chinese cpCER convention: Chinese has no word delimiter, so each
    character IS a token. ``"你好世界"`` -> ``"你 好 世 界"``."""
    return " ".join(list(text))


def build_segments(speaker_text: dict[str, str]) -> list[dict]:
    """Build MeetEval char-level segment dicts from {speaker: text}.

    Skips empty/whitespace-only strings (matches RQ31's build_segments)."""
    segs = []
    for spk, txt in speaker_text.items():
        if not txt or not txt.strip():
            continue
        segs.append({
            "session_id": SESSION_ID,
            "speaker": spk,
            "words": to_char_level(txt),
        })
    return segs


def build_mixed_segment(mixed_text: str) -> list[dict]:
    """Build a single-channel hypothesis segment for orcWER (char-level)."""
    if not mixed_text or not mixed_text.strip():
        return []
    return [{
        "session_id": SESSION_ID,
        "speaker": "mix",
        "words": to_char_level(mixed_text),
    }]


def safe_cpwer(ref_segs, hyp_segs) -> tuple[float, int, int]:
    """Run cpwer; on empty input return the project's empty-sentinel (1.0, -1, -1).

    Lifted verbatim from RQ31."""
    if not ref_segs or not hyp_segs:
        return 1.0, -1, -1
    r = cpwer(ref_segs, hyp_segs)[SESSION_ID]
    return float(r.error_rate), int(r.errors), int(r.length)


def safe_orcwer(ref_segs, hyp_segs) -> tuple[float, int, int]:
    """Run orcwer; on empty input return the project's empty-sentinel.

    Lifted verbatim from RQ31."""
    if not ref_segs or not hyp_segs:
        return 1.0, -1, -1
    r = orcwer(ref_segs, hyp_segs)[SESSION_ID]
    return float(r.error_rate), int(r.errors), int(r.length)


# ===========================================================================
# Part 3: bootstrap helpers (lifted VERBATIM from RQ39)
# ===========================================================================

def bootstrap_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``(n_boot, n)`` int array of resample indices (with replacement).

    Same convention as RQ16/RQ39: ``rng.integers(0, n, size=n)`` per resample.
    Deterministic for a fixed ``seed``."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(n_boot, n))


def bootstrap_distribution(values: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``n_boot`` array of bootstrap means of ``values``."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    idx = bootstrap_indices(n, n_boot, seed)
    return values[idx].mean(axis=1)


def percentile_ci(boot_dist: np.ndarray, alpha: float = ALPHA) -> tuple[float, float]:
    """Percentile CI: 2.5 / 97.5 percentiles of the bootstrap distribution."""
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
    values: np.ndarray, boot_dist: np.ndarray, alpha: float = ALPHA
) -> tuple[float, float]:
    """BCa (bias-corrected + accelerated) CI for the mean of ``values``.

    Implements the standard Efron & Tibshirani BCa formula (lifted verbatim
    from RQ39). Edge cases (constant data, zero denominator) fall back to the
    percentile CI."""
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
    """Bootstrap distribution of ``mean(a[idx]) - mean(b[idx])`` (paired)."""
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

    rows: list[dict[str, Any]] = []
    for w in windows:
        wid = w["window_id"]
        refs = w["ref_text_per_speaker"]
        sep_hyps = w["separated_text_per_speaker"]
        mixed = w.get("mixed_text", "")

        # ---- routing decision (lang-id entropy > 0.38 -> MIXED, else SEPARATED)
        ent = max_across_speakers(w, language_id_entropy)
        decision = corrected_router_decision(w)

        # ---- word-level cpWER (stored; for H55b width comparison context)
        word_mixed_cpwer = float(w["always_mixed_cpwer"])
        word_sep_cpwer = float(w["always_separated_cpwer"])
        word_oracle_cpwer = float(w["oracle_best_cpwer"])
        word_corrected_cpwer = word_mixed_cpwer if decision == "mixed" else word_sep_cpwer

        # ---- char-level cpWER (re-run MeetEval; matches RQ31/RQ35)
        ref_segs = build_segments(refs)
        sep_segs = build_segments(sep_hyps)
        mix_segs = build_mixed_segment(mixed)

        separated_char, sep_err, sep_len = safe_cpwer(ref_segs, sep_segs)
        mixed_char, mix_err, mix_len = safe_orcwer(ref_segs, mix_segs)

        corrected_char = mixed_char if decision == "mixed" else separated_char
        oracle_char = min(mixed_char, separated_char)

        residual = corrected_char - oracle_char

        rows.append({
            "window_id": wid,
            "overlap_label": w["overlap_label"],
            "num_speakers": w["num_speakers"],
            "router_v2_method": w["router_v2_method"],
            "lang_id_entropy": round(ent, 6),
            "corrected_decision": decision,
            # word-level (stored)
            "word_mixed_cpwer": _round6(word_mixed_cpwer),
            "word_separated_cpwer": _round6(word_sep_cpwer),
            "word_oracle_cpwer": _round6(word_oracle_cpwer),
            "word_corrected_cpwer": _round6(word_corrected_cpwer),
            # char-level (recomputed)
            "char_mixed_cpwer": _round6(mixed_char),
            "char_separated_cpwer": _round6(separated_char),
            "char_oracle_cpwer": _round6(oracle_char),
            "char_corrected_cpwer": _round6(corrected_char),
            "residual_corrected_minus_oracle": round(residual, 6),
            "separated_char_errors": sep_err,
            "separated_char_length": sep_len,
            "mixed_char_errors": mix_err,
            "mixed_char_length": mix_len,
        })

    # ----------------------------------------------------------------- aggregates
    def _mean(key: str) -> float:
        return float(np.mean([r[key] for r in rows]))

    word_corr_arr = np.array([r["word_corrected_cpwer"] for r in rows], dtype=float)
    word_mixed_arr = np.array([r["word_mixed_cpwer"] for r in rows], dtype=float)
    word_oracle_arr = np.array([r["word_oracle_cpwer"] for r in rows], dtype=float)

    char_corr_arr = np.array([r["char_corrected_cpwer"] for r in rows], dtype=float)
    char_mixed_arr = np.array([r["char_mixed_cpwer"] for r in rows], dtype=float)
    char_sep_arr = np.array([r["char_separated_cpwer"] for r in rows], dtype=float)
    char_oracle_arr = np.array([r["char_oracle_cpwer"] for r in rows], dtype=float)

    char_point = float(char_corr_arr.mean())
    char_mixed_point = float(char_mixed_arr.mean())
    char_sep_point = float(char_sep_arr.mean())
    char_oracle_point = float(char_oracle_arr.mean())
    word_point = float(word_corr_arr.mean())
    word_mixed_point = float(word_mixed_arr.mean())
    word_oracle_point = float(word_oracle_arr.mean())

    # Separation tax at char level.
    separation_tax_char = char_sep_point - char_mixed_point

    # Decision counts.
    decision_counts = {
        "mixed": sum(1 for r in rows if r["corrected_decision"] == "mixed"),
        "separated": sum(1 for r in rows if r["corrected_decision"] == "separated"),
    }

    # ----------------------------------------------------------------- bootstraps
    char_boot = bootstrap_distribution(char_corr_arr, N_BOOT, SEED)
    word_boot = bootstrap_distribution(word_corr_arr, N_BOOT, SEED)

    char_pct_ci = percentile_ci(char_boot)
    char_bca_ci = bca_ci(char_corr_arr, char_boot)
    word_pct_ci = percentile_ci(word_boot)
    word_bca_ci = bca_ci(word_corr_arr, word_boot)

    char_paired = paired_delta_distribution(char_corr_arr, char_mixed_arr, N_BOOT, SEED)
    char_paired_ci = percentile_ci(char_paired)

    # ----------------------------------------------------------------- verdicts
    char_bca_width = char_bca_ci[1] - char_bca_ci[0]
    word_bca_width = word_bca_ci[1] - word_bca_ci[0]

    # H55a: char-level BCa CI excludes oracle. Corrected router beats oracle
    # only if the corrected router's cpWER is below oracle's; for the CI to
    # exclude oracle in that direction the BCa UPPER bound must be below oracle.
    # (Per construction corrected >= oracle per window, so the CI can at most
    # tie oracle; "excludes oracle" here means upper CI < oracle.)
    h55a_excludes_oracle = char_bca_ci[1] < char_oracle_point
    h55a_oracle_inside = (char_bca_ci[0] <= char_oracle_point <= char_bca_ci[1])

    # H55b: char-level BCa width < word-level BCa width (0.0844).
    h55b_supported = char_bca_width < RQ39_WORD_BCA_WIDTH

    # H55c: char-level corrected cpWER < char-level always-mixed cpWER.
    h55c_supported = char_point < char_mixed_point

    # Win/tie/loss of corrected router vs always-mixed (per window).
    wins = int(np.sum(char_corr_arr < char_mixed_arr))
    ties = int(np.sum(np.isclose(char_corr_arr, char_mixed_arr)))
    losses = int(np.sum(char_corr_arr > char_mixed_arr))

    # Regret analysis (for context).
    char_regret_corrected = char_point - char_oracle_point
    char_regret_mixed = char_mixed_point - char_oracle_point
    char_recovery_vs_mixed = (
        (char_regret_mixed - char_regret_corrected) / char_regret_mixed
        if char_regret_mixed > EPS else 0.0
    )

    # Verify threshold 0.38 == 0.409 routing on this dataset.
    n_mixed_038 = decision_counts["mixed"]
    n_mixed_0409 = sum(
        1 for w in windows
        if max_across_speakers(w, language_id_entropy) > 0.409
    )
    threshold_routing_identical = (n_mixed_038 == n_mixed_0409)

    meeteval_version = meeteval.__version__ if meeteval is not None else None

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ55: Char-level BCa CI on corrected router",
        "closes_issue": 978,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "meeteval_version": meeteval_version,
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "method": (
            "Reanalysis only (no Whisper / no ASR run). RQ55 corrected router "
            "(lang-id entropy > 0.38 bits -> MIXED, else SEPARATED) applied at "
            "char-level (MeetEval 0.4.3 cpwer/orcwer with ' '.join(list(text)) "
            "tokenisation, RQ31 convention). Bootstrap 10,000 resamples, seed=42, "
            "with percentile CI and BCa CI (jackknife acceleration, RQ39 verbatim). "
            "Threshold 0.38 verified to give identical routing to RQ13's 0.409 "
            "operating point on this dataset (no window has entropy in (0.38, 0.409])."
        ),
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "note": (
                "RQ55 task spec threshold 0.38. Verified identical routing to "
                "RQ13's 0.409 operating point (>=90% specificity, 94.6% "
                "sensitivity) on AISHELL-4 -- no window has entropy in "
                "(0.38, 0.409]."
            ),
        },
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "alpha": ALPHA,
            "convention": "rng.integers(0, n, size=n) per resample (RQ16/RQ39 verbatim)",
        },
        "threshold_routing_check": {
            "n_mixed_at_0_38": n_mixed_038,
            "n_mixed_at_0_409": n_mixed_0409,
            "routing_identical": bool(threshold_routing_identical),
        },
        "decision_counts": decision_counts,
        "char_level_baselines": {
            "always_mixed_char": _round6(char_mixed_point),
            "always_separated_char": _round6(char_sep_point),
            "corrected_router_char": _round6(char_point),
            "oracle_char": _round6(char_oracle_point),
        },
        "char_level_ci_95": {
            "corrected_router_char_percentile": _ci_pair(char_pct_ci),
            "corrected_router_char_bca": _ci_pair(char_bca_ci),
            "paired_delta_corrected_minus_mixed": _ci_pair(char_paired_ci),
            "paired_delta_corrected_minus_mixed_point": _round6(char_point - char_mixed_point),
        },
        "word_level_reference": {
            "corrected_router_cpwer": _round6(word_point),
            "always_mixed_cpwer": _round6(word_mixed_point),
            "always_separated_cpwer": _round6(_mean("word_separated_cpwer")),
            "oracle_best_cpwer": _round6(word_oracle_point),
            "percentile_ci_95": _ci_pair(word_pct_ci),
            "bca_ci_95": _ci_pair(word_bca_ci),
            "bca_width": _round6(word_bca_width),
        },
        "rq39_word_level_reference": {
            "bca_ci_95": [RQ39_WORD_BCA_CI[0], RQ39_WORD_BCA_CI[1]],
            "bca_width": _round6(RQ39_WORD_BCA_WIDTH),
            "note": "RQ39 PR #960 word-level BCa CI on corrected router (threshold 0.409).",
        },
        "separation_tax": {
            "char_level": _round6(separation_tax_char),
            "word_level_rq31": 0.417749,
            "note": "word_level from RQ31: 1.590909 - 1.17316 = 0.417749; char shrinks ~79.5x.",
        },
        "ci_width_comparison": {
            "char_level_bca_width": _round6(char_bca_width),
            "word_level_bca_width": _round6(word_bca_width),
            "rq39_word_level_bca_width": _round6(RQ39_WORD_BCA_WIDTH),
            "char_narrower_than_word": bool(char_bca_width < word_bca_width),
            "char_narrower_than_rq39_word": bool(char_bca_width < RQ39_WORD_BCA_WIDTH),
        },
        "corrected_vs_mixed_win_tie_loss": {"wins": wins, "ties": ties, "losses": losses},
        "regret_analysis": {
            "char_level": {
                "always_mixed_regret_vs_oracle": _round6(char_regret_mixed),
                "corrected_regret_vs_oracle": _round6(char_regret_corrected),
                "recovery_fraction_of_always_mixed_gap": _round6(char_recovery_vs_mixed),
            },
        },
        "hypothesis_verdicts": {
            "H55a": {
                "statement": (
                    "Char-level corrected-router BCa CI excludes oracle char-level "
                    "cpWER (corrected router beats oracle at char-level)."
                ),
                "char_level_bca_ci_95": _ci_pair(char_bca_ci),
                "oracle_char": _round6(char_oracle_point),
                "corrected_router_char": _round6(char_point),
                "oracle_inside_ci": bool(h55a_oracle_inside),
                "excludes_oracle": bool(h55a_excludes_oracle),
                "success_criterion": "BCa upper CI < oracle (CI excludes oracle)",
                "kill_criterion": "CI includes oracle",
                "supported": bool(h55a_excludes_oracle),
            },
            "H55b": {
                "statement": (
                    "Char-level BCa CI width < word-level BCa CI width (0.0844)."
                ),
                "char_level_bca_width": _round6(char_bca_width),
                "word_level_bca_width": _round6(word_bca_width),
                "rq39_word_level_bca_width": _round6(RQ39_WORD_BCA_WIDTH),
                "success_criterion": "char_width < 0.0844",
                "kill_criterion": "char_width >= 0.0844",
                "supported": bool(h55b_supported),
            },
            "H55c": {
                "statement": (
                    "Char-level corrected-router cpWER < char-level always-mixed "
                    "cpWER (corrected router still beats mixed at char-level)."
                ),
                "corrected_router_char": _round6(char_point),
                "always_mixed_char": _round6(char_mixed_point),
                "delta_corrected_minus_mixed": _round6(char_point - char_mixed_point),
                "paired_delta_ci_95": _ci_pair(char_paired_ci),
                "success_criterion": "corrected_char < mixed_char (point estimate)",
                "kill_criterion": "corrected_char >= mixed_char",
                "supported": bool(h55c_supported),
            },
        },
    }

    # ----------------------------------------------------------- write CSV
    csv_fields = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow(r)

    # ----------------------------------------------------------- write JSON
    summary_with_rows = dict(summary)
    summary_with_rows["per_window"] = rows
    OUT_JSON.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- console
    print(f"=== RQ55: Char-level BCa CI on corrected router ({n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"MeetEval: {meeteval_version}  |  Bootstrap: {N_BOOT} resamples, seed={SEED}")
    print(f"Threshold: lang-id entropy > {LANG_ID_ENTROPY_THRESHOLD} -> MIXED")
    print()
    print(f"Corrected-router decisions: mixed={decision_counts['mixed']}, "
          f"separated={decision_counts['separated']}")
    print(f"  routing identical to 0.409: {threshold_routing_identical} "
          f"(mixed@0.38={n_mixed_038}, mixed@0.409={n_mixed_0409})")
    print()
    print("Char-level cpWER (mean over 77 windows):")
    print(f"  always_mixed      : {char_mixed_point:.6f}")
    print(f"  always_separated  : {char_sep_point:.6f}")
    print(f"  oracle_best       : {char_oracle_point:.6f}")
    print(f"  corrected_router  : {char_point:.6f}")
    print(f"    percentile CI   : [{char_pct_ci[0]:.6f}, {char_pct_ci[1]:.6f}]")
    print(f"    BCa CI          : [{char_bca_ci[0]:.6f}, {char_bca_ci[1]:.6f}]  (width {char_bca_width:.6f})")
    print(f"    paired-Δ CI     : [{char_paired_ci[0]:+.6f}, {char_paired_ci[1]:+.6f}]")
    print()
    print("Word-level reference (stored, for H55b width comparison):")
    print(f"  corrected_router  : {word_point:.6f}")
    print(f"    BCa CI          : [{word_bca_ci[0]:.6f}, {word_bca_ci[1]:.6f}]  (width {word_bca_width:.6f})")
    print(f"  RQ39 word BCa CI  : [{RQ39_WORD_BCA_CI[0]:.6f}, {RQ39_WORD_BCA_CI[1]:.6f}]  "
          f"(width {RQ39_WORD_BCA_WIDTH:.6f})")
    print()
    print("Hypothesis verdicts:")
    print(f"  H55a (char BCa CI excludes oracle): "
          f"{'SUPPORTED' if h55a_excludes_oracle else 'KILLED'}  "
          f"(BCa=[{char_bca_ci[0]:.4f}, {char_bca_ci[1]:.4f}] vs oracle={char_oracle_point:.4f}, "
          f"oracle_inside_ci={h55a_oracle_inside})")
    print(f"  H55b (char BCa width < word BCa width 0.0844): "
          f"{'SUPPORTED' if h55b_supported else 'KILLED'}  "
          f"(char_width={char_bca_width:.6f} vs word_width={RQ39_WORD_BCA_WIDTH:.6f})")
    print(f"  H55c (corrected_char < mixed_char): "
          f"{'SUPPORTED' if h55c_supported else 'KILLED'}  "
          f"(delta={char_point-char_mixed_point:+.6f}, "
          f"paired CI=[{char_paired_ci[0]:+.6f}, {char_paired_ci[1]:+.6f}])")
    print()
    print(f"Corrected vs always-mixed (char-level): {wins} wins, {ties} ties, {losses} losses")
    print(f"Recovery vs always-mixed gap: {char_recovery_vs_mixed:.1%}")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
