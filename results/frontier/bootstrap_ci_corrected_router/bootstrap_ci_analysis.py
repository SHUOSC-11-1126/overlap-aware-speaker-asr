"""RQ39: Bootstrap confidence intervals on the corrected-router cpWER 1.043.

REANALYSIS ONLY — no Whisper / no ASR model is run. This script reads the
existing AISHELL-4 external-validation results
(``results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json``,
label ``external/sanity-check``, PR #890) and computes bootstrap 95% CIs
(percentile + BCa + paired delta) for the corrected router's cpWER, at BOTH
granularities:

  * **Word-level** (the project's stored utterance-level convention, RQ30):
    each speaker's whole Chinese string is one token. We reuse the stored
    per-window ``always_mixed_cpwer`` / ``always_separated_cpwer`` so the
    point estimate reproduces RQ16's 1.0433 bit-for-bit.
  * **Char-level** (standard Chinese cpCER convention, RQ35): insert a space
    between each Chinese character so MeetEval treats each character as one
    "word". We re-run MeetEval 0.4.3 ``cpwer`` (separated, multi vs multi)
    and ``orcwer`` (mixed, single channel vs multi ref) so the per-window
    char-level cpWER reproduces RQ35's char-level baseline.

Routing logic (RQ16, verbatim): for each window compute the language-id
entropy (Shannon entropy over Unicode script categories, MAX across per-speaker
separated tracks, RQ13). Route to MIXED if ``lang_id_entropy > 0.409`` bits
else SEPARATED. RQ16 showed lang-id alone is identical to the full three-guard
corrected router on AISHELL-4, so we use lang-id alone — the per-window
decisions and cpWER match RQ16's ``corrected_decision`` / ``corrected_cpwer``
exactly.

Hypotheses
----------
- H39a: Bootstrap 95% CI of corrected-router cpWER excludes always-mixed
  (word-level 1.17316). Success: upper CI < 1.173.
- H39b: Bootstrap 95% CI excludes oracle (word-level 1.01732). Success:
  lower CI > 1.017.
- H39c: Paired bootstrap (per-window corrected minus mixed) CI excludes zero.
  Success: upper CI < 0.

Method
------
- 10,000 bootstrap resamples (seed=42) over the 77 windows, with replacement
  (``rng.integers(0, n, size=n)`` per resample — same convention as RQ16).
- Percentile CI: 2.5 / 97.5 percentiles of the bootstrap mean distribution.
- BCa CI: bias-corrected + accelerated; bias ``z0 = Phi^-1(P(boot < theta_hat))``
  and acceleration ``a`` via the jackknife (leave-one-out) on the original
  sample. BCa shifts the percentile CI to account for bias and skew, which
  matters here because the per-window cpWER distribution is lumpy and discrete
  (RQ16 reported a one-sided 97.5 percentile that touches zero).
- Paired delta CI: per-window ``corrected_cpwer - mixed_cpwer`` resampled with
  replacement; 2.5 / 97.5 percentiles. This is the H39c test.
- Char-level variants repeat the same three CIs at char-level granularity.

The detector primitives (``script_category``, ``language_id_entropy``,
``max_across_speakers``) are lifted verbatim from RQ16/RQ13 so the routing
decisions match. The MeetEval helpers (``to_char_level``, ``build_segments``,
``build_mixed_segment``, ``compute_cpwer_with_decomp``,
``compute_orcwer_with_decomp``) are lifted verbatim from RQ35 so the char-level
per-window cpWER matches.

Label: experimental/frontier. Closes #952.

Run:
    /opt/homebrew/bin/python3 results/frontier/bootstrap_ci_corrected_router/bootstrap_ci_analysis.py
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
import warnings
import zlib
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
OUT_CSV = OUT_DIR / "bootstrap_ci_results.csv"
OUT_JSON = OUT_DIR / "bootstrap_ci_results.json"

# ------------------------------------------------------------------ thresholds
# RQ13 calibrated operating point (>= 90% specificity on AISHELL-4 non-hallucinated
# tracks): threshold 0.409073, specificity 0.925, sensitivity 0.946. We use 0.409.
# RQ16 showed lang-id alone is identical to the full three-guard corrected router
# on AISHELL-4 (the silence and mode guards are redundant), so lang-id alone IS
# the corrected router here.
LANG_ID_ENTROPY_THRESHOLD = 0.409
N_BOOT = 10000
SEED = 42
ALPHA = 0.05
SESSION_ID = "s1"
EPS = 1e-9

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
    """Shannon entropy (bits) over the script-category distribution of the text (RQ13).

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
    """Max of fn(text) over the per-speaker separated transcripts (worst-case track).

    Same convention as RQ12's ``max_cr_separated`` and RQ13's
    ``max_across_speakers``: a window is flagged if ANY speaker track trips the
    detector. Empty/whitespace speaker texts contribute nothing and are
    effectively skipped."""
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def corrected_router_decision(window: dict[str, Any]) -> str:
    """RQ16's corrected-router decision using lang-id entropy alone.

    Route to MIXED if ``max_across_speakers(separated, language_id_entropy) >
    0.409`` bits, else SEPARATED. RQ16 verified that lang-id alone is identical
    to the full three-guard (lang-id + silence + mode) corrected router on
    AISHELL-4 — the silence and mode guards are strict subsets / fall on ties —
    so this single-guard rule IS the corrected router here."""
    ent = max_across_speakers(window, language_id_entropy)
    return "mixed" if ent > LANG_ID_ENTROPY_THRESHOLD else "separated"


# ===========================================================================
# Part 2: MeetEval cpWER helpers (lifted VERBATIM from RQ35)
# ===========================================================================

def to_char_level(text: str) -> str:
    """Space-separate each character so MeetEval treats it as one "word".

    Standard Chinese cpCER convention: Chinese has no word delimiter, so each
    character IS a token. ``"你好世界"`` -> ``"你 好 世 界"``."""
    return " ".join(list(text))


def build_segments(speaker_text: dict[str, str], char_level: bool) -> list[dict]:
    """Build MeetEval segment dicts from {speaker: text}.

    Skips empty/whitespace-only strings (matches the project's compute_cpwer).
    """
    segs = []
    for spk, txt in speaker_text.items():
        if not txt or not txt.strip():
            continue
        words = to_char_level(txt) if char_level else txt
        segs.append({"session_id": SESSION_ID, "speaker": spk, "words": words})
    return segs


def build_mixed_segment(mixed_text: str, char_level: bool) -> list[dict]:
    """Build a single-channel hypothesis segment for orcWER."""
    if not mixed_text or not mixed_text.strip():
        return []
    words = to_char_level(mixed_text) if char_level else mixed_text
    return [{"session_id": SESSION_ID, "speaker": "mix", "words": words}]


def compute_cpwer_with_decomp(
    refs: dict[str, str], hyps: dict[str, str], char_level: bool
) -> dict[str, Any]:
    """Run cpwer (multi-speaker vs multi-speaker) and return the decomposition.

    Returns the project's empty-sentinel (error_rate=1.0, zero counts, length=0,
    ``empty=True``) when either side has no non-empty speakers — MeetEval itself
    refuses to run on empty input. Matches RQ30/RQ35's ``safe_cpwer`` convention.
    """
    ref_segs = build_segments(refs, char_level)
    hyp_segs = build_segments(hyps, char_level)
    if not ref_segs or not hyp_segs:
        return {
            "error_rate": 1.0, "errors": 0, "length": 0,
            "substitutions": 0, "insertions": 0, "deletions": 0,
            "empty": True,
        }
    r = cpwer(ref_segs, hyp_segs)[SESSION_ID]
    return {
        "error_rate": float(r.error_rate),
        "errors": int(r.errors),
        "length": int(r.length),
        "substitutions": int(r.substitutions),
        "insertions": int(r.insertions),
        "deletions": int(r.deletions),
        "empty": False,
    }


def compute_orcwer_with_decomp(
    refs: dict[str, str], mixed_text: str, char_level: bool
) -> dict[str, Any]:
    """Run orcwer (single mixed channel vs multi-speaker reference) with decomp.

    Uses the project's empty-sentinel (1.0) when refs or mixed is empty.
    """
    ref_segs = build_segments(refs, char_level)
    mix_segs = build_mixed_segment(mixed_text, char_level)
    if not ref_segs or not mix_segs:
        return {
            "error_rate": 1.0, "errors": 0, "length": 0,
            "substitutions": 0, "insertions": 0, "deletions": 0,
            "empty": True,
        }
    r = orcwer(ref_segs, mix_segs)[SESSION_ID]
    return {
        "error_rate": float(r.error_rate),
        "errors": int(r.errors),
        "length": int(r.length),
        "substitutions": int(r.substitutions),
        "insertions": int(r.insertions),
        "deletions": int(r.deletions),
        "empty": False,
    }


# ===========================================================================
# Part 3: bootstrap pure helpers (NEW — RQ39)
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
    bootstrap distribution.

    Pure helper — does not re-run the bootstrap. Returns ``(lo, hi)``.
    """
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

    Implements the standard Efron & Tibshirani BCa formula:

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
    # Clip to avoid Phi^-1(0) = -inf or Phi^-1(1) = +inf.
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
    # If the denominator collapses (extreme a), fall back to percentile alphas.
    if abs(denom_lo) < EPS or abs(denom_hi) < EPS:
        return percentile_ci(boot_dist, alpha)

    alpha1 = float(norm.cdf(z0 + (z0 + z_lo) / denom_lo))
    alpha2 = float(norm.cdf(z0 + (z0 + z_hi) / denom_hi))

    # Clip alpha1/alpha2 to (0, 1) to avoid percentile edge cases.
    alpha1 = min(max(alpha1, 0.0), 1.0)
    alpha2 = min(max(alpha2, 0.0), 1.0)

    lo = float(np.percentile(boot_dist, 100.0 * alpha1))
    hi = float(np.percentile(boot_dist, 100.0 * alpha2))
    # Ensure lo <= hi (numerical safety).
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def paired_delta_distribution(
    a: np.ndarray, b: np.ndarray, n_boot: int, seed: int
) -> np.ndarray:
    """Bootstrap distribution of ``mean(a[idx]) - mean(b[idx])`` (paired, per-window).

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
    """Percentile CI for the paired bootstrap ``mean(a) - mean(b)``.

    Returns ``(lo, hi)``. Pure helper combining
    ``paired_delta_distribution`` + ``percentile_ci``.
    """
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

        # ---- routing decision (RQ16 verbatim)
        ent = max_across_speakers(w, language_id_entropy)
        decision = "mixed" if ent > LANG_ID_ENTROPY_THRESHOLD else "separated"

        # ---- word-level cpWER (stored; matches RQ16 bit-for-bit)
        word_mixed_cpwer = float(w["always_mixed_cpwer"])
        word_sep_cpwer = float(w["always_separated_cpwer"])
        word_router_v2_cpwer = float(w["router_v2_cpwer"])
        word_oracle_cpwer = float(w["oracle_best_cpwer"])
        word_corrected_cpwer = word_mixed_cpwer if decision == "mixed" else word_sep_cpwer

        # ---- char-level cpWER (re-run MeetEval; matches RQ35)
        char_sep = compute_cpwer_with_decomp(refs, sep_hyps, char_level=True)
        char_mix = compute_orcwer_with_decomp(refs, mixed, char_level=True)
        char_corrected_cpwer = (
            char_mix["error_rate"] if decision == "mixed" else char_sep["error_rate"]
        )
        # Char-level router-v2 and oracle (for the char-level regret analysis).
        char_router_v2_cpwer = (
            char_sep["error_rate"]
            if w["router_v2_method"] == "separated"
            else char_mix["error_rate"]
        )
        if char_sep["error_rate"] <= char_mix["error_rate"] + EPS:
            char_oracle_cpwer = char_sep["error_rate"]
        else:
            char_oracle_cpwer = char_mix["error_rate"]

        rows.append({
            "window_id": wid,
            "overlap_label": w["overlap_label"],
            "num_speakers": w["num_speakers"],
            "router_v2_method": w["router_v2_method"],
            "lang_id_entropy": round(ent, 6),
            "corrected_decision": decision,
            # word-level
            "word_mixed_cpwer": _round6(word_mixed_cpwer),
            "word_separated_cpwer": _round6(word_sep_cpwer),
            "word_router_v2_cpwer": _round6(word_router_v2_cpwer),
            "word_oracle_cpwer": _round6(word_oracle_cpwer),
            "word_corrected_cpwer": _round6(word_corrected_cpwer),
            # char-level
            "char_mixed_cpwer": _round6(char_mix["error_rate"]),
            "char_separated_cpwer": _round6(char_sep["error_rate"]),
            "char_router_v2_cpwer": _round6(char_router_v2_cpwer),
            "char_oracle_cpwer": _round6(char_oracle_cpwer),
            "char_corrected_cpwer": _round6(char_corrected_cpwer),
            "char_sep_empty": char_sep["empty"],
        })

    # ----------------------------------------------------------------- aggregates
    def _mean(key: str) -> float:
        return float(np.mean([r[key] for r in rows]))

    word_corr_arr = np.array([r["word_corrected_cpwer"] for r in rows], dtype=float)
    word_mixed_arr = np.array([r["word_mixed_cpwer"] for r in rows], dtype=float)
    word_oracle_arr = np.array([r["word_oracle_cpwer"] for r in rows], dtype=float)
    word_rv2_arr = np.array([r["word_router_v2_cpwer"] for r in rows], dtype=float)

    char_corr_arr = np.array([r["char_corrected_cpwer"] for r in rows], dtype=float)
    char_mixed_arr = np.array([r["char_mixed_cpwer"] for r in rows], dtype=float)
    char_oracle_arr = np.array([r["char_oracle_cpwer"] for r in rows], dtype=float)
    char_rv2_arr = np.array([r["char_router_v2_cpwer"] for r in rows], dtype=float)

    word_point = float(word_corr_arr.mean())
    char_point = float(char_corr_arr.mean())
    word_mixed_point = float(word_mixed_arr.mean())
    word_oracle_point = float(word_oracle_arr.mean())
    char_mixed_point = float(char_mixed_arr.mean())
    char_oracle_point = float(char_oracle_arr.mean())

    # ----------------------------------------------------------------- bootstraps
    word_boot = bootstrap_distribution(word_corr_arr, N_BOOT, SEED)
    char_boot = bootstrap_distribution(char_corr_arr, N_BOOT, SEED)
    word_paired = paired_delta_distribution(word_corr_arr, word_mixed_arr, N_BOOT, SEED)
    char_paired = paired_delta_distribution(char_corr_arr, char_mixed_arr, N_BOOT, SEED)

    word_pct_ci = percentile_ci(word_boot)
    word_bca_ci = bca_ci(word_corr_arr, word_boot)
    char_pct_ci = percentile_ci(char_boot)
    char_bca_ci = bca_ci(char_corr_arr, char_boot)
    word_paired_ci = percentile_ci(word_paired)
    char_paired_ci = percentile_ci(char_paired)

    # ----------------------------------------------------------------- verdicts
    # H39a: upper CI < always-mixed (word-level 1.17316). Use BCa for the
    # primary verdict (BCa is the more accurate CI for skewed/lumpy data);
    # report percentile alongside.
    h39a_word_supported_pct = word_pct_ci[1] < word_mixed_point
    h39a_word_supported_bca = word_bca_ci[1] < word_mixed_point
    h39a_char_supported_pct = char_pct_ci[1] < char_mixed_point
    h39a_char_supported_bca = char_bca_ci[1] < char_mixed_point

    # H39b: lower CI > oracle (word-level 1.01732).
    h39b_word_supported_pct = word_pct_ci[0] > word_oracle_point
    h39b_word_supported_bca = word_bca_ci[0] > word_oracle_point
    h39b_char_supported_pct = char_pct_ci[0] > char_oracle_point
    h39b_char_supported_bca = char_bca_ci[0] > char_oracle_point

    # H39c: paired delta CI (corrected - mixed) upper < 0.
    h39c_word_supported = word_paired_ci[1] < 0
    h39c_char_supported = char_paired_ci[1] < 0

    # Decision counts (sanity: should match RQ16: mixed=42, separated=35).
    decision_counts = {
        "mixed": sum(1 for r in rows if r["corrected_decision"] == "mixed"),
        "separated": sum(1 for r in rows if r["corrected_decision"] == "separated"),
    }

    # Regret analysis (for context). Report TWO recovery fractions:
    #   * vs router v2's regret gap (RQ16's headline 86.2%)
    #   * vs always-mixed's regret gap (the deployable baseline; collapses to
    #     13.3% at char-level, the RQ31 narrative)
    word_regret_corrected = word_point - word_oracle_point
    word_regret_rv2 = float(word_rv2_arr.mean()) - word_oracle_point
    word_regret_mixed = word_mixed_point - word_oracle_point
    word_recovery_vs_rv2 = (
        (word_regret_rv2 - word_regret_corrected) / word_regret_rv2
        if word_regret_rv2 > EPS else 0.0
    )
    word_recovery_vs_mixed = (
        (word_regret_mixed - word_regret_corrected) / word_regret_mixed
        if word_regret_mixed > EPS else 0.0
    )
    char_regret_corrected = char_point - char_oracle_point
    char_regret_rv2 = float(char_rv2_arr.mean()) - char_oracle_point
    char_regret_mixed = char_mixed_point - char_oracle_point
    char_recovery_vs_rv2 = (
        (char_regret_rv2 - char_regret_corrected) / char_regret_rv2
        if char_regret_rv2 > EPS else 0.0
    )
    char_recovery_vs_mixed = (
        (char_regret_mixed - char_regret_corrected) / char_regret_mixed
        if char_regret_mixed > EPS else 0.0
    )

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ39: Bootstrap CIs on corrected-router cpWER 1.043",
        "closes_issue": 952,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "meeteval_version": meeteval.__version__,
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "method": (
            "Reanalysis only (no Whisper / no ASR run). RQ16's corrected router "
            "(lang-id entropy > 0.409 bits -> MIXED, else SEPARATED) applied at "
            "two granularities: word-level (stored utterance-level cpWER, matches "
            "RQ16 bit-for-bit) and char-level (re-run MeetEval 0.4.3 cpwer/orcwer "
            "with ' '.join(list(text)) tokenisation, matches RQ35). Bootstrap "
            "10,000 resamples, seed=42, with percentile CI, BCa CI (jackknife "
            "acceleration), and paired-delta CI (corrected - mixed)."
        ),
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "note": (
                "lang_id_entropy threshold 0.409 from RQ13 (>=90% specificity, "
                "94.6% sensitivity). RQ16 showed lang-id alone == full "
                "three-guard corrected router on AISHELL-4."
            ),
        },
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "alpha": ALPHA,
            "convention": "rng.integers(0, n, size=n) per resample (RQ16 verbatim)",
        },
        "decision_counts": decision_counts,
        "rq16_reference": {
            "corrected_router_cpwer": 1.04329,
            "corrected_router_ci_95": [1.008658, 1.088745],
            "always_mixed_cpwer": 1.17316,
            "always_separated_cpwer": 1.590909,
            "router_v2_cpwer": 1.205628,
            "oracle_best_cpwer": 1.017316,
            "note": "RQ16's reported values (PR #909) — word-level must reproduce these.",
        },
        "word_level": {
            "corrected_router_cpwer": _round6(word_point),
            "always_mixed_cpwer": _round6(word_mixed_point),
            "always_separated_cpwer": _round6(_mean("word_separated_cpwer")),
            "router_v2_cpwer": _round6(float(word_rv2_arr.mean())),
            "oracle_best_cpwer": _round6(word_oracle_point),
            "percentile_ci_95": _ci_pair(word_pct_ci),
            "bca_ci_95": _ci_pair(word_bca_ci),
            "paired_delta_corrected_minus_mixed_ci_95": _ci_pair(word_paired_ci),
            "paired_delta_corrected_minus_mixed_point": _round6(word_point - word_mixed_point),
        },
        "char_level": {
            "corrected_router_cpwer": _round6(char_point),
            "always_mixed_cpwer": _round6(char_mixed_point),
            "always_separated_cpwer": _round6(_mean("char_separated_cpwer")),
            "router_v2_cpwer": _round6(float(char_rv2_arr.mean())),
            "oracle_best_cpwer": _round6(char_oracle_point),
            "percentile_ci_95": _ci_pair(char_pct_ci),
            "bca_ci_95": _ci_pair(char_bca_ci),
            "paired_delta_corrected_minus_mixed_ci_95": _ci_pair(char_paired_ci),
            "paired_delta_corrected_minus_mixed_point": _round6(char_point - char_mixed_point),
        },
        "regret_analysis": {
            "word_level": {
                "router_v2_regret_vs_oracle": _round6(word_regret_rv2),
                "always_mixed_regret_vs_oracle": _round6(word_regret_mixed),
                "corrected_regret_vs_oracle": _round6(word_regret_corrected),
                "recovery_fraction_of_router_v2_gap": _round6(word_recovery_vs_rv2),
                "recovery_fraction_of_always_mixed_gap": _round6(word_recovery_vs_mixed),
            },
            "char_level": {
                "router_v2_regret_vs_oracle": _round6(char_regret_rv2),
                "always_mixed_regret_vs_oracle": _round6(char_regret_mixed),
                "corrected_regret_vs_oracle": _round6(char_regret_corrected),
                "recovery_fraction_of_router_v2_gap": _round6(char_recovery_vs_rv2),
                "recovery_fraction_of_always_mixed_gap": _round6(char_recovery_vs_mixed),
            },
        },
        "hypothesis_verdicts": {
            "H39a": {
                "statement": (
                    "Bootstrap 95% CI of corrected-router cpWER excludes "
                    "always-mixed (word-level 1.17316). Success: upper CI < 1.173."
                ),
                "word_level": {
                    "always_mixed_cpwer": _round6(word_mixed_point),
                    "corrected_router_cpwer": _round6(word_point),
                    "percentile_ci_95": _ci_pair(word_pct_ci),
                    "bca_ci_95": _ci_pair(word_bca_ci),
                    "upper_ci_below_mixed_pct": bool(h39a_word_supported_pct),
                    "upper_ci_below_mixed_bca": bool(h39a_word_supported_bca),
                    "supported": bool(h39a_word_supported_bca),
                },
                "char_level": {
                    "always_mixed_cpwer": _round6(char_mixed_point),
                    "corrected_router_cpwer": _round6(char_point),
                    "percentile_ci_95": _ci_pair(char_pct_ci),
                    "bca_ci_95": _ci_pair(char_bca_ci),
                    "upper_ci_below_mixed_pct": bool(h39a_char_supported_pct),
                    "upper_ci_below_mixed_bca": bool(h39a_char_supported_bca),
                    "supported": bool(h39a_char_supported_bca),
                },
            },
            "H39b": {
                "statement": (
                    "Bootstrap 95% CI excludes oracle (word-level 1.01732). "
                    "Success: lower CI > 1.017."
                ),
                "word_level": {
                    "oracle_best_cpwer": _round6(word_oracle_point),
                    "corrected_router_cpwer": _round6(word_point),
                    "percentile_ci_95": _ci_pair(word_pct_ci),
                    "bca_ci_95": _ci_pair(word_bca_ci),
                    "lower_ci_above_oracle_pct": bool(h39b_word_supported_pct),
                    "lower_ci_above_oracle_bca": bool(h39b_word_supported_bca),
                    "supported": bool(h39b_word_supported_bca),
                },
                "char_level": {
                    "oracle_best_cpwer": _round6(char_oracle_point),
                    "corrected_router_cpwer": _round6(char_point),
                    "percentile_ci_95": _ci_pair(char_pct_ci),
                    "bca_ci_95": _ci_pair(char_bca_ci),
                    "lower_ci_above_oracle_pct": bool(h39b_char_supported_pct),
                    "lower_ci_above_oracle_bca": bool(h39b_char_supported_bca),
                    "supported": bool(h39b_char_supported_bca),
                },
            },
            "H39c": {
                "statement": (
                    "Paired bootstrap (per-window corrected minus mixed) CI "
                    "excludes zero. Success: upper CI < 0."
                ),
                "word_level": {
                    "paired_delta_point": _round6(word_point - word_mixed_point),
                    "paired_delta_ci_95": _ci_pair(word_paired_ci),
                    "upper_ci_below_zero": bool(h39c_word_supported),
                    "supported": bool(h39c_word_supported),
                },
                "char_level": {
                    "paired_delta_point": _round6(char_point - char_mixed_point),
                    "paired_delta_ci_95": _ci_pair(char_paired_ci),
                    "upper_ci_below_zero": bool(h39c_char_supported),
                    "supported": bool(h39c_char_supported),
                },
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
    print(f"=== RQ39: Bootstrap CIs on corrected-router cpWER ({n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"MeetEval: {meeteval.__version__}  |  Bootstrap: {N_BOOT} resamples, seed={SEED}")
    print()
    print(f"Corrected-router decisions (lang-id alone): mixed={decision_counts['mixed']}, "
          f"separated={decision_counts['separated']}")
    print(f"  (RQ16's full 3-guard corrected router: mixed=42, separated=35; the 4 extra "
          f"flags fall on mixed==separated ties, so cpWER is identical: 1.043290)")
    print()
    print("Word-level (utterance-level, matches RQ16):")
    print(f"  always_mixed     : {word_mixed_point:.6f}")
    print(f"  always_separated : {_mean('word_separated_cpwer'):.6f}")
    print(f"  router_v2        : {float(word_rv2_arr.mean()):.6f}")
    print(f"  oracle_best      : {word_oracle_point:.6f}")
    print(f"  corrected_router : {word_point:.6f}  (RQ16: 1.043290)")
    print(f"    percentile CI  : [{word_pct_ci[0]:.6f}, {word_pct_ci[1]:.6f}]")
    print(f"    BCa CI         : [{word_bca_ci[0]:.6f}, {word_bca_ci[1]:.6f}]")
    print(f"    paired delta CI (corrected - mixed): [{word_paired_ci[0]:+.6f}, {word_paired_ci[1]:+.6f}]")
    print()
    print("Char-level (matches RQ35):")
    print(f"  always_mixed     : {char_mixed_point:.6f}")
    print(f"  always_separated : {_mean('char_separated_cpwer'):.6f}")
    print(f"  router_v2        : {float(char_rv2_arr.mean()):.6f}")
    print(f"  oracle_best      : {char_oracle_point:.6f}")
    print(f"  corrected_router : {char_point:.6f}")
    print(f"    percentile CI  : [{char_pct_ci[0]:.6f}, {char_pct_ci[1]:.6f}]")
    print(f"    BCa CI         : [{char_bca_ci[0]:.6f}, {char_bca_ci[1]:.6f}]")
    print(f"    paired delta CI (corrected - mixed): [{char_paired_ci[0]:+.6f}, {char_paired_ci[1]:+.6f}]")
    print()
    print("Hypothesis verdicts (BCa primary for H39a/H39b; paired-delta for H39c):")
    print(f"  H39a (upper CI < always-mixed):")
    print(f"    word-level: {'SUPPORTED' if h39a_word_supported_bca else 'NOT SUPPORTED'}  "
          f"(BCa upper={word_bca_ci[1]:.4f} vs mixed={word_mixed_point:.4f})")
    print(f"    char-level: {'SUPPORTED' if h39a_char_supported_bca else 'NOT SUPPORTED'}  "
          f"(BCa upper={char_bca_ci[1]:.4f} vs mixed={char_mixed_point:.4f})")
    print(f"  H39b (lower CI > oracle):")
    print(f"    word-level: {'SUPPORTED' if h39b_word_supported_bca else 'NOT SUPPORTED'}  "
          f"(BCa lower={word_bca_ci[0]:.4f} vs oracle={word_oracle_point:.4f})")
    print(f"    char-level: {'SUPPORTED' if h39b_char_supported_bca else 'NOT SUPPORTED'}  "
          f"(BCa lower={char_bca_ci[0]:.4f} vs oracle={char_oracle_point:.4f})")
    print(f"  H39c (paired delta upper CI < 0):")
    print(f"    word-level: {'SUPPORTED' if h39c_word_supported else 'NOT SUPPORTED'}  "
          f"(paired upper={word_paired_ci[1]:+.4f})")
    print(f"    char-level: {'SUPPORTED' if h39c_char_supported else 'NOT SUPPORTED'}  "
          f"(paired upper={char_paired_ci[1]:+.4f})")
    print()
    print("Regret recovery (vs router v2's gap to oracle):")
    print(f"  word-level: {word_recovery_vs_rv2:.1%}  (RQ16: 86.2%)")
    print(f"  char-level: {char_recovery_vs_rv2:.1%}")
    print("Regret recovery (vs always-mixed's gap to oracle):")
    print(f"  word-level: {word_recovery_vs_mixed:.1%}")
    print(f"  char-level: {char_recovery_vs_mixed:.1%}  (RQ31 narrative: collapses to 13.3%)")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
