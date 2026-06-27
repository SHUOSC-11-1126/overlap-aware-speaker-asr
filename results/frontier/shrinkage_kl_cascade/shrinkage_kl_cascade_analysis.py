"""RQ69: Cascade with shrinkage-calibrated KL gate.

REANALYSIS ONLY -- no Whisper / no ASR / no LLM model is run. RQ62 (PR #992)
showed the KL+lang-id ensemble cascade gate gives 55.8% escalation (escaping
RQ59's 83.1% collapse) but OOB cpWER 0.942 > 0.889 (RQ43 baseline). RQ61
(PR #991) showed shrinkage calibration eliminates the pathological 0.01 Mode S
mode on the lang-id detector. RQ69 asks: does replacing the raw KL gate with a
shrinkage-calibrated KL gate improve the cascade's OOB cpWER?

Label: experimental/frontier. Closes #997.

Controlled comparison design
----------------------------
The cascade simulation is held fixed at RQ43's actual implementation (RQ59 /
RQ62 convention) so the comparison to RQ43's 0.888947 anchor (H69a), RQ59's
83.1% escalation (H69b), and RQ59's 0.2827 BCa width (H69c) is apples-to-apples:

- Tier 1 (whisper-tiny) cpWER per window = RQ43's ``tiny_sep_cpwer`` (the real
  whisper-tiny separated-audio cpWER; == ``always_separated_cpwer`` in
  AISHELL-4, verified in tests).
- Tier 3 (whisper-base) cpWER per window = RQ43's ``base_sep_cpwer`` =
  ``tiny_sep_cpwer * 0.428031`` (the model_scale separated base/tiny CER
  ratio, constant across overlap). This is RQ43's actual base-cpWER estimate.
- Tier 2 (KL gate): escalate to base when RQ43's character-bigram asymmetric
  KL divergence of the tiny transcript (``kl_sep``, range [0, 8.5255]) >= the
  SHRINKAGE-CALIBRATED threshold.

The ONLY independent variable vs RQ59 (Youden's J) and RQ62 (ensemble OR) is
the calibration rule: RQ69 uses RQ61's shrinkage calibration
(``sensitivity - lambda * |t_norm - prior_mean_norm|`` at >= 90% specificity)
with a Beta(2,2) posterior-mode prior, applied to the KL detector threshold.

Beta(2,2) posterior mode prior
------------------------------
RQ61 used ``prior_mean = 0.38`` (the lang-id bootstrap median, data-derived).
RQ69 replaces this with a Bayesian Beta(2,2) prior on the hallucination rate,
updated by the observed class counts:

    prior:        Beta(alpha=2, beta=2)         (mode 0.5, weakly informative)
    likelihood:   Binomial(n, p) with k=37 hallucinated out of n=77
    posterior:    Beta(2 + 37, 2 + 40) = Beta(39, 42)
    posterior mode = (alpha' - 1) / (alpha' + beta' - 2) = 38 / 79 ~= 0.481013

The posterior mode 0.481013 is the shrinkage target on the NORMALISED KL
threshold scale [0, 1] (``t_norm = t / kl_max``). The prior is data-informed
(it incorporates the 37/40 class balance) but regularised toward 0.5 by the
Beta(2,2) prior, unlike RQ61's pure data-derived 0.38. The shrinkage penalty
operates on the normalised scale so ``lambda`` has the same meaning as RQ61
(penalty in [0, ~0.5], comparable to sensitivity in [0, 1]).

Method
------
1. Load RQ43's 77 per-window (tiny_sep_cpwer, base_sep_cpwer, kl_sep) from
   ``three_tier_cascade_results.json`` (so the cascade corpus is byte-identical
   to RQ43/RQ59/RQ62). Verify n=77, baseline 1.590909, and that the in-sample
   cascade @ KL=3.30 (RQ43's original rule) reproduces 0.888947.
2. Labels = tiny_sep_cpwer > 1.0 (37 hall / 40 clean).
3. Compute the Beta(2,2) posterior mode: 38/79 ~= 0.481013 (normalised scale).
4. In-sample shrinkage calibration (per lambda in {0.0, 0.01, 0.1, 0.5, 1.0}):
   maximise ``sensitivity(t) - lambda * |t_norm - prior_mean_norm|`` subject to
   specificity >= 0.90, over the 0.01-step KL grid [0.00, 8.55]. At lambda=0
   this reduces to RQ44's max-sensitivity-at-90%-specificity rule.
5. In-sample cascade cpWER (theta_hat), escalation fraction, compute cost at
   the calibrated threshold (per lambda).
6. Bootstrap B=10000, seed=42: for each resample, re-calibrate the shrinkage
   KL threshold on the in-bag windows and evaluate the cascade cpWER on the
   out-of-bag (OOB) windows (RQ44's OOB protocol). Records the per-resample
   threshold (for mode counting) and OOB cpWER (for the BCa CI).
7. Delete-1 jackknife (77 fits) for the BCa acceleration, at the best lambda.
8. BCa 95% CI on the OOB cpWER distribution (bias-corrected + accelerated;
   Acklam inverse-normal, no scipy) at the best lambda.
9. Mode count on the bootstrap threshold distribution (RQ48's ``count_modes``,
   min_fraction=0.05).
10. Best-lambda selection: lowest OOB cpWER median (H69a is the primary), then
    narrowest BCa width, then fewest modes, then smallest lambda.
11. Pre-registered hypothesis verdicts H69a/b/c at the best lambda.

Pre-registered hypotheses
-------------------------
- H69a: Shrinkage KL cascade OOB cpWER < 0.889 (RQ43 baseline). KILL if >=
        0.889.
- H69b: Shrinkage KL cascade escalation rate < 83.1% (RQ59 baseline). KILL if
        >= 83.1%.
- H69c: Shrinkage KL cascade BCa width < 0.283 (RQ59 baseline). KILL if >=
        0.283.

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / Whisper
are NOT required). The BCa CI helpers (norm_cdf, norm_ppf, bca_ci) and the
jackknife acceleration structure are imported verbatim from RQ59 (PR #980);
count_modes is imported verbatim from RQ48 (PR #965); the shrinkage objective
mirrors RQ61's ``shrinkage_objective`` (PR #991) on the normalised KL scale.
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
RQ59_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "cascade_youdens_j"
    / "cascade_youdens_j_results.json"
)
RQ62_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "ensemble_cascade_gate"
    / "ensemble_cascade_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "shrinkage_kl_cascade"
OUT_JSON = OUT_DIR / "shrinkage_kl_cascade_results.json"
OUT_CSV = OUT_DIR / "shrinkage_kl_cascade_results.csv"

# ------------------------------------------ import RQ59's BCa + RQ48's count_modes (verbatim reuse)
# RQ59 (PR #980) contributes the BCa CI scaffolding (norm_cdf, norm_ppf, bca_ci)
# and the jackknife acceleration structure; reusing them guarantees the CI
# methodology is byte-identical to RQ59/RQ62 (only the gate changes: shrinkage-
# calibrated KL here). RQ48 (PR #965) contributes count_modes. RQ44 (PR #963)
# contributes EPS and the bootstrap index draw convention.
_RQ59_DIR = PROJECT_ROOT / "results" / "frontier" / "cascade_youdens_j"
_RQ48_DIR = PROJECT_ROOT / "results" / "frontier" / "calibration_rule_comparison"
_RQ44_DIR = PROJECT_ROOT / "results" / "frontier" / "bootstrap_threshold_stability"
sys.path.insert(0, str(_RQ59_DIR))
sys.path.insert(0, str(_RQ48_DIR))
sys.path.insert(0, str(_RQ44_DIR))
import cascade_youdens_j_analysis as rq59  # noqa: E402  (path-injected import)
import calibration_rule_analysis as rq48  # noqa: E402  (path-injected import)
import bootstrap_threshold_analysis as rq44  # noqa: E402  (path-injected import)

# ------------------------------------------------------------------ constants
# RQ59's BCa CI helpers and RQ48's mode counter, re-exported for traceability.
norm_cdf = rq59.norm_cdf       # standard-normal forward CDF (erfc-based, no scipy)
norm_ppf = rq59.norm_ppf       # standard-normal inverse CDF (Acklam + Halley)
bca_ci = rq59.bca_ci           # BCa 95% CI (bias-corrected + accelerated)
count_modes = rq48.count_modes  # RQ48's >= 5% mode counter
EPS = rq44.EPS                          # 1e-9 (RQ44/RQ48/RQ59 tolerance)

# KL threshold grid: 0.01 step spanning RQ43's observed KL range [0.0, 8.5255].
# Identical to RQ59's grid so the lambda=0 (no-shrinkage) baseline and the
# shrinkage lambda > 0 cases are compared on the same grid.
KL_THRESHOLD_GRID = [round(0.01 * i, 2) for i in range(0, 856)]  # 0.00 .. 8.55

N_BOOT = 10000            # bootstrap iterations (>= task's B=1000 minimum; BCa needs B)
SEED = 42                 # task-specified seed
MIN_MODE_FRACTION = 0.05  # "mode" = distinct threshold with >= 5% frequency (RQ48)
ALPHA = 0.05              # 95% CI
TARGET_SPECIFICITY = 0.90  # shrinkage calibration at >= 90% specificity (RQ44/RQ61)

COMPUTE_TINY = 1.0        # whisper-tiny relative compute (RQ43)
COMPUTE_BASE = 1.93       # whisper-base relative compute (RQ43 / runtime_cascade)
CATASTROPHIC_CPWER = 1.0  # cpWER > 1.0 => hallucination label (RQ44/RQ48/RQ59)

# Shrinkage prior: Beta(2,2) posterior mode of the hallucination rate.
# Prior Beta(2,2) (mode 0.5); observe k=37 hallucinated out of n=77; posterior
# Beta(39, 42); mode = (39-1)/(39+42-2) = 38/79 ~= 0.4810126582.
BETA_PRIOR_ALPHA = 2.0
BETA_PRIOR_BETA = 2.0
PRIOR_MEAN_NORM = 38.0 / 79.0   # Beta(2+37, 2+40) posterior mode (normalised [0,1])
LAMBDAS = [0.0, 0.01, 0.1, 0.5, 1.0]   # RQ61's lambda grid (best was 1.0)

# RQ43 / RQ59 / RQ62 anchors (the controlled-comparison reference values).
RQ43_KL_THRESHOLD = 3.30             # RQ43's original n=3 KL threshold (kl_sep)
RQ43_CASCADE_CPWER = 0.888947        # RQ43 in-sample cascade cpWER @ KL=3.30
RQ43_BASELINE_CPWER = 1.590909       # always-tiny-separated
RQ43_BASE_RATIO = 0.428031           # model_scale separated base/tiny CER ratio
RQ59_YOUDENS_J_ESCALATION = 0.831169  # RQ59's Youden's J escalation (H69b anchor)
RQ59_YOUDENS_J_OOB_MEDIAN_CPWER = 0.782394  # RQ59's Youden's J OOB median cpWER
RQ59_YOUDENS_J_BCA_WIDTH = 0.282660   # RQ59's Youden's J BCa width (H69c anchor)
RQ62_OR_OOB_MEDIAN_CPWER = 0.9423     # RQ62's ensemble OR OOB median cpWER
RQ62_OR_BCA_WIDTH = 0.2391            # RQ62's ensemble OR BCa width
RQ62_OR_ESCALATION = 0.5584           # RQ62's ensemble OR escalation

# Hypothesis kill thresholds.
H69A_MAX_CPWER = 0.889        # H69a: kill if OOB median cpWER >= 0.889
H69B_MAX_ESCALATION = 0.831   # H69b: kill if escalation fraction >= 0.831
H69C_MAX_WIDTH = 0.283        # H69c: kill if BCa width >= 0.283


# --------------------------------------------------------------- Beta(2,2) prior
def beta_posterior_mode(
    alpha_prior: float, beta_prior: float, k_success: int, n_total: int
) -> float:
    """Mode of the Beta posterior after a binomial update.

    prior:        Beta(alpha_prior, beta_prior)
    likelihood:   Binomial(n_total, p) observing k_success successes
    posterior:    Beta(alpha_prior + k_success, beta_prior + (n_total - k_success))
    posterior mode (when alpha' > 1 and beta' > 1):
        (alpha' - 1) / (alpha' + beta' - 2)

    Returns 0.0 for the degenerate case where the posterior is not unimodal
    (alpha' <= 1 or beta' <= 1); the mean is returned as a fallback for
    alpha' = 1 or beta' = 1 (uniform / J-shaped posteriors). Used to compute
    the Beta(2,2) posterior mode shrinkage prior from the class counts."""
    a_post = float(alpha_prior) + float(k_success)
    b_post = float(beta_prior) + float(n_total - k_success)
    if a_post > 1.0 and b_post > 1.0:
        return (a_post - 1.0) / (a_post + b_post - 2.0)
    # Fallback: posterior mean (always defined for a_post, b_post > 0).
    if a_post + b_post > 0.0:
        return a_post / (a_post + b_post)
    return 0.5


# --------------------------------------------------------------- shrinkage objective
def shrinkage_objective(
    threshold_norm: float, sensitivity: float, prior_mean_norm: float, lam: float
) -> float:
    """The regularised calibration objective on the NORMALISED scale:
    ``sensitivity - lam * |t_norm - prior_mean_norm|``.

    Mirrors RQ61's ``shrinkage_objective`` but on [0, 1] (KL threshold divided
    by ``kl_max``) so ``lam`` has the same meaning as RQ61 (penalty in
    [0, ~0.5], comparable to sensitivity in [0, 1]). At ``lam = 0`` the
    objective reduces to pure sensitivity (RQ44's max-sensitivity-at-90%-
    specificity rule). The penalty pulls the threshold toward ``prior_mean_norm``
    (the Beta(2,2) posterior mode): when two thresholds tie on sensitivity, the
    one closer to the prior has the higher objective."""
    return float(sensitivity) - float(lam) * abs(
        float(threshold_norm) - float(prior_mean_norm))


# --------------------------------------------------------------- confusion helper
def _confusion_arrays(
    scores: np.ndarray, labels: np.ndarray, grid_arr: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, int]:
    """Vectorised confusion-matrix sweep over ``grid_arr`` (RQ48/RQ61 helper).

    For each grid threshold ``t`` (ascending), flag = ``score >= t`` (with EPS
    tolerance, matching RQ44/RQ48). Returns ``(tp, fp, tn, fn, n_pos, n_neg)``
    as int arrays of shape ``(len(grid),)``."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    grid_arr = np.asarray(grid_arr, dtype=float)
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    n_pos = int(len(pos))
    n_neg = int(len(neg))
    if n_pos > 0:
        tp = (pos[None, :] >= grid_arr[:, None] - EPS).sum(axis=1).astype(int)
    else:
        tp = np.zeros(grid_arr.shape, dtype=int)
    if n_neg > 0:
        fp = (neg[None, :] >= grid_arr[:, None] - EPS).sum(axis=1).astype(int)
    else:
        fp = np.zeros(grid_arr.shape, dtype=int)
    tn = n_neg - fp
    fn = n_pos - tp
    return tp, fp, tn, fn, n_pos, n_neg


def _sens_spec(
    tp: np.ndarray, fp: np.ndarray, tn: np.ndarray, fn: np.ndarray,
    n_pos: int, n_neg: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Sensitivity / specificity arrays with safe division (RQ48/RQ61 helper).

    sensitivity = tp / n_pos (0 if n_pos == 0); specificity = tn / n_neg
    (1 if n_neg == 0)."""
    safe_pos = n_pos if n_pos > 0 else 1
    safe_neg = n_neg if n_neg > 0 else 1
    sens = tp / safe_pos if n_pos > 0 else np.zeros(tp.shape, dtype=float)
    spec = tn / safe_neg if n_neg > 0 else np.ones(tn.shape, dtype=float)
    return sens, spec


# --------------------------------------------------------------- shrinkage selection
def _select_shrinkage(
    grid_arr: np.ndarray,
    sens: np.ndarray,
    spec: np.ndarray,
    tp: np.ndarray,
    fp: np.ndarray,
    tn: np.ndarray,
    fn: np.ndarray,
    kl_max: float,
    prior_mean_norm: float,
    lam: float,
    target_spec: float,
) -> dict[str, Any]:
    """Pick the grid threshold maximising
    ``sensitivity - lam * |t/kl_max - prior_mean_norm|`` subject to
    ``specificity >= target_spec``.

    Tie-break: higher objective -> higher specificity -> lower threshold (the
    last via the first True in the ascending grid). At ``lam = 0`` this matches
    RQ44's ``calibrate_threshold_at_spec`` exactly (max sensitivity at
    >= target_spec specificity, tie-break higher specificity then lower
    threshold). The penalty operates on the NORMALISED threshold (t / kl_max)
    so ``lam`` is scale-free."""
    grid_arr = np.asarray(grid_arr, dtype=float)
    t_norm = grid_arr / kl_max if kl_max > 0 else grid_arr
    penalty = lam * np.abs(t_norm - prior_mean_norm)
    objective = sens - penalty
    feasible = spec >= target_spec - EPS
    if not feasible.any():
        # Fallback: highest grid threshold (most conservative: flag nothing),
        # matching RQ44/RQ61's fallback.
        t_max = float(grid_arr[-1])
        return {
            "threshold": t_max,
            "sensitivity": 0.0,
            "specificity": 1.0,
            "tp": 0, "fp": 0,
            "tn": int(tn[-1] if tn.size else 0),
            "fn": int(fn[-1] if fn.size else 0),
            "objective": float(0.0 - lam * abs(t_max / kl_max - prior_mean_norm))
                         if kl_max > 0 else 0.0,
            "penalty": float(lam * abs(t_max / kl_max - prior_mean_norm))
                       if kl_max > 0 else 0.0,
            "threshold_norm": float(t_max / kl_max) if kl_max > 0 else 0.0,
        }
    # Mask infeasible objectives to -inf so they never win.
    obj_masked = np.where(feasible, objective, -np.inf)
    best_val = float(np.max(obj_masked))
    # Tie-break 1: highest objective (within EPS).
    tie1 = (obj_masked >= best_val - EPS) & feasible
    # Tie-break 2: highest specificity.
    spec_masked = np.where(tie1, spec, -np.inf)
    best_spec = float(np.max(spec_masked))
    tie2 = tie1 & (spec >= best_spec - EPS)
    # Tie-break 3: lowest threshold (first True in ascending grid).
    idx = int(np.argmax(tie2))
    return {
        "threshold": float(grid_arr[idx]),
        "sensitivity": float(sens[idx]),
        "specificity": float(spec[idx]),
        "tp": int(tp[idx]),
        "fp": int(fp[idx]),
        "tn": int(tn[idx]),
        "fn": int(fn[idx]),
        "objective": float(objective[idx]),
        "penalty": float(penalty[idx]),
        "threshold_norm": float(grid_arr[idx] / kl_max) if kl_max > 0 else 0.0,
    }


def calibrate_shrinkage_kl(
    kl: np.ndarray,
    labels: np.ndarray,
    kl_max: float,
    prior_mean_norm: float = PRIOR_MEAN_NORM,
    lam: float = 0.0,
    grid: list[float] | None = None,
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """Shrinkage calibration on the KL detector: among thresholds with
    specificity >= ``target_spec``, maximise
    ``sensitivity - lam * |t/kl_max - prior_mean_norm|``.

    At ``lam = 0`` this reproduces RQ44's max-sensitivity-at-90%-specificity
    rule (the no-shrinkage baseline). At ``lam > 0`` the penalty pulls the
    threshold toward ``prior_mean_norm * kl_max`` (the Beta(2,2) posterior-mode
    target on the KL scale). The penalty is on the normalised scale so ``lam``
    is comparable to RQ61."""
    if grid is None:
        grid = KL_THRESHOLD_GRID
    grid_arr = np.asarray(grid, dtype=float)
    kl = np.asarray(kl, dtype=float)
    labels = np.asarray(labels, dtype=int)
    tp, fp, tn, fn, n_pos, n_neg = _confusion_arrays(kl, labels, grid_arr)
    sens, spec = _sens_spec(tp, fp, tn, fn, n_pos, n_neg)
    return _select_shrinkage(
        grid_arr, sens, spec, tp, fp, tn, fn,
        kl_max, prior_mean_norm, lam, target_spec,
    )


# --------------------------------------------------------------- cascade simulation
def cascade_cpwer_at_threshold(
    tiny: np.ndarray, base: np.ndarray, kl: np.ndarray, threshold: float
) -> float:
    """In-sample cascade cpWER at ``threshold``.

    Escalation: ``kl >= threshold - EPS`` -> base (else tiny). Uses the
    ``>= - EPS`` convention to match RQ48/RQ59/RQ62 flagging."""
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    if tiny.size == 0:
        return 0.0
    escalated = kl >= threshold - EPS
    selected = np.where(escalated, base, tiny)
    return float(selected.mean())


def cascade_compute_at_threshold(kl: np.ndarray, threshold: float) -> float:
    """Cascade compute = 1.0*(1-f) + 1.93*f, f = escalation fraction.

    The KL gate cost is negligible and folded into the 1.0x tiny budget
    (RQ43 convention)."""
    kl = np.asarray(kl, dtype=float)
    if kl.size == 0:
        return 0.0
    frac = float(np.mean(kl >= threshold - EPS))
    return COMPUTE_TINY * (1.0 - frac) + COMPUTE_BASE * frac


def escalation_fraction_at_threshold(kl: np.ndarray, threshold: float) -> float:
    """Fraction of windows escalated to base at ``threshold``
    (``kl >= threshold - EPS``)."""
    kl = np.asarray(kl, dtype=float)
    if kl.size == 0:
        return 0.0
    return float(np.mean(kl >= threshold - EPS))


def cascade_oob_cpwer(
    tiny: np.ndarray,
    base: np.ndarray,
    kl: np.ndarray,
    threshold: float,
    in_bag_idx: np.ndarray,
) -> dict[str, Any]:
    """Cascade cpWER on the out-of-bag (OOB) windows at ``threshold``.

    Mirrors RQ44's / RQ59's / RQ62's OOB protocol but routes escalated windows
    to ``base`` (whisper-base) and non-escalated to ``tiny`` (whisper-tiny).
    Returns the mean selected cpWER over the OOB windows (``nan`` if there are
    none), the OOB size, and the escalation count."""
    n = len(kl)
    all_idx = np.arange(n)
    in_bag_set = np.unique(np.asarray(in_bag_idx, dtype=int))
    oob_mask = ~np.isin(all_idx, in_bag_set)
    n_oob = int(oob_mask.sum())
    if n_oob == 0:
        return {"cpwer": float("nan"), "n_oob": 0, "n_escalated": 0}
    oob_kl = kl[oob_mask]
    oob_tiny = tiny[oob_mask]
    oob_base = base[oob_mask]
    escalated = oob_kl >= threshold - EPS
    selected = np.where(escalated, oob_base, oob_tiny)
    return {"cpwer": float(selected.mean()), "n_oob": n_oob,
            "n_escalated": int(escalated.sum())}


# --------------------------------------------------------------- bootstrap shrinkage cascade
def bootstrap_shrinkage_cascade(
    tiny: np.ndarray,
    base: np.ndarray,
    kl: np.ndarray,
    labels: np.ndarray,
    kl_max: float,
    prior_mean_norm: float,
    lam: float,
    grid: list[float] | None = None,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, np.ndarray]:
    """Bootstrap the shrinkage-calibrated KL cascade over ``n_boot`` resamples.

    For each resample: draw n indices with replacement, re-calibrate the
    shrinkage KL threshold (maximise
    ``sensitivity - lam * |t/kl_max - prior_mean_norm|`` at >= 90% specificity)
    on the in-bag windows, and evaluate the cascade cpWER on the OOB windows
    (RQ44 OOB protocol). Returns a dict with:
      ``boot_idx``       -- (n_boot, n) int array of resample indices
      ``thresholds``     -- (n_boot,) calibrated KL threshold per resample
      ``oob_cpwer``      -- (n_boot,) OOB cascade cpWER (nan if OOB empty)
      ``n_oob``          -- (n_boot,) OOB size per resample
      ``n_escalated_oob``-- (n_boot,) escalated count within OOB
    """
    if grid is None:
        grid = KL_THRESHOLD_GRID
    grid_arr = np.asarray(grid, dtype=float)
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    labels = np.asarray(labels, dtype=int)
    n = kl.shape[0]
    T = grid_arr.size

    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, n, size=(n_boot, n))  # (B, n)

    thresholds = np.empty(n_boot, dtype=float)
    oob_cpwer = np.empty(n_boot, dtype=float)
    n_oob_arr = np.empty(n_boot, dtype=int)
    n_esc_arr = np.empty(n_boot, dtype=int)

    t_norm_grid = grid_arr / kl_max if kl_max > 0 else grid_arr
    penalty_grid = lam * np.abs(t_norm_grid - prior_mean_norm)

    for b in range(n_boot):
        idx = boot_idx[b]
        kl_in = kl[idx]
        labels_in = labels[idx]
        tp, fp, tn, fn, n_pos, n_neg = _confusion_arrays(kl_in, labels_in, grid_arr)
        sens, spec = _sens_spec(tp, fp, tn, fn, n_pos, n_neg)
        objective = sens - penalty_grid
        feasible = spec >= TARGET_SPECIFICITY - EPS
        if not feasible.any():
            thr = float(grid_arr[-1])
        else:
            obj_masked = np.where(feasible, objective, -np.inf)
            best_val = float(np.max(obj_masked))
            tie1 = (obj_masked >= best_val - EPS) & feasible
            spec_masked = np.where(tie1, spec, -np.inf)
            best_spec = float(np.max(spec_masked))
            tie2 = tie1 & (spec >= best_spec - EPS)
            thr = float(grid_arr[int(np.argmax(tie2))])
        thresholds[b] = thr

        counts = np.bincount(idx, minlength=n)
        oob_mask = counts == 0
        no = int(oob_mask.sum())
        n_oob_arr[b] = no
        if no == 0:
            oob_cpwer[b] = float("nan")
            n_esc_arr[b] = 0
            continue
        esc = kl[oob_mask] >= thr - EPS
        sel = np.where(esc, base[oob_mask], tiny[oob_mask])
        oob_cpwer[b] = float(sel.mean())
        n_esc_arr[b] = int(esc.sum())

    return {
        "boot_idx": boot_idx,
        "thresholds": thresholds,
        "oob_cpwer": oob_cpwer,
        "n_oob": n_oob_arr,
        "n_escalated_oob": n_esc_arr,
    }


# --------------------------------------------------------------- jackknife acceleration
def jackknife_acceleration(
    tiny: np.ndarray, base: np.ndarray, kl: np.ndarray, labels: np.ndarray,
    kl_max: float, prior_mean_norm: float, lam: float,
    grid: list[float] | None = None,
) -> tuple[float, np.ndarray]:
    """Delete-1 jackknife acceleration for the BCa CI (shrinkage KL cascade).

    For each i in 0..n-1: leave window i out, re-calibrate the shrinkage KL
    threshold on the remaining n-1 windows, and compute the in-sample cascade
    cpWER on those n-1 windows (theta_(i)). The acceleration is

        a = sum( (theta_bar - theta_(i))^3 ) / ( 6 * sum( (theta_bar - theta_(i))^2 )^1.5 )

    Returns (a, theta_loo). a = 0.0 when the denominator is 0 (no variation),
    which collapses BCa to the bias-corrected percentile. Mirrors RQ59's /
    RQ62's jackknife structure exactly; only the calibration rule changes
    (shrinkage KL here vs Youden's J / ensemble there)."""
    if grid is None:
        grid = KL_THRESHOLD_GRID
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    labels = np.asarray(labels, dtype=int)
    n = kl.shape[0]
    theta_loo = np.empty(n, dtype=float)
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        cal = calibrate_shrinkage_kl(
            kl[mask], labels[mask], kl_max, prior_mean_norm, lam, grid=grid)
        theta_loo[i] = cascade_cpwer_at_threshold(
            tiny[mask], base[mask], kl[mask], cal["threshold"])
    theta_bar = float(theta_loo.mean())
    diff = theta_bar - theta_loo
    scale = max(abs(theta_bar), 1.0)
    if float(np.max(np.abs(diff))) < 1e-12 * scale:
        return 0.0, theta_loo
    num = float(np.sum(diff ** 3))
    den = 6.0 * (float(np.sum(diff ** 2)) ** 1.5)
    a = num / den if den > 0 else 0.0
    return a, theta_loo


# --------------------------------------------------------------- finite-only stats
def _finite_stats(arr: np.ndarray) -> dict[str, float]:
    """Descriptive stats on the finite subset of ``arr`` (inf/nan dropped).

    The shrinkage threshold distribution can contain ``+inf`` (resamples where
    the in-bag set has too few negatives to meet the >= 90% specificity floor,
    so no finite threshold flags anything). Those resamples are legitimate
    operating points (no KL escalation) and are counted by ``count_modes``,
    but mean/std/min/max are not meaningful with inf mixed in."""
    arr = np.asarray(arr, dtype=float)
    n_total = int(arr.size)
    finite = arr[np.isfinite(arr)]
    n_finite = int(finite.size)
    n_inf = int(np.sum(np.isposinf(arr)))
    if n_finite == 0:
        return {"median": float("nan"), "mean": float("nan"),
                "std": float("nan"), "min": float("nan"),
                "max": float("nan"), "n_finite": 0, "n_inf": n_inf,
                "n_total": n_total, "inf_fraction": round(n_inf / n_total, 6)
                if n_total > 0 else 0.0}
    return {
        "median": round(float(np.median(finite)), 6),
        "mean": round(float(np.mean(finite)), 6),
        "std": round(float(np.std(finite)), 6),
        "min": round(float(np.min(finite)), 6),
        "max": round(float(np.max(finite)), 6),
        "n_finite": n_finite, "n_inf": n_inf, "n_total": n_total,
        "inf_fraction": round(n_inf / n_total, 6) if n_total > 0 else 0.0,
    }


# --------------------------------------------------------------- best-lambda selection
def select_best_lambda(per_lambda_summary: dict[str, Any]) -> dict[str, Any]:
    """Pick the lambda that best satisfies H69a (the primary, strictest gate).

    Criteria (in order):
    1. Lowest OOB cpWER median (H69a is the primary hypothesis).
    2. Narrowest BCa width (H69c).
    3. Fewest modes (n_modes_5pct).
    4. Smallest lambda (least regularisation, most faithful to data).

    ``per_lambda_summary`` is a dict keyed by lambda-string with values
    carrying ``lambda``, ``oob_cpwer_median``, ``bca_width``, ``n_modes_5pct``.
    """
    items = list(per_lambda_summary.items())
    best_key, best_v = min(
        items,
        key=lambda kv: (
            float(kv[1]["oob_cpwer_median"]),
            float(kv[1]["bca_width"]),
            int(kv[1]["n_modes_5pct"]),
            float(kv[1]["lambda"]),
        ),
    )
    return {
        "lambda": float(best_v["lambda"]),
        "lambda_key": best_key,
        "reason": ("selected by lowest OOB cpWER median (H69a primary), then "
                   "narrowest BCa width (H69c), then fewest modes, then "
                   "smallest lambda"),
        "n_modes_5pct": int(best_v["n_modes_5pct"]),
        "bca_width": float(best_v["bca_width"]),
        "oob_cpwer_median": float(best_v["oob_cpwer_median"]),
    }


# --------------------------------------------------------------- hypothesis helpers
def _h69a_supported(oob_median: float) -> bool:
    """H69a: OOB cpWER < 0.889 supported; >= 0.889 killed (strict <)."""
    return float(oob_median) < H69A_MAX_CPWER - EPS


def _h69b_supported(escalation: float) -> bool:
    """H69b: escalation < 0.831 supported; >= 0.831 killed (strict <)."""
    return float(escalation) < H69B_MAX_ESCALATION - EPS


def _h69c_supported(width: float) -> bool:
    """H69c: BCa width < 0.283 supported; >= 0.283 killed (strict <)."""
    return float(width) < H69C_MAX_WIDTH - EPS


# --------------------------------------------------------------- data loading
def load_rq43_per_window() -> dict[str, Any]:
    """Load RQ43's 77 per-window (tiny_sep_cpwer, base_sep_cpwer, kl_sep).

    Reads ``three_tier_cascade_results.json`` ``per_window`` so the cascade
    corpus is byte-identical to RQ43/RQ59/RQ62 (the values are rounded to 6 dp
    in the JSON, which is sufficient to reproduce RQ43's 0.888947 anchor).
    Returns a dict of float arrays and asserts n == 77."""
    data = json.loads(RQ43_JSON.read_text(encoding="utf-8"))
    pw = data["per_window"]
    assert len(pw) == 77, f"expected 77 AISHELL-4 windows, got {len(pw)}"
    tiny = np.array([float(w["tiny_sep_cpwer"]) for w in pw], dtype=float)
    base = np.array([float(w["base_sep_cpwer"]) for w in pw], dtype=float)
    kl = np.array([float(w["kl_sep"]) for w in pw], dtype=float)
    return {"tiny": tiny, "base": base, "kl": kl,
            "window_id": [w["window_id"] for w in pw]}


# --------------------------------------------------------------- CSV output
def write_bootstrap_csv(
    path: Path,
    boot_idx: np.ndarray,
    thresholds: np.ndarray,
    oob_cpwer: np.ndarray,
    n_oob: np.ndarray,
    n_escalated_oob: np.ndarray,
    n_windows: int,
) -> None:
    """Write the per-resample bootstrap table as CSV.

    One row per bootstrap resample (B rows) plus a header. Columns:
    ``resample, threshold, oob_cpwer, n_oob, n_escalated_oob, oob_fraction,
    escalation_fraction_oob``. ``oob_cpwer`` is blank when the OOB set was
    empty (nan)."""
    B = int(thresholds.shape[0])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow([
            "resample", "threshold", "oob_cpwer", "n_oob",
            "n_escalated_oob", "oob_fraction", "escalation_fraction_oob",
        ])
        for b in range(B):
            no = int(n_oob[b])
            cp = float(oob_cpwer[b])
            esc = int(n_escalated_oob[b])
            w.writerow([
                b,
                round(float(thresholds[b]), 6),
                "" if (no == 0 or math.isnan(cp)) else round(cp, 6),
                no,
                esc,
                round(no / n_windows, 6) if n_windows > 0 else 0.0,
                round(esc / no, 6) if no > 0 else "",
            ])


# --------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- load RQ43's cascade corpus (byte-identical to RQ43/RQ59/RQ62)
    windows = load_rq43_per_window()
    tiny = windows["tiny"]
    base = windows["base"]
    kl = windows["kl"]
    n = kl.shape[0]
    labels = (tiny > CATASTROPHIC_CPWER).astype(int)  # 1 = hallucinated
    n_hall = int(labels.sum())
    n_clean = int((labels == 0).sum())

    # --- controlled-comparison smoke: RQ43's original rule reproduces 0.888947
    rq43_cas = float(np.where(kl >= RQ43_KL_THRESHOLD - EPS, base, tiny).mean())
    baseline = float(tiny.mean())
    assert abs(rq43_cas - RQ43_CASCADE_CPWER) < 1e-4, (
        f"RQ43 cascade @ KL=3.30 = {rq43_cas}, expected ~{RQ43_CASCADE_CPWER}")
    assert abs(baseline - RQ43_BASELINE_CPWER) < 1e-4
    assert n_hall == 37 and n_clean == 40, f"label counts {n_hall}/{n_clean}"
    # base ratio is constant per window (0.428031)
    ratio = base / tiny
    assert np.allclose(ratio, RQ43_BASE_RATIO, atol=1e-4), (
        f"base/tiny ratio not constant {RQ43_BASE_RATIO}: min={ratio.min()}, "
        f"max={ratio.max()}")

    # --- KL detector geometry
    kl_min = float(kl.min())
    kl_max = float(kl.max())
    kl_mean = float(kl.mean())
    kl_median = float(np.median(kl))

    # --- Beta(2,2) posterior mode shrinkage prior
    prior_mean_norm = beta_posterior_mode(
        BETA_PRIOR_ALPHA, BETA_PRIOR_BETA, n_hall, n)
    prior_mean_kl = prior_mean_norm * kl_max
    # verify the analytic value 38/79
    assert abs(prior_mean_norm - 38.0 / 79.0) < 1e-12, (
        f"Beta(2,2) posterior mode {prior_mean_norm} != 38/79")

    # --- in-sample calibration per lambda
    in_sample: dict[str, Any] = {}
    for lam in LAMBDAS:
        cal = calibrate_shrinkage_kl(
            kl, labels, kl_max, prior_mean_norm, lam)
        thr = float(cal["threshold"])
        theta_hat = cascade_cpwer_at_threshold(tiny, base, kl, thr)
        compute = cascade_compute_at_threshold(kl, thr)
        frac = escalation_fraction_at_threshold(kl, thr)
        n_esc = int(np.sum(kl >= thr - EPS))
        in_sample[str(lam)] = {
            "lambda": lam,
            "threshold": round(thr, 6),
            "threshold_norm": round(thr / kl_max, 6) if kl_max > 0 else 0.0,
            "sensitivity": round(float(cal["sensitivity"]), 6),
            "specificity": round(float(cal["specificity"]), 6),
            "tp": int(cal["tp"]), "fp": int(cal["fp"]),
            "tn": int(cal["tn"]), "fn": int(cal["fn"]),
            "penalty": round(float(cal["penalty"]), 6),
            "objective": round(float(cal["objective"]), 6),
            "cascade_cpwer": round(theta_hat, 6),
            "cascade_compute": round(compute, 6),
            "escalation_fraction": round(frac, 6),
            "n_escalated": n_esc,
        }

    # --- bootstrap shrinkage cascade (B=10000, seed=42) per lambda
    per_lambda: dict[str, Any] = {}
    for lam in LAMBDAS:
        boot = bootstrap_shrinkage_cascade(
            tiny, base, kl, labels, kl_max, prior_mean_norm, lam,
            n_boot=N_BOOT, seed=SEED)
        per_lambda[str(lam)] = boot

    # --- mode count + OOB stats per lambda
    per_lambda_summary: dict[str, Any] = {}
    per_lambda_full: dict[str, Any] = {}
    for lam in LAMBDAS:
        key = str(lam)
        boot = per_lambda[key]
        thr_arr = boot["thresholds"]
        oob_arr = boot["oob_cpwer"]
        n_oob_mean = float(np.mean(boot["n_oob"]))
        modes = count_modes(thr_arr, MIN_MODE_FRACTION)
        thr_fs = _finite_stats(thr_arr)
        valid = ~np.isnan(oob_arr)
        oob_valid = oob_arr[valid]
        oob_median = float(np.median(oob_valid)) if oob_valid.size else float("nan")
        oob_mean = float(np.mean(oob_valid)) if oob_valid.size else float("nan")
        per_lambda_summary[key] = {
            "lambda": lam,
            "n_modes_5pct": modes["n_modes"],
            "oob_cpwer_median": round(oob_median, 6),
            "oob_cpwer_mean": round(oob_mean, 6),
            "n_oob_mean": round(n_oob_mean, 4),
            "modes_5pct": modes["modes"],
        }
        per_lambda_full[key] = {
            "lambda": lam,
            "in_sample": in_sample[key],
            "threshold_distribution": thr_fs,
            "modes": modes,
            "oob_distribution": {
                "n_valid": int(valid.sum()),
                "median": round(oob_median, 6),
                "mean": round(oob_mean, 6),
                "min": round(float(np.nanmin(oob_arr)), 6) if valid.any() else float("nan"),
                "max": round(float(np.nanmax(oob_arr)), 6) if valid.any() else float("nan"),
                "p2_5": round(float(np.nanpercentile(oob_arr, 2.5)), 6) if valid.any() else float("nan"),
                "p97_5": round(float(np.nanpercentile(oob_arr, 97.5)), 6) if valid.any() else float("nan"),
            },
            "mean_oob_size": round(n_oob_mean, 4),
        }

    # --- BCa CI + jackknife at each lambda (full BCa requires the jackknife)
    for lam in LAMBDAS:
        key = str(lam)
        boot = per_lambda[key]
        theta_hat = float(in_sample[key]["cascade_cpwer"])
        accel, theta_loo = jackknife_acceleration(
            tiny, base, kl, labels, kl_max, prior_mean_norm, lam)
        bca = bca_ci(theta_hat, boot["oob_cpwer"], accel, alpha=ALPHA)
        bca_width = bca["hi"] - bca["lo"]
        per_lambda_full[key]["bca_ci"] = {
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
        }
        per_lambda_full[key]["jackknife"] = {
            "accel": round(accel, 6),
            "theta_loo_mean": round(float(np.mean(theta_loo)), 6),
            "theta_loo_min": round(float(np.min(theta_loo)), 6),
            "theta_loo_max": round(float(np.max(theta_loo)), 6),
        }
        per_lambda_summary[key]["bca_width"] = round(bca_width, 6)
        per_lambda_summary[key]["bca_lo"] = round(bca["lo"], 6)
        per_lambda_summary[key]["bca_hi"] = round(bca["hi"], 6)

    # --- best lambda selection
    best = select_best_lambda(per_lambda_summary)
    best_key = best["lambda_key"]
    best_lam = best["lambda"]
    best_thr = float(in_sample[best_key]["threshold"])
    best_theta_hat = float(in_sample[best_key]["cascade_cpwer"])
    best_frac = float(in_sample[best_key]["escalation_fraction"])
    best_oob_median = float(per_lambda_summary[best_key]["oob_cpwer_median"])
    best_bca_width = float(per_lambda_summary[best_key]["bca_width"])
    best_bca_lo = float(per_lambda_summary[best_key]["bca_lo"])
    best_bca_hi = float(per_lambda_summary[best_key]["bca_hi"])
    best_n_modes = int(per_lambda_summary[best_key]["n_modes_5pct"])

    # --- hypothesis verdicts (at best lambda)
    h69a = _h69a_supported(best_oob_median)
    h69b = _h69b_supported(best_frac)
    h69c = _h69c_supported(best_bca_width)

    # --- RQ59 / RQ62 references (read from JSONs where available)
    rq59_ref = {
        "youdens_j_threshold": 0.01,
        "youdens_j_escalation": RQ59_YOUDENS_J_ESCALATION,
        "youdens_j_oob_median_cpwer": RQ59_YOUDENS_J_OOB_MEDIAN_CPWER,
        "youdens_j_bca_width": RQ59_YOUDENS_J_BCA_WIDTH,
    }
    try:
        rq59_data = json.loads(RQ59_JSON.read_text(encoding="utf-8"))
        rq59_ref["youdens_j_threshold"] = float(
            rq59_data["in_sample_youdens_j_calibration"]["threshold"])
        rq59_ref["youdens_j_escalation"] = float(
            rq59_data["in_sample_youdens_j_calibration"]["escalation_fraction"])
        rq59_ref["youdens_j_oob_median_cpwer"] = float(
            rq59_data["bootstrap_oob_cpwer_distribution"]["median"])
        rq59_ref["youdens_j_bca_width"] = float(rq59_data["bca_ci"]["width"])
    except (OSError, ValueError, KeyError) as exc:
        print(f"[warn] RQ59 reference JSON unreadable ({exc}); "
              f"falling back to hardcoded RQ59 anchors.", file=sys.stderr)

    rq62_ref = {
        "or_escalation": RQ62_OR_ESCALATION,
        "or_oob_median_cpwer": RQ62_OR_OOB_MEDIAN_CPWER,
        "or_bca_width": RQ62_OR_BCA_WIDTH,
    }
    try:
        rq62_data = json.loads(RQ62_JSON.read_text(encoding="utf-8"))
        rq62_ref["or_escalation"] = float(
            rq62_data["in_sample_ensemble"]["or"]["escalation_fraction"])
        rq62_ref["or_oob_median_cpwer"] = float(
            rq62_data["bootstrap_oob_cpwer_distributions"]["or"]["median"])
        rq62_ref["or_bca_width"] = float(rq62_data["bca_ci"]["or"]["width"])
    except (OSError, ValueError, KeyError) as exc:
        print(f"[warn] RQ62 reference JSON unreadable ({exc}); "
              f"falling back to hardcoded RQ62 anchors.", file=sys.stderr)

    # --- threshold sweep (Pareto-style: escalation fraction -> cascade cpWER)
    sweep: list[dict[str, Any]] = []
    for t in [round(0.01 * i, 2) for i in range(0, 856)]:
        m = kl >= t - EPS
        if not m.any():
            continue
        cp = float(np.where(m, base, tiny).mean())
        fr = float(np.mean(m))
        co = COMPUTE_TINY * (1.0 - fr) + COMPUTE_BASE * fr
        sweep.append({"threshold": t, "escalation_fraction": round(fr, 6),
                      "cpwer": round(cp, 6), "compute": round(co, 6)})

    # --- assemble summary
    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": ("RQ69: Cascade with shrinkage-calibrated KL gate -- does "
               "replacing the raw KL gate with a shrinkage-calibrated KL gate "
               "(Beta(2,2) posterior-mode prior) improve the cascade's OOB "
               "cpWER?"),
        "closes_issue": 997,
        "builds_on": {
            "RQ43": "results/frontier/three_tier_cascade/ (PR #959, 3-tier KL cascade)",
            "RQ44": "results/frontier/bootstrap_threshold_stability/ (PR #963, OOB bootstrap)",
            "RQ48": "results/frontier/calibration_rule_comparison/ (PR #965, count_modes)",
            "RQ59": "results/frontier/cascade_youdens_j/ (PR #980, BCa CI + jackknife framework)",
            "RQ61": "results/frontier/shrinkage_threshold_calibration/ (PR #991, shrinkage calibration)",
            "RQ62": "results/frontier/ensemble_cascade_gate/ (PR #992, ensemble cascade comparison)",
        },
        "source_data": {
            "rq43_json": str(RQ43_JSON.relative_to(PROJECT_ROOT)),
            "rq43_label": "experimental/frontier",
            "aishell4_json": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
            "aishell4_label": "external/sanity-check",
            "aishell4_asr_model": "whisper-tiny",
        },
        "method": (
            "REANALYSIS (no ASR run). Loads RQ43's 77 per-window cascade data "
            "(tiny_sep_cpwer, base_sep_cpwer, kl_sep) so the cascade corpus is "
            "byte-identical to RQ43/RQ59/RQ62. The ONLY change vs RQ59 "
            "(Youden's J) and RQ62 (ensemble OR) is the calibration rule: RQ69 "
            "uses RQ61's shrinkage calibration "
            "(sensitivity - lambda * |t/kl_max - prior_mean_norm| at >= 90% "
            "specificity) with a Beta(2,2) posterior-mode prior. The prior is "
            "Beta(2,2) on the hallucination rate, updated by the observed "
            "37 hallucinated / 40 clean counts: posterior Beta(39, 42), mode "
            "38/79 ~= 0.481013 on the normalised [0,1] KL scale. The shrinkage "
            "penalty operates on the normalised scale (t / kl_max) so lambda "
            "is comparable to RQ61. Hallucination label = tiny_sep_cpwer > 1.0 "
            "(37 hall / 40 clean). Cascade: tiny on all windows -> shrinkage-KL "
            "gate -> base (cpWER = tiny * 0.428031, RQ43's separated ratio). "
            "Bootstrap B=10000 seed=42: per resample re-calibrate the shrinkage "
            "KL threshold on in-bag windows, evaluate cascade cpWER on OOB "
            "windows (RQ44 OOB protocol). BCa 95% CI on the OOB cpWER "
            "distribution (bias-correction z0 from the in-sample point estimate "
            "theta_hat; acceleration from a delete-1 jackknife). Mode count via "
            "RQ48's count_modes (>= 5% frequency). Best-lambda selected by "
            "lowest OOB cpWER median (H69a primary), then narrowest BCa width, "
            "then fewest modes, then smallest lambda."
        ),
        "controlled_comparison_note": (
            "The cascade simulation is held fixed at RQ43's actual "
            "implementation (real whisper-tiny cpWER for tier 1; base cpWER = "
            "tiny * 0.428031 for tier 3) so the H69a comparison to RQ43's "
            "0.888947 anchor, the H69b comparison to RQ59's 83.1% escalation, "
            "and the H69c comparison to RQ59's 0.2827 BCa width are "
            "apples-to-apples. The ONLY independent variable vs RQ59/RQ62 is "
            "the calibration rule (shrinkage KL here vs Youden's J / ensemble "
            "there)."
        ),
        "n_windows": n,
        "n_hallucinated": n_hall,
        "n_clean": n_clean,
        "hallucination_label_rule": "tiny_sep_cpwer > 1.0 (== always_separated_cpwer > 1.0)",
        "kl_detector": {
            "source": "RQ43 (PR #959), character-bigram asymmetric KL (kl_sep)",
            "range": [round(kl_min, 6), round(kl_max, 6)],
            "mean": round(kl_mean, 6),
            "median": round(kl_median, 6),
            "grid": "0.01-step [0.00, 8.55] (856 points, identical to RQ59)",
        },
        "shrinkage_prior": {
            "prior_family": "Beta(2, 2) on the hallucination rate",
            "prior_alpha": BETA_PRIOR_ALPHA,
            "prior_beta": BETA_PRIOR_BETA,
            "prior_mode": 0.5,
            "observed_successes": n_hall,
            "observed_total": n,
            "posterior": f"Beta({int(BETA_PRIOR_ALPHA + n_hall)}, {int(BETA_PRIOR_BETA + n_clean)})",
            "posterior_mode_norm": round(prior_mean_norm, 6),
            "posterior_mode_analytic": "38/79",
            "prior_mean_kl": round(prior_mean_kl, 6),
            "scale": "normalised [0,1] (t / kl_max); penalty on normalised scale so lambda is comparable to RQ61",
            "lambdas": LAMBDAS,
        },
        "compute_model": {"tiny": COMPUTE_TINY, "base": COMPUTE_BASE,
                          "source": "RQ43 / runtime_cascade (base 1.93x slower)"},
        "bootstrap": {"n_boot": N_BOOT, "seed": SEED, "resample_size": n,
                      "oob_protocol": "RQ44 out_of_bag (calibrate in-bag, evaluate OOB)",
                      "expected_oob_size": round(n * ((1 - 1 / n) ** n), 4),
                      "note": ("B=10000 >= task's B=1000 minimum; BCa CI requires "
                               "the full bootstrap distribution so B=10000 is used "
                               "for both OOB cpWER and BCa (consistent with "
                               "RQ59/RQ62).")},
        "bca_method": {
            "theta_hat": "in-sample shrinkage-KL cascade cpWER at the in-sample calibrated threshold",
            "boot_samples": "OOB shrinkage-KL cascade cpWER per resample",
            "acceleration": "delete-1 jackknife (in-sample shrinkage-KL cascade cpWER on n-1)",
            "bias_correction": "z0 = Phi^{-1}( #{boot < theta_hat} / B ), clamped to (0.5/B, 1-0.5/B)",
            "normal_inverse": "Acklam rational approximation + 1 Halley step (no scipy)",
        },
        "rq43_original_rule_reference": {
            "kl_threshold": RQ43_KL_THRESHOLD,
            "cascade_cpwer": RQ43_CASCADE_CPWER,
            "baseline_cpwer": RQ43_BASELINE_CPWER,
            "base_ratio": RQ43_BASE_RATIO,
            "reproduced_in_sample": round(rq43_cas, 6),
            "rule": "fixed threshold 3.30 (RQ43's n=3 kl_sep)",
        },
        "rq59_youdens_j_reference": {
            **rq59_ref,
            "note": ("RQ59's Youden's J cascade on the KL detector: 83.1% "
                     "escalation (flat-topped ROC collapse), OOB median cpWER "
                     "~0.782, BCa width ~0.283. RQ69 tests whether shrinkage "
                     "calibration gives a less aggressive AND lower-cpWER "
                     "operating point."),
        },
        "rq62_ensemble_reference": {
            **rq62_ref,
            "note": ("RQ62's ensemble OR cascade: 55.8% escalation, OOB median "
                     "cpWER 0.942, BCa width 0.239. RQ69 tests whether "
                     "shrinkage on the KL detector alone (no lang-id ensemble) "
                     "improves on RQ62's OOB cpWER."),
        },
        "in_sample_calibration": in_sample,
        "best_lambda": best,
        "best_lambda_in_sample": {
            "lambda": best_lam,
            "threshold": round(best_thr, 6),
            "threshold_norm": round(best_thr / kl_max, 6) if kl_max > 0 else 0.0,
            "cascade_cpwer": round(best_theta_hat, 6),
            "escalation_fraction": round(best_frac, 6),
            "compute": round(
                COMPUTE_TINY * (1.0 - best_frac) + COMPUTE_BASE * best_frac, 6),
        },
        "per_lambda_summary": per_lambda_summary,
        "per_lambda_full": {k: {kk: vv for kk, vv in v.items()}
                            for k, v in per_lambda_full.items()},
        "threshold_sweep": sweep,
        "hypothesis_verdicts": {
            "H69a": {
                "statement": ("Shrinkage KL cascade OOB cpWER < 0.889 "
                              f"(RQ43 baseline {RQ43_CASCADE_CPWER})"),
                "best_lambda": best_lam,
                "oob_median_cpwer": round(best_oob_median, 6),
                "max_cpwer": H69A_MAX_CPWER,
                "kill": f"OOB cpWER >= {H69A_MAX_CPWER}",
                "supported": bool(h69a),
            },
            "H69b": {
                "statement": ("Shrinkage KL cascade escalation rate < 83.1% "
                              f"(RQ59 baseline {RQ59_YOUDENS_J_ESCALATION:.4f})"),
                "best_lambda": best_lam,
                "escalation_fraction": round(best_frac, 6),
                "max_escalation": H69B_MAX_ESCALATION,
                "kill": f"escalation >= {H69B_MAX_ESCALATION}",
                "supported": bool(h69b),
            },
            "H69c": {
                "statement": ("Shrinkage KL cascade BCa width < 0.283 "
                              f"(RQ59 baseline {RQ59_YOUDENS_J_BCA_WIDTH})"),
                "best_lambda": best_lam,
                "bca_ci_width": round(best_bca_width, 6),
                "bca_ci_lo": round(best_bca_lo, 6),
                "bca_ci_hi": round(best_bca_hi, 6),
                "max_width": H69C_MAX_WIDTH,
                "kill": f"BCa width >= {H69C_MAX_WIDTH}",
                "supported": bool(h69c),
            },
        },
    }

    # --- attach per-bootstrap arrays for the best lambda (reproducibility)
    best_boot = per_lambda[best_key]
    summary["per_bootstrap"] = {
        "thresholds": [round(float(t), 6) for t in best_boot["thresholds"]],
        "oob_cpwer": [round(float(c), 6) if not math.isnan(float(c)) else None
                      for c in best_boot["oob_cpwer"]],
        "n_oob": [int(x) for x in best_boot["n_oob"]],
    }

    # --- write JSON
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    # --- write CSV (per-resample bootstrap table at best lambda)
    write_bootstrap_csv(
        OUT_CSV, best_boot["boot_idx"], best_boot["thresholds"],
        best_boot["oob_cpwer"], best_boot["n_oob"],
        best_boot["n_escalated_oob"], n)

    # --- console
    print(f"=== RQ69: Cascade with shrinkage-calibrated KL gate ===")
    print(f"Label: experimental/frontier  |  Closes #997  |  n={n} AISHELL-4 "
          f"windows ({n_hall} hall / {n_clean} clean)")
    print(f"Controlled comparison: only the calibration rule changes vs "
          f"RQ59/RQ62 (shrinkage KL vs Youden's J / ensemble).")
    print(f"RQ43 original rule @ kl_sep>=3.30: cpwer={rq43_cas:.4f} "
          f"(reproduces {RQ43_CASCADE_CPWER})")
    print()
    print(f"Shrinkage prior: Beta(2,2) -> posterior Beta(39,42) -> mode "
          f"{prior_mean_norm:.6f} (normalised) = {prior_mean_kl:.4f} (KL scale)")
    print(f"KL detector range: [{kl_min:.4f}, {kl_max:.4f}]  mean={kl_mean:.4f}")
    print()
    print(f"In-sample calibration (full 77 windows, per lambda):")
    print(f"  {'lam':>5s} {'thr':>8s} {'sens':>6s} {'spec':>6s} {'frac':>6s} "
          f"{'cpwer':>8s} {'compute':>8s}")
    for lam in LAMBDAS:
        isam = in_sample[str(lam)]
        print(f"  {lam:5.2f} {isam['threshold']:8.4f} {isam['sensitivity']:6.3f} "
              f"{isam['specificity']:6.3f} {isam['escalation_fraction']:6.3f} "
              f"{isam['cascade_cpwer']:8.4f} {isam['cascade_compute']:8.4f}")
    print()
    print(f"Bootstrap B={N_BOOT} seed={SEED} (OOB, re-calibrated threshold per resample):")
    for lam in LAMBDAS:
        key = str(lam)
        s = per_lambda_summary[key]
        fs = per_lambda_full[key]["threshold_distribution"]
        print(f"  --- lambda={lam} ---")
        print(f"    threshold: median(finite)={fs['median']}  "
              f"n_unique={len(set(per_lambda[key]['thresholds']))}  "
              f"n_modes>=5%={s['n_modes_5pct']}  "
              f"inf_frac={fs['inf_fraction']:.3f}")
        for m in s["modes_5pct"]:
            t_str = "inf" if math.isinf(m["threshold"]) else f"{m['threshold']:.4f}"
            print(f"      mode KL={t_str}  count={m['count']}  frac={m['fraction']:.3f}")
        print(f"    OOB cpWER: median={s['oob_cpwer_median']:.4f}  "
              f"mean={s['oob_cpwer_mean']:.4f}")
        print(f"    BCa CI: [{s['bca_lo']:.4f}, {s['bca_hi']:.4f}]  "
              f"width={s['bca_width']:.4f}")
    print()
    print(f"Best lambda: {best_lam}  (threshold={best_thr:.4f}, "
          f"escalation={best_frac:.4f})")
    print(f"  reason: {best['reason']}")
    print()
    print("Hypothesis verdicts (at best lambda):")
    print(f"  H69a (OOB cpWER < {H69A_MAX_CPWER}):  "
          f"{'SUPPORTED' if h69a else 'KILLED'}  "
          f"(median OOB={best_oob_median:.4f})  [RQ43 ref={RQ43_CASCADE_CPWER}]")
    print(f"  H69b (escalation < {H69B_MAX_ESCALATION:.1%}):  "
          f"{'SUPPORTED' if h69b else 'KILLED'}  "
          f"(frac={best_frac:.4f})  [RQ59 ref={RQ59_YOUDENS_J_ESCALATION:.4f}]")
    print(f"  H69c (BCa width < {H69C_MAX_WIDTH}):  "
          f"{'SUPPORTED' if h69c else 'KILLED'}  "
          f"(width={best_bca_width:.4f})  [RQ59 ref={RQ59_YOUDENS_J_BCA_WIDTH}]")
    print()
    print(f"RQ59 Youden's J reference: thr={rq59_ref['youdens_j_threshold']}  "
          f"frac={rq59_ref['youdens_j_escalation']:.4f}  "
          f"cpwer={rq59_ref['youdens_j_oob_median_cpwer']:.4f}  "
          f"width={rq59_ref['youdens_j_bca_width']:.4f}")
    print(f"RQ62 ensemble OR reference: frac={rq62_ref['or_escalation']:.4f}  "
          f"cpwer={rq62_ref['or_oob_median_cpwer']:.4f}  "
          f"width={rq62_ref['or_bca_width']:.4f}")
    print()
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
