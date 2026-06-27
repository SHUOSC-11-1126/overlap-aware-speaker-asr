"""RQ59: Cascade with Youden's J calibration -- does Youden's J give a less
aggressive cascade operating point than F1 while maintaining robustness?

REANALYSIS ONLY -- no Whisper / no ASR / no LLM model is run. RQ54 (PR #971)
found that F1 calibration of RQ43's KL gate collapses the bootstrap threshold
distribution to a single mode (KL = 0.01, 96.3% of 10000 resamples) but is too
aggressive: it escalates 83.1% of windows to whisper-base (cascade compute
1.773x vs RQ43's ~1.4x). RQ48 (PR #965) found Youden's J = TPR - FPR gives 3
modes on the lang-id-entropy detector (vs F1's 2, vs the original rule's 6).
RQ59 asks whether Youden's J -- which balances sensitivity and specificity
rather than maximising precision x recall on the hallucinated class -- gives a
less aggressive cascade operating point than F1 while maintaining robustness.

Label: experimental/frontier.

Controlled comparison design
----------------------------
The ONLY independent variable vs RQ54 is the calibration rule. The cascade
simulation is held fixed at RQ43's actual implementation so the comparison to
RQ43's 0.888947 anchor (H59b) and RQ54's F1 reference is apples-to-apples:

- Tier 1 (whisper-tiny) cpWER per window = RQ43's ``tiny_sep_cpwer`` (the real
  whisper-tiny separated-audio cpWER; ``always_separated_cpwer`` in AISHELL-4).
- Tier 3 (whisper-base) cpWER per window = RQ43's ``base_sep_cpwer`` =
  ``tiny_sep_cpwer * 0.428031`` (the model_scale separated base/tiny CER
  ratio, constant across overlap). This is RQ43's actual base-cpWER estimate;
  it is NOT ``always_mixed_cpwer``.
- Tier 2 (KL gate): escalate to base when the character-bigram asymmetric KL
  divergence of the tiny transcript (RQ43's ``kl_sep``) >= the calibrated
  threshold.

The hallucination label used to calibrate Youden's J is ``tiny_sep_cpwer > 1.0``
(== ``always_separated_cpwer > 1.0``; 37 hallucinated / 40 clean), matching
RQ44/RQ48/RQ54's label rule. High KL flags a window as hallucinated and
escalates it to base -- the same direction as RQ43's cascade (which improves
cpWER by escalating high-KL windows to the lower-cpWER base tier).

Youden's J calibration rule (RQ48's ``calibrate_youdens_j``, reused verbatim)
---------------------------------------------------------------------------
J = sensitivity + specificity - 1 = TPR - FPR. The KL threshold is swept over a
0.01-step grid spanning the observed KL range [0.00, 8.55]; the grid point
maximising J is chosen, with the lowest threshold breaking ties (RQ48's
``_select_threshold`` convention, ``>= - EPS`` flagging). This is RQ48's exact
Youden's J rule applied to the KL detector signal instead of lang-id-entropy.
Unlike F1 (which collapses to the lowest grid point because recall dominates),
J trades sensitivity against specificity continuously, so it should land at a
higher, less aggressive threshold.

Method
------
1. Load RQ43's 77 per-window (tiny_sep_cpwer, base_sep_cpwer, kl_sep) from
   ``three_tier_cascade_results.json`` (so the cascade corpus is byte-identical
   to RQ43/RQ46/RQ54). Verify n=77, baseline 1.590909, and that the in-sample
   cascade @ KL=3.30 (RQ43's original rule) reproduces 0.888947.
2. Labels = tiny_sep_cpwer > 1.0 (37 hall / 40 clean).
3. In-sample Youden's J calibration on all 77 windows -> J-optimal KL threshold
   and the in-sample cascade cpWER (the BCa point estimate theta_hat).
4. Bootstrap B=10000, seed=42: for each resample, calibrate the J-optimal KL
   threshold on the in-bag windows and evaluate the cascade cpWER on the
   out-of-bag (OOB) windows (RQ44's OOB protocol). Records the per-resample
   threshold (for mode counting) and OOB cpWER (for the BCa CI).
5. Delete-1 jackknife (77 fits) for the BCa acceleration.
6. BCa 95% CI on the OOB cpWER distribution (bias-corrected + accelerated;
   Acklam inverse-normal, no scipy).
7. Mode count on the bootstrap threshold distribution (RQ48's ``count_modes``,
   min_fraction=0.05 -- the explicit kill-condition definition).
8. Pre-registered hypothesis verdicts H59a/b/c.

Pre-registered hypotheses
-------------------------
- H59a: Youden's J cascade escalates < 83% of windows to base (less aggressive
        than F1's 83.1%). Kill: in-sample escalation fraction >= 0.83.
- H59b: Youden's J cascade OOB cpWER <= 0.889 (matches RQ43's original-rule
        cpWER 0.888947). Kill: OOB median cpWER > 0.889.
- H59c: Youden's J cascade BCa CI width <= 0.2489 (maintains robustness vs
        RQ46's original-rule width). Kill: BCa width > 0.2489.

Methodological note on the H59c comparison: RQ46's 0.2489 anchor was a
percentile CI evaluated in-bag at a FIXED threshold (3.30); RQ59's BCa CI is
bias-corrected + accelerated and evaluated OOB at a RE-CALIBRATED threshold.
The comparison is therefore directional (does Youden's J + BCa + OOB keep the
interval within the original-rule width) rather than a pure like-for-like
CI-method swap; this is documented in FINDINGS.md and mirrors RQ54's H54b
caveat.

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / Whisper
are NOT required). Youden's J calibration and mode-counting are imported
verbatim from RQ48 (PR #965) to guarantee the calibration rule is identical;
the bootstrap index draw and OOB protocol mirror RQ44 (PR #963) and RQ54
(PR #971).
"""
from __future__ import annotations

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
RQ46_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "bootstrap_pareto"
    / "bootstrap_pareto_results.json"
)
RQ48_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "calibration_rule_comparison"
    / "calibration_rule_results.json"
)
RQ54_JSON = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "cascade_f1_calibration"
    / "cascade_f1_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "cascade_youdens_j"
OUT_JSON = OUT_DIR / "cascade_youdens_j_results.json"
OUT_CSV = OUT_DIR / "cascade_youdens_j_results.csv"

# ------------------------------------------ import RQ48's Youden's J + RQ44's framework (verbatim reuse)
# RQ48's calibrate_youdens_j / count_modes ARE RQ48's Youden's J rule; reusing
# them guarantees the calibration rule is byte-identical to RQ48 (only the
# detector signal changes: KL here vs lang-id-entropy in RQ48). RQ44
# contributes the bootstrap index draw and the OOB protocol conventions; RQ54
# contributes the cascade-simulation + BCa scaffolding.
_RQ48_DIR = PROJECT_ROOT / "results" / "frontier" / "calibration_rule_comparison"
_RQ44_DIR = PROJECT_ROOT / "results" / "frontier" / "bootstrap_threshold_stability"
sys.path.insert(0, str(_RQ48_DIR))
sys.path.insert(0, str(_RQ44_DIR))
import calibration_rule_analysis as rq48  # noqa: E402  (path-injected import)
import bootstrap_threshold_analysis as rq44  # noqa: E402  (path-injected import)

# ------------------------------------------------------------------ constants
# RQ48's Youden's J calibration rule and mode counter, re-exported for
# traceability. calibrate_youdens_j maximises J = sens + spec - 1 on the same
# >= - EPS flagging convention as calibrate_f1.
calibrate_youdens_j = rq48.calibrate_youdens_j   # RQ48's exact Youden's J maximiser
count_modes = rq48.count_modes                   # RQ48's >= 5% mode counter
EPS = rq44.EPS                                    # 1e-9 (RQ44/RQ48/RQ54 tolerance)

# KL threshold grid: 0.01 step spanning RQ43's observed KL range [0.0, 8.5255].
# 0.01 matches RQ48's grid granularity; the range is extended to cover the KL
# detector's support (identical to RQ54 so the F1/Youden comparison is on the
# same grid).
KL_THRESHOLD_GRID = [round(0.01 * i, 2) for i in range(0, 856)]  # 0.00 .. 8.55

N_BOOT = 10000           # task-specified bootstrap iterations
SEED = 42                # task-specified seed
MIN_MODE_FRACTION = 0.05  # "mode" = distinct threshold with >= 5% frequency (RQ48)
ALPHA = 0.05             # 95% CI

COMPUTE_TINY = 1.0       # whisper-tiny relative compute (RQ43)
COMPUTE_BASE = 1.93      # whisper-base relative compute (RQ43 / runtime_cascade)
CATASTROPHIC_CPWER = 1.0  # cpWER > 1.0 => hallucination label (RQ44/RQ48/RQ54)

# RQ43 / RQ46 / RQ54 anchors (the controlled-comparison reference values).
RQ43_KL_THRESHOLD = 3.30
RQ43_CASCADE_CPWER = 0.888947          # RQ43 in-sample cascade cpWER @ KL=3.30
RQ43_BASELINE_CPWER = 1.590909         # always-tiny-separated
RQ43_BASE_RATIO = 0.428031             # model_scale separated base/tiny CER ratio
RQ46_CI_LO = 0.767399                  # RQ46 bootstrap percentile CI lo @ KL=3.30
RQ46_CI_HI = 1.016343                  # RQ46 bootstrap percentile CI hi @ KL=3.30
RQ46_CI_WIDTH = round(RQ46_CI_HI - RQ46_CI_LO, 4)  # 0.2489 (H59c anchor)
RQ48_YOUDENS_J_MODES_LANGID = 3        # RQ48's Youden's J mode count on lang-id-entropy
RQ54_F1_MODES_KL = 1                   # RQ54's F1 mode count on KL
RQ54_F1_ESCALATION = 0.831169          # RQ54's F1 in-sample escalation fraction
RQ54_F1_OOB_MEDIAN_CPWER = 0.779853    # RQ54's F1 OOB median cpWER
RQ54_F1_BCA_WIDTH = 0.248072           # RQ54's F1 BCa CI width

# Hypothesis kill thresholds.
H59A_MAX_ESCALATION = 0.83   # Youden's J: kill if escalation fraction >= 0.83
H59B_MAX_CPWER = 0.889       # Youden's J: kill if OOB median cpWER > 0.889
H59C_MAX_WIDTH = RQ46_CI_WIDTH  # BCa cpWER CI width: kill if > 0.2489


# --------------------------------------------------------------- data loading
def load_rq43_per_window() -> dict[str, np.ndarray]:
    """Load RQ43's 77 per-window (tiny_sep_cpwer, base_sep_cpwer, kl_sep).

    Reads ``three_tier_cascade_results.json`` ``per_window`` so the cascade
    corpus is byte-identical to RQ43/RQ46/RQ54 (the values are rounded to 6 dp
    in the JSON, which is sufficient to reproduce RQ43's 0.888947 anchor).
    Returns a dict of float arrays and asserts n == 77.
    """
    data = json.loads(RQ43_JSON.read_text(encoding="utf-8"))
    pw = data["per_window"]
    assert len(pw) == 77, f"expected 77 AISHELL-4 windows, got {len(pw)}"
    tiny = np.array([float(w["tiny_sep_cpwer"]) for w in pw], dtype=float)
    base = np.array([float(w["base_sep_cpwer"]) for w in pw], dtype=float)
    kl = np.array([float(w["kl_sep"]) for w in pw], dtype=float)
    return {"tiny": tiny, "base": base, "kl": kl, "window_id": [w["window_id"] for w in pw]}


# --------------------------------------------------------------- cascade simulation
def cascade_cpwer_at_threshold(
    tiny: np.ndarray, base: np.ndarray, kl: np.ndarray, threshold: float
) -> float:
    """In-sample cascade cpWER at ``threshold``.

    Escalation: ``kl >= threshold - EPS`` -> base (else tiny). Uses the
    ``>= - EPS`` convention to match RQ48's Youden's J flagging (a window
    flagged by J as hallucinated is the same window escalated to base). RQ43
    used strict ``>``; on the 0.01 grid the two conventions differ only at
    exact equality (rare for continuous KL), and the in-sample KL=3.30 anchor
    is reproduced by both (verified in tests)."""
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


def cascade_oob_cpwer(
    tiny: np.ndarray,
    base: np.ndarray,
    kl: np.ndarray,
    threshold: float,
    in_bag_idx: np.ndarray,
) -> dict[str, Any]:
    """Cascade cpWER on the out-of-bag (OOB) windows at ``threshold``.

    Mirrors RQ44's / RQ54's ``out_of_bag_cpwer`` protocol but routes escalated
    windows to ``base`` (whisper-base) and non-escalated to ``tiny`` (whisper-
    tiny). Returns the mean selected cpWER over the OOB windows (``nan`` if
    there are none), the OOB size, and the escalation count."""
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


# --------------------------------------------------------------- vectorised bootstrap Youden's J
def bootstrap_youdens_j_cascade(
    tiny: np.ndarray,
    base: np.ndarray,
    kl: np.ndarray,
    labels: np.ndarray,
    grid: list[float] | None = None,
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict[str, np.ndarray]:
    """Bootstrap the Youden's-J-calibrated cascade over ``n_boot`` resamples.

    For each resample: draw n indices with replacement, calibrate the J-optimal
    KL threshold on the in-bag windows (RQ48's ``calibrate_youdens_j`` rule,
    vectorised across resamples), and evaluate the cascade cpWER on the OOB
    windows.

    Returns a dict with:
      ``boot_idx``       -- (n_boot, n) int array of resample indices
      ``thresholds``     -- (n_boot,) J-optimal KL threshold per resample
      ``oob_cpwer``      -- (n_boot,) OOB cascade cpWER (nan if OOB empty)
      ``n_oob``          -- (n_boot,) OOB size per resample
      ``n_escalated_oob``-- (n_boot,) escalated count within OOB

    The vectorised J selection is proved equivalent to RQ48's per-call
    ``calibrate_youdens_j`` by ``test_vectorised_matches_calibrate_youdens_j``
    (lowest-t tie-break, ``>= - EPS`` flagging, RQ48's specificity=1 /
    sensitivity=0 convention for empty-class bags)."""
    if grid is None:
        grid = KL_THRESHOLD_GRID
    tiny = np.asarray(tiny, dtype=float)
    base = np.asarray(base, dtype=float)
    kl = np.asarray(kl, dtype=float)
    labels = np.asarray(labels, dtype=int)
    n = kl.shape[0]
    grid_arr = np.asarray(grid, dtype=float)
    T = grid_arr.size

    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, n, size=(n_boot, n))  # (B, n)
    kl_boot = kl[boot_idx]                            # (B, n)
    lab_boot = labels[boot_idx]                       # (B, n)
    pos_boot = (lab_boot == 1)
    neg_boot = (lab_boot == 0)
    n_pos_b = pos_boot.sum(axis=1).astype(float)      # (B,)
    n_neg_b = neg_boot.sum(axis=1).astype(float)      # (B,)

    # Youden's J matrix (B, T): loop over the (small) grid, vectorise over
    # resamples. J = sensitivity + specificity - 1, with RQ48's safe-division
    # convention: sens = 0 if n_pos == 0; spec = 1 if n_neg == 0.
    jmat = np.zeros((n_boot, T), dtype=float)
    for ti in range(T):
        t = grid_arr[ti]
        flagged = kl_boot >= t - EPS                  # (B, n)
        tp = (flagged & pos_boot).sum(axis=1).astype(float)
        fp = (flagged & neg_boot).sum(axis=1).astype(float)
        tn = n_neg_b - fp
        # sens = tp / n_pos_b (0 if n_pos_b == 0); spec = tn / n_neg_b (1 if 0).
        sens = np.where(n_pos_b > 0, tp / np.where(n_pos_b > 0, n_pos_b, 1.0), 0.0)
        spec = np.where(n_neg_b > 0,
                        tn / np.where(n_neg_b > 0, n_neg_b, 1.0), 1.0)
        jmat[:, ti] = sens + spec - 1.0

    # theta*_b = lowest-t threshold achieving max J (within EPS) for resample b.
    best_per_b = jmat.max(axis=1)                     # (B,)
    is_max = jmat >= best_per_b[:, None] - EPS        # (B, T)
    idx_b = is_max.argmax(axis=1)                      # first True = lowest t
    thresholds = grid_arr[idx_b]                       # (B,)

    # OOB cascade cpWER per resample (clean loop; each iteration is cheap).
    oob_cpwer = np.empty(n_boot, dtype=float)
    n_oob_arr = np.empty(n_boot, dtype=int)
    n_esc_arr = np.empty(n_boot, dtype=int)
    for b in range(n_boot):
        counts = np.bincount(boot_idx[b], minlength=n)
        oob_mask = counts == 0
        no = int(oob_mask.sum())
        n_oob_arr[b] = no
        if no == 0:
            oob_cpwer[b] = float("nan")
            n_esc_arr[b] = 0
            continue
        esc = kl[oob_mask] >= thresholds[b] - EPS
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
    grid: list[float] | None = None,
) -> tuple[float, np.ndarray]:
    """Delete-1 jackknife acceleration for the BCa CI.

    For each i in 0..n-1: leave window i out, calibrate the J-optimal KL
    threshold on the remaining n-1 windows, and compute the in-sample cascade
    cpWER on those n-1 windows (theta_(i)). The acceleration is

        a = sum( (theta_bar - theta_(i))^3 ) / ( 6 * sum( (theta_bar - theta_(i))^2 )^1.5 )

    Returns (a, theta_loo). a = 0.0 when the denominator is 0 (no variation),
    which collapses BCa to the bias-corrected percentile."""
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
        cal = calibrate_youdens_j(kl[mask], labels[mask], grid=grid)
        theta_loo[i] = cascade_cpwer_at_threshold(
            tiny[mask], base[mask], kl[mask], cal["threshold"])
    theta_bar = float(theta_loo.mean())
    diff = theta_bar - theta_loo
    # Guard against float-precision noise (mirrors RQ54's jackknife guard).
    scale = max(abs(theta_bar), 1.0)
    if float(np.max(np.abs(diff))) < 1e-12 * scale:
        return 0.0, theta_loo
    num = float(np.sum(diff ** 3))
    den = 6.0 * (float(np.sum(diff ** 2)) ** 1.5)
    a = num / den if den > 0 else 0.0
    return a, theta_loo


# --------------------------------------------------------------- normal CDF helpers
def norm_cdf(x: float) -> float:
    """Standard-normal forward CDF: Phi(x) = 0.5 * erfc(-x / sqrt(2)).

    Used by the BCa adjusted-percentile step (the argument there is a z-score,
    so the FORWARD CDF is required, not the inverse). No scipy dependency."""
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


# --------------------------------------------------------------- inverse normal CDF
def norm_ppf(p: float) -> float:
    """Standard-normal inverse CDF (Acklam's rational approximation).

    Accurate to ~1e-9 across (0, 1); no scipy dependency. ``p`` outside (0, 1)
    returns +/-inf for p <= 0 / p >= 1."""
    if p <= 0.0:
        return float("-inf")
    if p >= 1.0:
        return float("inf")
    # Acklam constants.
    a = (-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00)
    plow = 0.02425
    phigh = 1.0 - plow
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    elif p <= phigh:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    # one Halley refinement step against math.erf for ~1e-10 accuracy
    e = 0.5 * math.erfc(-x / math.sqrt(2.0)) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    x = x - u / (1.0 + x * u / 2.0)
    return float(x)


# --------------------------------------------------------------- BCa CI
def bca_ci(
    theta_hat: float,
    boot_samples: np.ndarray,
    accel: float,
    alpha: float = ALPHA,
) -> dict[str, Any]:
    """BCa (bias-corrected and accelerated) 95% CI on ``boot_samples``.

    - theta_hat: the point estimate (in-sample cascade cpWER at the in-sample
      Youden's J threshold).
    - boot_samples: the bootstrap OOB cpWER values (nan dropped).
    - accel: the jackknife acceleration (``jackknife_acceleration``).

    Returns a dict with the CI bounds, z0, accel, the adjusted percentiles, and
    a ``method`` flag ("bca" or "percentile_fallback" if the BCa denominator
    degenerates). Bias-correction proportion is clamped to (0.5/B, 1 - 0.5/B)
    so z0 stays finite when theta_hat lies outside the bootstrap range."""
    boot = np.asarray(boot_samples, dtype=float)
    boot = boot[~np.isnan(boot)]
    B = int(boot.size)
    if B == 0:
        return {"lo": float("nan"), "hi": float("nan"), "median": float("nan"),
                "z0": float("nan"), "accel": float(accel),
                "alpha1": float("nan"), "alpha2": float("nan"),
                "method": "empty", "n_valid": 0}
    median = float(np.median(boot))
    # bias correction z0 = Phi^{-1}( #{boot < theta_hat} / B )
    prop_less = float(np.mean(boot < theta_hat))
    prop_less = min(max(prop_less, 0.5 / B), 1.0 - 0.5 / B)
    z0 = norm_ppf(prop_less)
    z_lo = norm_ppf(alpha / 2.0)
    z_hi = norm_ppf(1.0 - alpha / 2.0)

    def _adjust(z: float) -> float:
        # BCa adjusted percentile: alpha = Phi(z0 + (z0 + z_alpha) / (1 - a(z0 + z_alpha))).
        # The argument is a z-score, so the FORWARD CDF (norm_cdf) is required,
        # not the inverse (norm_ppf).
        denom = 1.0 - accel * (z0 + z)
        if abs(denom) < 1e-12:
            return float("nan")
        return norm_cdf(z0 + (z0 + z) / denom)

    a1 = _adjust(z_lo)
    a2 = _adjust(z_hi)
    if not (np.isfinite(a1) and np.isfinite(a2)):
        lo = float(np.percentile(boot, 100.0 * alpha / 2.0))
        hi = float(np.percentile(boot, 100.0 * (1.0 - alpha / 2.0)))
        return {"lo": lo, "hi": hi, "median": median, "z0": z0, "accel": float(accel),
                "alpha1": float("nan"), "alpha2": float("nan"),
                "method": "percentile_fallback", "n_valid": B}
    a1c = min(max(a1, 0.0), 1.0)
    a2c = min(max(a2, 0.0), 1.0)
    lo = float(np.percentile(boot, 100.0 * a1c))
    hi = float(np.percentile(boot, 100.0 * a2c))
    return {"lo": lo, "hi": hi, "median": median, "z0": z0, "accel": float(accel),
            "alpha1": float(a1c), "alpha2": float(a2c),
            "method": "bca", "n_valid": B}


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
    ``resample, threshold, oob_cpwer, n_oob, n_escalated_oob, oob_fraction, escalation_fraction_oob``.
    ``oob_cpwer`` is blank when the OOB set was empty (nan). This is the
    machine-readable per-resample counterpart to the JSON ``per_bootstrap``
    block, suitable for downstream Pareto / stability plotting.
    """
    import csv
    B = int(thresholds.shape[0])
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["resample", "threshold", "oob_cpwer", "n_oob",
                    "n_escalated_oob", "oob_fraction", "escalation_fraction_oob"])
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
    assert abs(rq43_cas - RQ43_CASCADE_CPWER) < 1e-4, (
        f"RQ43 cascade @ KL=3.30 = {rq43_cas}, expected ~{RQ43_CASCADE_CPWER}")
    assert abs(baseline - RQ43_BASELINE_CPWER) < 1e-4
    assert n_hall == 37 and n_clean == 40, f"label counts {n_hall}/{n_clean}"

    # --- in-sample Youden's J calibration (full 77 windows)
    in_sample_cal = calibrate_youdens_j(kl, labels, grid=KL_THRESHOLD_GRID)
    j_threshold = float(in_sample_cal["threshold"])
    theta_hat = cascade_cpwer_at_threshold(tiny, base, kl, j_threshold)
    j_compute = cascade_compute_at_threshold(kl, j_threshold)
    j_frac = float(np.mean(kl >= j_threshold - EPS))

    # --- bootstrap Youden's J cascade (B=10000, seed=42)
    boot = bootstrap_youdens_j_cascade(tiny, base, kl, labels,
                                       grid=KL_THRESHOLD_GRID, n_boot=N_BOOT, seed=SEED)
    boot_thr = boot["thresholds"]
    boot_oob = boot["oob_cpwer"]
    n_oob_mean = float(np.mean(boot["n_oob"]))

    # --- mode count on the bootstrap threshold distribution (RQ48's count_modes)
    modes = count_modes(boot_thr, MIN_MODE_FRACTION)

    # --- jackknife acceleration + BCa CI on the OOB cpWER distribution
    accel, theta_loo = jackknife_acceleration(tiny, base, kl, labels, KL_THRESHOLD_GRID)
    bca = bca_ci(theta_hat, boot_oob, accel, alpha=ALPHA)
    bca_width = bca["hi"] - bca["lo"]
    oob_median = bca["median"]
    oob_mean = float(np.nanmean(boot_oob))

    # --- hypothesis verdicts
    h59a_supported = j_frac < H59A_MAX_ESCALATION
    h59b_supported = oob_median <= H59B_MAX_CPWER
    h59c_supported = bca_width <= H59C_MAX_WIDTH

    # --- RQ46 original-rule reference (read from RQ46 JSON @ KL=3.30)
    rq46_ref = {"ci_lo": RQ46_CI_LO, "ci_hi": RQ46_CI_HI, "width": RQ46_CI_WIDTH}
    try:
        rq46_data = json.loads(RQ46_JSON.read_text(encoding="utf-8"))
        for p in rq46_data.get("per_point", []):
            if abs(float(p["threshold"]) - RQ43_KL_THRESHOLD) < 1e-9:
                rq46_ref = {"ci_lo": float(p["cpwer_ci_lo"]),
                            "ci_hi": float(p["cpwer_ci_hi"]),
                            "width": round(float(p["cpwer_ci_hi"]) - float(p["cpwer_ci_lo"]), 6)}
                break
    except (OSError, ValueError, KeyError):
        pass

    # --- RQ54 F1 reference (read from RQ54 JSON for direct comparison)
    rq54_ref = {
        "f1_threshold": None, "f1_escalation": RQ54_F1_ESCALATION,
        "f1_oob_median_cpwer": RQ54_F1_OOB_MEDIAN_CPWER,
        "f1_bca_width": RQ54_F1_BCA_WIDTH, "f1_modes": RQ54_F1_MODES_KL,
    }
    try:
        rq54_data = json.loads(RQ54_JSON.read_text(encoding="utf-8"))
        rq54_ref["f1_threshold"] = float(rq54_data["in_sample_f1_calibration"]["threshold"])
        rq54_ref["f1_escalation"] = float(
            rq54_data["in_sample_f1_calibration"]["escalation_fraction"])
        rq54_ref["f1_oob_median_cpwer"] = float(
            rq54_data["bootstrap_oob_cpwer_distribution"]["median"])
        rq54_ref["f1_bca_width"] = float(rq54_data["bca_ci"]["width"])
        rq54_ref["f1_modes"] = int(
            rq54_data["bootstrap_threshold_distribution"]["n_modes_5pct"])
    except (OSError, ValueError, KeyError):
        pass

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": ("RQ59: Cascade with Youden's J calibration -- does Youden's J give "
               "a less aggressive cascade operating point than F1 while "
               "maintaining robustness?"),
        "builds_on": {
            "RQ43": "results/frontier/three_tier_cascade/ (PR #959, 3-tier KL cascade)",
            "RQ44": "results/frontier/bootstrap_threshold_stability/ (PR #963, OOB bootstrap)",
            "RQ46": "results/frontier/bootstrap_pareto/ (PR #966, original-rule CI anchor)",
            "RQ48": "results/frontier/calibration_rule_comparison/ (PR #965, Youden's J rule + count_modes)",
            "RQ54": "results/frontier/cascade_f1_calibration/ (PR #971, F1 cascade comparison baseline)",
        },
        "source_data": {
            "rq43_json": str(RQ43_JSON.relative_to(PROJECT_ROOT)),
            "rq43_label": "experimental/frontier",
            "aishell4_json": str(AISHELL4_JSON.relative_to(PROJECT_ROOT)),
            "aishell4_label": "external/sanity-check",
            "aishell4_asr_model": "whisper-tiny",
        },
        "method": (
            "REANALYSIS (no ASR run). Loads RQ43's 77 per-window (tiny_sep_cpwer, "
            "base_sep_cpwer, kl_sep) so the cascade corpus is byte-identical to "
            "RQ43/RQ46/RQ54. The ONLY change vs RQ54 is the KL-gate calibration "
            "rule: RQ54's F1 maximisation is replaced by RQ48's Youden's J "
            "maximisation (J = sensitivity + specificity - 1, 0.01-step KL grid "
            "over [0.00, 8.55], lowest-threshold tie-break), imported verbatim "
            "from RQ48. Hallucination label = tiny_sep_cpwer > 1.0 (37 hall / 40 "
            "clean, RQ44/RQ48/RQ54 rule). Cascade: tiny on all windows -> KL gate "
            "(kl >= thr -> escalate to base) -> base (cpWER = tiny * 0.428031, "
            "RQ43's separated ratio). Bootstrap B=10000 seed=42: per resample "
            "calibrate J threshold on in-bag windows, evaluate cascade cpWER on "
            "OOB windows (RQ44 OOB protocol). BCa 95% CI on the OOB cpWER "
            "distribution (bias-correction z0 from the in-sample point estimate "
            "theta_hat; acceleration from a delete-1 jackknife). Mode count via "
            "RQ48's count_modes (>= 5% frequency)."
        ),
        "controlled_comparison_note": (
            "The cascade simulation is held fixed at RQ43's actual implementation "
            "(real whisper-tiny cpWER for tier 1; base cpWER = tiny * 0.428031 for "
            "tier 3) so the H59b comparison to RQ43's 0.888947 anchor and the "
            "H59a comparison to RQ54's 83.1% F1 escalation are apples-to-apples. "
            "The ONLY independent variable vs RQ54 is the calibration rule "
            "(Youden's J instead of F1)."
        ),
        "n_windows": n,
        "n_hallucinated": n_hall,
        "n_clean": n_clean,
        "hallucination_label_rule": "tiny_sep_cpwer > 1.0 (== always_separated_cpwer > 1.0)",
        "kl_grid": {"step": 0.01, "lo": 0.0, "hi": 8.55, "n_points": len(KL_THRESHOLD_GRID)},
        "compute_model": {"tiny": COMPUTE_TINY, "base": COMPUTE_BASE,
                          "source": "RQ43 / runtime_cascade (base 1.93x slower)"},
        "bootstrap": {"n_boot": N_BOOT, "seed": SEED, "resample_size": n,
                      "oob_protocol": "RQ44 out_of_bag (calibrate in-bag, evaluate OOB)",
                      "expected_oob_size": round(n * ((1 - 1 / n) ** n), 4),
                      "mean_oob_size": round(n_oob_mean, 4)},
        "bca_method": {
            "theta_hat": "in-sample cascade cpWER at the in-sample Youden's J threshold",
            "boot_samples": "OOB cascade cpWER per resample",
            "acceleration": "delete-1 jackknife (in-sample cascade cpWER on n-1)",
            "bias_correction": "z0 = Phi^{-1}( #{boot < theta_hat} / B ), clamped to (0.5/B, 1-0.5/B)",
            "normal_inverse": "Acklam rational approximation + 1 Halley step (no scipy)",
        },
        "rq43_original_rule_reference": {
            "kl_threshold": RQ43_KL_THRESHOLD,
            "cascade_cpwer": RQ43_CASCADE_CPWER,
            "baseline_cpwer": RQ43_BASELINE_CPWER,
            "base_ratio": RQ43_BASE_RATIO,
            "reproduced_in_sample": round(rq43_cas, 6),
            "rule": "max sensitivity at >= 90% specificity",
        },
        "rq46_original_rule_ci_reference": {
            **rq46_ref,
            "method": "percentile CI (RQ46), in-bag at fixed threshold 3.30",
            "note": ("RQ46's anchor is a percentile CI evaluated in-bag at the FIXED "
                     "threshold 3.30. RQ59's BCa CI is bias-corrected + accelerated "
                     "and evaluated OOB at the RE-CALIBRATED Youden's J threshold. "
                     "The H59c comparison is therefore directional, not a pure "
                     "CI-method swap (same caveat as RQ54's H54b)."),
        },
        "rq48_youdens_j_reference": {
            "detector": "lang_id_entropy",
            "youdens_j_modes": RQ48_YOUDENS_J_MODES_LANGID,
            "note": ("RQ48 found Youden's J gives 3 modes on lang-id-entropy (vs "
                     "F1's 2, vs the original rule's 6). RQ59 tests whether that "
                     "transfers to the KL detector and the cascade operating point."),
        },
        "rq54_f1_reference": {
            "detector": "kl_sep",
            **rq54_ref,
            "note": ("RQ54's F1 cascade on the KL detector: 1 mode (KL=0.01, 96.3%), "
                     "83.1% escalation, OOB median cpWER 0.780, BCa width 0.2481. "
                     "RQ59 asks whether Youden's J is less aggressive (H59a) while "
                     "maintaining robustness (H59b/c)."),
        },
        "in_sample_youdens_j_calibration": {
            "threshold": round(j_threshold, 6),
            "sensitivity": round(float(in_sample_cal["sensitivity"]), 6),
            "specificity": round(float(in_sample_cal["specificity"]), 6),
            "youdens_j": round(float(in_sample_cal.get("youdens_j", float("nan"))), 6),
            "tp": int(in_sample_cal["tp"]), "fp": int(in_sample_cal["fp"]),
            "tn": int(in_sample_cal["tn"]), "fn": int(in_sample_cal["fn"]),
            "cascade_cpwer": round(theta_hat, 6),
            "cascade_compute": round(j_compute, 6),
            "escalation_fraction": round(j_frac, 6),
        },
        "bootstrap_threshold_distribution": {
            "median": round(float(np.median(boot_thr)), 6),
            "mean": round(float(np.mean(boot_thr)), 6),
            "std": round(float(np.std(boot_thr)), 6),
            "min": round(float(np.min(boot_thr)), 6),
            "max": round(float(np.max(boot_thr)), 6),
            "n_unique": int(np.unique(boot_thr).size),
            "n_modes_5pct": modes["n_modes"],
            "modes_5pct": modes["modes"],
            "min_mode_fraction": float(MIN_MODE_FRACTION),
        },
        "bootstrap_oob_cpwer_distribution": {
            "n_valid": int(np.sum(~np.isnan(boot_oob))),
            "median": round(oob_median, 6),
            "mean": round(oob_mean, 6),
            "min": round(float(np.nanmin(boot_oob)), 6),
            "max": round(float(np.nanmax(boot_oob)), 6),
            "p2_5": round(float(np.nanpercentile(boot_oob, 2.5)), 6),
            "p97_5": round(float(np.nanpercentile(boot_oob, 97.5)), 6),
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
        "hypothesis_verdicts": {
            "H59a": {
                "statement": ("Youden's J cascade escalates < 83% of windows to base "
                              "(less aggressive than F1's 83.1%)"),
                "escalation_fraction": round(j_frac, 6),
                "f1_reference_escalation": RQ54_F1_ESCALATION,
                "max_escalation": H59A_MAX_ESCALATION,
                "kill": f"escalation fraction >= {H59A_MAX_ESCALATION}",
                "supported": bool(h59a_supported),
            },
            "H59b": {
                "statement": ("Youden's J cascade OOB cpWER <= 0.889 (matches RQ43's "
                              "original-rule cpWER 0.888947)"),
                "median_cpwer": round(oob_median, 6),
                "rq43_reference_cpwer": RQ43_CASCADE_CPWER,
                "max_cpwer": H59B_MAX_CPWER,
                "kill": f"median cpWER > {H59B_MAX_CPWER}",
                "supported": bool(h59b_supported),
            },
            "H59c": {
                "statement": ("Youden's J cascade BCa CI width <= 0.2489 (maintains "
                              "robustness vs RQ46's original-rule width)"),
                "bca_ci_width": round(bca_width, 6),
                "rq46_reference_width": RQ46_CI_WIDTH,
                "max_width": H59C_MAX_WIDTH,
                "kill": f"BCa width > {H59C_MAX_WIDTH}",
                "supported": bool(h59c_supported),
            },
        },
        "per_bootstrap": {
            "thresholds": [round(float(t), 6) for t in boot_thr],
            "oob_cpwer": [round(float(c), 6) if not math.isnan(float(c)) else None
                          for c in boot_oob],
            "n_oob": [int(x) for x in boot["n_oob"]],
        },
    }
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_bootstrap_csv(OUT_CSV, boot["boot_idx"], boot_thr, boot_oob,
                        boot["n_oob"], boot["n_escalated_oob"], n)

    # --- console
    print(f"=== RQ59: Cascade with Youden's J calibration ===")
    print(f"Label: experimental/frontier  |  n={n} AISHELL-4 windows "
          f"({n_hall} hall / {n_clean} clean)")
    print(f"Controlled comparison: only the KL-gate calibration rule changes vs RQ54 (F1).")
    print(f"RQ43 original rule @ KL=3.30: cpwer={rq43_cas:.4f} (reproduces {RQ43_CASCADE_CPWER})")
    print()
    print(f"In-sample Youden's J calibration:")
    print(f"  J KL threshold = {j_threshold:.4f}  (RQ43 original: 3.30, RQ54 F1: 0.01)")
    print(f"  J = {in_sample_cal.get('youdens_j', float('nan')):.4f}  "
          f"sens={in_sample_cal['sensitivity']:.4f} spec={in_sample_cal['specificity']:.4f}")
    print(f"  TP/FP/TN/FN = {in_sample_cal['tp']}/{in_sample_cal['fp']}/"
          f"{in_sample_cal['tn']}/{in_sample_cal['fn']}")
    print(f"  in-sample cascade cpWER = {theta_hat:.4f}  "
          f"(compute {j_compute:.4f}x, frac {j_frac:.1%})")
    print()
    print(f"Bootstrap B={N_BOOT} seed={SEED} (OOB, re-calibrated J threshold per resample):")
    print(f"  threshold: median={np.median(boot_thr):.4f}  "
          f"n_unique={np.unique(boot_thr).size}  n_modes>=5%={modes['n_modes']}")
    for m in modes["modes"]:
        print(f"    mode KL={m['threshold']:.4f}  count={m['count']}  frac={m['fraction']:.3f}")
    print(f"  OOB cpWER: median={oob_median:.4f}  mean={oob_mean:.4f}  "
          f"pct[{np.nanpercentile(boot_oob,2.5):.4f},{np.nanpercentile(boot_oob,97.5):.4f}]")
    print(f"  BCa CI: [{bca['lo']:.4f}, {bca['hi']:.4f}]  width={bca_width:.4f}  "
          f"(z0={bca['z0']:.4f}, a={accel:.4f}, method={bca['method']})")
    print()
    print("Hypothesis verdicts:")
    print(f"  H59a (escalation < {H59A_MAX_ESCALATION:.0%}):  "
          f"{'SUPPORTED' if h59a_supported else 'KILLED'}  "
          f"(frac={j_frac:.4f}, F1 ref={RQ54_F1_ESCALATION:.4f})")
    print(f"  H59b (median cpWER <= {H59B_MAX_CPWER}):  "
          f"{'SUPPORTED' if h59b_supported else 'KILLED'}  (median={oob_median:.4f})")
    print(f"  H59c (BCa width <= {H59C_MAX_WIDTH}):  "
          f"{'SUPPORTED' if h59c_supported else 'KILLED'}  (width={bca_width:.4f})")
    print()
    print(f"RQ54 F1 reference: thr={rq54_ref['f1_threshold']}  frac={rq54_ref['f1_escalation']:.4f}  "
          f"cpwer={rq54_ref['f1_oob_median_cpwer']:.4f}  width={rq54_ref['f1_bca_width']:.4f}  "
          f"modes={rq54_ref['f1_modes']}")
    print(f"RQ46 original-rule reference: CI=[{rq46_ref['ci_lo']:.4f},{rq46_ref['ci_hi']:.4f}] "
          f"width={rq46_ref['width']:.4f} (percentile, in-bag, fixed thr=3.30)")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
