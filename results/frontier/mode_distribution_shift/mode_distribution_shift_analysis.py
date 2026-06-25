"""RQ26: Hallucination mode distribution shift — why the dataset prior matters.

RQ21 (PR #917) found CR and lang-id entropy are complementary detectors (CR on gold's
repetitive Mode R, lang-id on AISHELL-4's diverse hallucination). RQ23 (PR #924) found
the dataset prior is worth 13.5 percentage points: a per-track mode classifier achieves
95.7% leave-one-out accuracy but only 81.1% AISHELL-4 sensitivity, versus the
dataset-aware switch's 94.6%. WHY does the prior matter? This study quantifies the
hallucination mode distribution shift between gold and AISHELL-4 and tests whether it
explains the 13.5pp gap.

Hypotheses
----------
- H26a: Mode distribution differs significantly between gold and AISHELL-4
  (chi-squared p < 0.05). Kill: p >= 0.05.
- H26b: Oracle mode-routed detector (using TRUE mode labels) achieves > 90% sensitivity
  on both gold and AISHELL-4. Kill: oracle <= 90% on either.
- H26c: Diverse-vs-Non-hallucinated confusion is driven by lang-id entropy overlap
  > 30%. Kill: overlap <= 30%.

Method
------
1. Mode distribution analysis (H26a): 2x3 contingency table (gold vs AISHELL-4 x
   Mode R / Mode S+Diverse / Non-hallucinated). Pearson chi-squared test with
   analytical p-value computed via the regularized lower incomplete gamma function
   (numpy + stdlib only, no scipy). Cramer's V for effect size.
2. Oracle mode-routed detector (H26b): Using TRUE mode labels, route Mode R -> CR
   detector (threshold 15.818, gold-calibrated), Mode S -> unresolvable, Diverse ->
   lang-id detector (threshold 0.409, AISHELL-4-calibrated), Non-hallucinated -> no
   detection. Measure sensitivity on gold (n=5) and AISHELL-4 (n=37). Bootstrap 95%
   CIs with 10,000 resamples (seed=42).
3. Lang-id overlap (H26c): Gaussian KDE (Scott's bandwidth) of lang-id entropy for
   Diverse hallucinated (n=35) vs Non-hallucinated (n=40, both from AISHELL-4).
   Overlap coefficient = integral of min(f, g) dx / integral of max(f, g) dx.

Data sources are read-only. Mode labels and aggregation match RQ23 exactly: gold uses
per-track cr/lang_id from comparison_results.csv; AISHELL-4 uses cr on concatenated
separated text and lang_id as max across per-speaker texts (reproducing the
pre-registered 0 Mode R / 2 Mode S / 35 Diverse / 40 Non-hall split).

Label: experimental/frontier. Closes #927.
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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "mode_distribution_shift"
GOLD_CSV = (
    PROJECT_ROOT / "results" / "frontier" / "gold_detector_comparison" / "comparison_results.csv"
)
AISHELL4_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_JSON = OUT_DIR / "mode_distribution_shift_results.json"

# --------------------------------------------------------------- thresholds
# From RQ21 (PR #917) / RQ23 (PR #924). These reproduce the pre-registered mode labels.
GOLD_CR_THRESHOLD = 15.818182      # gold-calibrated CR threshold (RQ21, 100% specificity)
LANG_ID_THRESHOLD = 0.409073      # AISHELL-4-calibrated lang-id threshold (RQ21, 92.5% spec)
CR_MODE_THRESHOLD = 2.4           # Whisper compression_ratio_threshold (Mode R boundary)
AISHELL4_CPWER_HALLUC = 1.0       # cpWER > 1.0 => hallucinated (AISHELL-4)
N_BOOT = 10000
SEED = 42
EPS = 1e-9

# Contingency table column order (Mode S and Diverse collapsed into one column)
TABLE_COLS = ["Mode_R", "Mode_S+Diverse", "Non-hallucinated"]
TABLE_ROWS = ["gold", "aishell4"]


# ----------------------------------------------------------------- CR primitive
def compression_ratio(text: str) -> float:
    """Whisper-style compression ratio: len(utf8 bytes) / len(zlib-compressed bytes).

    Matches RQ13/RQ21/RQ23. Returns 0.0 for empty/whitespace text. High (>~2.4) =
    repetitive loop."""
    if not text or not text.strip():
        return 0.0
    b = text.encode("utf-8")
    c = zlib.compress(b)
    return len(b) / len(c) if len(c) > 0 else 0.0


# ------------------------------------------------------------- script detection
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (same as RQ13/RQ21/RQ23)."""
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

    Clean Chinese (near-monoscript Han) -> entropy ~ 0. Diverse multilingual gibberish
    mixing Han+Latin+Katakana+Hangul -> high entropy."""
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


# --------------------------------------------------------------- load gold tracks
def load_gold_tracks() -> list[dict[str, Any]]:
    """Load 600 gold tracks from comparison_results.csv (RQ21).

    Per-track cr and lang_id_entropy come directly from the CSV (computed on the
    individual separated track text in RQ21). Hallucination label is in the CSV.
    """
    tracks: list[dict[str, Any]] = []
    with GOLD_CSV.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["dataset"] != "gold":
                continue
            tracks.append({
                "dataset": "gold",
                "track_id": r["track_id"],
                "hallucinated": bool(int(r["hallucinated"])),
                "cr": float(r["cr"]),
                "lang_id_entropy": float(r["lang_id_entropy"]),
                "cer": float(r["cer"]),
            })
    return tracks


# ------------------------------------------------------------ load AISHELL-4 tracks
def load_aishell4_tracks() -> list[dict[str, Any]]:
    """Load 77 AISHELL-4 windows with RQ23's hybrid aggregation.

    - cr: computed on the CONCATENATED separated text (per RQ23 spec; concatenation
      dilutes single-speaker repetition so no window exceeds cr > 2.4 Mode R boundary).
    - lang_id_entropy: MAX across per-speaker separated texts (matching RQ21's
      calibration, where the 0.409 threshold was set on max-aggregated entropy).

    This reproduces the pre-registered 0 Mode R / 2 Mode S / 35 Diverse / 40 Non-hall
    split exactly (windows 22 and 30 are Mode S). Hallucination label:
    always_separated_cpwer > 1.0.
    """
    data = json.loads(AISHELL4_JSON.read_text(encoding="utf-8"))
    tracks: list[dict[str, Any]] = []
    for w in data["windows"]:
        sep_cpwer = float(w["always_separated_cpwer"])
        sep_texts = w.get("separated_text_per_speaker", {})
        non_empty = [str(t) for t in sep_texts.values() if t and str(t).strip()]
        sep_concat = "".join(non_empty)
        cr = compression_ratio(sep_concat)
        ent_vals = [language_id_entropy(t) for t in non_empty]
        ent = max(ent_vals) if ent_vals else 0.0
        halluc = sep_cpwer > AISHELL4_CPWER_HALLUC
        tracks.append({
            "dataset": "aishell4",
            "track_id": str(w["window_id"]),
            "hallucinated": bool(halluc),
            "cr": float(cr),
            "lang_id_entropy": float(ent),
            "cer": sep_cpwer,
        })
    return tracks


# --------------------------------------------------------------- mode labeling
def assign_mode(track: dict[str, Any]) -> str:
    """Assign a 4-class mode label from the pre-registered definitions (RQ23).

    Mode R: hallucinated AND cr > 2.4 (gold's repetitive loops).
    Mode S: hallucinated AND lang_id_entropy < 0.409 AND cr <= 2.4 (monoscript near-dup).
    Diverse: hallucinated AND lang_id_entropy >= 0.409.
    Non-hallucinated: not hallucinated.
    """
    if not track["hallucinated"]:
        return "Non-hallucinated"
    if track["cr"] > CR_MODE_THRESHOLD:
        return "Mode_R"
    if track["lang_id_entropy"] < LANG_ID_THRESHOLD:
        return "Mode_S"
    return "Diverse"


def assign_table_column(mode: str) -> str:
    """Map a 4-class mode to the 2x3 contingency table column (Mode S + Diverse merged)."""
    if mode == "Mode_R":
        return "Mode_R"
    if mode in ("Mode_S", "Diverse"):
        return "Mode_S+Diverse"
    return "Non-hallucinated"


# ----------------------------------------- regularized lower incomplete gamma
def _gamma_series(a: float, x: float) -> float:
    """Series expansion of the regularized lower incomplete gamma P(a, x).

    Converges for x < a + 1. Numerical Recipes 6.2.5."""
    gln = math.lgamma(a)
    ap = a
    summ = 1.0 / a
    delta = summ
    for _ in range(1000):
        ap += 1.0
        delta *= x / ap
        summ += delta
        if abs(delta) < abs(summ) * 1e-16:
            break
    return summ * math.exp(-x + a * math.log(x) - gln)


def _gamma_cf(a: float, x: float) -> float:
    """Continued fraction for the regularized upper incomplete gamma Q(a, x) = 1 - P(a, x).

    Converges for x >= a + 1. Numerical Recipes 6.2.7 (Lentz's algorithm)."""
    gln = math.lgamma(a)
    b = x + 1.0 - a
    c = 1.0 / 1e-30
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            break
    return math.exp(-x + a * math.log(x) - gln) * h


def regularized_lower_gamma(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x) = gamma(a, x) / Gamma(a).

    This is the CDF of the Gamma(a, 1) distribution at x. For chi-squared with k df,
    P(X <= chi2) = regularized_lower_gamma(k/2, chi2/2)."""
    if x <= 0.0 or a <= 0.0:
        return 0.0
    if x < a + 1.0:
        return _gamma_series(a, x)
    return 1.0 - _gamma_cf(a, x)


def chi_squared_pvalue(chi2: float, df: int) -> float:
    """Upper-tail p-value for a chi-squared statistic with df degrees of freedom.

    p = 1 - CDF = Q(df/2, chi2/2) = 1 - regularized_lower_gamma(df/2, chi2/2).
    Implemented via the regularized lower/upper incomplete gamma (numpy + stdlib only).

    For large chi2 (x >= a + 1), the p-value is computed directly from the continued-
    fraction form of the upper incomplete gamma Q(a, x), avoiding the catastrophic
    cancellation of 1 - P when P is numerically 1.0."""
    if df <= 0:
        return float("nan")
    if chi2 <= 0.0:
        return 1.0
    a = df / 2.0
    x = chi2 / 2.0
    if x < a + 1.0:
        # Series gives P(a, x) directly; p-value = 1 - P.
        cdf = _gamma_series(a, x)
        return max(0.0, 1.0 - cdf)
    # Continued fraction gives Q(a, x) directly (= the p-value).
    return _gamma_cf(a, x)


# --------------------------------------------------------------- chi-squared test
def chi_squared_test(table: np.ndarray) -> dict[str, float]:
    """Pearson chi-squared test on a contingency table (no Yates correction).

    Returns chi2 statistic, degrees of freedom, p-value, and Cramer's V.
    Expected counts are also returned for small-cell diagnostics."""
    n = float(table.sum())
    row_totals = table.sum(axis=1, keepdims=True)
    col_totals = table.sum(axis=0, keepdims=True)
    expected = row_totals @ col_totals / n
    # Guard against division by zero (zero row or column totals).
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2_arr = np.where(expected > 0, (table - expected) ** 2 / expected, 0.0)
    chi2 = float(chi2_arr.sum())
    n_rows, n_cols = table.shape
    df = (n_rows - 1) * (n_cols - 1)
    p = chi_squared_pvalue(chi2, df)
    cramers_v = math.sqrt(chi2 / (n * min(n_rows - 1, n_cols - 1))) if n > 0 else 0.0
    min_expected = float(expected.min())
    n_cells_below_5 = int((expected < 5.0).sum())
    return {
        "chi2": chi2,
        "df": df,
        "p_value": p,
        "cramers_v": cramers_v,
        "n": n,
        "expected": expected.tolist(),
        "min_expected": min_expected,
        "n_cells_below_5": n_cells_below_5,
        "n_cells": int(expected.size),
    }


# --------------------------------------------------------------- bootstrap CI
def bootstrap_sensitivity_ci(
    flags: np.ndarray, labels: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED
) -> tuple[float, float]:
    """Bootstrap 95% CI for sensitivity = P(flagged | hallucinated).

    Resamples the tracks with replacement and recomputes sensitivity. Resamples with
    no hallucinated track are skipped."""
    pos_idx = np.where(labels == 1)[0]
    n_pos = len(pos_idx)
    if n_pos <= 0:
        return 0.0, 0.0
    rng = np.random.default_rng(seed)
    pos_flags = flags[pos_idx]
    sens: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n_pos, size=n_pos)
        sens.append(float(pos_flags[idx].mean()))
    return float(np.percentile(sens, 2.5)), float(np.percentile(sens, 97.5))


# --------------------------------------------------------------- oracle detector
def oracle_detect(track: dict[str, Any], true_mode: str) -> bool:
    """Oracle mode-routed detector using TRUE mode labels.

    Mode R -> CR detector fires (threshold 15.818, gold-calibrated).
    Diverse -> lang-id detector fires (threshold 0.409, AISHELL-4-calibrated).
    Mode S -> unresolvable (never flagged).
    Non-hallucinated -> no detection.
    """
    if true_mode == "Mode_R":
        return track["cr"] >= GOLD_CR_THRESHOLD - EPS
    if true_mode == "Diverse":
        return track["lang_id_entropy"] >= LANG_ID_THRESHOLD - EPS
    # Mode_S and Non-hallucinated -> not flagged.
    return False


# --------------------------------------------------------------- Gaussian KDE
def gaussian_kde(
    data: np.ndarray, grid: np.ndarray, bandwidth: float | None = None
) -> tuple[np.ndarray, float]:
    """1D Gaussian KDE with Scott's bandwidth (or a custom bandwidth).

    Returns (density, bandwidth). The density is normalized to integrate to 1 over the grid."""
    data = np.asarray(data, dtype=float)
    n = len(data)
    if n == 0:
        return np.zeros_like(grid), 0.0
    if bandwidth is None:
        sigma = float(np.std(data, ddof=1)) if n > 1 else 0.0
        if sigma < EPS:
            sigma = 1.0  # degenerate fallback
        # Scott's normal reference rule: h = 1.06 * sigma * n^(-1/5)
        bandwidth = 1.06 * sigma * n ** (-1.0 / 5.0)
    # f(x) = (1/n) * sum_i N((x - x_i) / h) / h
    # Vectorized: (n_grid, n_data) matrix.
    diffs = (grid[:, None] - data[None, :]) / bandwidth
    kernel = np.exp(-0.5 * diffs ** 2) / math.sqrt(2.0 * math.pi)
    density = kernel.mean(axis=1) / bandwidth
    # Normalize to integrate to 1 over the grid (trapezoidal).
    dx = float(grid[1] - grid[0])
    integral = float(np.trapezoid(density, dx=dx))
    if integral > EPS:
        density = density / integral
    return density, bandwidth


def kde_overlap_coefficient(
    data_f: np.ndarray, data_g: np.ndarray, n_grid: int = 10000
) -> dict[str, Any]:
    """Overlap coefficient = integral min(f, g) dx / integral max(f, g) dx.

    Uses Gaussian KDE with Scott's bandwidth for each group independently. The grid
    spans [min(all)-pad, max(all)+pad] with n_grid points."""
    data_f = np.asarray(data_f, dtype=float)
    data_g = np.asarray(data_g, dtype=float)
    lo = float(min(data_f.min(), data_g.min())) - 0.5
    hi = float(max(data_f.max(), data_g.max())) + 0.5
    grid = np.linspace(lo, hi, n_grid)
    f, bw_f = gaussian_kde(data_f, grid)
    g, bw_g = gaussian_kde(data_g, grid)
    min_fg = np.minimum(f, g)
    max_fg = np.maximum(f, g)
    dx = float(grid[1] - grid[0])
    int_min = float(np.trapezoid(min_fg, dx=dx))
    int_max = float(np.trapezoid(max_fg, dx=dx))
    overlap = int_min / int_max if int_max > EPS else 0.0
    return {
        "overlap_coefficient": overlap,
        "integral_min": int_min,
        "integral_max": int_max,
        "bandwidth_f": bw_f,
        "bandwidth_g": bw_g,
        "n_f": len(data_f),
        "n_g": len(data_g),
        "grid_min": lo,
        "grid_max": hi,
        "n_grid": n_grid,
        "data_f_summary": {
            "min": float(data_f.min()),
            "max": float(data_f.max()),
            "mean": float(data_f.mean()),
            "median": float(np.median(data_f)),
            "std": float(np.std(data_f, ddof=1)) if len(data_f) > 1 else 0.0,
        },
        "data_g_summary": {
            "min": float(data_g.min()),
            "max": float(data_g.max()),
            "mean": float(data_g.mean()),
            "median": float(np.median(data_g)),
            "std": float(np.std(data_g, ddof=1)) if len(data_g) > 1 else 0.0,
        },
    }


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gold_tracks = load_gold_tracks()
    aishell4_tracks = load_aishell4_tracks()
    all_tracks = gold_tracks + aishell4_tracks

    # --- Assign mode labels (4-class) and table columns (3-class, Mode S + Diverse merged).
    for t in all_tracks:
        t["true_mode"] = assign_mode(t)
        t["table_column"] = assign_table_column(t["true_mode"])

    # --- Mode counts per dataset.
    mode_4 = ["Mode_R", "Mode_S", "Diverse", "Non-hallucinated"]
    mode_counts: dict[str, dict[str, int]] = {ds: {m: 0 for m in mode_4} for ds in TABLE_ROWS}
    for t in all_tracks:
        mode_counts[t["dataset"]][t["true_mode"]] += 1

    # ======================================================= H26a: chi-squared
    # Build 2x3 contingency table: rows = gold / aishell4, cols = Mode_R / Mode_S+Diverse / Non-hall.
    table = np.zeros((2, 3), dtype=float)
    for t in all_tracks:
        r = TABLE_ROWS.index(t["dataset"])
        c = TABLE_COLS.index(t["table_column"])
        table[r, c] += 1
    chi2_result = chi_squared_test(table)

    h26a_p = chi2_result["p_value"]
    h26a_supported = h26a_p < 0.05
    h26a_killed = h26a_p >= 0.05

    # ======================================================= H26b: oracle detector
    for t in all_tracks:
        t["oracle_flagged"] = bool(oracle_detect(t, t["true_mode"]))

    gold_halluc = [t for t in gold_tracks if t["hallucinated"]]
    a4_halluc = [t for t in aishell4_tracks if t["hallucinated"]]
    gold_tp = sum(1 for t in gold_halluc if t["oracle_flagged"])
    a4_tp = sum(1 for t in a4_halluc if t["oracle_flagged"])
    gold_sens = gold_tp / len(gold_halluc) if gold_halluc else 0.0
    a4_sens = a4_tp / len(a4_halluc) if a4_halluc else 0.0

    gold_flags = np.array([1 if t["oracle_flagged"] else 0 for t in gold_tracks], dtype=float)
    gold_labels = np.array([1 if t["hallucinated"] else 0 for t in gold_tracks], dtype=float)
    a4_flags = np.array([1 if t["oracle_flagged"] else 0 for t in aishell4_tracks], dtype=float)
    a4_labels = np.array([1 if t["hallucinated"] else 0 for t in aishell4_tracks], dtype=float)
    gold_ci = bootstrap_sensitivity_ci(gold_flags, gold_labels, seed=SEED)
    a4_ci = bootstrap_sensitivity_ci(a4_flags, a4_labels, seed=SEED + 1)

    h26b_supported = gold_sens > 0.90 and a4_sens > 0.90
    h26b_killed = gold_sens <= 0.90 or a4_sens <= 0.90

    # Breakdown of oracle detections by mode (for the writeup).
    oracle_by_mode: dict[str, dict[str, int]] = {}
    for m in mode_4:
        rows = [t for t in all_tracks if t["true_mode"] == m]
        n = len(rows)
        flagged = sum(1 for t in rows if t["oracle_flagged"])
        halluc = sum(1 for t in rows if t["hallucinated"])
        oracle_by_mode[m] = {"n": n, "flagged": flagged, "hallucinated": halluc}

    # ======================================================= H26c: KDE overlap
    # Diverse hallucinated (n=35) vs Non-hallucinated (n=40), both from AISHELL-4.
    diverse_ent = np.array(
        [t["lang_id_entropy"] for t in aishell4_tracks if t["true_mode"] == "Diverse"],
        dtype=float,
    )
    nonhall_ent = np.array(
        [t["lang_id_entropy"] for t in aishell4_tracks if t["true_mode"] == "Non-hallucinated"],
        dtype=float,
    )
    overlap_result = kde_overlap_coefficient(diverse_ent, nonhall_ent)
    overlap = overlap_result["overlap_coefficient"]

    h26c_supported = overlap > 0.30
    h26c_killed = overlap <= 0.30

    # --- Cross-check: how many non-hallucinated AISHELL-4 tracks have lang_id >= threshold?
    nonhall_above_thresh = int((nonhall_ent >= LANG_ID_THRESHOLD - EPS).sum())
    diverse_above_thresh = int((diverse_ent >= LANG_ID_THRESHOLD - EPS).sum())

    # --- Summary.
    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ26: Hallucination mode distribution shift — why the dataset prior matters",
        "closes_issue": 927,
        "method": (
            "reanalysis only (no Whisper / no ASR run by this script); gold features loaded "
            "from comparison_results.csv (RQ21); AISHELL-4 features computed on concatenated "
            "separated text (cr) and max across per-speaker texts (lang_id) from "
            "rq1_aishell4_validation_results.json, matching RQ23's aggregation exactly"
        ),
        "gold_source": str(GOLD_CSV.relative_to(PROJECT_ROOT)),
        "aishell4_source": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
        "mode_definitions": {
            "Mode_R": f"hallucinated AND cr > {CR_MODE_THRESHOLD}",
            "Mode_S": f"hallucinated AND lang_id_entropy < {LANG_ID_THRESHOLD} AND cr <= {CR_MODE_THRESHOLD}",
            "Diverse": f"hallucinated AND lang_id_entropy >= {LANG_ID_THRESHOLD}",
            "Non-hallucinated": "not hallucinated",
        },
        "aggregation_note": (
            "AISHELL-4 uses RQ23's hybrid aggregation: cr on concatenated separated text (per "
            "the RQ23 spec; concatenation dilutes single-speaker repetition so no window exceeds "
            "the cr > 2.4 Mode R boundary) and lang_id_entropy as max across speakers (the 0.409 "
            "threshold was calibrated on max-aggregated entropy in RQ21). Gold uses per-track "
            "values from RQ21's CSV. This reproduces the pre-registered mode labels exactly."
        ),
        "thresholds": {
            "gold_cr_threshold": GOLD_CR_THRESHOLD,
            "lang_id_threshold": LANG_ID_THRESHOLD,
            "cr_mode_threshold": CR_MODE_THRESHOLD,
            "aishell4_cpwer_halluc": AISHELL4_CPWER_HALLUC,
        },
        "counts": {
            "total_tracks": len(all_tracks),
            "gold_tracks": len(gold_tracks),
            "gold_hallucinated": len(gold_halluc),
            "gold_nonhallucinated": len(gold_tracks) - len(gold_halluc),
            "aishell4_tracks": len(aishell4_tracks),
            "aishell4_hallucinated": len(a4_halluc),
            "aishell4_nonhallucinated": len(aishell4_tracks) - len(a4_halluc),
            "mode_counts_by_dataset": mode_counts,
        },
        "h26a_chi_squared": {
            "contingency_table_rows": TABLE_ROWS,
            "contingency_table_cols": TABLE_COLS,
            "observed": table.tolist(),
            "expected": chi2_result["expected"],
            "chi2": round(chi2_result["chi2"], 6),
            "df": chi2_result["df"],
            "p_value": chi2_result["p_value"],
            "cramers_v": round(chi2_result["cramers_v"], 6),
            "n": chi2_result["n"],
            "min_expected": round(chi2_result["min_expected"], 6),
            "n_cells_below_5": chi2_result["n_cells_below_5"],
            "n_cells": chi2_result["n_cells"],
            "p_value_method": "analytical via regularized lower incomplete gamma (numpy + stdlib)",
        },
        "h26b_oracle_detector": {
            "policy": (
                "Mode R -> CR detector (>= 15.818); Diverse -> lang-id (>= 0.409); "
                "Mode S -> unresolvable; Non-hallucinated -> none"
            ),
            "uses_true_mode_labels": True,
            "gold_sensitivity": round(gold_sens, 6),
            "gold_sensitivity_ci_95": [round(gold_ci[0], 6), round(gold_ci[1], 6)],
            "gold_tp": gold_tp,
            "gold_n_hallucinated": len(gold_halluc),
            "aishell4_sensitivity": round(a4_sens, 6),
            "aishell4_sensitivity_ci_95": [round(a4_ci[0], 6), round(a4_ci[1], 6)],
            "aishell4_tp": a4_tp,
            "aishell4_n_hallucinated": len(a4_halluc),
            "oracle_by_mode": oracle_by_mode,
            "comparison_rq23_classifier": {
                "rq23_gold_sensitivity": 1.0,
                "rq23_aishell4_sensitivity": 0.811,
                "gap_aishell4_pp": round((a4_sens - 0.811) * 100, 2),
                "note": "RQ23 classifier (no dataset prior) achieved 81.1% on AISHELL-4; oracle (true modes) achieves the value above",
            },
        },
        "h26c_kde_overlap": {
            "groups": {
                "f": "Diverse hallucinated (AISHELL-4, lang_id_entropy)",
                "g": "Non-hallucinated (AISHELL-4, lang_id_entropy)",
            },
            "overlap_coefficient": round(overlap, 6),
            "integral_min": round(overlap_result["integral_min"], 6),
            "integral_max": round(overlap_result["integral_max"], 6),
            "bandwidth_f": round(overlap_result["bandwidth_f"], 6),
            "bandwidth_g": round(overlap_result["bandwidth_g"], 6),
            "n_f": overlap_result["n_f"],
            "n_g": overlap_result["n_g"],
            "diverse_summary": overlap_result["data_f_summary"],
            "nonhall_summary": overlap_result["data_g_summary"],
            "nonhall_above_threshold": nonhall_above_thresh,
            "diverse_above_threshold": diverse_above_thresh,
            "method": "Gaussian KDE, Scott's bandwidth (h = 1.06 * sigma * n^(-1/5)), overlap = int min(f,g) / int max(f,g)",
        },
        "hypothesis_verdicts": {
            "H26a": {
                "statement": "Mode distribution differs significantly between gold and AISHELL-4 (chi-squared p < 0.05)",
                "kill_criterion": "p >= 0.05",
                "chi2": round(chi2_result["chi2"], 6),
                "df": chi2_result["df"],
                "p_value": chi2_result["p_value"],
                "cramers_v": round(chi2_result["cramers_v"], 6),
                "supported": bool(h26a_supported),
                "killed": bool(h26a_killed),
            },
            "H26b": {
                "statement": "Oracle mode-routed detector (using TRUE mode labels) achieves > 90% sensitivity on both gold and AISHELL-4",
                "kill_criterion": "oracle <= 90% on either",
                "gold_sensitivity": round(gold_sens, 6),
                "gold_ci_95": [round(gold_ci[0], 6), round(gold_ci[1], 6)],
                "aishell4_sensitivity": round(a4_sens, 6),
                "aishell4_ci_95": [round(a4_ci[0], 6), round(a4_ci[1], 6)],
                "supported": bool(h26b_supported),
                "killed": bool(h26b_killed),
            },
            "H26c": {
                "statement": "Diverse-vs-Non-hallucinated confusion is driven by lang-id entropy overlap > 30%",
                "kill_criterion": "overlap <= 30%",
                "overlap_coefficient": round(overlap, 6),
                "supported": bool(h26c_supported),
                "killed": bool(h26c_killed),
            },
        },
    }

    # --- Write JSON.
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- Console summary.
    print("=== RQ26: Hallucination mode distribution shift ===")
    print(f"Label: experimental/frontier  |  Closes #927")
    print(f"Tracks: {len(all_tracks)} (gold {len(gold_tracks)} + aishell4 {len(aishell4_tracks)})")
    print(f"Mode counts (gold):       {mode_counts['gold']}")
    print(f"Mode counts (aishell4):   {mode_counts['aishell4']}")
    print()
    print("H26a — Chi-squared test (2x3: gold vs aishell4 x Mode R / Mode S+Diverse / Non-hall):")
    print(f"  Observed:")
    print(f"    {'':12s}" + "".join(f"{c:>16s}" for c in TABLE_COLS))
    for i, r in enumerate(TABLE_ROWS):
        print(f"    {r:12s}" + "".join(f"{int(table[i,j]):16d}" for j in range(3)))
    print(f"  Expected:")
    print(f"    {'':12s}" + "".join(f"{c:>16s}" for c in TABLE_COLS))
    exp = chi2_result["expected"]
    for i, r in enumerate(TABLE_ROWS):
        print(f"    {r:12s}" + "".join(f"{exp[i][j]:16.2f}" for j in range(3)))
    print(f"  chi2 = {chi2_result['chi2']:.4f}, df = {chi2_result['df']}, "
          f"p = {chi2_result['p_value']:.6e}")
    print(f"  Cramer's V = {chi2_result['cramers_v']:.4f}")
    print(f"  Cells with expected < 5: {chi2_result['n_cells_below_5']}/{chi2_result['n_cells']} "
          f"(min expected = {chi2_result['min_expected']:.2f})")
    print(f"  Verdict: {'SUPPORTED' if h26a_supported else 'NOT SUPPORTED'}"
          f"{'  [KILLED]' if h26a_killed else ''} (p {'< 0.05' if h26a_supported else '>= 0.05'})")
    print()
    print("H26b — Oracle mode-routed detector (TRUE mode labels):")
    print(f"  gold:     sens={gold_sens:.1%} ({gold_tp}/{len(gold_halluc)}) "
          f"CI [{gold_ci[0]:.1%}, {gold_ci[1]:.1%}]")
    print(f"  aishell4: sens={a4_sens:.1%} ({a4_tp}/{len(a4_halluc)}) "
          f"CI [{a4_ci[0]:.1%}, {a4_ci[1]:.1%}]")
    print(f"  Oracle by mode: {oracle_by_mode}")
    print(f"  Verdict: {'SUPPORTED' if h26b_supported else 'NOT SUPPORTED'}"
          f"{'  [KILLED]' if h26b_killed else ''}")
    print()
    print("H26c — KDE overlap (Diverse hallucinated vs Non-hallucinated, AISHELL-4):")
    print(f"  Diverse: n={overlap_result['n_f']}, "
          f"lang_id min={overlap_result['data_f_summary']['min']:.4f}, "
          f"max={overlap_result['data_f_summary']['max']:.4f}, "
          f"median={overlap_result['data_f_summary']['median']:.4f}")
    print(f"  Non-hall: n={overlap_result['n_g']}, "
          f"lang_id min={overlap_result['data_g_summary']['min']:.4f}, "
          f"max={overlap_result['data_g_summary']['max']:.4f}, "
          f"median={overlap_result['data_g_summary']['median']:.4f}")
    print(f"  Bandwidth: f={overlap_result['bandwidth_f']:.4f}, g={overlap_result['bandwidth_g']:.4f}")
    print(f"  Overlap coefficient = {overlap:.4f} ({overlap:.1%})")
    print(f"  Non-hall tracks above 0.409 threshold: {nonhall_above_thresh}/{overlap_result['n_g']}")
    print(f"  Verdict: {'SUPPORTED' if h26c_supported else 'NOT SUPPORTED'}"
          f"{'  [KILLED]' if h26c_killed else ''} (overlap {'> 30%' if h26c_supported else '<= 30%'})")
    print()
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
