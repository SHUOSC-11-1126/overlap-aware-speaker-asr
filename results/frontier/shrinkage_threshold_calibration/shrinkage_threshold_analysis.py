"""RQ61: Shrinkage threshold calibration.

REANALYSIS ONLY -- no Whisper / no ASR / no LLM. This script reuses RQ44's
bootstrap framework (PR #963, ``results/frontier/bootstrap_threshold_stability/``)
and the same AISHELL-4 external-validation windows
(``results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json``,
label ``external/sanity-check``, PR #890) to ask: does a Bayesian shrinkage
prior on the threshold reduce the 6-modality that RQ44 observed under the "max
sensitivity at >= 90% specificity" rule (H44b KILLED, width 0.94)?

Motivation (RQ44 -> RQ48 -> RQ49/RQ57 -> RQ61)
----------------------------------------------
RQ44 showed the bootstrap threshold distribution is 6-modal over [0.01, 0.95]
under the baseline rule. RQ48 (calibration-rule comparison) decomposed the
modality: the high-threshold modes (0.87, 0.95) are rule artefacts that smoother
rules (Youden's J, F1) eliminate, but the low-threshold "Mode S catch" mode
(0.01) persists under every rule -- a fundamental detector ambiguity, not a
calibration choice. RQ49 (speaker-count stratification) and RQ57 (duration
stratification) both FAILED to reduce the modality by slicing the data. RQ57
explicitly recommended: "next lever: a different calibration rule
(shrinkage/regularised), not another stratification variable." RQ61 tests
whether a Bayesian shrinkage prior on the threshold reduces the modality.

Method (RQ61)
-------------
Instead of pure maximum-sensitivity-at-90%-specificity, maximise the
regularised objective

    sensitivity - lambda * |threshold - prior_mean|

over thresholds with specificity >= 0.90, where ``prior_mean = 0.38`` (RQ44's
bootstrap median) and ``lambda`` is the regularisation strength. The penalty
pulls the threshold toward the prior: when two thresholds tie (or nearly tie)
on sensitivity, the one closer to 0.38 wins. When ``lambda = 0`` the rule
reduces EXACTLY to RQ44's ``calibrate_threshold_at_spec`` (max sensitivity at
>= 90% specificity, tie-break higher specificity then lower threshold) -- this
is verified by a direct equivalence test.

For each ``lambda`` in {0.0, 0.01, 0.1, 0.5, 1.0}: draw B=10000 bootstrap
resamples (seed=42, n=77 with replacement) ONCE and reuse the SAME resample
indices for all lambdas (paired comparison). On each resample: calibrate the
shrinkage threshold on the in-bag windows, evaluate the corrected-router cpWER
on the out-of-bag (OOB) windows (RQ44's ``out_of_bag_cpwer``). Aggregate:
threshold median, 2.5/97.5 percentile interval width, mode count (RQ48's
``count_modes``, >= 5% frequency), and median OOB cpWER.

Pre-registered hypotheses (issue #985)
--------------------------------------
- H61a: Shrinkage-calibrated threshold has <= 2 modes (vs RQ44's 6). KILLED
        if > 2 modes (>= 5% frequency).
- H61b: Shrinkage OOB cpWER <= 1.056 (matches RQ44's deployability). KILLED
        if > 1.056.
- H61c: Shrinkage threshold width < 0.94 (RQ44's width). KILLED if >= 0.94.

This script is pure reanalysis (numpy + stdlib only; no scipy / sklearn /
Whisper / meeteval / LLM). Detector primitives, the bootstrap draw, the OOB
cpWER evaluator, and the baseline calibration rule are imported verbatim from
RQ44's module; ``count_modes`` is imported verbatim from RQ48's module.

Label: experimental/frontier. Builds on RQ13 (PR #904), RQ16 (PR #912), RQ25
(PR #929), RQ44 (PR #963), RQ48 (PR #969), RQ49, RQ57. Closes #985.
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
SRC_JSON = (
    PROJECT_ROOT
    / "results"
    / "external_sanity_check"
    / "aishell4"
    / "rq1_aishell4_validation_results.json"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "shrinkage_threshold_calibration"
OUT_CSV = OUT_DIR / "shrinkage_threshold_results.csv"
OUT_JSON = OUT_DIR / "shrinkage_threshold_results.json"

# ------------------------------------------ import RQ44's framework (verbatim reuse)
_RQ44_DIR = PROJECT_ROOT / "results" / "frontier" / "bootstrap_threshold_stability"
sys.path.insert(0, str(_RQ44_DIR))
import bootstrap_threshold_analysis as rq44  # noqa: E402  (path-injected import)

# ------------------------------------------ import RQ48's count_modes (verbatim reuse)
_RQ48_DIR = PROJECT_ROOT / "results" / "frontier" / "calibration_rule_comparison"
sys.path.insert(0, str(_RQ48_DIR))
import calibration_rule_analysis as rq48  # noqa: E402  (path-injected import)

# ------------------------------------------------------------------ constants
# Re-export RQ44's constants so thresholds are on the identical grid and the
# hallucination label matches RQ44 exactly (37 hallucinated / 40 clean).
THRESHOLD_GRID = rq44.THRESHOLD_GRID            # 0.00, 0.01, ..., 2.00 (201 pts)
EPS = rq44.EPS                                  # 1e-9
CATASTROPHIC_CPWER = rq44.CATASTROPHIC_CPWER    # 1.0
TARGET_SPECIFICITY = rq44.TARGET_SPECIFICITY    # 0.90

N_BOOT = 10000          # B=10000 (matches RQ44; RQ48 used 2000 for speed)
SEED = 42
MIN_MODE_FRACTION = 0.05   # "mode" = distinct threshold with >= 5% frequency (RQ48)

# Shrinkage prior: RQ44's bootstrap median threshold (0.380).
PRIOR_MEAN = 0.38
LAMBDAS = [0.0, 0.01, 0.1, 0.5, 1.0]

# RQ44 reference values (from PR #963 FINDINGS) -- the baseline to beat.
RQ44_OOB_CPWER_MEDIAN = 1.056      # RQ44's median held-out cpWER (H44c supported)
RQ44_N_UNIQUE = 6                  # RQ44's 6 distinct thresholds
RQ44_N_MODES_5PCT = 5              # RQ44's 5 modes at >= 5% (RQ48's definition)
RQ44_INTERVAL_WIDTH = 0.94         # RQ44's 2.5/97.5 percentile interval width

# Hypothesis kill thresholds.
H61A_MAX_MODES = 2     # H61a: kill if > 2 modes (>= 5% frequency)
H61B_MAX_CPWER = 1.056  # H61b: kill if OOB cpWER > 1.056 (supported if <= 1.056)
H61C_MAX_WIDTH = 0.94   # H61c: kill if width >= 0.94 (supported if < 0.94)
OOB_CPWER_GOOD = 1.10   # "good" OOB cpWER threshold (RQ44's H44c kill line)

# Detector + bootstrap framework reused verbatim from RQ44.
max_across_speakers = rq44.max_across_speakers
bootstrap_indices = rq44.bootstrap_indices
out_of_bag_cpwer = rq44.out_of_bag_cpwer
percentile_interval = rq44.percentile_interval

# Mode counter reused verbatim from RQ48.
count_modes = rq48.count_modes


# --------------------------------------------------------------- shrinkage objective
def shrinkage_objective(
    threshold: float, sensitivity: float, prior_mean: float, lam: float
) -> float:
    """The regularised calibration objective: ``sensitivity - lam * |t - prior|``.

    The penalty pulls the threshold toward ``prior_mean``: when two thresholds
    tie on sensitivity, the one closer to the prior has the higher objective.
    At ``lam = 0`` the objective reduces to pure sensitivity (RQ44's rule)."""
    return float(sensitivity) - float(lam) * abs(float(threshold) - float(prior_mean))


# --------------------------------------------------------------- confusion helper
def _confusion_arrays(
    scores: np.ndarray, labels: np.ndarray, grid_arr: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, int]:
    """Vectorised confusion-matrix sweep over ``grid_arr`` (faithful copy of
    RQ48's helper).

    For each grid threshold ``t`` (ascending), flag = ``score >= t`` (with EPS
    tolerance, matching RQ44). Returns ``(tp, fp, tn, fn, n_pos, n_neg)`` as
    int arrays of shape ``(len(grid),)``. Computed via broadcasting so the full
    201-point grid sweep on <= 77 windows is a single numpy expression."""
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
    """Sensitivity / specificity arrays with safe division (no RuntimeWarning).

    sensitivity = tp / n_pos (0 if n_pos == 0); specificity = tn / n_neg
    (1 if n_neg == 0). Faithful copy of RQ48's helper."""
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
    prior_mean: float,
    lam: float,
    target_spec: float,
) -> dict[str, Any]:
    """Pick the grid threshold maximising ``sensitivity - lam * |t - prior|``
    subject to ``specificity >= target_spec``.

    Tie-break: higher objective -> higher specificity -> lower threshold (the
    last via the first True in the ascending grid). At ``lam = 0`` this matches
    RQ44's ``calibrate_threshold_at_spec`` exactly (max sensitivity at
    >= target_spec specificity, tie-break higher specificity then lower
    threshold), so the shrinkage rule is a strict generalisation of RQ44's."""
    penalty = lam * np.abs(grid_arr - prior_mean)
    objective = sens - penalty
    feasible = spec >= target_spec - EPS
    if not feasible.any():
        # Fallback: highest grid threshold (most conservative: flag nothing),
        # matching RQ44's fallback. Hardcode sens=0, spec=1 (flag nothing).
        t_max = float(grid_arr[-1])
        return {
            "threshold": t_max,
            "sensitivity": 0.0,
            "specificity": 1.0,
            "tp": 0, "fp": 0,
            "tn": int(tn[-1] if tn.size else 0),
            "fn": int(fn[-1] if fn.size else 0),
            "objective": float(0.0 - lam * abs(t_max - prior_mean)),
            "penalty": float(lam * abs(t_max - prior_mean)),
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
    }


def calibrate_shrinkage(
    scores: np.ndarray,
    labels: np.ndarray,
    prior_mean: float = PRIOR_MEAN,
    lam: float = 0.0,
    grid: list[float] | None = None,
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """Shrinkage calibration: among thresholds with specificity >=
    ``target_spec``, maximise ``sensitivity - lam * |threshold - prior_mean|``.

    At ``lam = 0`` this reproduces RQ44's ``calibrate_threshold_at_spec`` (max
    sensitivity at >= 90% specificity, tie-break higher specificity then lower
    threshold) exactly -- the comparison's anchor. At ``lam > 0`` the penalty
    pulls the threshold toward ``prior_mean`` (0.38), breaking sensitivity ties
    (and near-ties) in favour of thresholds closer to the prior."""
    if grid is None:
        grid = THRESHOLD_GRID
    grid_arr = np.asarray(grid, dtype=float)
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    tp, fp, tn, fn, n_pos, n_neg = _confusion_arrays(scores, labels, grid_arr)
    sens, spec = _sens_spec(tp, fp, tn, fn, n_pos, n_neg)
    return _select_shrinkage(
        grid_arr, sens, spec, tp, fp, tn, fn, prior_mean, lam, target_spec
    )


# --------------------------------------------------------------- per-lambda aggregation
def _summarise_lambda(
    thresholds: np.ndarray, oob_cpwer: np.ndarray
) -> dict[str, Any]:
    """Aggregate the bootstrap threshold + OOB cpWER distributions for one
    lambda. Mirrors RQ48's ``_summarise_rule`` so the output schema is directly
    comparable to RQ44/RQ48."""
    thr = np.asarray(thresholds, dtype=float)
    oob_all = np.asarray(oob_cpwer, dtype=float)
    valid = ~np.isnan(oob_all)
    oob = oob_all[valid]
    thr_lo, thr_hi = percentile_interval(thr, 2.5, 97.5)
    oob_lo, oob_hi = percentile_interval(oob, 2.5, 97.5)
    modes = count_modes(thr, MIN_MODE_FRACTION)
    # RQ44-style "modes within 10% of max count" for traceability.
    rq44_dist = rq44.threshold_distribution(thr)
    return {
        "threshold_distribution": {
            "median": round(float(np.median(thr)), 6),
            "mean": round(float(np.mean(thr)), 6),
            "std": round(float(np.std(thr)), 6),
            "min": round(float(np.min(thr)), 6),
            "max": round(float(np.max(thr)), 6),
            "percentile_2_5": round(float(thr_lo), 6),
            "percentile_97_5": round(float(thr_hi), 6),
            "interval_width": round(float(thr_hi - thr_lo), 6),
            "n_unique": int(np.unique(thr).size),
            "n_modes_5pct": modes["n_modes"],
            "modes_5pct": modes["modes"],
            "min_mode_fraction": float(MIN_MODE_FRACTION),
            "modes_within_10pct_max": [
                {"threshold": round(t, 6), "count": c, "fraction": round(f, 6)}
                for t, c, f in rq44_dist["modes_within_10pct"]
            ],
            "top_values": [
                {"threshold": round(t, 6), "count": c, "fraction": round(f, 6)}
                for t, c, f in rq44_dist["top_values"]
            ],
        },
        "oob_cpwer_distribution": {
            "n_valid": int(valid.sum()),
            "median": round(float(np.median(oob)), 6),
            "mean": round(float(np.mean(oob)), 6),
            "min": round(float(np.min(oob)), 6),
            "max": round(float(np.max(oob)), 6),
            "percentile_2_5": round(float(oob_lo), 6),
            "percentile_97_5": round(float(oob_hi), 6),
            "frac_below_1_10": round(float(np.mean(oob < OOB_CPWER_GOOD)), 6),
            "frac_below_rq44_median": round(
                float(np.mean(oob < RQ44_OOB_CPWER_MEDIAN)), 6),
        },
    }


# --------------------------------------------------------------- best-lambda selection
def select_best_lambda(per_lambda_summary: dict[str, Any]) -> dict[str, Any]:
    """Pick the lambda that best reduces modality while maintaining
    deployability.

    Criteria (in order):
    1. Deployable: OOB median cpWER <= 1.056 (RQ44's median; H61b boundary).
    2. Among deployable: fewest modes (n_modes_5pct).
    3. Tie-break: narrowest interval width.
    4. Tie-break: smallest lambda (least regularisation, most faithful to data).

    If NO lambda is deployable, pick the one whose OOB cpWER is closest to
    (and <=) 1.056 -- i.e. the minimum OOB cpWER -- then fewest modes, then
    smallest lambda. ``per_lambda_summary`` is a dict keyed by lambda-string
    with values carrying ``lambda``, ``n_modes_5pct``, ``interval_width``,
    ``oob_cpwer_median``."""
    items = list(per_lambda_summary.items())
    deployable = [
        (k, v) for k, v in items
        if float(v["oob_cpwer_median"]) <= H61B_MAX_CPWER + EPS
    ]
    if deployable:
        best_key, best_v = min(
            deployable,
            key=lambda kv: (
                int(kv[1]["n_modes_5pct"]),
                float(kv[1]["interval_width"]),
                float(kv[1]["lambda"]),
            ),
        )
        reason = ("deployable (OOB <= 1.056); selected by fewest modes, then "
                  "narrowest width, then smallest lambda")
    else:
        best_key, best_v = min(
            items,
            key=lambda kv: (
                float(kv[1]["oob_cpwer_median"]),
                int(kv[1]["n_modes_5pct"]),
                float(kv[1]["lambda"]),
            ),
        )
        reason = ("no lambda deployable (all OOB > 1.056); selected by closest "
                  "OOB cpWER to 1.056, then fewest modes, then smallest lambda")
    all_supported = (
        _h61a_supported(best_v["n_modes_5pct"])
        and _h61b_supported(best_v["oob_cpwer_median"])
        and _h61c_supported(best_v["interval_width"])
    )
    return {
        "lambda": float(best_v["lambda"]),
        "lambda_key": best_key,
        "reason": reason,
        "all_hypotheses_supported": bool(all_supported),
        "n_modes_5pct": int(best_v["n_modes_5pct"]),
        "interval_width": float(best_v["interval_width"]),
        "oob_cpwer_median": float(best_v["oob_cpwer_median"]),
    }


# --------------------------------------------------------------- hypothesis helpers
def _h61a_supported(n_modes: int) -> bool:
    """H61a: <= 2 modes supported; > 2 killed."""
    return int(n_modes) <= H61A_MAX_MODES


def _h61b_supported(oob_median: float) -> bool:
    """H61b: OOB cpWER <= 1.056 supported; > 1.056 killed."""
    return float(oob_median) <= H61B_MAX_CPWER + EPS


def _h61c_supported(width: float) -> bool:
    """H61c: width < 0.94 supported; >= 0.94 killed."""
    return float(width) < H61C_MAX_WIDTH - EPS


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # Per-window signals (identical to RQ44/RQ48).
    lang_ent = np.array([max_across_speakers(w) for w in windows], dtype=float)
    mixed_cpwer = np.array([float(w["always_mixed_cpwer"]) for w in windows], dtype=float)
    sep_cpwer = np.array([float(w["always_separated_cpwer"]) for w in windows], dtype=float)
    labels = (sep_cpwer > CATASTROPHIC_CPWER).astype(int)  # 1 = hallucinated
    n_hall = int(labels.sum())
    n_clean = int((labels == 0).sum())
    grid_arr = np.asarray(THRESHOLD_GRID, dtype=float)

    # ----------------------------------------------- in-sample calibration per lambda
    in_sample: dict[str, Any] = {}
    for lam in LAMBDAS:
        cal = calibrate_shrinkage(lang_ent, labels, prior_mean=PRIOR_MEAN, lam=lam)
        flag = lang_ent >= cal["threshold"] - EPS
        selected = np.where(flag, mixed_cpwer, sep_cpwer)
        in_sample[str(lam)] = {
            "lambda": lam,
            "threshold": round(float(cal["threshold"]), 6),
            "sensitivity": round(float(cal["sensitivity"]), 6),
            "specificity": round(float(cal["specificity"]), 6),
            "tp": int(cal["tp"]), "fp": int(cal["fp"]),
            "tn": int(cal["tn"]), "fn": int(cal["fn"]),
            "penalty": round(float(cal["penalty"]), 6),
            "objective": round(float(cal["objective"]), 6),
            "expected_cpwer": round(float(selected.mean()), 6),
        }

    # ----------------------------------------------------------------- bootstrap
    # ONE index draw, reused for all lambdas -> paired comparison (RQ48 design).
    boot_idx = bootstrap_indices(n, N_BOOT, SEED)  # (N_BOOT, n)
    per_lambda: dict[str, Any] = {}
    for lam in LAMBDAS:
        per_lambda[str(lam)] = {
            "thresholds": np.empty(N_BOOT, dtype=float),
            "oob_cpwer": np.empty(N_BOOT, dtype=float),
            "n_oob": np.empty(N_BOOT, dtype=int),
        }

    for b in range(N_BOOT):
        idx = boot_idx[b]
        # Confusion arrays depend only on the resample, not on lambda -> compute
        # once per resample and reuse for all lambdas (5x speedup vs. calling
        # calibrate_shrinkage per lambda).
        tp, fp, tn, fn, n_pos, n_neg = _confusion_arrays(
            lang_ent[idx], labels[idx], grid_arr
        )
        sens, spec = _sens_spec(tp, fp, tn, fn, n_pos, n_neg)
        for lam in LAMBDAS:
            cal = _select_shrinkage(
                grid_arr, sens, spec, tp, fp, tn, fn,
                PRIOR_MEAN, lam, TARGET_SPECIFICITY,
            )
            thr = float(cal["threshold"])
            oob = out_of_bag_cpwer(lang_ent, mixed_cpwer, sep_cpwer, thr, idx)
            slot = per_lambda[str(lam)]
            slot["thresholds"][b] = thr
            slot["oob_cpwer"][b] = oob["cpwer"]
            slot["n_oob"][b] = oob["n_oob"]

    # ----------------------------------------------- aggregate per lambda
    per_lambda_summary: dict[str, Any] = {}
    per_lambda_full: dict[str, Any] = {}
    for lam in LAMBDAS:
        key = str(lam)
        thr = per_lambda[key]["thresholds"]
        oob = per_lambda[key]["oob_cpwer"]
        n_oob_mean = float(np.mean(per_lambda[key]["n_oob"]))
        summary = _summarise_lambda(thr, oob)
        td = summary["threshold_distribution"]
        od = summary["oob_cpwer_distribution"]
        h61a = _h61a_supported(td["n_modes_5pct"])
        h61b = _h61b_supported(od["median"])
        h61c = _h61c_supported(td["interval_width"])
        per_lambda_summary[key] = {
            "lambda": lam,
            "n_modes_5pct": td["n_modes_5pct"],
            "interval_width": td["interval_width"],
            "oob_cpwer_median": od["median"],
            "h61a_supported": bool(h61a),
            "h61b_supported": bool(h61b),
            "h61c_supported": bool(h61c),
        }
        per_lambda_full[key] = {
            "lambda": lam,
            "in_sample": in_sample[key],
            "summary": summary,
            "mean_oob_size": round(n_oob_mean, 4),
            "hypothesis_verdicts": {
                "H61a": {
                    "statement": f"<= {H61A_MAX_MODES} modes (vs RQ44's {RQ44_N_MODES_5PCT})",
                    "n_modes_5pct": td["n_modes_5pct"],
                    "max_modes": H61A_MAX_MODES,
                    "kill": f"> {H61A_MAX_MODES} modes with >= 5% frequency",
                    "supported": bool(h61a),
                },
                "H61b": {
                    "statement": f"OOB cpWER <= {H61B_MAX_CPWER} (matches RQ44)",
                    "median_oob_cpwer": od["median"],
                    "rq44_median_oob_cpwer": RQ44_OOB_CPWER_MEDIAN,
                    "kill": f"OOB cpWER > {H61B_MAX_CPWER}",
                    "supported": bool(h61b),
                },
                "H61c": {
                    "statement": f"threshold width < {H61C_MAX_WIDTH} (RQ44's width)",
                    "interval_width": td["interval_width"],
                    "rq44_interval_width": RQ44_INTERVAL_WIDTH,
                    "kill": f"width >= {H61C_MAX_WIDTH}",
                    "supported": bool(h61c),
                },
            },
            "per_bootstrap": {
                "thresholds": [round(float(t), 6) for t in thr],
                "oob_cpwer": [round(float(c), 6) if not math.isnan(float(c)) else None
                              for c in oob],
                "n_oob": [int(x) for x in per_lambda[key]["n_oob"]],
            },
        }

    # ------------------------------------------------------------ best lambda
    best = select_best_lambda(per_lambda_summary)
    best_key = best["lambda_key"]
    best_h61a = per_lambda_summary[best_key]["h61a_supported"]
    best_h61b = per_lambda_summary[best_key]["h61b_supported"]
    best_h61c = per_lambda_summary[best_key]["h61c_supported"]

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": ("RQ61: Shrinkage threshold calibration "
               "(Bayesian shrinkage prior on the lang-id entropy threshold)"),
        "closes_issue": 985,
        "builds_on": {
            "RQ13": "results/frontier/diverse_hallucination_detector/ (PR #904)",
            "RQ16": "results/frontier/corrected_router_simulation/ (PR #912)",
            "RQ25": "results/frontier/out_of_sample_router/ (PR #929)",
            "RQ44": "results/frontier/bootstrap_threshold_stability/ (PR #963)",
            "RQ48": "results/frontier/calibration_rule_comparison/ (PR #969)",
        },
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR / no LLM); B=10000 bootstrap "
            "resamples (seed=42) of the 77 AISHELL-4 windows, drawn ONCE and "
            "reused for all 5 lambda values (paired comparison). On each "
            "resample: calibrate the shrinkage threshold (maximise "
            "sensitivity - lambda * |threshold - 0.38| at >= 90% specificity) on "
            "in-bag windows, evaluate corrected-router cpWER on the out-of-bag "
            "windows (RQ44's out_of_bag_cpwer). At lambda=0 the rule reproduces "
            "RQ44's calibrate_threshold_at_spec exactly. Detector, bootstrap "
            "draw, OOB evaluator imported verbatim from RQ44; count_modes from RQ48."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated": n_hall,
        "n_clean": n_clean,
        "hallucination_label_rule": "always_separated_cpwer > 1.0",
        "routing_rule": (
            "lang_id_entropy >= threshold -> route MIXED (always_mixed_cpwer); "
            "else route SEPARATED (always_separated_cpwer). HIGH lang-id entropy "
            "= diverse multilingual gibberish = hallucination (RQ13/RQ16/RQ25/"
            "RQ44 convention)."
        ),
        "shrinkage_rule": (
            "maximise sensitivity - lambda * |threshold - prior_mean| subject to "
            "specificity >= 0.90, where prior_mean = 0.38 (RQ44's bootstrap "
            "median). Tie-break: higher objective, then higher specificity, then "
            "lower threshold. lambda=0 reproduces RQ44 exactly."
        ),
        "mode_definition": (
            "mode = distinct threshold value with bootstrap frequency >= 5% "
            "(RQ48 count_modes, min_fraction=0.05). This is the explicit "
            "kill-condition definition for H61a/b/c."
        ),
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "resample_size": n,
            "paired": True,
            "expected_oob_size": round(n * ((1 - 1 / n) ** n), 4),
        },
        "prior": {
            "prior_mean": PRIOR_MEAN,
            "prior_mean_source": "RQ44 bootstrap median threshold (0.380)",
            "lambdas": LAMBDAS,
        },
        "rq44_reference": {
            "median_oob_cpwer": RQ44_OOB_CPWER_MEDIAN,
            "n_distinct_thresholds": RQ44_N_UNIQUE,
            "n_modes_5pct": RQ44_N_MODES_5PCT,
            "interval_width": RQ44_INTERVAL_WIDTH,
            "baseline_rule": "max sensitivity at >= 90% specificity",
            "note": ("RQ61 lambda=0 uses the same seed (42) and B=10000 as RQ44, "
                     "so lambda=0 reproduces RQ44's threshold distribution."),
        },
        "in_sample_calibration": in_sample,
        "per_lambda": {k: {kk: vv for kk, vv in v.items() if kk != "per_bootstrap"}
                       for k, v in per_lambda_full.items()},
        "best_lambda": best,
        "hypothesis_verdicts": {
            "H61a": {
                "statement": (f"Shrinkage-calibrated threshold (best lambda="
                              f"{best['lambda']}) has <= {H61A_MAX_MODES} modes "
                              f"(vs RQ44's {RQ44_N_MODES_5PCT})"),
                "best_lambda": best["lambda"],
                "n_modes_5pct": best["n_modes_5pct"],
                "max_modes": H61A_MAX_MODES,
                "kill": f"> {H61A_MAX_MODES} modes with >= 5% frequency",
                "supported": bool(best_h61a),
            },
            "H61b": {
                "statement": (f"Shrinkage OOB cpWER (best lambda={best['lambda']}) "
                              f"<= {H61B_MAX_CPWER} (matches RQ44)"),
                "best_lambda": best["lambda"],
                "median_oob_cpwer": best["oob_cpwer_median"],
                "rq44_median_oob_cpwer": RQ44_OOB_CPWER_MEDIAN,
                "kill": f"OOB cpWER > {H61B_MAX_CPWER}",
                "supported": bool(best_h61b),
            },
            "H61c": {
                "statement": (f"Shrinkage threshold width (best lambda="
                              f"{best['lambda']}) < {H61C_MAX_WIDTH} (RQ44's width)"),
                "best_lambda": best["lambda"],
                "interval_width": best["interval_width"],
                "rq44_interval_width": RQ44_INTERVAL_WIDTH,
                "kill": f"width >= {H61C_MAX_WIDTH}",
                "supported": bool(best_h61c),
            },
        },
    }

    # ----------------------------------------------------------- write JSON
    summary_with_arrays: dict[str, Any] = dict(summary)
    summary_with_arrays["per_bootstrap"] = {
        k: per_lambda_full[k]["per_bootstrap"] for k in per_lambda_full
    }
    OUT_JSON.write_text(
        json.dumps(summary_with_arrays, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- write CSV
    csv_fields = [
        "lambda", "in_sample_threshold", "in_sample_expected_cpwer",
        "thr_median", "thr_p2_5", "thr_p97_5", "thr_interval_width",
        "thr_n_unique", "thr_n_modes_5pct",
        "oob_cpwer_median", "oob_cpwer_mean", "oob_cpwer_p2_5", "oob_cpwer_p97_5",
        "oob_frac_below_1_10", "oob_frac_below_rq44",
        "H61a_supported", "H61b_supported", "H61c_supported",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for lam in LAMBDAS:
            key = str(lam)
            pf = per_lambda_full[key]
            s = pf["summary"]
            td = s["threshold_distribution"]
            od = s["oob_cpwer_distribution"]
            wr.writerow({
                "lambda": lam,
                "in_sample_threshold": in_sample[key]["threshold"],
                "in_sample_expected_cpwer": in_sample[key]["expected_cpwer"],
                "thr_median": td["median"],
                "thr_p2_5": td["percentile_2_5"],
                "thr_p97_5": td["percentile_97_5"],
                "thr_interval_width": td["interval_width"],
                "thr_n_unique": td["n_unique"],
                "thr_n_modes_5pct": td["n_modes_5pct"],
                "oob_cpwer_median": od["median"],
                "oob_cpwer_mean": od["mean"],
                "oob_cpwer_p2_5": od["percentile_2_5"],
                "oob_cpwer_p97_5": od["percentile_97_5"],
                "oob_frac_below_1_10": od["frac_below_1_10"],
                "oob_frac_below_rq44": od["frac_below_rq44_median"],
                "H61a_supported": "yes" if per_lambda_summary[key]["h61a_supported"] else "no",
                "H61b_supported": "yes" if per_lambda_summary[key]["h61b_supported"] else "no",
                "H61c_supported": "yes" if per_lambda_summary[key]["h61c_supported"] else "no",
            })

    # ----------------------------------------------------------- console
    print(f"=== RQ61: Shrinkage threshold calibration (AISHELL-4, {n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucination label: always_separated_cpwer > 1.0 -> {n_hall} hall / {n_clean} clean")
    print(f"Bootstrap: B={N_BOOT}, seed={SEED}, paired across lambdas | prior_mean={PRIOR_MEAN}")
    print()
    print("In-sample calibration (full 77 windows, per lambda):")
    for lam in LAMBDAS:
        isam = in_sample[str(lam)]
        print(f"  lambda={lam:<4}  thr={isam['threshold']:.4f}  cpWER={isam['expected_cpwer']:.4f}"
              f"  sens={isam['sensitivity']:.4f} spec={isam['specificity']:.4f}"
              f"  penalty={isam['penalty']:.4f}  obj={isam['objective']:.4f}")
    print()
    print("Bootstrap threshold + OOB cpWER distributions (B=10000, paired):")
    for lam in LAMBDAS:
        key = str(lam)
        td = per_lambda_full[key]["summary"]["threshold_distribution"]
        od = per_lambda_full[key]["summary"]["oob_cpwer_distribution"]
        print(f"  --- lambda={lam} ---")
        print(f"    threshold: median={td['median']:.4f}  "
              f"pct[{td['percentile_2_5']:.4f}, {td['percentile_97_5']:.4f}]  "
              f"width={td['interval_width']:.4f}  "
              f"n_unique={td['n_unique']}  n_modes>=5%={td['n_modes_5pct']}")
        for m in td["modes_5pct"]:
            print(f"      mode thr={m['threshold']:.4f}  count={m['count']}  "
                  f"frac={m['fraction']:.3f}")
        print(f"    oob cpWER: median={od['median']:.4f}  mean={od['mean']:.4f}  "
              f"pct[{od['percentile_2_5']:.4f}, {od['percentile_97_5']:.4f}]  "
              f"frac<1.10={od['frac_below_1_10']:.3f}")
    print()
    print(f"Best lambda: {best['lambda']}  (all hypotheses supported: "
          f"{best['all_hypotheses_supported']})")
    print(f"  reason: {best['reason']}")
    print()
    print("Hypothesis verdicts (at best lambda):")
    print(f"  H61a (<= {H61A_MAX_MODES} modes vs RQ44's {RQ44_N_MODES_5PCT}): "
          f"{'SUPPORTED' if best_h61a else 'KILLED'}  "
          f"(n_modes={best['n_modes_5pct']})")
    print(f"  H61b (OOB cpWER <= {H61B_MAX_CPWER}):                  "
          f"{'SUPPORTED' if best_h61b else 'KILLED'}  "
          f"(median OOB={best['oob_cpwer_median']:.4f})")
    print(f"  H61c (width < {H61C_MAX_WIDTH}):                      "
          f"{'SUPPORTED' if best_h61c else 'KILLED'}  "
          f"(width={best['interval_width']:.4f})")
    print()
    print(f"RQ44 reference: {RQ44_N_UNIQUE} unique, {RQ44_N_MODES_5PCT} modes (>=5%), "
          f"width {RQ44_INTERVAL_WIDTH}, OOB {RQ44_OOB_CPWER_MEDIAN}")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
