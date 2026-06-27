"""RQ64: Retrospective bootstrap power analysis.

RQ39 (word-level) and RQ55 (char-level) both showed the corrected router's BCa
CI INCLUDES the oracle. RQ58 (KL-corrected) also includes oracle. Is this
"includes oracle" verdict a SAMPLE SIZE problem (n=77 is too small to exclude a
small-but-real gap) or a REAL CEILING (the gap is effectively zero)? RQ64
answers via retrospective bootstrap power analysis: at what sample size n would
the BCa CI exclude the oracle?

Method
------
1. Load 77 AISHELL-4 windows. Compute the corrected router's per-window cpWER
   (lang-id entropy threshold 0.38 -> MIXED, else SEPARATED; RQ55 convention,
   verified identical to RQ16's 0.409 on this dataset) and the oracle per-window
   cpWER (stored ``oracle_best_cpwer``). Word-level (utterance-level) cpWER,
   matching RQ16/RQ39 bit-for-bit (1.04329).
2. Baseline (H64a): bootstrap (B=10000, seed=42) the corrected cpWER at n=77.
   Compute BCa CI (RQ39 framework). Confirm it INCLUDES the oracle (1.017316).
   This reproduces RQ39's BCa CI [1.012987, 1.097403] bit-for-bit.
3. Extrapolation (H64b): treat the 77 per-window cpWER values as the empirical
   population F_hat. For each target n in a fine grid (including the task's
   coarse grid {77, 154, 308, 616, 1232, 2464}), draw B=10000 resamples of size
   n WITH replacement from the 77 values, compute the BCa CI. CI width scales as
   ~1/sqrt(n); eventually the lower bound exceeds the oracle.
4. For each n: check if BCa CI lower bound > oracle. Find the minimum n.
5. Effect size (H64c): corrected cpWER - oracle cpWER. If < 0.01, practically
   negligible (real ceiling); if >= 0.01, the gap is real (sample-size problem).
6. Repeat for the KL-corrected router (RQ58, cpWER 1.0303): read RQ58's
   per-window ``kl_cpwer`` from its results JSON and apply the same extrapolated
   bootstrap power analysis. KL's smaller gap (0.013 vs 0.026) should require a
   larger n to exclude the oracle.

Extrapolated bootstrap (the core technique)
-------------------------------------------
The 77 per-window cpWER values are treated as the population F_hat. For a target
sample size n, we draw B resamples of size n WITH replacement from F_hat and
compute the mean of each. This is the "extrapolated bootstrap" (also called the
"bootstrap of the bootstrap" or "two-level bootstrap" in some texts): it
simulates what the bootstrap CI would look like if we had collected n windows
instead of 77, under the assumption that the empirical distribution F_hat is a
good estimate of the true distribution.

The BCa CI at extrapolated n reuses RQ39's ``bca_ci`` verbatim, with:
  * ``theta_hat`` = population mean (mean of 77 values) = the "true" parameter
    under F_hat. Constant across n (the population doesn't change).
  * ``z0`` = Phi^-1(P(boot < theta_hat)) — recomputed per n from the extrapolated
    bootstrap distribution. As n grows, the distribution concentrates around
    theta_hat, so z0 -> 0 (symmetric).
  * ``a`` = jackknife acceleration on the 77-value population. A fixed property
    of F_hat (skewness of the mean estimator); does not change with n.

At n=77 the extrapolated BCa CI = RQ39's BCa CI (H64a reproducibility check).

Hypotheses
----------
- H64a: At n=77, BCa CI includes oracle (baseline confirmation). KILLED if
  already excludes (contradicts RQ39/RQ55/RQ58).
- H64b: Required n to exclude oracle > 770 (10x current). KILLED if <= 770.
- H64c: Effect size (corrected - oracle) < 0.01 (practically negligible).
  KILLED if >= 0.01.

REANALYSIS ONLY — no Whisper / no ASR / no LLM / no ollama. Pure numpy + scipy +
stdlib. The corrected router's per-window cpWER is the stored word-level
``always_mixed_cpwer`` / ``always_separated_cpwer`` (matches RQ16 bit-for-bit).
The KL router's per-window cpWER is read from RQ58's results JSON (no KL
recompute, no LLM).

Label: experimental/frontier. Closes #988.

Run:
    /opt/homebrew/bin/python3 results/frontier/bootstrap_power_analysis/bootstrap_power_analysis.py
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
OUT_CSV = OUT_DIR / "bootstrap_power_results.csv"
OUT_JSON = OUT_DIR / "bootstrap_power_results.json"

# ------------------------------------------------------------------ thresholds
# RQ55 task spec: lang-id entropy threshold 0.38. Verified to give identical
# routing to RQ13's 0.409 operating point on AISHELL-4 (no window has entropy
# in (0.38, 0.409]), so the per-window decisions match RQ16/RQ39/RQ55.
LANG_ID_ENTROPY_THRESHOLD = 0.38
N_BOOT = 10000
SEED = 42
ALPHA = 0.05
EPS = 1e-9

# RQ39 / RQ55 / RQ58 reference values (for reproducibility checks).
RQ39_WORD_BCA_CI = (1.012987, 1.097403)
RQ39_WORD_CORRECTED_CPWER = 1.04329
RQ39_WORD_ORACLE_CPWER = 1.017316
RQ39_WORD_PERCENTILE_CI = (1.008658, 1.088745)
RQ58_KL_CPWER = 1.030303
RQ58_KL_BCA_CI = (1.006494, 1.077922)
RQ58_KL_PERCENTILE_CI = (1.004329, 1.0671)
RQ58_KL_THRESHOLD = 5.418144

# Sample-size grid. The coarse grid is the task's {77, 154, 308, 616, 1232,
# 2464} (1x, 2x, 4x, 8x, 16x, 32x current n). The fine grid adds intermediate
# points to pin down the exact crossing where the BCa CI first excludes the
# oracle. All points are computed for both routers.
N_GRID_COARSE = [77, 154, 308, 616, 1232, 2464]
N_GRID_FINE = [
    77, 80, 85, 90, 95, 100, 105, 110, 120, 130, 140, 154,
    175, 200, 225, 250, 275, 308, 350, 400, 500, 616, 770, 1000, 1232, 2464,
]

# H64b kill threshold: required n <= 770 means the sample size is tractable
# (10x current n). KILLED if required n <= 770.
H64B_TRACTABLE_THRESHOLD = 770

# H64c negligible-effect threshold: effect size < 0.01 means the gap is
# practically negligible (real ceiling). KILLED if effect size >= 0.01.
H64C_NEGLIGIBLE_THRESHOLD = 0.01


# ===========================================================================
# Part 1: detector primitives (lifted VERBATIM from RQ13/RQ16/RQ55)
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

    Same convention as RQ12/RQ13/RQ16/RQ55: a window is flagged if ANY speaker
    track trips the detector. Empty/whitespace speaker texts contribute nothing.
    """
    vals = [
        fn(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


def corrected_router_decision(window: dict[str, Any]) -> str:
    """RQ64 corrected-router decision using lang-id entropy alone (threshold 0.38).

    Route to MIXED if ``max_across_speakers(separated, language_id_entropy) >
    0.38`` bits, else SEPARATED. RQ55 verified this gives identical routing to
    RQ13's 0.409 operating point on AISHELL-4 (no window has entropy in
    (0.38, 0.409]), so the per-window cpWER matches RQ16/RQ39 bit-for-bit.
    """
    ent = max_across_speakers(window, language_id_entropy)
    return "mixed" if ent > LANG_ID_ENTROPY_THRESHOLD else "separated"


# ===========================================================================
# Part 2: bootstrap + BCa CI helpers (lifted VERBATIM from RQ39, PURE)
# ===========================================================================

def bootstrap_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``(n_boot, n)`` int array of resample indices (with replacement).

    Same convention as RQ16/RQ39/RQ55: ``rng.integers(0, n, size=n)`` per
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

    Standard Efron & Tibshirani BCa formula (lifted verbatim from RQ39):
      * ``z0 = Phi^-1(P(boot < theta_hat))`` — bias correction
      * ``a`` via jackknife: ``a = sum((theta_bar - theta_i)^3) /
        (6 * (sum((theta_bar - theta_i)^2))^1.5)``
      * BCa alphas:
          ``alpha1 = Phi(z0 + (z0 + z_{alpha/2}) / (1 - a*(z0 + z_{alpha/2})))``
          ``alpha2 = Phi(z0 + (z0 + z_{1-alpha/2}) / (1 - a*(z0 + z_{1-alpha/2})))``
      * BCa CI = ``(percentile(boot, 100*alpha1), percentile(boot, 100*alpha2))``

    Edge cases (constant data, zero denominator, ``P(boot < theta_hat)`` of 0/1)
    are handled by clipping to a small epsilon and falling back to the
    percentile CI when the acceleration is undefined.

    For RQ64's extrapolated bootstrap: pass ``values`` = the 77-value population
    (so theta_hat = population mean, jackknife `a` = population skewness) and
    ``boot_dist`` = the extrapolated bootstrap distribution at size n. At n=77
    this reproduces RQ39's BCa CI bit-for-bit.
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
# Part 3: extrapolated bootstrap (NEW — RQ64)
# ===========================================================================

def extrapolated_bootstrap_distribution(
    population: np.ndarray,
    n_target: int,
    n_boot: int,
    seed: int,
    chunk: int = 500,
) -> np.ndarray:
    """Extrapolated bootstrap distribution of the mean at sample size ``n_target``.

    Treats ``population`` (the 77 per-window cpWER values) as the empirical
    distribution F_hat. Draws ``n_boot`` resamples of size ``n_target`` WITH
    replacement from ``population`` and returns the mean of each resample.

    As ``n_target`` grows, the distribution concentrates around the population
    mean (CI width scales as ~1/sqrt(n_target)). At ``n_target = len(population)``
    this reproduces ``bootstrap_distribution`` bit-for-bit (same RNG stream),
    which is the H64a reproducibility check against RQ39.

    Chunked to bound memory: for large ``n_target`` (e.g. 2464) the full
    ``(n_boot, n_target)`` index array would be ~200 MB; chunking at 500
    resamples keeps peak memory to ``chunk * n_target`` floats (~10 MB).

    Deterministic for a fixed ``seed``. Pure helper — no I/O, no global state.
    """
    population = np.asarray(population, dtype=float)
    n_pop = len(population)
    if n_target < 1:
        raise ValueError(
            f"extrapolated_bootstrap_distribution: n_target must be >= 1, got {n_target}"
        )
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot, dtype=float)
    for start in range(0, n_boot, chunk):
        end = min(start + chunk, n_boot)
        idx = rng.integers(0, n_pop, size=(end - start, n_target))
        out[start:end] = population[idx].mean(axis=1)
    return out


def extrapolated_bca_at_n(
    population: np.ndarray,
    n_target: int,
    n_boot: int,
    seed: int,
    alpha: float = ALPHA,
    chunk: int = 500,
) -> dict[str, Any]:
    """Compute the extrapolated BCa CI at sample size ``n_target``.

    Returns a dict with: ``n``, ``theta_hat`` (population mean), ``boot_mean``,
    ``boot_std``, ``pct_ci`` (lo, hi), ``bca_ci`` (lo, hi), ``bca_width``,
    ``pct_width``.

    The BCa CI reuses RQ39's ``bca_ci`` verbatim with ``values`` = population
    (theta_hat = population mean, jackknife `a` = population skewness) and
    ``boot_dist`` = the extrapolated bootstrap distribution at size n. At
    n_target = len(population) this reproduces RQ39's BCa CI bit-for-bit.
    """
    population = np.asarray(population, dtype=float)
    boot_dist = extrapolated_bootstrap_distribution(
        population, n_target, n_boot, seed, chunk=chunk
    )
    theta_hat = float(population.mean())
    pct_lo, pct_hi = percentile_ci(boot_dist, alpha)
    bca_lo, bca_hi = bca_ci(population, boot_dist, alpha)
    return {
        "n": int(n_target),
        "theta_hat": theta_hat,
        "boot_mean": float(boot_dist.mean()),
        "boot_std": float(boot_dist.std()),
        "pct_ci_lo": pct_lo,
        "pct_ci_hi": pct_hi,
        "bca_ci_lo": bca_lo,
        "bca_ci_hi": bca_hi,
        "bca_width": bca_hi - bca_lo,
        "pct_width": pct_hi - pct_lo,
    }


def find_min_n_to_exclude(
    population: np.ndarray,
    oracle: float,
    n_list: list[int],
    n_boot: int,
    seed: int,
    alpha: float = ALPHA,
    chunk: int = 500,
) -> int | None:
    """Find the minimum n in ``n_list`` where the BCa CI lower bound > oracle.

    The BCa CI "excludes the oracle" when the lower bound is strictly above the
    oracle point estimate (the corrected router cannot beat the oracle, so the
    relevant exclusion direction is lower bound > oracle).

    Returns the minimum such n, or ``None`` if no n in the list excludes the
    oracle. ``n_list`` is searched in ascending order; the first n that
    excludes is returned (the BCa CI is monotonic in n in practice — once it
    excludes, it stays excluded — but this function returns the FIRST excluding
    n found, not necessarily the globally smallest if the list is unsorted).
    """
    for n in sorted(n_list):
        res = extrapolated_bca_at_n(
            population, n, n_boot, seed, alpha, chunk=chunk
        )
        if res["bca_ci_lo"] > oracle:
            return int(n)
    return None


def compute_effect_size(corrected_mean: float, oracle_mean: float) -> float:
    """Effect size = corrected cpWER - oracle cpWER (point estimate).

    Positive = corrected router is worse than oracle (the typical case). If
    < 0.01 the gap is "practically negligible" (real ceiling); if >= 0.01 the
    gap is real and the "includes oracle" verdict is a sample-size problem.
    """
    return float(corrected_mean - oracle_mean)


def ci_includes_value(ci: tuple[float, float], value: float) -> bool:
    """True if ``value`` is inside the CI [lo, hi] (inclusive).

    Pure helper for the H64a baseline check. ``ci`` = (lo, hi)."""
    lo, hi = ci
    return lo <= value <= hi


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


def _run_power_analysis(
    name: str,
    per_window_cpwer: np.ndarray,
    oracle_point: float,
    n_grid: list[int],
    n_boot: int = N_BOOT,
    seed: int = SEED,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    """Run the full extrapolated bootstrap power analysis for one router.

    Returns a dict with: name, n_population, theta_hat (point estimate),
    oracle_point, effect_size, baseline (n=77 BCa CI + H64a verdict),
    extrapolation (list of per-n BCa results), min_n_to_exclude (H64b),
    h64c verdict."""
    per_window_cpwer = np.asarray(per_window_cpwer, dtype=float)
    n_pop = len(per_window_cpwer)
    theta_hat = float(per_window_cpwer.mean())
    effect_size = compute_effect_size(theta_hat, oracle_point)

    # --- baseline (n=77): standard bootstrap, must reproduce RQ39 framework
    baseline_boot = bootstrap_distribution(per_window_cpwer, n_boot, seed)
    baseline_pct_ci = percentile_ci(baseline_boot, alpha)
    baseline_bca_ci = bca_ci(per_window_cpwer, baseline_boot, alpha)
    baseline_includes_oracle = ci_includes_value(baseline_bca_ci, oracle_point)

    # --- extrapolation grid
    grid_results: list[dict[str, Any]] = []
    for n in n_grid:
        res = extrapolated_bca_at_n(
            per_window_cpwer, n, n_boot, seed, alpha
        )
        excludes_oracle_bca = res["bca_ci_lo"] > oracle_point
        excludes_oracle_pct = res["pct_ci_lo"] > oracle_point
        grid_results.append({
            "n": res["n"],
            "theta_hat": _round6(res["theta_hat"]),
            "boot_mean": _round6(res["boot_mean"]),
            "boot_std": _round6(res["boot_std"]),
            "pct_ci": _ci_pair((res["pct_ci_lo"], res["pct_ci_hi"])),
            "bca_ci": _ci_pair((res["bca_ci_lo"], res["bca_ci_hi"])),
            "bca_width": _round6(res["bca_width"]),
            "pct_width": _round6(res["pct_width"]),
            "bca_ci_lo": _round6(res["bca_ci_lo"]),
            "bca_ci_hi": _round6(res["bca_ci_hi"]),
            "oracle_point": _round6(oracle_point),
            "excludes_oracle_bca": bool(excludes_oracle_bca),
            "excludes_oracle_pct": bool(excludes_oracle_pct),
            "oracle_inside_bca_ci": bool(
                res["bca_ci_lo"] <= oracle_point <= res["bca_ci_hi"]
            ),
        })

    # --- minimum n to exclude oracle (H64b)
    min_n_to_exclude = find_min_n_to_exclude(
        per_window_cpwer, oracle_point, n_grid, n_boot, seed, alpha
    )

    # --- H64a: baseline (n=77) includes oracle. KILLED if already excludes.
    h64a_supported = baseline_includes_oracle  # SUPPORTED = includes (baseline confirmed)

    # --- H64b: required n > 770. KILLED if <= 770 (tractable).
    if min_n_to_exclude is None:
        h64b_supported = True  # never excludes even at max n -> real ceiling
        h64b_verdict = "never_excludes_within_grid"
    else:
        h64b_supported = min_n_to_exclude > H64B_TRACTABLE_THRESHOLD
        h64b_verdict = (
            f"excludes_at_n={min_n_to_exclude}"
        )

    # --- H64c: effect size < 0.01. KILLED if >= 0.01.
    h64c_supported = effect_size < H64C_NEGLIGIBLE_THRESHOLD

    # --- overall verdict: sample-size problem vs real ceiling
    # Sample-size problem: effect size >= 0.01 (gap is real) AND min_n is finite
    #   (more data would exclude the oracle).
    # Real ceiling: effect size < 0.01 (gap negligible) OR min_n is None
    #   (CI never excludes oracle regardless of n).
    if h64c_supported:
        overall_verdict = "real_ceiling"
        verdict_reason = (
            f"Effect size {effect_size:.6f} < {H64C_NEGLIGIBLE_THRESHOLD} "
            f"(practically negligible): the gap is effectively zero regardless "
            f"of n. Real ceiling."
        )
    elif min_n_to_exclude is None:
        overall_verdict = "real_ceiling"
        verdict_reason = (
            f"Effect size {effect_size:.6f} >= {H64C_NEGLIGIBLE_THRESHOLD} but "
            f"BCa CI never excludes oracle within the grid (max n="
            f"{max(n_grid)}). Cannot resolve with more data in the tested range."
        )
    else:
        overall_verdict = "sample_size_problem"
        verdict_reason = (
            f"Effect size {effect_size:.6f} >= {H64C_NEGLIGIBLE_THRESHOLD} "
            f"(gap is real) and BCa CI excludes oracle at n={min_n_to_exclude} "
            f"(<= {max(n_grid)}). More data would resolve the 'includes oracle' "
            f"verdict. Sample-size problem."
        )

    return {
        "name": name,
        "n_population": n_pop,
        "theta_hat": _round6(theta_hat),
        "oracle_point": _round6(oracle_point),
        "effect_size": _round6(effect_size),
        "baseline_n77": {
            "corrected_cpwer": _round6(theta_hat),
            "oracle_cpwer": _round6(oracle_point),
            "percentile_ci_95": _ci_pair(baseline_pct_ci),
            "bca_ci_95": _ci_pair(baseline_bca_ci),
            "bca_width": _round6(baseline_bca_ci[1] - baseline_bca_ci[0]),
            "oracle_inside_bca_ci": bool(baseline_includes_oracle),
            "bca_lower_above_oracle": bool(baseline_bca_ci[0] > oracle_point),
        },
        "extrapolation_grid": grid_results,
        "min_n_to_exclude_oracle_bca": (
            int(min_n_to_exclude) if min_n_to_exclude is not None else None
        ),
        "hypothesis_verdicts": {
            "H64a": {
                "statement": (
                    "At n=77, BCa CI includes oracle (baseline confirmation). "
                    "KILLED if already excludes."
                ),
                "bca_ci_95": _ci_pair(baseline_bca_ci),
                "oracle_point": _round6(oracle_point),
                "oracle_inside_ci": bool(baseline_includes_oracle),
                "supported": bool(h64a_supported),
                "reason": (
                    f"BCa CI {baseline_bca_ci} "
                    f"{'includes' if baseline_includes_oracle else 'excludes'} "
                    f"oracle {oracle_point:.6f}."
                ),
            },
            "H64b": {
                "statement": (
                    f"Required n to exclude oracle > {H64B_TRACTABLE_THRESHOLD} "
                    f"(10x current). KILLED if <= {H64B_TRACTABLE_THRESHOLD}."
                ),
                "min_n_to_exclude": (
                    int(min_n_to_exclude) if min_n_to_exclude is not None else None
                ),
                "tractable_threshold": H64B_TRACTABLE_THRESHOLD,
                "supported": bool(h64b_supported),
                "verdict": h64b_verdict,
                "reason": (
                    f"BCa CI first excludes oracle at n={min_n_to_exclude}. "
                    f"{'>' if h64b_supported else '<='} "
                    f"{H64B_TRACTABLE_THRESHOLD} -> "
                    f"{'tractable (KILLED)' if not h64b_supported else 'intractable (SUPPORTED)'}."
                ),
            },
            "H64c": {
                "statement": (
                    f"Effect size (corrected - oracle) < {H64C_NEGLIGIBLE_THRESHOLD} "
                    f"(practically negligible). KILLED if >= {H64C_NEGLIGIBLE_THRESHOLD}."
                ),
                "effect_size": _round6(effect_size),
                "negligible_threshold": H64C_NEGLIGIBLE_THRESHOLD,
                "supported": bool(h64c_supported),
                "reason": (
                    f"Effect size {effect_size:.6f} "
                    f"{'<' if h64c_supported else '>='} "
                    f"{H64C_NEGLIGIBLE_THRESHOLD} -> "
                    f"{'negligible (SUPPORTED)' if h64c_supported else 'real gap (KILLED)'}."
                ),
            },
        },
        "overall_verdict": overall_verdict,
        "verdict_reason": verdict_reason,
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

    lang_analysis = _run_power_analysis(
        name="lang_id_corrected_router_rq39",
        per_window_cpwer=lang_corr_arr,
        oracle_point=lang_oracle_point,
        n_grid=N_GRID_FINE,
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
        kl_analysis = _run_power_analysis(
            name="kl_corrected_router_rq58",
            per_window_cpwer=kl_corr_arr,
            oracle_point=kl_oracle_point,
            n_grid=N_GRID_FINE,
        )
    else:
        kl_analysis = None

    # --- decision counts (sanity: should match RQ39: mixed=38, separated=39)
    lang_decision_counts = {
        "mixed": sum(1 for r in lang_rows if r["corrected_decision"] == "mixed"),
        "separated": sum(1 for r in lang_rows if r["corrected_decision"] == "separated"),
    }

    # --- reproducibility checks against RQ39 / RQ58
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
        "rq": "RQ64: Retrospective bootstrap power analysis",
        "closes_issue": 988,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "kl_source": str(KL_JSON.relative_to(PROJECT_ROOT)) if KL_JSON.exists() else None,
        "method": (
            "Reanalysis only (no Whisper / no ASR / no LLM). Extrapolated "
            "bootstrap: treat the 77 per-window cpWER values as the empirical "
            "population F_hat; for each target n draw B=10000 resamples of size "
            "n WITH replacement from F_hat and compute the BCa CI (RQ39 "
            "framework, jackknife acceleration on the 77-value population). CI "
            "width scales as ~1/sqrt(n). At n=77 the extrapolated BCa "
            "reproduces RQ39's BCa CI [1.012987, 1.097403] bit-for-bit (H64a "
            "reproducibility check). Two routers analysed: (1) lang-id corrected "
            "router (threshold 0.38, RQ39/RQ55, cpWER 1.0433); (2) KL-corrected "
            "router (RQ58, cpWER 1.0303, per-window data read from RQ58's JSON)."
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
            "h64b_tractable_threshold": H64B_TRACTABLE_THRESHOLD,
            "h64c_negligible_threshold": H64C_NEGLIGIBLE_THRESHOLD,
        },
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "alpha": ALPHA,
            "convention": "rng.integers(0, n_pop, size=n_target) per resample (RQ39 verbatim, chunked)",
            "n_grid_coarse": N_GRID_COARSE,
            "n_grid_fine": N_GRID_FINE,
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
    # One row per (router, n) with the BCa CI and exclusion verdict.
    csv_fields = [
        "router", "n", "theta_hat", "oracle_point", "effect_size",
        "bca_ci_lo", "bca_ci_hi", "bca_width",
        "pct_ci_lo", "pct_ci_hi", "pct_width",
        "bca_lower_above_oracle", "oracle_inside_bca_ci",
    ]
    csv_rows: list[dict[str, Any]] = []
    for router_name, analysis in [
        ("lang_id_corrected", lang_analysis),
        ("kl_corrected", kl_analysis),
    ]:
        if analysis is None:
            continue
        for res in analysis["extrapolation_grid"]:
            csv_rows.append({
                "router": router_name,
                "n": res["n"],
                "theta_hat": res["theta_hat"],
                "oracle_point": res["oracle_point"],
                "effect_size": analysis["effect_size"],
                "bca_ci_lo": res["bca_ci"][0],
                "bca_ci_hi": res["bca_ci"][1],
                "bca_width": res["bca_width"],
                "pct_ci_lo": res["pct_ci"][0],
                "pct_ci_hi": res["pct_ci"][1],
                "pct_width": res["pct_width"],
                "bca_lower_above_oracle": res["excludes_oracle_bca"],
                "oracle_inside_bca_ci": res["oracle_inside_bca_ci"],
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
    print(f"=== RQ64: Retrospective bootstrap power analysis ({n_windows} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Bootstrap: {N_BOOT} resamples, seed={SEED}, alpha={ALPHA}")
    print(f"Grid: {len(N_GRID_FINE)} points (coarse {N_GRID_COARSE} + fine)")
    print()
    print(f"Lang-id corrected router decisions (threshold {LANG_ID_ENTROPY_THRESHOLD}): "
          f"mixed={lang_decision_counts['mixed']}, separated={lang_decision_counts['separated']}")
    print()
    print("--- Reproducibility checks ---")
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
    for label, analysis in [
        ("Lang-id corrected router (RQ39)", lang_analysis),
        ("KL-corrected router (RQ58)", kl_analysis),
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
        print(f"  H64a (n=77 CI includes oracle): "
              f"{'SUPPORTED' if h['H64a']['supported'] else 'KILLED'}")
        print(f"  H64b (required n > {H64B_TRACTABLE_THRESHOLD}): "
              f"{'SUPPORTED' if h['H64b']['supported'] else 'KILLED'}  "
              f"(min n to exclude = {analysis['min_n_to_exclude_oracle_bca']})")
        print(f"  H64c (effect < {H64C_NEGLIGIBLE_THRESHOLD}): "
              f"{'SUPPORTED' if h['H64c']['supported'] else 'KILLED'}  "
              f"(effect = {analysis['effect_size']})")
        print(f"  OVERALL VERDICT: {analysis['overall_verdict']}")
        # Print the coarse-grid table
        print(f"  Coarse-grid BCa CI by n:")
        for res in analysis["extrapolation_grid"]:
            if res["n"] in N_GRID_COARSE:
                print(f"    n={res['n']:5d}  BCa [{res['bca_ci'][0]:.6f}, {res['bca_ci'][1]:.6f}]  "
                      f"width={res['bca_width']:.6f}  "
                      f"excludes_oracle={res['excludes_oracle_bca']}")
        print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
