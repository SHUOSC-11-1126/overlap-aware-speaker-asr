"""RQ68: Multi-Meeting Power Simulation for Oracle Exclusion.

RQ64 (PR #993) showed that the "corrected router reaches oracle within noise"
verdict at n=77 is a SAMPLE-SIZE problem: lang-id needs n=105, KL needs n=250,
but the meeting has only n=77 windows. RQ64 reached this verdict via the
*extrapolated bootstrap* (treat the 77 per-window cpWER values as the empirical
population F_hat, draw B=10000 resamples of size n, compute ONE BCa CI per n
using the population mean as theta_hat).

RQ68 asks the follow-up question: does RQ64's prediction hold up under a
*multi-meeting simulation*? Instead of computing one extrapolated BCa CI per n,
we simulate M independent "synthetic meetings" of size n (each a resample WITH
replacement from F_hat), and for each synthetic meeting we compute the standard
BCa CI the way a researcher would on a freshly collected n-window meeting
(theta_hat = the meeting's sample mean; jackknife `a` from the meeting's n
values; bootstrap distribution from B resamples of the meeting's data). Power
is then the fraction of M simulated meetings whose BCa CI excludes the oracle.

This is the standard retrospective power simulation: it estimates the
probability that a researcher collecting n windows and running the RQ39 BCa CI
procedure would conclude "corrected router excludes oracle (BCa lower bound
above oracle)." RQ64's extrapolated bootstrap gives the *expected* BCa CI at
size n; RQ68 gives the *distribution* of BCa CIs a researcher would actually
see, and hence the power.

Method
------
1. Load 77 AISHELL-4 windows. Compute the corrected router's per-window cpWER
   (lang-id entropy threshold 0.38 -> MIXED, else SEPARATED; RQ55 convention,
   verified identical to RQ16's 0.409 on this dataset) and the oracle per-window
   cpWER (stored ``oracle_best_cpwer``). Word-level (utterance-level) cpWER,
   matching RQ16/RQ39 bit-for-bit (1.04329). The 77 per-window corrected cpWER
   values are the empirical population F_hat.
2. For the KL-corrected router (RQ58, cpWER 1.0303): read RQ58's per-window
   ``kl_cpwer`` from its results JSON. Those 77 values are F_hat for KL.
3. For each n in {77, 105, 154, 250, 308, 500, 616, 770, 1000}:
   * Headline primary meeting (H68a/H68b): draw ONE meeting of size n from
     F_hat with meeting_seed=42, compute BCa CI with B=10000, boot_seed=42.
     Check if BCa lower bound > oracle.
   * Power curve (H68c): draw M=200 simulated meetings of size n from F_hat
     (meeting_seed = 42 + i, i=0..199), compute BCa CI on each with B=2000
     (boot_seed = 42 + i + 1000). Power = fraction of meetings where BCa
     lower bound > oracle.
4. Find n* = minimum n where power >= 0.80 (linear interpolation on the grid).
5. Compare n* to RQ64's extrapolated ceiling of 770.

Multi-meeting simulation (the core technique)
----------------------------------------------
The 77 per-window cpWER values are treated as the population F_hat. For a
target sample size n, we draw M independent "synthetic meetings" each of size
n WITH replacement from F_hat. Each synthetic meeting is a fresh dataset of n
windows that a researcher might have collected. For each meeting we run the
*standard* RQ39 BCa CI procedure (bootstrap resample WITH replacement from the
meeting's own n values, jackknife acceleration on the meeting's n values).
This is the "bootstrap of the bootstrap" / "double bootstrap" pattern: the
outer resample simulates the data-collection process, the inner bootstrap
simulates the CI-construction process.

RQ64's extrapolated bootstrap is the *limit* of this procedure as M -> 1 with
theta_hat fixed to the population mean. RQ68 relaxes that limit: theta_hat
varies per meeting (sample mean), and we average over many meetings.

Hypotheses
----------
- H68a: Simulated n=105 lang-id BCa CI (primary meeting, seed=42) excludes
  oracle. KILL if includes oracle.
- H68b: Simulated n=250 KL BCa CI (primary meeting, seed=42) excludes oracle.
  KILL if includes oracle.
- H68c: Power curve reaches 80% at n <= 770 (RQ64's extrapolated ceiling).
  KILL if n* > 770.

REANALYSIS ONLY - no Whisper / no ASR / no LLM / no ollama. Pure numpy + scipy
+ stdlib. The corrected router's per-window cpWER is the stored word-level
``always_mixed_cpwer`` / ``always_separated_cpwer`` (matches RQ16 bit-for-bit).
The KL router's per-window cpWER is read from RQ58's results JSON (no KL
recompute, no LLM).

Label: experimental/frontier. Closes #996.

Run:
    /opt/homebrew/bin/python3 results/frontier/multi_meeting_power_simulation/analysis.py
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
SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
KL_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "kl_corrected_router"
    / "kl_corrected_router_results.json"
)
OUT_DIR = Path(__file__).resolve().parent
OUT_CSV = OUT_DIR / "multi_meeting_power_results.csv"
OUT_JSON = OUT_DIR / "multi_meeting_power_results.json"

# ------------------------------------------------------------------ thresholds
# RQ55 task spec: lang-id entropy threshold 0.38. Verified to give identical
# routing to RQ13's 0.409 operating point on AISHELL-4 (no window has entropy
# in (0.38, 0.409]), so the per-window decisions match RQ16/RQ39/RQ55.
LANG_ID_ENTROPY_THRESHOLD = 0.38

# Primary (headline) inner bootstrap - matches RQ64's B=10000, seed=42 spec.
PRIMARY_N_BOOT = 10000
PRIMARY_BOOT_SEED = 42
PRIMARY_MEETING_SEED = 42

# Power-curve inner bootstrap. M=200 meetings x B=2000 inner is tractable
# (each meeting's inner bootstrap is ~20 ms at n=1000) and gives power
# resolution of ~3.5 percentage points (binomial SE at p=0.5, M=200).
POWER_N_MEETINGS = 200
POWER_N_BOOT = 2000
POWER_BASE_SEED = 42

ALPHA = 0.05
EPS = 1e-9

# RQ39 / RQ55 / RQ58 reference values (for reproducibility checks at n=77).
RQ39_WORD_BCA_CI = (1.012987, 1.097403)
RQ39_WORD_CORRECTED_CPWER = 1.04329
RQ39_WORD_ORACLE_CPWER = 1.017316
RQ39_WORD_PERCENTILE_CI = (1.008658, 1.088745)
RQ58_KL_CPWER = 1.030303
RQ58_KL_BCA_CI = (1.006494, 1.077922)
RQ58_KL_PERCENTILE_CI = (1.004329, 1.0671)
RQ58_KL_THRESHOLD = 5.418144

# RQ64's extrapolated-bootstrap predictions (for comparison).
RQ64_LANG_ID_MIN_N = 105
RQ64_KL_MIN_N = 250
RQ64_TRACTABLE_CEILING = 770

# Multi-meeting grid: includes the pre-registered H68a/H68b points (105, 250),
# the RQ64 tractable ceiling (770), and intermediate points to pin down the
# power curve. n=77 is the baseline (must reproduce RQ39/RQ58 "includes oracle").
N_GRID = [77, 105, 154, 250, 308, 500, 616, 770, 1000]

# H68c: power reaches 80% at n <= 770. KILLED if n* > 770.
H68C_POWER_TARGET = 0.80
H68C_TRACTABLE_CEILING = 770


# ===========================================================================
# Part 1: detector primitives (lifted VERBATIM from RQ13/RQ16/RQ55/RQ64)
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

    Same convention as RQ12/RQ13/RQ16/RQ55/RQ64: a window is flagged if ANY
    speaker track trips the detector. Empty/whitespace speaker texts
    contribute nothing.
    """
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def corrected_router_decision(window: dict[str, Any]) -> str:
    """RQ68 corrected-router decision using lang-id entropy alone (threshold 0.38).

    Route to MIXED if ``max_across_speakers(separated, language_id_entropy) >
    0.38`` bits, else SEPARATED. RQ55 verified this gives identical routing to
    RQ13's 0.409 operating point on AISHELL-4 (no window has entropy in
    (0.38, 0.409]), so the per-window cpWER matches RQ16/RQ39 bit-for-bit.
    """
    ent = max_across_speakers(window, language_id_entropy)
    return "mixed" if ent > LANG_ID_ENTROPY_THRESHOLD else "separated"


# ===========================================================================
# Part 2: bootstrap + BCa CI helpers (lifted VERBATIM from RQ39/RQ64, PURE)
# ===========================================================================

def bootstrap_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``(n_boot, n)`` int array of resample indices (with replacement).

    Same convention as RQ16/RQ39/RQ55/RQ64: ``rng.integers(0, n, size=n)`` per
    resample. Deterministic for a fixed ``seed``."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(n_boot, n))


def bootstrap_distribution(values: np.ndarray, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``n_boot`` array of bootstrap means of ``values`` (standard
    bootstrap at the original sample size).

    Resamples ``values`` with replacement (``n`` indices per resample, n =
    len(values)) and takes the mean. Deterministic for a fixed ``seed``.
    At n=77 this reproduces RQ39's ``bootstrap_distribution`` bit-for-bit.
    """
    values = np.asarray(values, dtype=float)
    n = len(values)
    idx = bootstrap_indices(n, n_boot, seed)
    return values[idx].mean(axis=1)


def percentile_ci(boot_dist: np.ndarray, alpha: float = ALPHA) -> tuple[float, float]:
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
    values: np.ndarray, boot_dist: np.ndarray, alpha: float = ALPHA
) -> tuple[float, float]:
    """BCa (bias-corrected + accelerated) CI for the mean of ``values``.

    Standard Efron & Tibshirani BCa formula (lifted verbatim from RQ39/RQ64):
      * ``z0 = Phi^-1(P(boot < theta_hat))`` -- bias correction
      * ``a`` via jackknife: ``a = sum((theta_bar - theta_i)^3) /
        (6 * (sum((theta_bar - theta_i)^2))^1.5)``
      * BCa alphas:
          ``alpha1 = Phi(z0 + (z0 + z_{alpha/2}) / (1 - a*(z0 + z_{alpha/2})))``
          ``alpha2 = Phi(z0 + (z0 + z_{1-alpha/2}) / (1 - a*(z0 + z_{1-alpha/2})))``
      * BCa CI = ``(percentile(boot, 100*alpha1), percentile(boot, 100*alpha2))``

    Edge cases (constant data, zero denominator, ``P(boot < theta_hat)`` of 0/1)
    are handled by clipping to a small epsilon and falling back to the
    percentile CI when the acceleration is undefined.

    For RQ68's multi-meeting simulation: pass ``values`` = the simulated
    meeting's n data points (so theta_hat = the meeting's sample mean,
    jackknife `a` = meeting's skewness) and ``boot_dist`` = the inner bootstrap
    distribution of size n_boot. This is the standard BCa CI a researcher
    would compute on a freshly collected n-window meeting.
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


# ===========================================================================
# Part 3: multi-meeting simulation (NEW - RQ68)
# ===========================================================================

def draw_meeting(
    population: np.ndarray, n_target: int, meeting_seed: int
) -> np.ndarray:
    """Draw ONE synthetic meeting of size ``n_target`` from ``population`` F_hat.

    Resamples WITH replacement from the 77 per-window cpWER values, treating
    each resample as a "new meeting window." This is the outer resample of the
    multi-meeting simulation. Deterministic for a fixed ``meeting_seed``.

    Returns an ``n_target``-length float array -- the simulated meeting's data.
    """
    population = np.asarray(population, dtype=float)
    if n_target < 1:
        raise ValueError(
            f"draw_meeting: n_target must be >= 1, got {n_target}"
        )
    rng = np.random.default_rng(meeting_seed)
    idx = rng.integers(0, len(population), size=n_target)
    return population[idx]


def meeting_bca_ci(
    meeting: np.ndarray,
    n_boot: int,
    boot_seed: int,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    """Compute the standard BCa CI on a simulated meeting's data.

    Treats ``meeting`` (n values) as the sample. theta_hat = meeting's sample
    mean; jackknife `a` from the meeting's n values; bootstrap distribution =
    means of ``n_boot`` resamples of size n from the meeting's data. This is
    the standard RQ39 BCa CI procedure a researcher would run on a freshly
    collected n-window meeting.

    Returns a dict with: ``meeting_mean`` (theta_hat), ``bca_ci`` (lo, hi),
    ``pct_ci`` (lo, hi), ``bca_width``, ``pct_width``.
    """
    meeting = np.asarray(meeting, dtype=float)
    n = len(meeting)
    if n < 2:
        theta = float(meeting.mean()) if n == 1 else float("nan")
        return {
            "meeting_mean": theta,
            "bca_ci": (theta, theta),
            "pct_ci": (theta, theta),
            "bca_width": 0.0,
            "pct_width": 0.0,
        }
    boot_dist = bootstrap_distribution(meeting, n_boot, boot_seed)
    pct_lo, pct_hi = percentile_ci(boot_dist, alpha)
    bca_lo, bca_hi = bca_ci(meeting, boot_dist, alpha)
    return {
        "meeting_mean": float(meeting.mean()),
        "bca_ci": (bca_lo, bca_hi),
        "pct_ci": (pct_lo, pct_hi),
        "bca_width": bca_hi - bca_lo,
        "pct_width": pct_hi - pct_lo,
    }


def primary_meeting_bca_at_n(
    population: np.ndarray,
    n_target: int,
    n_boot: int = PRIMARY_N_BOOT,
    meeting_seed: int = PRIMARY_MEETING_SEED,
    boot_seed: int = PRIMARY_BOOT_SEED,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    """Headline BCa CI for ONE primary simulated meeting at size ``n_target``.

    Uses the pre-registered meeting_seed=42 / boot_seed=42 / B=10000 (matches
    RQ64's spec). Returns the dict from ``meeting_bca_ci`` plus ``n`` and the
    population reference values for context.
    """
    population = np.asarray(population, dtype=float)
    meeting = draw_meeting(population, n_target, meeting_seed)
    res = meeting_bca_ci(meeting, n_boot, boot_seed, alpha)
    res["n"] = int(n_target)
    res["population_mean"] = float(population.mean())
    res["meeting_size"] = int(n_target)
    return res


def power_at_n(
    population: np.ndarray,
    n_target: int,
    oracle: float,
    n_meetings: int = POWER_N_MEETINGS,
    n_boot: int = POWER_N_BOOT,
    base_seed: int = POWER_BASE_SEED,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    """Simulated power at sample size ``n_target``.

    Power = fraction of ``n_meetings`` simulated meetings whose BCa CI lower
    bound exceeds ``oracle`` (i.e., the BCa CI EXCLUDES the oracle).

    Each meeting i (0-indexed) uses:
      * meeting_seed = base_seed + i  (draws the synthetic meeting from F_hat)
      * boot_seed    = base_seed + i + n_meetings  (inner bootstrap on the
        meeting's data)

    This pairing makes the power-curve reproducible: meeting i at any n uses
    the same meeting_seed stream, so the only thing that changes with n is the
    meeting's size. Returns a dict with: ``n``, ``n_meetings``, ``power``,
    ``excludes_count``, ``median_bca_ci``, ``mean_bca_lo``, ``mean_bca_hi``,
    ``mean_meeting_mean``, and per-meeting summaries (truncated for the JSON).
    """
    population = np.asarray(population, dtype=float)
    if n_target < 2:
        raise ValueError(
            f"power_at_n: n_target must be >= 2 for BCa CI, got {n_target}"
        )
    if n_meetings < 1:
        raise ValueError(
            f"power_at_n: n_meetings must be >= 1, got {n_meetings}"
        )

    per_meeting_lo: list[float] = []
    per_meeting_hi: list[float] = []
    per_meeting_mean: list[float] = []
    excludes_count = 0
    for i in range(n_meetings):
        meeting_seed = base_seed + i
        boot_seed = base_seed + i + n_meetings
        meeting = draw_meeting(population, n_target, meeting_seed)
        r = meeting_bca_ci(meeting, n_boot, boot_seed, alpha)
        lo, hi = r["bca_ci"]
        per_meeting_lo.append(lo)
        per_meeting_hi.append(hi)
        per_meeting_mean.append(r["meeting_mean"])
        if lo > oracle:
            excludes_count += 1

    power = excludes_count / n_meetings
    arr_lo = np.array(per_meeting_lo, dtype=float)
    arr_hi = np.array(per_meeting_hi, dtype=float)
    arr_mean = np.array(per_meeting_mean, dtype=float)

    # Median BCa CI (the "typical" meeting's CI)
    median_lo = float(np.median(arr_lo))
    median_hi = float(np.median(arr_hi))

    return {
        "n": int(n_target),
        "n_meetings": int(n_meetings),
        "n_boot": int(n_boot),
        "power": float(power),
        "excludes_count": int(excludes_count),
        "oracle_point": float(oracle),
        "median_bca_ci_lo": median_lo,
        "median_bca_ci_hi": median_hi,
        "median_bca_excludes_oracle": bool(median_lo > oracle),
        "mean_bca_lo": float(arr_lo.mean()),
        "mean_bca_hi": float(arr_hi.mean()),
        "mean_meeting_mean": float(arr_mean.mean()),
        "std_meeting_mean": float(arr_mean.std()),
        # Keep the per-meeting arrays for downstream diagnostics but truncate
        # to the first 20 in the JSON to keep file size bounded.
        "per_meeting_bca_lo_first20": [float(x) for x in arr_lo[:20]],
        "per_meeting_bca_hi_first20": [float(x) for x in arr_hi[:20]],
        "per_meeting_mean_first20": [float(x) for x in arr_mean[:20]],
    }


def find_n_star_for_power(
    power_curve: list[dict[str, Any]],
    target: float = H68C_POWER_TARGET,
) -> int | None:
    """Find the minimum n where power >= ``target`` (linear interpolation).

    Walks the power curve (sorted by n) and linearly interpolates between
    adjacent grid points to find the n at which power crosses ``target``.
    Returns the interpolated n rounded UP to the nearest integer (conservative
    -- the smallest n that is *guaranteed* to meet target), or ``None`` if
    power never reaches ``target`` within the grid.
    """
    pts = sorted(power_curve, key=lambda r: r["n"])
    for i in range(len(pts) - 1):
        n_lo, n_hi = pts[i]["n"], pts[i + 1]["n"]
        p_lo, p_hi = pts[i]["power"], pts[i + 1]["power"]
        if p_lo >= target:
            return int(n_lo)
        if p_lo < target <= p_hi:
            # Linear interpolation: n* = n_lo + (target - p_lo) / (p_hi - p_lo) * (n_hi - n_lo)
            if p_hi <= p_lo:
                return int(n_hi)
            frac = (target - p_lo) / (p_hi - p_lo)
            n_star = n_lo + frac * (n_hi - n_lo)
            return int(math.ceil(n_star))
    if pts and pts[-1]["power"] >= target:
        return int(pts[-1]["n"])
    return None


def ci_includes_value(ci: tuple[float, float], value: float) -> bool:
    """True if ``value`` is inside the CI [lo, hi] (inclusive).

    Pure helper for the H68a/H68b headline check. ``ci`` = (lo, hi)."""
    lo, hi = ci
    return lo <= value <= hi


def compute_effect_size(corrected_mean: float, oracle_mean: float) -> float:
    """Effect size = corrected cpWER - oracle cpWER (point estimate).

    Positive = corrected router is worse than oracle (the typical case). If
    < 0.01 the gap is "practically negligible"; if >= 0.01 the gap is real.
    """
    return float(corrected_mean - oracle_mean)


# ===========================================================================
# Part 4: driver
# ===========================================================================

def _round6(x: float) -> float:
    return round(float(x), 6)


def _ci_pair(ci: tuple[float, float]) -> list[float]:
    return [_round6(ci[0]), _round6(ci[1])]


def _load_corrected_per_window(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Compute per-window corrected cpWER + oracle cpWER for the lang-id
    corrected router (threshold 0.38).

    Returns a list of 77 dicts with window_id, lang_id_entropy,
    corrected_decision, corrected_cpwer, oracle_cpwer, always_mixed_cpwer,
    always_separated_cpwer. The corrected cpWER reproduces RQ16/RQ39's 1.04329
    bit-for-bit (lang-id alone, threshold 0.38 == 0.409 on this dataset).
    """
    rows: list[dict[str, Any]] = []
    for w in data["windows"]:
        ent = max_across_speakers(w, language_id_entropy)
        decision = "mixed" if ent > LANG_ID_ENTROPY_THRESHOLD else "separated"
        mixed_cpwer = float(w["always_mixed_cpwer"])
        sep_cpwer = float(w["always_separated_cpwer"])
        corrected = mixed_cpwer if decision == "mixed" else sep_cpwer
        rows.append({
            "window_id": w["window_id"],
            "overlap_label": w["overlap_label"],
            "num_speakers": w["num_speakers"],
            "lang_id_entropy": round(ent, 6),
            "corrected_decision": decision,
            "always_mixed_cpwer": _round6(mixed_cpwer),
            "always_separated_cpwer": _round6(sep_cpwer),
            "oracle_best_cpwer": _round6(float(w["oracle_best_cpwer"])),
            "corrected_cpwer": _round6(corrected),
        })
    return rows


def _load_kl_per_window() -> list[dict[str, Any]] | None:
    """Load the KL-corrected router's per-window cpWER from RQ58's results JSON.

    Returns a list of 77 dicts with window_id, kl_decision, kl_cpwer,
    oracle_best_cpwer, kl_score, kl_flag; or None if RQ58's JSON is missing
    (the KL analysis is secondary and gracefully skipped if unavailable).

    Pure reanalysis: reads RQ58's committed JSON, does NOT recompute the KL
    detector (no LLM, no ollama, no src.llm_semantic_critic import).
    """
    if not KL_JSON.exists():
        return None
    kl_data = json.loads(KL_JSON.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for r in kl_data.get("per_window", []):
        rows.append({
            "window_id": r["window_id"],
            "kl_decision": r["kl_decision"],
            "kl_score": r["kl_score"],
            "kl_flag": r["kl_flag"],
            "always_mixed_cpwer": r["always_mixed_cpwer"],
            "always_separated_cpwer": r["always_separated_cpwer"],
            "oracle_best_cpwer": r["oracle_best_cpwer"],
            "kl_cpwer": r["kl_cpwer"],
        })
    return rows


def _run_multi_meeting_analysis(
    name: str,
    per_window_cpwer: np.ndarray,
    oracle_point: float,
    n_grid: list[int],
    rq64_min_n: int,
) -> dict[str, Any]:
    """Run the full multi-meeting power simulation for one router.

    Returns a dict with: name, n_population, theta_hat (population mean),
    oracle_point, effect_size, baseline (n=77 BCa CI reproducing RQ39/RQ58),
    per_n (list of per-n primary meeting BCa CI + power-curve result),
    n_star_80pct (H68c), hypothesis verdicts.
    """
    per_window_cpwer = np.asarray(per_window_cpwer, dtype=float)
    n_pop = len(per_window_cpwer)
    theta_hat = float(per_window_cpwer.mean())
    effect_size = compute_effect_size(theta_hat, oracle_point)

    # --- baseline (n=77): standard bootstrap on the 77 values, reproduces
    #     RQ39's BCa CI [1.012987, 1.097403] for lang-id and RQ58's
    #     [1.006494, 1.077922] for KL.
    baseline_boot = bootstrap_distribution(per_window_cpwer, PRIMARY_N_BOOT, PRIMARY_BOOT_SEED)
    baseline_pct_ci = percentile_ci(baseline_boot, ALPHA)
    baseline_bca_ci = bca_ci(per_window_cpwer, baseline_boot, ALPHA)
    baseline_includes_oracle = ci_includes_value(baseline_bca_ci, oracle_point)

    # --- per-n primary meeting + power curve
    per_n: list[dict[str, Any]] = []
    power_curve: list[dict[str, Any]] = []
    for n in n_grid:
        primary = primary_meeting_bca_at_n(
            per_window_cpwer, n,
            n_boot=PRIMARY_N_BOOT,
            meeting_seed=PRIMARY_MEETING_SEED,
            boot_seed=PRIMARY_BOOT_SEED,
        )
        primary_bca = primary["bca_ci"]
        primary_excludes = primary_bca[0] > oracle_point

        pw = power_at_n(
            per_window_cpwer, n, oracle_point,
            n_meetings=POWER_N_MEETINGS,
            n_boot=POWER_N_BOOT,
            base_seed=POWER_BASE_SEED,
        )
        power_curve.append(pw)

        per_n.append({
            "n": int(n),
            "primary_meeting_mean": _round6(primary["meeting_mean"]),
            "primary_bca_ci": _ci_pair(primary_bca),
            "primary_pct_ci": _ci_pair(primary["pct_ci"]),
            "primary_bca_width": _round6(primary["bca_width"]),
            "primary_bca_excludes_oracle": bool(primary_excludes),
            "oracle_inside_primary_bca_ci": bool(
                primary_bca[0] <= oracle_point <= primary_bca[1]
            ),
            "power": _round6(pw["power"]),
            "power_excludes_count": pw["excludes_count"],
            "power_n_meetings": pw["n_meetings"],
            "power_n_boot": pw["n_boot"],
            "median_bca_ci": [_round6(pw["median_bca_ci_lo"]), _round6(pw["median_bca_ci_hi"])],
            "median_bca_excludes_oracle": bool(pw["median_bca_ci_lo"] > oracle_point),
            "mean_bca_ci": [_round6(pw["mean_bca_lo"]), _round6(pw["mean_bca_hi"])],
            "mean_meeting_mean": _round6(pw["mean_meeting_mean"]),
            "std_meeting_mean": _round6(pw["std_meeting_mean"]),
        })

    # --- n* where power crosses 80%
    n_star = find_n_star_for_power(power_curve, H68C_POWER_TARGET)

    # --- H68a/H68b: primary meeting BCa CI at the RQ64-predicted n
    #     (n=105 for lang-id, n=250 for KL) excludes oracle.
    rq64_n_row = next((r for r in per_n if r["n"] == rq64_min_n), None)
    if rq64_n_row is None:
        h68_verdict_supported = False
        h68_reason = f"n={rq64_min_n} not in grid"
    else:
        h68_verdict_supported = bool(rq64_n_row["primary_bca_excludes_oracle"])
        h68_reason = (
            f"Primary simulated BCa CI at n={rq64_min_n}: "
            f"{rq64_n_row['primary_bca_ci']}, oracle={_round6(oracle_point)}. "
            f"{'Excludes (SUPPORTED)' if h68_verdict_supported else 'Includes (KILLED)'}."
        )

    # --- H68c: power reaches 80% at n <= 770.
    if n_star is None:
        h68c_supported = False
        h68c_reason = (
            f"Power never reaches {H68C_POWER_TARGET*100:.0f}% within the grid "
            f"(max n={max(n_grid)}). KILLED."
        )
    else:
        h68c_supported = n_star <= H68C_TRACTABLE_CEILING
        h68c_reason = (
            f"Power reaches {H68C_POWER_TARGET*100:.0f}% at n*={n_star} "
            f"({'<=' if h68c_supported else '>'} {H68C_TRACTABLE_CEILING}). "
            f"{'SUPPORTED' if h68c_supported else 'KILLED'}."
        )

    # --- RQ64 prediction comparison
    rq64_compare = {
        "rq64_min_n_to_exclude": rq64_min_n,
        "rq68_primary_meeting_excludes_at_rq64_n": (
            bool(rq64_n_row["primary_bca_excludes_oracle"]) if rq64_n_row else None
        ),
        "rq68_power_at_rq64_n": (
            _round6(rq64_n_row["power"]) if rq64_n_row else None
        ),
        "rq68_n_star_80pct": n_star,
        "rq64_tractable_ceiling": RQ64_TRACTABLE_CEILING,
    }

    return {
        "name": name,
        "n_population": n_pop,
        "theta_hat": _round6(theta_hat),
        "oracle_point": _round6(oracle_point),
        "effect_size": _round6(effect_size),
        "rq64_min_n_prediction": rq64_min_n,
        "baseline_n77": {
            "corrected_cpwer": _round6(theta_hat),
            "oracle_cpwer": _round6(oracle_point),
            "percentile_ci_95": _ci_pair(baseline_pct_ci),
            "bca_ci_95": _ci_pair(baseline_bca_ci),
            "bca_width": _round6(baseline_bca_ci[1] - baseline_bca_ci[0]),
            "oracle_inside_bca_ci": bool(baseline_includes_oracle),
            "bca_lower_above_oracle": bool(baseline_bca_ci[0] > oracle_point),
        },
        "per_n": per_n,
        "n_star_80pct": (int(n_star) if n_star is not None else None),
        "rq64_comparison": rq64_compare,
        "hypothesis_verdicts": {
            "H68": {
                "statement": (
                    f"Simulated n={rq64_min_n} BCa CI (primary meeting, "
                    f"seed=42, B=10000) excludes oracle. KILL if includes."
                ),
                "primary_bca_ci_at_rq64_n": (
                    rq64_n_row["primary_bca_ci"] if rq64_n_row else None
                ),
                "oracle_point": _round6(oracle_point),
                "primary_excludes_oracle": (
                    bool(rq64_n_row["primary_bca_excludes_oracle"]) if rq64_n_row else None
                ),
                "supported": bool(h68_verdict_supported),
                "reason": h68_reason,
            },
            "H68c": {
                "statement": (
                    f"Power curve reaches {H68C_POWER_TARGET*100:.0f}% at n <= "
                    f"{H68C_TRACTABLE_CEILING} (RQ64's extrapolated ceiling). "
                    f"KILL if n* > {H68C_TRACTABLE_CEILING}."
                ),
                "n_star_80pct": (int(n_star) if n_star is not None else None),
                "tractable_ceiling": H68C_TRACTABLE_CEILING,
                "supported": bool(h68c_supported),
                "reason": h68c_reason,
            },
        },
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    n_windows = len(data["windows"])

    # --- lang-id corrected router per-window cpWER (threshold 0.38)
    lang_rows = _load_corrected_per_window(data)
    lang_corr_arr = np.array(
        [r["corrected_cpwer"] for r in lang_rows], dtype=float
    )
    lang_oracle_arr = np.array(
        [r["oracle_best_cpwer"] for r in lang_rows], dtype=float
    )
    lang_oracle_point = float(lang_oracle_arr.mean())

    lang_analysis = _run_multi_meeting_analysis(
        name="lang_id_corrected_router_rq39",
        per_window_cpwer=lang_corr_arr,
        oracle_point=lang_oracle_point,
        n_grid=N_GRID,
        rq64_min_n=RQ64_LANG_ID_MIN_N,
    )

    # --- KL-corrected router per-window cpWER (from RQ58's JSON)
    kl_rows = _load_kl_per_window()
    if kl_rows is not None:
        kl_corr_arr = np.array(
            [r["kl_cpwer"] for r in kl_rows], dtype=float
        )
        kl_oracle_arr = np.array(
            [r["oracle_best_cpwer"] for r in kl_rows], dtype=float
        )
        kl_oracle_point = float(kl_oracle_arr.mean())
        kl_analysis = _run_multi_meeting_analysis(
            name="kl_corrected_router_rq58",
            per_window_cpwer=kl_corr_arr,
            oracle_point=kl_oracle_point,
            n_grid=N_GRID,
            rq64_min_n=RQ64_KL_MIN_N,
        )
    else:
        kl_analysis = None

    # --- decision counts (sanity: should match RQ39: mixed=38, separated=39)
    lang_decision_counts = {
        "mixed": sum(1 for r in lang_rows if r["corrected_decision"] == "mixed"),
        "separated": sum(1 for r in lang_rows if r["corrected_decision"] == "separated"),
    }

    # --- reproducibility checks against RQ39 / RQ58 at n=77
    lang_baseline = lang_analysis["baseline_n77"]
    rq39_repro = {
        "lang_id_corrected_cpwer": lang_analysis["theta_hat"],
        "rq39_reference_cpwer": RQ39_WORD_CORRECTED_CPWER,
        "lang_id_bca_ci": lang_baseline["bca_ci_95"],
        "rq39_reference_bca_ci": [RQ39_WORD_BCA_CI[0], RQ39_WORD_BCA_CI[1]],
        "lang_id_percentile_ci": lang_baseline["percentile_ci_95"],
        "rq39_reference_percentile_ci": [
            RQ39_WORD_PERCENTILE_CI[0], RQ39_WORD_PERCENTILE_CI[1]
        ],
        "reproduces_rq39_cpwer": abs(
            lang_analysis["theta_hat"] - RQ39_WORD_CORRECTED_CPWER
        ) < 1e-4,
        "reproduces_rq39_bca_ci": (
            abs(lang_baseline["bca_ci_95"][0] - RQ39_WORD_BCA_CI[0]) < 1e-4
            and abs(lang_baseline["bca_ci_95"][1] - RQ39_WORD_BCA_CI[1]) < 1e-4
        ),
    }
    kl_repro = None
    if kl_analysis is not None:
        kl_baseline = kl_analysis["baseline_n77"]
        kl_repro = {
            "kl_corrected_cpwer": kl_analysis["theta_hat"],
            "rq58_reference_cpwer": RQ58_KL_CPWER,
            "kl_bca_ci": kl_baseline["bca_ci_95"],
            "rq58_reference_bca_ci": [RQ58_KL_BCA_CI[0], RQ58_KL_BCA_CI[1]],
            "reproduces_rq58_cpwer": abs(
                kl_analysis["theta_hat"] - RQ58_KL_CPWER
            ) < 1e-4,
            "reproduces_rq58_bca_ci": (
                abs(kl_baseline["bca_ci_95"][0] - RQ58_KL_BCA_CI[0]) < 1e-4
                and abs(kl_baseline["bca_ci_95"][1] - RQ58_KL_BCA_CI[1]) < 1e-4
            ),
        }

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ68: Multi-Meeting Power Simulation for Oracle Exclusion",
        "closes_issue": 996,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "kl_source": str(KL_JSON.relative_to(PROJECT_ROOT)) if KL_JSON.exists() else None,
        "method": (
            "Reanalysis only (no Whisper / no ASR / no LLM). Multi-meeting "
            "simulation: treat the 77 per-window cpWER values as the empirical "
            "population F_hat; for each target n draw M=200 independent "
            "synthetic meetings of size n WITH replacement from F_hat; for each "
            "meeting compute the standard RQ39 BCa CI (B=2000 inner bootstrap, "
            "jackknife acceleration on the meeting's n values). Power = "
            "fraction of M meetings whose BCa CI lower bound exceeds oracle. "
            "Also computes a primary headline BCa CI per n (single meeting, "
            "seed=42, B=10000) for H68a/H68b. At n=77 the baseline reproduces "
            "RQ39's BCa CI [1.012987, 1.097403] bit-for-bit. Two routers "
            "analysed: (1) lang-id corrected (threshold 0.38, RQ39/RQ55, cpWER "
            "1.0433); (2) KL-corrected (RQ58, cpWER 1.0303). RQ64 predicted "
            "n=105 (lang-id) and n=250 (KL) as the minimum n to exclude oracle "
            "via extrapolated bootstrap; RQ68 verifies this under the more "
            "realistic multi-meeting simulation."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n_windows,
        "thresholds": {
            "lang_id_entropy": LANG_ID_ENTROPY_THRESHOLD,
            "note": (
                "lang_id_entropy threshold 0.38 (RQ55 convention). Verified "
                "identical routing to RQ13's 0.409 operating point on AISHELL-4 "
                "(no window has entropy in (0.38, 0.409])."
            ),
            "h68c_power_target": H68C_POWER_TARGET,
            "h68c_tractable_ceiling": H68C_TRACTABLE_CEILING,
            "rq64_tractable_ceiling": RQ64_TRACTABLE_CEILING,
        },
        "simulation": {
            "primary_n_boot": PRIMARY_N_BOOT,
            "primary_meeting_seed": PRIMARY_MEETING_SEED,
            "primary_boot_seed": PRIMARY_BOOT_SEED,
            "power_n_meetings": POWER_N_MEETINGS,
            "power_n_boot": POWER_N_BOOT,
            "power_base_seed": POWER_BASE_SEED,
            "alpha": ALPHA,
            "n_grid": N_GRID,
            "convention": (
                "meeting_seed = base_seed + i; boot_seed = base_seed + i + "
                "n_meetings. Each meeting is a resample of size n WITH "
                "replacement from F_hat (the 77 per-window cpWER values). "
                "BCa CI uses jackknife acceleration on the meeting's n values "
                "(NOT the 77-value population) -- this is the standard BCa CI "
                "a researcher would compute on a freshly collected n-window "
                "meeting."
            ),
        },
        "decision_counts_lang_id": lang_decision_counts,
        "reproducibility_checks": {
            "rq39": rq39_repro,
            "rq58": kl_repro,
        },
        "lang_id_corrected_router": lang_analysis,
        "kl_corrected_router": kl_analysis,
        "per_window_lang_id": lang_rows,
        "per_window_kl": kl_rows,
    }

    # ----------------------------------------------------------- write CSV
    csv_fields = [
        "router", "n",
        "primary_meeting_mean", "primary_bca_ci_lo", "primary_bca_ci_hi",
        "primary_bca_width", "primary_bca_excludes_oracle",
        "oracle_inside_primary_bca_ci",
        "power", "power_excludes_count", "power_n_meetings",
        "median_bca_ci_lo", "median_bca_ci_hi", "median_bca_excludes_oracle",
        "mean_meeting_mean", "std_meeting_mean",
    ]
    csv_rows: list[dict[str, Any]] = []
    for router_name, analysis in [
        ("lang_id_corrected", lang_analysis),
        ("kl_corrected", kl_analysis),
    ]:
        if analysis is None:
            continue
        for r in analysis["per_n"]:
            csv_rows.append({
                "router": router_name,
                "n": r["n"],
                "primary_meeting_mean": r["primary_meeting_mean"],
                "primary_bca_ci_lo": r["primary_bca_ci"][0],
                "primary_bca_ci_hi": r["primary_bca_ci"][1],
                "primary_bca_width": r["primary_bca_width"],
                "primary_bca_excludes_oracle": r["primary_bca_excludes_oracle"],
                "oracle_inside_primary_bca_ci": r["oracle_inside_primary_bca_ci"],
                "power": r["power"],
                "power_excludes_count": r["power_excludes_count"],
                "power_n_meetings": r["power_n_meetings"],
                "median_bca_ci_lo": r["median_bca_ci"][0],
                "median_bca_ci_hi": r["median_bca_ci"][1],
                "median_bca_excludes_oracle": r["median_bca_excludes_oracle"],
                "mean_meeting_mean": r["mean_meeting_mean"],
                "std_meeting_mean": r["std_meeting_mean"],
            })
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in csv_rows:
            wr.writerow(r)

    # ----------------------------------------------------------- write JSON
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- console
    print(f"=== RQ68: Multi-Meeting Power Simulation ({n_windows} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Simulation: M={POWER_N_MEETINGS} meetings per n, B_inner={POWER_N_BOOT}, "
          f"primary B={PRIMARY_N_BOOT} seed=42")
    print(f"Grid: {N_GRID}")
    print()
    print(f"Lang-id corrected router decisions (threshold {LANG_ID_ENTROPY_THRESHOLD}): "
          f"mixed={lang_decision_counts['mixed']}, separated={lang_decision_counts['separated']}")
    print()
    print("--- Reproducibility checks at n=77 ---")
    print(f"  RQ39 cpWER : {lang_analysis['theta_hat']} vs {RQ39_WORD_CORRECTED_CPWER}  "
          f"{'OK' if rq39_repro['reproduces_rq39_cpwer'] else 'MISMATCH'}")
    print(f"  RQ39 BCa CI: {lang_baseline['bca_ci_95']} vs "
          f"[{RQ39_WORD_BCA_CI[0]}, {RQ39_WORD_BCA_CI[1]}]  "
          f"{'OK' if rq39_repro['reproduces_rq39_bca_ci'] else 'MISMATCH'}")
    if kl_repro is not None:
        print(f"  RQ58 cpWER : {kl_analysis['theta_hat']} vs {RQ58_KL_CPWER}  "
              f"{'OK' if kl_repro['reproduces_rq58_cpwer'] else 'MISMATCH'}")
        print(f"  RQ58 BCa CI: {kl_baseline['bca_ci_95']} vs "
              f"[{RQ58_KL_BCA_CI[0]}, {RQ58_KL_BCA_CI[1]}]  "
              f"{'OK' if kl_repro['reproduces_rq58_bca_ci'] else 'MISMATCH'}")
    print()
    for label, analysis, h68_id in [
        ("Lang-id corrected router (RQ39)", lang_analysis, "H68a"),
        ("KL-corrected router (RQ58)", kl_analysis, "H68b"),
    ]:
        if analysis is None:
            print(f"--- {label}: SKIPPED (RQ58 JSON not found) ---")
            continue
        bl = analysis["baseline_n77"]
        h = analysis["hypothesis_verdicts"]
        print(f"--- {label} ---")
        print(f"  point estimate : {analysis['theta_hat']}  |  oracle: {analysis['oracle_point']}  "
              f"|  effect size: {analysis['effect_size']}")
        print(f"  baseline n=77 BCa CI: {bl['bca_ci_95']}  "
              f"(oracle inside: {bl['oracle_inside_bca_ci']})")
        print(f"  {h68_id} (primary meeting at n={analysis['rq64_min_n_prediction']} excludes oracle): "
              f"{'SUPPORTED' if h['H68']['supported'] else 'KILLED'}")
        rq64_row = next(r for r in analysis["per_n"] if r["n"] == analysis["rq64_min_n_prediction"])
        print(f"    primary BCa CI at n={rq64_row['n']}: {rq64_row['primary_bca_ci']}  "
              f"(excludes: {rq64_row['primary_bca_excludes_oracle']}, "
              f"power: {rq64_row['power']:.3f})")
        print(f"  H68c (power >= 80% at n <= {H68C_TRACTABLE_CEILING}): "
              f"{'SUPPORTED' if h['H68c']['supported'] else 'KILLED'}  "
              f"(n* = {analysis['n_star_80pct']})")
        print(f"  Power curve by n:")
        for r in analysis["per_n"]:
            print(f"    n={r['n']:5d}  power={r['power']:.3f}  "
                  f"primary_bca={r['primary_bca_ci']}  "
                  f"primary_excl={r['primary_bca_excludes_oracle']}  "
                  f"median_bca={r['median_bca_ci']}  "
                  f"median_excl={r['median_bca_excludes_oracle']}")
        print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
