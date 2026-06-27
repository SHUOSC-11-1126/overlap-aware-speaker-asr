"""RQ63: Cost-aware cascade Pareto -- does a cost-aware threshold that maximises
cpWER-per-compute-unit give a better Pareto operating point than the
detection-metric-calibrated thresholds (RQ54 F1, RQ59 Youden's J)?

REANALYSIS ONLY -- no Whisper / no ASR / no LLM model is run. RQ54 (PR #971) and
RQ59 (PR #974) both collapse to KL = 0.01 with 83.1% escalation (cascade compute
1.77x under RQ43's 1.93x-base model) because F1 and Youden's J maximise detection
metrics without considering compute cost. RQ43's original rule (KL = 3.30) is
less aggressive (~74% escalation, cpWER 0.889) but does not explicitly trade
cpWER against compute. RQ63 asks whether a cost-aware threshold -- selected to
maximise cpWER efficiency per compute unit -- yields a better Pareto operating
point than RQ43 / RQ54 / RQ59.

Label: experimental/frontier.

Cost model (task-specified, differs from RQ54/RQ59's 1.93x-base model)
----------------------------------------------------------------------
Per the task METHOD: cascade compute = 1.0 + fraction_escalated * 0.428, i.e.
tiny = 1.0x and escalating a window to base adds 0.428x (the RQ43 model_scale
separated base/tiny CER ratio 0.428031, reused as the compute surcharge). So
COMPUTE_TINY = 1.0, COMPUTE_BASE = 1.428031. This is a different cost model from
RQ54/RQ59 (which used COMPUTE_BASE = 1.93 from runtime_cascade); the cascade
cpWER simulation itself is held fixed at RQ43's (tier 1 = real whisper-tiny
separated cpWER; tier 3 = tiny * 0.428031). Only the compute axis changes, so
the cpWER anchors (RQ43 0.888947, RQ54 0.777525) reproduce exactly.

Pareto efficiency operationalisation
-------------------------------------
The task METHOD writes "Pareto efficiency = cpWER / compute; select maximising".
cpWER is a LOSS (lower is better), so the raw ratio cpWER/compute is minimised
by escalating everything (lower error per compute unit) and maximised by
escalating nothing (all-tiny corner). Two observations disambiguate the intent:

1. H63c's reference points are RQ43 (0.889/1.4x = 0.635) and RQ54
   (0.780/1.77x = 0.441). RQ54 is the BETTER cascade (lower cpWER 0.780 < 0.889)
   and has the LOWER ratio (0.441 < 0.635). "Strictly better ratio" therefore
   means LOWER cpWER/compute (less error per compute unit) -- i.e. the
   cost-aware objective is to MINIMISE cpWER/compute, equivalently MAXIMISE the
   efficiency compute/cpWER. Maximising cpWER/compute would label the worse
   cascade (RQ43) as "better", which is incoherent.
2. Maximising cpWER/compute collapses to the all-tiny corner (compute 1.0x,
   cpWER 1.591) -- a degenerate no-escalation point that fails H63b trivially.

We therefore operationalise the cost-aware objective as MINIMISING cpWER/compute
(= maximising compute/cpWER efficiency): the threshold achieving the lowest
cpWER per compute unit is the cost-aware operating point. We ALSO report the
literal "maximise cpWER/compute" point (all-tiny corner) and the marginal-
efficiency (bang-for-buck) point (baseline-cpWER reduction per compute
increment) as secondary exploratory objectives, for full transparency. All
three objectives are evaluated on the same 0.01-step KL grid spanning
[0.01, 8.53] (the task-specified range; 853 points).

Method
------
1. Load RQ43's 77 per-window (tiny_sep_cpwer, base_sep_cpwer, kl_sep) from
   ``three_tier_cascade_results.json`` (byte-identical corpus to RQ43/RQ46/
   RQ54/RQ59). Verify n=77, baseline 1.590909, RQ43 @ KL=3.30 reproduces
   0.888947, label counts 37 hall / 40 clean.
2. Cost model: cascade compute = 1.0 + 0.428031 * frac, frac = mean(kl >= thr).
3. For each KL threshold on the 0.01..8.53 grid: compute cascade cpWER, cascade
   compute, cpWER/compute ratio, and marginal efficiency
   (baseline - cpWER)/(compute - 1.0). Build the full Pareto frontier.
4. Cost-aware operating point = threshold minimising cpWER/compute (primary).
   Secondary: threshold maximising cpWER/compute (literal) and threshold
   maximising marginal efficiency.
5. Bootstrap B=10000, seed=42: per resample re-select the cost-aware (min-ratio)
   threshold on in-bag windows, evaluate OOB cpWER and compute. BCa 95% CI on
   the OOB cpWER distribution (bias-correction z0 from the in-sample point
   estimate; acceleration from a delete-1 jackknife).
6. Pre-registered hypothesis verdicts H63a/b/c.

Pre-registered hypotheses (kill criteria)
-----------------------------------------
- H63a: Cost-aware escalation < 83.1% (less aggressive than F1/J). KILLED if
        in-sample escalation fraction >= 0.831.
- H63b: Cost-aware OOB cpWER <= 0.889 (matches RQ43's original rule). KILLED if
        OOB median cpWER > 0.889.
- H63c: Cost-aware Pareto efficiency: cpWER/compute ratio strictly better (lower)
        than both RQ43 and RQ54, and NOT Pareto-dominated by either. KILLED if
        dominated by RQ43 or RQ54, or if the ratio is not strictly lower than
        both.

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / matplotlib
/ Whisper are NOT required). The normal-CDF / BCa helpers and the RQ43 cascade
simulation are reused verbatim from RQ59 (cascade_youdens_j_analysis) and RQ46
(bootstrap_pareto_analysis) to guarantee the cascade corpus and CI machinery are
byte-identical to the RQ43/RQ54/RQ59 anchors.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
RQ43_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "three_tier_cascade"
    / "three_tier_cascade_results.json"
)
AISHELL4_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
RQ54_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "cascade_f1_calibration"
    / "cascade_f1_results.json"
)
RQ59_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "cascade_youdens_j"
    / "cascade_youdens_j_results.json"
)
RQ46_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "bootstrap_pareto"
    / "bootstrap_pareto_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "cost_aware_cascade"
OUT_JSON = OUT_DIR / "cost_aware_cascade_results.json"
OUT_CSV = OUT_DIR / "cost_aware_cascade_results.csv"

# ------------------------------------------ import RQ59's framework (verbatim reuse)
# RQ59 contributes the RQ43 cascade simulation (cascade_cpwer_at_threshold,
# cascade_oob_cpwer), the data loader, the EPS convention, and the full BCa
# machinery (norm_ppf / norm_cdf / bca_ci). Reusing them guarantees the cascade
# corpus and CI are byte-identical to RQ54/RQ59. Only the compute model, the
# selection objective, and the bootstrap/jackknife (which re-select on the
# cost-aware objective) are new to RQ63.
_RQ59_DIR = PROJECT_ROOT / "results" / "frontier" / "cascade_youdens_j"
_RQ46_DIR = PROJECT_ROOT / "results" / "frontier" / "bootstrap_pareto"
sys.path.insert(0, str(_RQ59_DIR))
sys.path.insert(0, str(_RQ46_DIR))
import cascade_youdens_j_analysis as rq59  # noqa: E402  (path-injected import)
import bootstrap_pareto_analysis as rq46  # noqa: E402  (path-injected import)

# Re-exported for traceability (RQ59's verbatim helpers).
load_rq43_per_window = rq59.load_rq43_per_window
cascade_cpwer_at_threshold = rq59.cascade_cpwer_at_threshold
norm_ppf = rq59.norm_ppf
norm_cdf = rq59.norm_cdf
bca_ci = rq59.bca_ci
EPS = rq59.EPS  # 1e-9 (RQ44/RQ48/RQ54/RQ59 tolerance)
pareto_dominates = rq46.pareto_dominates  # RQ46's strict 2D Pareto dominance

# ------------------------------------------------------------------ constants
# KL threshold grid: 0.01 step spanning the task-specified range [0.01, 8.53].
# 853 points. (RQ54/RQ59 used [0.00, 8.55]; RQ63 follows the task brief's
# [0.01, 8.53] exactly. At 8.53 no window is escalated -- max KL is 8.5255 --
# so 8.53 is the all-tiny corner; at 0.01 the 13 clean windows with KL=0 are
# not escalated, giving frac 0.831169 = RQ54's point.)
KL_THRESHOLD_GRID = [round(0.01 * i, 2) for i in range(1, 854)]  # 0.01 .. 8.53

N_BOOT = 10000            # task-specified bootstrap iterations
SEED = 42                 # task-specified seed
ALPHA = 0.05              # 95% CI
CATASTROPHIC_CPWER = 1.0  # cpWER > 1.0 => hallucination label (RQ44/RQ48/RQ54)

# Cost model (task METHOD): tiny = 1.0x, base adds 0.428031x (RQ43 model_scale
# separated base/tiny CER ratio, reused as the compute surcharge).
COMPUTE_TINY = 1.0
COMPUTE_BASE_ADD = 0.428031          # == RQ43_BASE_RATIO
COMPUTE_BASE = COMPUTE_TINY + COMPUTE_BASE_ADD  # 1.428031

# Baseline = always-tiny-separated (no escalation): cpWER 1.590909, compute 1.0x.
BASELINE_CPWER = 1.590909
BASELINE_COMPUTE = COMPUTE_TINY

# RQ43 / RQ54 / RQ59 anchors (the controlled-comparison reference values).
RQ43_KL_THRESHOLD = 3.30
RQ43_CASCADE_CPWER = 0.888947          # RQ43 in-sample cascade cpWER @ KL=3.30
RQ43_BASELINE_CPWER = 1.590909         # always-tiny-separated
RQ43_BASE_RATIO = 0.428031             # model_scale separated base/tiny CER ratio
RQ43_ESCALATION = 0.740260             # RQ43 in-sample escalation fraction @ 3.30
RQ54_KL_THRESHOLD = 0.01
RQ54_CASCADE_CPWER = 0.777525          # RQ54 in-sample cascade cpWER @ KL=0.01
RQ54_OOB_MEDIAN_CPWER = 0.779853       # RQ54 OOB median cpWER (task brief: 0.780)
RQ54_ESCALATION = 0.831169             # RQ54 in-sample escalation fraction
RQ59_KL_THRESHOLD = 0.01              # RQ59 == RQ54 operating point

# Task-brief stated reference Pareto coordinates (RQ43 0.889/1.4x, RQ54
# 0.780/1.77x). These mix cost models (RQ54's 1.77x is RQ54's 1.93x-base model;
# RQ43's 1.4x is approximate). For an apples-to-apples Pareto comparison we
# recompute both under RQ63's 0.428-base cost model and report both.
TASK_RQ43_CPWER = 0.889
TASK_RQ43_COMPUTE = 1.4
TASK_RQ54_CPWER = 0.780
TASK_RQ54_COMPUTE = 1.77

# Hypothesis kill thresholds.
H63A_MAX_ESCALATION = 0.831   # cost-aware: kill if escalation fraction >= 0.831
H63B_MAX_CPWER = 0.889        # cost-aware: kill if OOB median cpWER > 0.889


# --------------------------------------------------------------- cascade compute (NEW cost model)
def cascade_compute_at_threshold(kl: np.ndarray, threshold: float) -> float:
    """Cascade compute under RQ63's cost model: 1.0 + 0.428031 * frac.

    frac = mean(kl >= threshold - EPS). tiny = 1.0x; escalating a window to base
    adds 0.428031x (RQ43's separated base/tiny CER ratio, reused as the compute
    surcharge per the task METHOD). The KL gate cost is negligible and folded
    into the 1.0x tiny budget (RQ43 convention)."""
    kl = np.asarray(kl, dtype=float)
    if kl.size == 0:
        return 0.0
    frac = float(np.mean(kl >= threshold - EPS))
    return COMPUTE_TINY + COMPUTE_BASE_ADD * frac


def cascade_oob_cpwer_and_compute(
    tiny: np.ndarray,
    base: np.ndarray,
    kl: np.ndarray,
    threshold: float,
    in_bag_idx: np.ndarray,
) -> dict[str, Any]:
    """Cascade cpWER AND compute on the out-of-bag (OOB) windows at ``threshold``.

    Mirrors RQ59's ``cascade_oob_cpwer`` protocol but also returns the cascade
    compute (RQ63 cost model) on the OOB windows. Returns the mean selected
    cpWER (nan if OOB empty), the OOB compute, the OOB size, and the escalation
    count."""
    n = len(kl)
    all_idx = np.arange(n)
    in_bag_set = np.unique(np.asarray(in_bag_idx, dtype=int))
    oob_mask = ~np.isin(all_idx, in_bag_set)
    n_oob = int(oob_mask.sum())
    if n_oob == 0:
        return {"cpwer": float("nan"), "compute": float("nan"),
                "n_oob": 0, "n_escalated": 0}
    oob_kl = kl[oob_mask]
    oob_tiny = tiny[oob_mask]
    oob_base = base[oob_mask]
    escalated = oob_kl >= threshold - EPS
    selected = np.where(escalated, oob_base, oob_tiny)
    frac = float(np.mean(escalated))
    return {"cpwer": float(selected.mean()),
            "compute": COMPUTE_TINY + COMPUTE_BASE_ADD * frac,
            "n_oob": n_oob, "n_escalated": int(escalated.sum())}


# --------------------------------------------------------------- Pareto efficiency metrics
def pareto_ratio(cpwer: float, compute: float) -> float:
    """Literal cpWER/compute ratio (the task METHOD's 'Pareto efficiency').

    Lower is better (less error per compute unit). Returns inf when compute <= 0
    (degenerate)."""
    if compute <= 0.0:
        return float("inf")
    return float(cpwer) / float(compute)


def marginal_efficiency(
    cpwer: float, compute: float,
    baseline_cpwer: float = BASELINE_CPWER,
    baseline_compute: float = BASELINE_COMPUTE,
) -> float:
    """Marginal cpWER reduction per marginal compute unit (bang-for-buck).

    efficiency = (baseline_cpwer - cpwer) / (compute - baseline_compute). Higher
    is better (more cpWER reduction per compute added). Returns -inf when the
    cascade adds no compute (compute == baseline_compute, i.e. no escalation):
    no marginal compute spent, no marginal reduction attributable."""
    denom = float(compute) - float(baseline_compute)
    if denom <= 1e-12:
        return float("-inf")
    return (float(baseline_cpwer) - float(cpwer)) / denom


# --------------------------------------------------------------- threshold selection
def select_threshold_by_min_ratio(
    tiny: np.ndarray, base: np.ndarray, kl: np.ndarray,
    grid: list[float] | None = None,
) -> dict[str, Any]:
    """Cost-aware operating point: threshold MINIMISING cpWER/compute (primary).

    Sweeps the KL grid; for each threshold computes cascade cpWER, cascade
    compute, and the cpWER/compute ratio; returns the threshold achieving the
    lowest ratio (lowest-tie-break via the natural first-min sweep). This is
    the cost-aware operating point per H63c's 'lower ratio = better' convention.
    """
    if grid is None:
        grid = KL_THRESHOLD_GRID
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    best_t: float | None = None
    best_ratio = float("inf")
    best_cp = 0.0
    best_comp = 0.0
    best_frac = 0.0
    for t in grid:
        cp = cascade_cpwer_at_threshold(tiny, base, kl, t)
        comp = cascade_compute_at_threshold(kl, t)
        r = pareto_ratio(cp, comp)
        if r < best_ratio - EPS:
            best_ratio = r
            best_t = t
            best_cp = cp
            best_comp = comp
            best_frac = float(np.mean(kl >= t - EPS))
    return {"threshold": float(best_t), "cpwer": float(best_cp),
            "compute": float(best_comp), "ratio": float(best_ratio),
            "frac": float(best_frac)}


def select_threshold_by_max_ratio(
    tiny: np.ndarray, base: np.ndarray, kl: np.ndarray,
    grid: list[float] | None = None,
) -> dict[str, Any]:
    """Secondary (literal task METHOD): threshold MAXIMISING cpWER/compute.

    This is the literal reading of 'select maximising Pareto efficiency'. On the
    monotonic cascade frontier it collapses to the all-tiny corner (highest
    threshold, frac -> 0, compute 1.0x). Reported for transparency."""
    if grid is None:
        grid = KL_THRESHOLD_GRID
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    best_t: float | None = None
    best_ratio = float("-inf")
    best_cp = 0.0
    best_comp = 0.0
    best_frac = 0.0
    for t in grid:
        cp = cascade_cpwer_at_threshold(tiny, base, kl, t)
        comp = cascade_compute_at_threshold(kl, t)
        r = pareto_ratio(cp, comp)
        if r > best_ratio + EPS:
            best_ratio = r
            best_t = t
            best_cp = cp
            best_comp = comp
            best_frac = float(np.mean(kl >= t - EPS))
    return {"threshold": float(best_t), "cpwer": float(best_cp),
            "compute": float(best_comp), "ratio": float(best_ratio),
            "frac": float(best_frac)}


def select_threshold_by_marginal_eff(
    tiny: np.ndarray, base: np.ndarray, kl: np.ndarray,
    grid: list[float] | None = None,
) -> dict[str, Any]:
    """Secondary (exploratory): threshold MAXIMISING marginal efficiency
    (baseline-cpWER reduction per compute increment)."""
    if grid is None:
        grid = KL_THRESHOLD_GRID
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    best_t: float | None = None
    best_eff = float("-inf")
    best_cp = 0.0
    best_comp = 0.0
    best_frac = 0.0
    for t in grid:
        cp = cascade_cpwer_at_threshold(tiny, base, kl, t)
        comp = cascade_compute_at_threshold(kl, t)
        e = marginal_efficiency(cp, comp)
        if e > best_eff + EPS:
            best_eff = e
            best_t = t
            best_cp = cp
            best_comp = comp
            best_frac = float(np.mean(kl >= t - EPS))
    return {"threshold": float(best_t), "cpwer": float(best_cp),
            "compute": float(best_comp), "marginal_efficiency": float(best_eff),
            "frac": float(best_frac)}


def build_pareto_frontier(
    tiny: np.ndarray, base: np.ndarray, kl: np.ndarray,
    grid: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Full Pareto frontier: one point per KL threshold on the grid.

    Each point records threshold, cascade cpWER, cascade compute, escalation
    fraction, cpWER/compute ratio, and marginal efficiency."""
    if grid is None:
        grid = KL_THRESHOLD_GRID
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    out: list[dict[str, Any]] = []
    for t in grid:
        cp = cascade_cpwer_at_threshold(tiny, base, kl, t)
        comp = cascade_compute_at_threshold(kl, t)
        frac = float(np.mean(kl >= t - EPS))
        out.append({
            "threshold": float(t),
            "cpwer": round(cp, 6),
            "compute": round(comp, 6),
            "frac": round(frac, 6),
            "cpwer_per_compute": round(pareto_ratio(cp, comp), 6),
            "marginal_efficiency": round(marginal_efficiency(cp, comp), 6),
        })
    return out


# --------------------------------------------------------------- vectorised bootstrap (min-ratio cost-aware)
def bootstrap_cost_aware_cascade(
    tiny: np.ndarray,
    base: np.ndarray,
    kl: np.ndarray,
    grid: list[float] | None = None,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, np.ndarray]:
    """Bootstrap the cost-aware (min cpWER/compute) cascade over ``n_boot`` resamples.

    For each resample: draw n indices with replacement, select the in-bag
    threshold minimising cpWER/compute (lowest-tie-break), and evaluate the
    cascade cpWER and compute on the OOB windows.

    Returns a dict with:
      ``boot_idx``        -- (n_boot, n) int array of resample indices
      ``thresholds``      -- (n_boot,) cost-aware KL threshold per resample
      ``oob_cpwer``       -- (n_boot,) OOB cascade cpWER (nan if OOB empty)
      ``oob_compute``     -- (n_boot,) OOB cascade compute (nan if OOB empty)
      ``n_oob``           -- (n_boot,) OOB size per resample
      ``n_escalated_oob`` -- (n_boot,) escalated count within OOB

    The vectorised min-ratio selection is proved equivalent to the per-call
    ``select_threshold_by_min_ratio`` by ``test_vectorised_matches_select_min_ratio``.
    """
    if grid is None:
        grid = KL_THRESHOLD_GRID
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    n = kl.shape[0]
    grid_arr = np.asarray(grid, dtype=float)
    T = grid_arr.size

    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, n, size=(n_boot, n))  # (B, n)
    tiny_boot = tiny[boot_idx]                        # (B, n)
    base_boot = base[boot_idx]
    kl_boot = kl[boot_idx]

    # Ratio matrix (B, T): loop over the (small) grid, vectorise over resamples.
    # ratio = cpwer / compute, cpwer = mean(selected), compute = 1 + 0.428031*frac.
    ratio_mat = np.empty((n_boot, T), dtype=float)
    for ti in range(T):
        t = grid_arr[ti]
        flagged = kl_boot >= t - EPS                  # (B, n)
        selected = np.where(flagged, base_boot, tiny_boot)  # (B, n)
        cpwer_b = selected.mean(axis=1)               # (B,)
        frac_b = flagged.mean(axis=1)                 # (B,)
        compute_b = COMPUTE_TINY + COMPUTE_BASE_ADD * frac_b
        ratio_mat[:, ti] = cpwer_b / compute_b

    # theta*_b = lowest-t threshold achieving the MIN ratio (within EPS).
    best_per_b = ratio_mat.min(axis=1)                # (B,)
    is_min = ratio_mat <= best_per_b[:, None] + EPS   # (B, T)
    idx_b = is_min.argmax(axis=1)                      # first True = lowest t
    thresholds = grid_arr[idx_b]                       # (B,)

    # OOB cascade cpWER + compute per resample.
    oob_cpwer = np.empty(n_boot, dtype=float)
    oob_compute = np.empty(n_boot, dtype=float)
    n_oob_arr = np.empty(n_boot, dtype=int)
    n_esc_arr = np.empty(n_boot, dtype=int)
    for b in range(n_boot):
        counts = np.bincount(boot_idx[b], minlength=n)
        oob_mask = counts == 0
        no = int(oob_mask.sum())
        n_oob_arr[b] = no
        if no == 0:
            oob_cpwer[b] = float("nan")
            oob_compute[b] = float("nan")
            n_esc_arr[b] = 0
            continue
        esc = kl[oob_mask] >= thresholds[b] - EPS
        sel = np.where(esc, base[oob_mask], tiny[oob_mask])
        oob_cpwer[b] = float(sel.mean())
        oob_compute[b] = COMPUTE_TINY + COMPUTE_BASE_ADD * float(np.mean(esc))
        n_esc_arr[b] = int(esc.sum())

    return {
        "boot_idx": boot_idx,
        "thresholds": thresholds,
        "oob_cpwer": oob_cpwer,
        "oob_compute": oob_compute,
        "n_oob": n_oob_arr,
        "n_escalated_oob": n_esc_arr,
    }


# --------------------------------------------------------------- jackknife acceleration
def jackknife_acceleration(
    tiny: np.ndarray, base: np.ndarray, kl: np.ndarray,
    grid: list[float] | None = None,
) -> tuple[float, np.ndarray]:
    """Delete-1 jackknife acceleration for the BCa CI.

    For each i in 0..n-1: leave window i out, re-select the cost-aware (min-
    ratio) KL threshold on the remaining n-1 windows, and compute the in-sample
    cascade cpWER on those n-1 windows (theta_(i)). The acceleration is

        a = sum( (theta_bar - theta_(i))^3 ) / ( 6 * sum( (theta_bar - theta_(i))^2 )^1.5 )

    Returns (a, theta_loo). a = 0.0 when the denominator is 0 (no variation),
    which collapses BCa to the bias-corrected percentile."""
    if grid is None:
        grid = KL_THRESHOLD_GRID
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    n = kl.shape[0]
    theta_loo = np.empty(n, dtype=float)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        sel = select_threshold_by_min_ratio(tiny[mask], base[mask], kl[mask], grid=grid)
        theta_loo[i] = cascade_cpwer_at_threshold(
            tiny[mask], base[mask], kl[mask], sel["threshold"])
    theta_bar = float(theta_loo.mean())
    diff = theta_bar - theta_loo
    scale = max(abs(theta_bar), 1.0)
    if float(np.max(np.abs(diff))) < 1e-12 * scale:
        return 0.0, theta_loo
    num = float(np.sum(diff ** 3))
    den = 6.0 * (float(np.sum(diff ** 2)) ** 1.5)
    a = num / den if den > 0 else 0.0
    return a, theta_loo


# --------------------------------------------------------------- CSV output
def write_bootstrap_csv(
    path: Path,
    boot_idx: np.ndarray,
    thresholds: np.ndarray,
    oob_cpwer: np.ndarray,
    oob_compute: np.ndarray,
    n_oob: np.ndarray,
    n_escalated_oob: np.ndarray,
    n_windows: int,
) -> None:
    """Write the per-resample bootstrap table as CSV.

    One row per bootstrap resample (B rows) plus a header. Columns:
    ``resample, threshold, oob_cpwer, oob_compute, n_oob, n_escalated_oob,
    oob_fraction, escalation_fraction_oob``. ``oob_cpwer`` / ``oob_compute`` are
    blank when the OOB set was empty (nan)."""
    B = int(thresholds.shape[0])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["resample", "threshold", "oob_cpwer", "oob_compute",
                    "n_oob", "n_escalated_oob", "oob_fraction",
                    "escalation_fraction_oob"])
        for b in range(B):
            no = int(n_oob[b])
            cp = float(oob_cpwer[b])
            co = float(oob_compute[b])
            esc = int(n_escalated_oob[b])
            w.writerow([
                b,
                round(float(thresholds[b]), 6),
                "" if (no == 0 or math.isnan(cp)) else round(cp, 6),
                "" if (no == 0 or math.isnan(co)) else round(co, 6),
                no,
                esc,
                round(no / n_windows, 6) if n_windows > 0 else 0.0,
                round(esc / no, 6) if no > 0 else "",
            ])


# --------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    windows = load_rq43_per_window()
    tiny = windows["tiny"]
    base = windows["base"]
    kl = windows["kl"]
    n = kl.shape[0]
    labels = (tiny > CATASTROPHIC_CPWER).astype(int)  # 1 = hallucinated
    n_hall = int(labels.sum())
    n_clean = int((labels == 0).sum())

    # --- controlled-comparison smoke: RQ43's original rule reproduces 0.888947
    rq43_cas = cascade_cpwer_at_threshold(tiny, base, kl, RQ43_KL_THRESHOLD)
    baseline = float(tiny.mean())
    rq43_compute = cascade_compute_at_threshold(kl, RQ43_KL_THRESHOLD)
    rq43_frac = float(np.mean(kl >= RQ43_KL_THRESHOLD - EPS))
    assert abs(rq43_cas - RQ43_CASCADE_CPWER) < 1e-4, (
        f"RQ43 cascade @ KL=3.30 = {rq43_cas}, expected ~{RQ43_CASCADE_CPWER}")
    assert abs(baseline - RQ43_BASELINE_CPWER) < 1e-4
    assert n_hall == 37 and n_clean == 40, f"label counts {n_hall}/{n_clean}"

    # --- RQ54 / RQ59 reference points (recomputed under RQ63's cost model)
    rq54_cpwer = cascade_cpwer_at_threshold(tiny, base, kl, RQ54_KL_THRESHOLD)
    rq54_compute = cascade_compute_at_threshold(kl, RQ54_KL_THRESHOLD)
    rq54_frac = float(np.mean(kl >= RQ54_KL_THRESHOLD - EPS))
    rq59_cpwer = rq54_cpwer  # RQ59 == RQ54 operating point (RQ59 finding)
    rq59_compute = rq54_compute
    rq59_frac = rq54_frac

    # --- full Pareto frontier
    frontier = build_pareto_frontier(tiny, base, kl, grid=KL_THRESHOLD_GRID)

    # --- cost-aware operating points (primary + secondary)
    ca_min = select_threshold_by_min_ratio(tiny, base, kl, grid=KL_THRESHOLD_GRID)
    ca_max = select_threshold_by_max_ratio(tiny, base, kl, grid=KL_THRESHOLD_GRID)
    ca_marg = select_threshold_by_marginal_eff(tiny, base, kl, grid=KL_THRESHOLD_GRID)

    theta_hat = ca_min["cpwer"]              # BCa point estimate (in-sample @ cost-aware)
    ca_compute = ca_min["compute"]
    ca_frac = ca_min["frac"]
    ca_ratio = ca_min["ratio"]

    # --- bootstrap cost-aware cascade (B=10000, seed=42)
    boot = bootstrap_cost_aware_cascade(tiny, base, kl, grid=KL_THRESHOLD_GRID,
                                        n_boot=N_BOOT, seed=SEED)
    boot_thr = boot["thresholds"]
    boot_oob = boot["oob_cpwer"]
    boot_oob_compute = boot["oob_compute"]
    n_oob_mean = float(np.mean(boot["n_oob"]))

    # --- jackknife acceleration + BCa CI on the OOB cpWER distribution
    accel, theta_loo = jackknife_acceleration(tiny, base, kl, grid=KL_THRESHOLD_GRID)
    bca = bca_ci(theta_hat, boot_oob, accel, alpha=ALPHA)
    bca_width = bca["hi"] - bca["lo"]
    oob_median = bca["median"]
    oob_mean = float(np.nanmean(boot_oob))
    oob_compute_median = float(np.nanmedian(boot_oob_compute))

    # --- reference ratios (RQ43 / RQ54 under RQ63 cost model + task-brief values)
    rq43_ratio_new = pareto_ratio(rq43_cas, rq43_compute)
    rq54_ratio_new = pareto_ratio(rq54_cpwer, rq54_compute)
    rq43_ratio_task = pareto_ratio(TASK_RQ43_CPWER, TASK_RQ43_COMPUTE)
    rq54_ratio_task = pareto_ratio(TASK_RQ54_CPWER, TASK_RQ54_COMPUTE)

    # --- H63c: not dominated by RQ43 / RQ54 AND ratio strictly lower than both
    # (under the consistent RQ63 cost model).
    dom_by_rq43 = pareto_dominates(rq43_cas, rq43_compute, theta_hat, ca_compute)
    dom_by_rq54 = pareto_dominates(rq54_cpwer, rq54_compute, theta_hat, ca_compute)
    ratio_below_rq43 = ca_ratio < rq43_ratio_new - EPS
    ratio_below_rq54 = ca_ratio < rq54_ratio_new - EPS
    h63c_supported = (
        (not dom_by_rq43) and (not dom_by_rq54)
        and ratio_below_rq43 and ratio_below_rq54
    )

    # --- hypothesis verdicts
    h63a_supported = ca_frac < H63A_MAX_ESCALATION
    h63b_supported = oob_median <= H63B_MAX_CPWER

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": ("RQ63: Cost-aware cascade Pareto -- does a cost-aware threshold "
               "that maximises cpWER-per-compute-unit give a better Pareto "
               "operating point than RQ43 / RQ54 / RQ59?"),
        "closes_issue": 987,
        "builds_on": {
            "RQ43": "results/frontier/three_tier_cascade/ (PR #959, 3-tier KL cascade)",
            "RQ46": "results/frontier/bootstrap_pareto/ (PR #966, Pareto CI + dominance)",
            "RQ54": "results/frontier/cascade_f1_calibration/ (PR #971, F1 cascade comparison)",
            "RQ59": "results/frontier/cascade_youdens_j/ (PR #974, Youden's J cascade framework reuse)",
        },
        "source_data": {
            "rq43_json": str(RQ43_JSON.relative_to(PROJECT_ROOT)),
            "rq43_label": "experimental/frontier",
            "aishell4_json": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
            "aishell4_label": "external/sanity-check",
            "aishell4_asr_model": "whisper-tiny",
        },
        "method": (
            "REANALYSIS (no ASR / no LLM run). Loads RQ43's 77 per-window "
            "(tiny_sep_cpwer, base_sep_cpwer, kl_sep) so the cascade corpus is "
            "byte-identical to RQ43/RQ46/RQ54/RQ59. Cost model (task METHOD): "
            "cascade compute = 1.0 + 0.428031 * fraction_escalated (tiny 1.0x, "
            "base adds 0.428031x = RQ43's separated base/tiny CER ratio). For "
            "each KL threshold on the 0.01-step grid [0.01, 8.53] (853 points): "
            "compute cascade cpWER, cascade compute, cpWER/compute ratio, and "
            "marginal efficiency (baseline-cpWER reduction per compute "
            "increment). Cost-aware operating point = threshold MINIMISING "
            "cpWER/compute (primary; lower ratio = less error per compute unit "
            "= better, consistent with H63c's reference points where RQ54's "
            "lower ratio marks the better cascade). Bootstrap B=10000 seed=42: "
            "per resample re-select the min-ratio threshold on in-bag windows, "
            "evaluate cascade cpWER and compute on OOB windows (RQ44 OOB "
            "protocol). BCa 95% CI on the OOB cpWER distribution (z0 from the "
            "in-sample point estimate; acceleration from a delete-1 jackknife). "
            "Secondary objectives (literal max cpWER/compute; marginal-"
            "efficiency max) reported for transparency."
        ),
        "efficiency_operationalisation_note": (
            "The task METHOD writes 'Pareto efficiency = cpWER/compute; select "
            "maximising'. cpWER is a LOSS (lower is better), so the raw ratio "
            "cpWER/compute is maximised at the all-tiny corner (no escalation, "
            "compute 1.0x) -- a degenerate point that fails H63b trivially -- "
            "and minimised at the most-aggressive escalation. H63c's reference "
            "points (RQ43 0.889/1.4=0.635, RQ54 0.780/1.77=0.441) show the "
            "BETTER cascade (RQ54, lower cpWER) has the LOWER ratio, so "
            "'strictly better ratio' means LOWER cpWER/compute. RQ63 therefore "
            "operationalises the cost-aware objective as MINIMISING cpWER/compute "
            "(= maximising compute/cpWER efficiency). The literal maximise-"
            "cpWER/compute point (all-tiny) and the marginal-efficiency max are "
            "reported as secondary objectives."
        ),
        "n_windows": n,
        "n_hallucinated": n_hall,
        "n_clean": n_clean,
        "hallucination_label_rule": "tiny_sep_cpwer > 1.0 (== always_separated_cpwer > 1.0)",
        "kl_grid": {"step": 0.01, "lo": 0.01, "hi": 8.53, "n_points": len(KL_THRESHOLD_GRID)},
        "compute_model": {
            "tiny": COMPUTE_TINY,
            "base_add": COMPUTE_BASE_ADD,
            "base": COMPUTE_BASE,
            "formula": "1.0 + 0.428031 * fraction_escalated",
            "source": "RQ43 model_scale separated base/tiny CER ratio (0.428031) reused as compute surcharge per task METHOD",
            "differs_from_rq54_rq59": ("RQ54/RQ59 used COMPUTE_BASE=1.93 (runtime_cascade); "
                                       "RQ63 uses base-add=0.428031 per task METHOD. Only the "
                                       "compute axis changes; cpWER anchors reproduce exactly."),
        },
        "baseline": {"cpwer": BASELINE_CPWER, "compute": BASELINE_COMPUTE,
                     "name": "always-tiny-separated (no escalation)"},
        "bootstrap": {"n_boot": N_BOOT, "seed": SEED, "resample_size": n,
                      "oob_protocol": "RQ44 out_of_bag (select in-bag, evaluate OOB)",
                      "expected_oob_size": round(n * ((1 - 1 / n) ** n), 4),
                      "mean_oob_size": round(n_oob_mean, 4)},
        "bca_method": {
            "theta_hat": "in-sample cascade cpWER at the cost-aware (min-ratio) threshold",
            "boot_samples": "OOB cascade cpWER per resample",
            "acceleration": "delete-1 jackknife (in-sample cascade cpWER on n-1 at the LOO min-ratio threshold)",
            "bias_correction": "z0 = Phi^{-1}( #{boot < theta_hat} / B ), clamped to (0.5/B, 1-0.5/B)",
            "normal_inverse": "Acklam rational approximation + 1 Halley step (no scipy)",
        },
        "rq43_reference": {
            "kl_threshold": RQ43_KL_THRESHOLD,
            "cascade_cpwer": round(rq43_cas, 6),
            "cascade_compute": round(rq43_compute, 6),
            "escalation_fraction": round(rq43_frac, 6),
            "cpwer_per_compute": round(rq43_ratio_new, 6),
            "task_brief_compute": TASK_RQ43_COMPUTE,
            "task_brief_cpwer": TASK_RQ43_CPWER,
            "task_brief_ratio": round(rq43_ratio_task, 6),
        },
        "rq54_reference": {
            "kl_threshold": RQ54_KL_THRESHOLD,
            "cascade_cpwer": round(rq54_cpwer, 6),
            "cascade_compute": round(rq54_compute, 6),
            "escalation_fraction": round(rq54_frac, 6),
            "cpwer_per_compute": round(rq54_ratio_new, 6),
            "oob_median_cpwer": RQ54_OOB_MEDIAN_CPWER,
            "task_brief_compute": TASK_RQ54_COMPUTE,
            "task_brief_cpwer": TASK_RQ54_CPWER,
            "task_brief_ratio": round(rq54_ratio_task, 6),
        },
        "rq59_reference": {
            "kl_threshold": RQ59_KL_THRESHOLD,
            "cascade_cpwer": round(rq59_cpwer, 6),
            "cascade_compute": round(rq59_compute, 6),
            "escalation_fraction": round(rq59_frac, 6),
            "note": "RQ59 (Youden's J) collapses to the SAME operating point as RQ54 (F1): KL=0.01, 83.1% escalation.",
        },
        "in_sample_cost_aware_point_primary": {
            "objective": "minimise cpWER/compute (cost-aware: least error per compute unit)",
            "threshold": round(ca_min["threshold"], 6),
            "cascade_cpwer": round(ca_min["cpwer"], 6),
            "cascade_compute": round(ca_min["compute"], 6),
            "escalation_fraction": round(ca_min["frac"], 6),
            "cpwer_per_compute": round(ca_min["ratio"], 6),
            "marginal_efficiency": round(marginal_efficiency(ca_min["cpwer"], ca_min["compute"]), 6),
        },
        "in_sample_cost_aware_point_secondary_max_ratio": {
            "objective": "maximise cpWER/compute (literal task METHOD reading)",
            "threshold": round(ca_max["threshold"], 6),
            "cascade_cpwer": round(ca_max["cpwer"], 6),
            "cascade_compute": round(ca_max["compute"], 6),
            "escalation_fraction": round(ca_max["frac"], 6),
            "cpwer_per_compute": round(ca_max["ratio"], 6),
            "note": ("Literal maximise-cpWER/compute collapses to the all-tiny "
                     "corner (no escalation, compute 1.0x) because the ratio is "
                     "monotonic in escalation. Degenerate; fails H63b trivially."),
        },
        "in_sample_cost_aware_point_secondary_marginal_eff": {
            "objective": "maximise marginal efficiency (baseline-cpWER reduction per compute increment)",
            "threshold": round(ca_marg["threshold"], 6),
            "cascade_cpwer": round(ca_marg["cpwer"], 6),
            "cascade_compute": round(ca_marg["compute"], 6),
            "escalation_fraction": round(ca_marg["frac"], 6),
            "marginal_efficiency": round(ca_marg["marginal_efficiency"], 6),
        },
        "bootstrap_threshold_distribution": {
            "median": round(float(np.median(boot_thr)), 6),
            "mean": round(float(np.mean(boot_thr)), 6),
            "std": round(float(np.std(boot_thr)), 6),
            "min": round(float(np.min(boot_thr)), 6),
            "max": round(float(np.max(boot_thr)), 6),
            "n_unique": int(np.unique(boot_thr).size),
        },
        "bootstrap_oob_cpwer_distribution": {
            "n_valid": int(np.sum(~np.isnan(boot_oob))),
            "median": round(oob_median, 6),
            "mean": round(oob_mean, 6),
            "min": round(float(np.nanmin(boot_oob)), 6),
            "max": round(float(np.nanmax(boot_oob)), 6),
            "p2_5": round(float(np.nanpercentile(boot_oob, 2.5)), 6),
            "p97_5": round(float(np.nanpercentile(boot_oob, 97.5)), 6),
            "oob_compute_median": round(oob_compute_median, 6),
        },
        "bca_ci": {
            "lo": round(bca["lo"], 6),
            "hi": round(bca["hi"], 6),
            "width": round(bca_width, 6),
            "median": round(bca["median"], 6),
            "z0": round(bca["z0"], 6) if np.isfinite(bca["z0"]) else None,
            "accel": round(bca["accel"], 6),
            "alpha1": round(bca["alpha1"], 6) if np.isfinite(bca["alpha1"]) else None,
            "alpha2": round(bca["alpha2"], 6) if np.isfinite(bca["alpha2"]) else None,
            "method": bca["method"],
            "theta_hat": round(theta_hat, 6),
            "n_valid": int(bca["n_valid"]),
        },
        "jackknife": {
            "accel": round(accel, 6),
            "theta_loo_mean": round(float(np.mean(theta_loo)), 6),
            "theta_loo_min": round(float(np.min(theta_loo)), 6),
            "theta_loo_max": round(float(np.max(theta_loo)), 6),
        },
        "h63c_pareto_check": {
            "cost_aware_point": {"cpwer": round(theta_hat, 6),
                                 "compute": round(ca_compute, 6)},
            "rq43_point": {"cpwer": round(rq43_cas, 6),
                           "compute": round(rq43_compute, 6)},
            "rq54_point": {"cpwer": round(rq54_cpwer, 6),
                           "compute": round(rq54_compute, 6)},
            "dominated_by_rq43": bool(dom_by_rq43),
            "dominated_by_rq54": bool(dom_by_rq54),
            "cost_aware_ratio": round(ca_ratio, 6),
            "rq43_ratio": round(rq43_ratio_new, 6),
            "rq54_ratio": round(rq54_ratio_new, 6),
            "ratio_strictly_below_rq43": bool(ratio_below_rq43),
            "ratio_strictly_below_rq54": bool(ratio_below_rq54),
        },
        "hypothesis_verdicts": {
            "H63a": {
                "statement": ("Cost-aware escalation < 83.1% (less aggressive than "
                              "F1/J's 83.1%)"),
                "escalation_fraction": round(ca_frac, 6),
                "rq54_rq59_reference_escalation": RQ54_ESCALATION,
                "max_escalation": H63A_MAX_ESCALATION,
                "kill": f"escalation fraction >= {H63A_MAX_ESCALATION}",
                "supported": bool(h63a_supported),
            },
            "H63b": {
                "statement": ("Cost-aware OOB cpWER <= 0.889 (matches RQ43's "
                              "original-rule cpWER 0.888947)"),
                "median_cpwer": round(oob_median, 6),
                "rq43_reference_cpwer": RQ43_CASCADE_CPWER,
                "max_cpwer": H63B_MAX_CPWER,
                "kill": f"median cpWER > {H63B_MAX_CPWER}",
                "supported": bool(h63b_supported),
            },
            "H63c": {
                "statement": ("Cost-aware cpWER/compute ratio strictly better "
                              "(lower) than both RQ43 and RQ54, and NOT Pareto-"
                              "dominated by either"),
                "cost_aware_ratio": round(ca_ratio, 6),
                "rq43_ratio": round(rq43_ratio_new, 6),
                "rq54_ratio": round(rq54_ratio_new, 6),
                "dominated_by_rq43": bool(dom_by_rq43),
                "dominated_by_rq54": bool(dom_by_rq54),
                "kill": "dominated by RQ43 or RQ54, OR ratio not strictly below both",
                "supported": bool(h63c_supported),
            },
        },
        "pareto_frontier": frontier,
        "per_bootstrap": {
            "thresholds": [round(float(t), 6) for t in boot_thr],
            "oob_cpwer": [round(float(c), 6) if not math.isnan(float(c)) else None
                          for c in boot_oob],
            "oob_compute": [round(float(c), 6) if not math.isnan(float(c)) else None
                            for c in boot_oob_compute],
            "n_oob": [int(x) for x in boot["n_oob"]],
        },
        "plot_note": (
            "Pareto frontier plot (task METHOD step 6) omitted: matplotlib is "
            "not installed in this environment. The full frontier is in the "
            "pareto_frontier array (cpwer vs compute vs cpwer_per_compute vs "
            "marginal_efficiency per threshold) and is plottable downstream."
        ),
    }
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_bootstrap_csv(OUT_CSV, boot["boot_idx"], boot_thr, boot_oob,
                        boot_oob_compute, boot["n_oob"], boot["n_escalated_oob"], n)

    # --- console
    print(f"=== RQ63: Cost-aware cascade Pareto ===")
    print(f"Label: experimental/frontier  |  Closes #987  |  n={n} AISHELL-4 windows "
          f"({n_hall} hall / {n_clean} clean)")
    print(f"Cost model: compute = 1.0 + 0.428031 * frac  (tiny 1.0x, base 1.428x)")
    print(f"RQ43 @ KL=3.30: cpwer={rq43_cas:.4f} compute={rq43_compute:.4f}x "
          f"frac={rq43_frac:.1%} ratio={rq43_ratio_new:.4f}")
    print(f"RQ54 @ KL=0.01: cpwer={rq54_cpwer:.4f} compute={rq54_compute:.4f}x "
          f"frac={rq54_frac:.1%} ratio={rq54_ratio_new:.4f}")
    print()
    print(f"Cost-aware (PRIMARY, min cpWER/compute):")
    print(f"  KL threshold = {ca_min['threshold']:.4f}  cpwer={ca_min['cpwer']:.4f}  "
          f"compute={ca_min['compute']:.4f}x  frac={ca_min['frac']:.1%}  "
          f"ratio={ca_min['ratio']:.4f}")
    print(f"  (RQ43 ratio={rq43_ratio_new:.4f}, RQ54 ratio={rq54_ratio_new:.4f})")
    print(f"Cost-aware (secondary, max cpWER/compute -> all-tiny):")
    print(f"  KL threshold = {ca_max['threshold']:.4f}  cpwer={ca_max['cpwer']:.4f}  "
          f"compute={ca_max['compute']:.4f}x  frac={ca_max['frac']:.1%}  "
          f"ratio={ca_max['ratio']:.4f}")
    print(f"Cost-aware (secondary, max marginal efficiency):")
    print(f"  KL threshold = {ca_marg['threshold']:.4f}  cpwer={ca_marg['cpwer']:.4f}  "
          f"compute={ca_marg['compute']:.4f}x  frac={ca_marg['frac']:.1%}  "
          f"marg_eff={ca_marg['marginal_efficiency']:.4f}")
    print()
    print(f"Bootstrap B={N_BOOT} seed={SEED} (OOB, re-selected min-ratio threshold):")
    print(f"  threshold: median={np.median(boot_thr):.4f}  "
          f"n_unique={np.unique(boot_thr).size}")
    print(f"  OOB cpWER: median={oob_median:.4f}  mean={oob_mean:.4f}  "
          f"pct[{np.nanpercentile(boot_oob,2.5):.4f},{np.nanpercentile(boot_oob,97.5):.4f}]")
    print(f"  OOB compute median={oob_compute_median:.4f}x")
    print(f"  BCa CI: [{bca['lo']:.4f}, {bca['hi']:.4f}]  width={bca_width:.4f}  "
          f"(z0={bca['z0']:.4f}, a={accel:.4f}, method={bca['method']})")
    print()
    print("Hypothesis verdicts (PRIMARY min-ratio cost-aware point):")
    print(f"  H63a (escalation < {H63A_MAX_ESCALATION:.1%}):  "
          f"{'SUPPORTED' if h63a_supported else 'KILLED'}  "
          f"(frac={ca_frac:.4f}, RQ54 ref={RQ54_ESCALATION:.4f})")
    print(f"  H63b (median cpWER <= {H63B_MAX_CPWER}):  "
          f"{'SUPPORTED' if h63b_supported else 'KILLED'}  (median={oob_median:.4f})")
    print(f"  H63c (ratio < both & not dominated):  "
          f"{'SUPPORTED' if h63c_supported else 'KILLED'}  "
          f"(ratio={ca_ratio:.4f}, RQ43={rq43_ratio_new:.4f}, RQ54={rq54_ratio_new:.4f}; "
          f"dom_rq43={dom_by_rq43}, dom_rq54={dom_by_rq54})")
    print()
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
