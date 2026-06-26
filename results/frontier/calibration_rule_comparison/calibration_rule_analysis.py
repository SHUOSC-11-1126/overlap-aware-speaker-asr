"""RQ48: Calibration rule comparison for threshold stability.

REANALYSIS ONLY -- no Whisper / no ASR model is run. This script reuses RQ44's
bootstrap framework (PR #963, ``results/frontier/bootstrap_threshold_stability/``)
and the same AISHELL-4 external-validation windows (``results/external_sanity_check/
aishell4/rq1_aishell4_validation_results.json``, label ``external/sanity-check``,
PR #890) to ask: does a smoother calibration rule reduce the 6-modality of the
lang-id entropy threshold distribution that RQ44 observed under the "max
sensitivity at >= 90% specificity" rule (H44b KILLED, interval width 0.94)?

Motivation (RQ44)
-----------------
RQ44 showed the bootstrap threshold distribution is 6-modal over [0.01, 0.95]
under RQ44's baseline rule. RQ44's limitations (point 5) explicitly flagged that
the 6-modality is "partly a property of this rule's discontinuous behaviour at
the specificity boundary" and that "a smoother rule (e.g. maximise F1, or use a
parametric ROC fit) might reduce the number of modes". RQ48 tests that
conjecture directly by comparing 4 calibration rules on the SAME bootstrap
resamples.

The four calibration rules
--------------------------
1. ``calibrate_max_sens_at_spec`` -- RQ44's baseline: select the threshold with
   specificity >= 0.90 and maximal sensitivity. Delegates to RQ44's exact
   ``calibrate_threshold_at_spec`` so the baseline reproduces RQ44's 0.38
   in-sample threshold byte-for-byte.
2. ``calibrate_youdens_j`` -- maximise Youden's J = sensitivity + specificity - 1
   (a smooth, single-objective ROC-criterion with no specificity boundary).
3. ``calibrate_f1`` -- maximise F1 = 2*precision*recall / (precision+recall)
   (a smooth, single-objective precision/recall criterion).
4. ``calibrate_cost_aware`` -- minimise expected cpWER directly using the routing
   rule (flagged -> MIXED, unflagged -> SEPARATED). NOTE: this rule uses
   reference cpWER as the CALIBRATION OBJECTIVE on labelled data (analogous to
   how the other rules use the hallucination label, which is itself derived from
   cpWER > 1.0). cpWER is NOT used as a routing input -- the deployable routing
   signal remains lang_id_entropy. The cost-aware rule is therefore an
   oracle-style calibration criterion included to bound the achievable
   stability; it is labelled experimental/frontier.

Method
------
Load the 77 AISHELL-4 windows (read-only). Compute the lang-id entropy detector
score per window (max across separated speaker tracks -- RQ13/RQ16/RQ25/RQ44
verbatim, imported from RQ44's module so thresholds are directly comparable).
Draw B=2000 bootstrap resamples (seed=42, n=77 with replacement) ONCE and reuse
the SAME resample indices for all 4 rules, so the comparison is paired: any
difference in the threshold distribution is purely due to the calibration rule.
On each resample: calibrate the threshold on the in-bag windows, evaluate the
corrected-router cpWER on the out-of-bag (OOB) windows (RQ44's
``out_of_bag_cpwer``).

Pre-registered hypotheses (issue for RQ48)
------------------------------------------
- H48a: Youden's J gives <= 3 modes (vs RQ44's 6). Kill: > 3 modes with >= 5%
        frequency.
- H48b: F1 maximisation gives <= 3 modes. Kill: > 3 modes with >= 5% frequency.
- H48c: Cost-aware rule gives <= 2 modes AND median OOB cpWER < RQ44's 1.056.
        Kill: > 2 modes OR median OOB cpWER >= 1.056.

"Modes" here = distinct threshold values whose bootstrap frequency is >= 5%
(the ``count_modes`` helper). This is the explicit kill-condition definition;
it is stricter than RQ44's "modes within 10% of max count" -- the two are
reported side by side in the JSON for traceability.

This script is pure reanalysis (numpy + stdlib only; no scipy / sklearn /
Whisper / meeteval). Detector primitives, the bootstrap index draw, the OOB
cpWER evaluator, and the baseline calibration rule are imported verbatim from
RQ44's module to guarantee direct comparability.

Label: experimental/frontier. Builds on RQ13 (PR #904), RQ16 (PR #912), RQ25
(PR #929), and RQ44 (PR #963).
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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "calibration_rule_comparison"
OUT_CSV = OUT_DIR / "calibration_rule_results.csv"
OUT_JSON = OUT_DIR / "calibration_rule_results.json"

# ------------------------------------------ import RQ44's framework (verbatim reuse)
# The RQ44 analysis script lives in results/frontier/bootstrap_threshold_stability/.
# Reusing its detector + bootstrap + OOB evaluator guarantees the ONLY thing that
# varies across rules is the calibration criterion.
_RQ44_DIR = PROJECT_ROOT / "results" / "frontier" / "bootstrap_threshold_stability"
sys.path.insert(0, str(_RQ44_DIR))
import bootstrap_threshold_analysis as rq44  # noqa: E402  (path-injected import)

# ------------------------------------------------------------------ constants
# Re-export RQ44's constants so thresholds are on the identical grid and the
# hallucination label matches RQ44 exactly (37 hallucinated / 40 clean).
THRESHOLD_GRID = rq44.THRESHOLD_GRID            # 0.00, 0.01, ..., 2.00 (201 pts)
EPS = rq44.EPS                                  # 1e-9
CATASTROPHIC_CPWER = rq44.CATASTROPHIC_CPWER    # 1.0
TARGET_SPECIFICITY = rq44.TARGET_SPECIFICITY    # 0.90

N_BOOT = 2000          # B=2000 (keeps per-rule runtime < 60s; cf. RQ44's 10000)
SEED = 42
MIN_MODE_FRACTION = 0.05   # "mode" = distinct threshold with >= 5% frequency

# RQ44 reference values (from PR #963 FINDINGS) -- used by H48c's kill condition.
RQ44_OOB_CPWER_MEDIAN = 1.056      # RQ44's median held-out cpWER (H44c supported)
RQ44_N_DISTINCT_THRESHOLDS = 6     # RQ44's 6-modal threshold distribution

# Hypothesis kill thresholds.
H48A_MAX_MODES = 3     # Youden's J: kill if > 3 modes (>= 5% frequency)
H48B_MAX_MODES = 3     # F1: kill if > 3 modes (>= 5% frequency)
H48C_MAX_MODES = 2     # Cost-aware: kill if > 2 modes
H48C_CPWER_KILL = RQ44_OOB_CPWER_MEDIAN  # cost-aware: kill if median OOB cpWER >= 1.056
OOB_CPWER_GOOD = 1.10  # "good" OOB cpWER threshold (RQ44's H44c kill line)

# Detector + bootstrap framework reused verbatim from RQ44.
max_across_speakers = rq44.max_across_speakers
bootstrap_indices = rq44.bootstrap_indices
out_of_bag_cpwer = rq44.out_of_bag_cpwer
percentile_interval = rq44.percentile_interval


# --------------------------------------------------------------- confusion helper
def _confusion_arrays(
    scores: np.ndarray, labels: np.ndarray, grid: list[float]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, int, int]:
    """Vectorised confusion-matrix sweep over ``grid``.

    For each grid threshold ``t`` (ascending), flag = ``score >= t`` (with EPS
    tolerance, matching RQ44). Returns ``(tp, fp, tn, fn, n_pos, n_neg)`` as
    int arrays of shape ``(len(grid),)``. Computed via broadcasting so a full
    201-point grid sweep on <= 77 windows is a single numpy expression (the
    per-resample calibration is ~1000x faster than RQ44's Python loop, which
    matters because RQ48 runs 4 rules x B=2000 resamples)."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    grid_arr = np.asarray(grid, dtype=float)
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
    (1 if n_neg == 0). Uses a guarded denominator so numpy never divides by
    zero in the discarded branch."""
    safe_pos = n_pos if n_pos > 0 else 1
    safe_neg = n_neg if n_neg > 0 else 1
    sens = tp / safe_pos if n_pos > 0 else np.zeros(tp.shape, dtype=float)
    spec = tn / safe_neg if n_neg > 0 else np.ones(tn.shape, dtype=float)
    return sens, spec


def _select_threshold(
    grid_arr: np.ndarray,
    objective: np.ndarray,
    maximise: bool,
    tp: np.ndarray,
    fp: np.ndarray,
    tn: np.ndarray,
    fn: np.ndarray,
    sens: np.ndarray,
    spec: np.ndarray,
    extra: dict[str, np.ndarray] | None = None,
) -> dict[str, Any]:
    """Pick the grid threshold optimising ``objective``.

    Tie-breaker: the LOWEST threshold among ties (the grid is ascending, so the
    first index achieving the optimum within EPS). This mirrors RQ44's
    "lower threshold = more sensitive" convention and keeps every rule
    deterministic. Returns a dict shaped like RQ44's calibration output
    (``threshold, sensitivity, specificity, tp, fp, tn, fn``) plus any
    rule-specific metric in ``extra``."""
    obj = np.asarray(objective, dtype=float)
    if maximise:
        best_val = float(np.max(obj))
        mask = obj >= best_val - EPS
    else:
        best_val = float(np.min(obj))
        mask = obj <= best_val + EPS
    # np.argmax on a boolean array returns the first True index = lowest threshold.
    idx = int(np.argmax(mask))
    out: dict[str, Any] = {
        "threshold": float(grid_arr[idx]),
        "sensitivity": float(sens[idx]),
        "specificity": float(spec[idx]),
        "tp": int(tp[idx]),
        "fp": int(fp[idx]),
        "tn": int(tn[idx]),
        "fn": int(fn[idx]),
    }
    if extra is not None:
        for k, v in extra.items():
            out[k] = float(np.asarray(v, dtype=float)[idx])
    return out


# --------------------------------------------------------------- calibration rules
def calibrate_max_sens_at_spec(
    scores: np.ndarray,
    labels: np.ndarray,
    grid: list[float] | None = None,
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """RQ44's baseline rule: max sensitivity at >= ``target_spec`` specificity.

    Delegates to RQ44's exact ``calibrate_threshold_at_spec`` so the baseline
    reproduces RQ44's in-sample threshold (0.38) byte-for-byte -- the
    comparison's anchor."""
    if grid is None:
        grid = THRESHOLD_GRID
    return rq44.calibrate_threshold_at_spec(
        scores, labels, grid=grid, target_spec=target_spec
    )


def calibrate_youdens_j(
    scores: np.ndarray, labels: np.ndarray, grid: list[float] | None = None
) -> dict[str, Any]:
    """Maximise Youden's J = sensitivity + specificity - 1 (smooth ROC criterion).

    Unlike RQ44's rule, J has no discontinuous specificity boundary: it trades
    sensitivity and specificity continuously, so H48a tests whether it produces
    a less fragmented threshold distribution."""
    if grid is None:
        grid = THRESHOLD_GRID
    grid_arr = np.asarray(grid, dtype=float)
    tp, fp, tn, fn, n_pos, n_neg = _confusion_arrays(scores, labels, grid)
    sens, spec = _sens_spec(tp, fp, tn, fn, n_pos, n_neg)
    j = sens + spec - 1.0
    return _select_threshold(
        grid_arr, j, maximise=True, tp=tp, fp=fp, tn=tn, fn=fn,
        sens=sens, spec=spec, extra={"youdens_j": j},
    )


def calibrate_f1(
    scores: np.ndarray, labels: np.ndarray, grid: list[float] | None = None
) -> dict[str, Any]:
    """Maximise F1 = 2 * precision * recall / (precision + recall).

    precision = TP / (TP + FP); recall = TP / (TP + FN) = sensitivity. When
    TP = 0 (or prec + rec = 0) F1 is defined as 0. F1 is a smooth
    precision/recall criterion with no specificity boundary; H48b tests whether
    it reduces the mode count."""
    if grid is None:
        grid = THRESHOLD_GRID
    grid_arr = np.asarray(grid, dtype=float)
    tp, fp, tn, fn, n_pos, n_neg = _confusion_arrays(scores, labels, grid)
    sens, spec = _sens_spec(tp, fp, tn, fn, n_pos, n_neg)
    denom_prec = tp + fp
    safe_prec_denom = np.where(denom_prec > 0, denom_prec, 1)
    prec = np.where(denom_prec > 0, tp / safe_prec_denom, 0.0)
    rec = sens
    denom_f1 = prec + rec
    safe_f1_denom = np.where(denom_f1 > 0, denom_f1, 1.0)
    f1 = np.where(denom_f1 > 0, 2.0 * prec * rec / safe_f1_denom, 0.0)
    return _select_threshold(
        grid_arr, f1, maximise=True, tp=tp, fp=fp, tn=tn, fn=fn,
        sens=sens, spec=spec, extra={"f1": f1, "precision": prec},
    )


def calibrate_cost_aware(
    scores: np.ndarray,
    labels: np.ndarray,
    cpwer_mixed: np.ndarray,
    cpwer_separated: np.ndarray,
    grid: list[float] | None = None,
) -> dict[str, Any]:
    """Minimise expected cpWER using the routing rule (flagged -> MIXED,
    unflagged -> SEPARATED).

    For each grid threshold ``t``: flag = ``score >= t``; route flagged windows
    to ``cpwer_mixed`` and unflagged to ``cpwer_separated``; the calibration
    cost is the mean selected cpWER over the calibration set. Select the
    threshold minimising this cost.

    NOTE: ``cpwer_mixed`` / ``cpwer_separated`` are reference-derived and are
    used ONLY as the calibration objective on labelled data (the same role the
    hallucination label plays for the other rules -- and that label is itself
    ``cpwer_separated > 1.0``). cpWER is NOT a routing input: the deployable
    routing signal is lang_id_entropy. This rule is an oracle-style calibration
    criterion that bounds the achievable stability; labelled
    experimental/frontier.

    ``labels`` is accepted for signature uniformity and used only to report the
    confusion matrix at the chosen threshold (not in the cost objective)."""
    if grid is None:
        grid = THRESHOLD_GRID
    scores = np.asarray(scores, dtype=float)
    mixed = np.asarray(cpwer_mixed, dtype=float)
    sep = np.asarray(cpwer_separated, dtype=float)
    grid_arr = np.asarray(grid, dtype=float)
    # flagged (G, n): score >= t  -> route MIXED; else SEPARATED.
    flagged = scores[None, :] >= grid_arr[:, None] - EPS
    selected = np.where(flagged, mixed[None, :], sep[None, :])
    cost = selected.mean(axis=1)
    tp, fp, tn, fn, n_pos, n_neg = _confusion_arrays(scores, labels, grid)
    sens, spec = _sens_spec(tp, fp, tn, fn, n_pos, n_neg)
    return _select_threshold(
        grid_arr, cost, maximise=False, tp=tp, fp=fp, tn=tn, fn=fn,
        sens=sens, spec=spec, extra={"expected_cpwer": cost},
    )


# --------------------------------------------------------------- mode counting
def count_modes(
    thresholds: np.ndarray, min_fraction: float = MIN_MODE_FRACTION
) -> dict[str, Any]:
    """Count distinct threshold values whose bootstrap frequency is >=
    ``min_fraction`` (default 5%).

    Returns the mode count, the list of modes (threshold / count / fraction)
    sorted by descending count then ascending threshold for determinism, and the
    total number of distinct thresholds. This is the explicit kill-condition
    definition of "mode" for RQ48's hypotheses."""
    arr = np.asarray(thresholds, dtype=float)
    n = int(arr.size)
    if n == 0:
        return {"n_modes": 0, "modes": [], "n_unique": 0,
                "min_fraction": float(min_fraction)}
    uniq, counts = np.unique(arr, return_counts=True)
    fracs = counts / n
    mask = fracs >= min_fraction - EPS
    mode_idx = np.where(mask)[0]
    # Sort by descending count; stable sort keeps ascending-threshold order ties.
    order = mode_idx[np.argsort(-counts[mode_idx], kind="stable")]
    modes = [
        {"threshold": float(uniq[i]),
         "count": int(counts[i]),
         "fraction": float(fracs[i])}
        for i in order
    ]
    return {"n_modes": len(modes), "modes": modes,
            "n_unique": int(uniq.size), "min_fraction": float(min_fraction)}


# --------------------------------------------------------------- per-rule aggregation
def _summarise_rule(
    thresholds: np.ndarray, oob_cpwer: np.ndarray
) -> dict[str, Any]:
    """Aggregate the bootstrap threshold + OOB cpWER distributions for one rule."""
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


# --------------------------------------------------------------- rule registry
# Each rule's calibrator takes (scores, labels, mixed_cpwer, sep_cpwer) and
# returns RQ44-shaped dict; the non-cost rules ignore the cpWER arrays. The same
# bootstrap indices are reused for every rule so the comparison is paired.
def _cal_max(s, l, m, sp):
    return calibrate_max_sens_at_spec(s, l)


def _cal_j(s, l, m, sp):
    return calibrate_youdens_j(s, l)


def _cal_f1(s, l, m, sp):
    return calibrate_f1(s, l)


def _cal_cost(s, l, m, sp):
    return calibrate_cost_aware(s, l, m, sp)


RULES = [
    {"key": "max_sens_at_90_spec",
     "name": "Max sensitivity at >=90% specificity (RQ44 baseline)",
     "calibrate": _cal_max,
     "hypothesis": None},
    {"key": "youdens_j",
     "name": "Youden's J (maximise sensitivity + specificity - 1)",
     "calibrate": _cal_j,
     "hypothesis": "H48a"},
    {"key": "f1",
     "name": "F1 maximisation (2*prec*rec/(prec+rec))",
     "calibrate": _cal_f1,
     "hypothesis": "H48b"},
    {"key": "cost_aware",
     "name": "Cost-aware (minimise expected cpWER; flagged->mixed, unflagged->separated)",
     "calibrate": _cal_cost,
     "hypothesis": "H48c"},
]


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # Per-window signals (identical to RQ44).
    lang_ent = np.array([max_across_speakers(w) for w in windows], dtype=float)
    mixed_cpwer = np.array([float(w["always_mixed_cpwer"]) for w in windows], dtype=float)
    sep_cpwer = np.array([float(w["always_separated_cpwer"]) for w in windows], dtype=float)
    labels = (sep_cpwer > CATASTROPHIC_CPWER).astype(int)  # 1 = hallucinated
    n_hall = int(labels.sum())
    n_clean = int((labels == 0).sum())

    # ----------------------------------------------- in-sample calibration per rule
    in_sample: dict[str, Any] = {}
    for rule in RULES:
        cal = rule["calibrate"](lang_ent, labels, mixed_cpwer, sep_cpwer)
        flag = lang_ent >= cal["threshold"] - EPS
        selected = np.where(flag, mixed_cpwer, sep_cpwer)
        in_sample[rule["key"]] = {
            "name": rule["name"],
            "threshold": round(float(cal["threshold"]), 6),
            "sensitivity": round(float(cal["sensitivity"]), 6),
            "specificity": round(float(cal["specificity"]), 6),
            "tp": int(cal["tp"]), "fp": int(cal["fp"]),
            "tn": int(cal["tn"]), "fn": int(cal["fn"]),
            "expected_cpwer": round(float(selected.mean()), 6),
            "youdens_j": round(float(cal.get("youdens_j", float("nan"))), 6)
                         if "youdens_j" in cal else None,
            "f1": round(float(cal.get("f1", float("nan"))), 6)
                  if "f1" in cal else None,
            "calibration_cost": round(float(cal.get("expected_cpwer", float("nan"))), 6)
                                 if "expected_cpwer" in cal else None,
        }

    # ----------------------------------------------------------------- bootstrap
    # ONE index draw, reused for all 4 rules -> paired comparison.
    boot_idx = bootstrap_indices(n, N_BOOT, SEED)  # (N_BOOT, n)
    per_rule: dict[str, Any] = {}
    for rule in RULES:
        key = rule["key"]
        cal_fn = rule["calibrate"]
        boot_thr = np.empty(N_BOOT, dtype=float)
        boot_oob = np.empty(N_BOOT, dtype=float)
        boot_n_oob = np.empty(N_BOOT, dtype=int)
        for b in range(N_BOOT):
            idx = boot_idx[b]
            cal = cal_fn(lang_ent[idx], labels[idx], mixed_cpwer[idx], sep_cpwer[idx])
            thr = float(cal["threshold"])
            boot_thr[b] = thr
            oob = out_of_bag_cpwer(lang_ent, mixed_cpwer, sep_cpwer, thr, idx)
            boot_oob[b] = oob["cpwer"]
            boot_n_oob[b] = oob["n_oob"]
        per_rule[key] = {
            "name": rule["name"],
            "hypothesis": rule["hypothesis"],
            "in_sample": in_sample[key],
            "summary": _summarise_rule(boot_thr, boot_oob),
            "mean_oob_size": round(float(np.mean(boot_n_oob)), 4),
            "per_bootstrap": {
                "thresholds": [round(float(t), 6) for t in boot_thr],
                "oob_cpwer": [round(float(c), 6) if not math.isnan(float(c)) else None
                              for c in boot_oob],
                "n_oob": [int(x) for x in boot_n_oob],
            },
        }

    # ------------------------------------------------------------ hypotheses
    n_modes = {k: per_rule[k]["summary"]["threshold_distribution"]["n_modes_5pct"]
               for k in per_rule}
    oob_med = {k: per_rule[k]["summary"]["oob_cpwer_distribution"]["median"]
               for k in per_rule}

    h48a_supported = n_modes["youdens_j"] <= H48A_MAX_MODES
    h48b_supported = n_modes["f1"] <= H48B_MAX_MODES
    h48c_modes_ok = n_modes["cost_aware"] <= H48C_MAX_MODES
    h48c_cpwer_ok = oob_med["cost_aware"] < H48C_CPWER_KILL
    h48c_supported = h48c_modes_ok and h48c_cpwer_ok

    hypothesis_verdicts = {
        "H48a": {
            "statement": "Youden's J gives <= 3 modes (vs RQ44's 6)",
            "rule": "youdens_j",
            "n_modes_5pct": n_modes["youdens_j"],
            "max_modes": H48A_MAX_MODES,
            "kill": f"> {H48A_MAX_MODES} modes with >= 5% frequency",
            "supported": bool(h48a_supported),
        },
        "H48b": {
            "statement": "F1 maximisation gives <= 3 modes",
            "rule": "f1",
            "n_modes_5pct": n_modes["f1"],
            "max_modes": H48B_MAX_MODES,
            "kill": f"> {H48B_MAX_MODES} modes with >= 5% frequency",
            "supported": bool(h48b_supported),
        },
        "H48c": {
            "statement": ("Cost-aware rule gives <= 2 modes AND median OOB cpWER "
                          f"< RQ44's {RQ44_OOB_CPWER_MEDIAN}"),
            "rule": "cost_aware",
            "n_modes_5pct": n_modes["cost_aware"],
            "max_modes": H48C_MAX_MODES,
            "median_oob_cpwer": oob_med["cost_aware"],
            "rq44_median_oob_cpwer": RQ44_OOB_CPWER_MEDIAN,
            "kill": (f"> {H48C_MAX_MODES} modes OR median OOB cpWER "
                     f">= {H48C_CPWER_KILL}"),
            "modes_ok": bool(h48c_modes_ok),
            "cpwer_ok": bool(h48c_cpwer_ok),
            "supported": bool(h48c_supported),
        },
    }

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": ("RQ48: Calibration rule comparison for threshold stability "
               "(Youden's J / F1 / cost-aware vs RQ44's max-sens-at-90%-spec)"),
        "builds_on": {
            "RQ13": "results/frontier/diverse_hallucination_detector/ (PR #904)",
            "RQ16": "results/frontier/corrected_router_simulation/ (PR #912)",
            "RQ25": "results/frontier/out_of_sample_router/ (PR #929)",
            "RQ44": "results/frontier/bootstrap_threshold_stability/ (PR #963)",
        },
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR run); B=2000 bootstrap resamples "
            "(seed=42) of the 77 AISHELL-4 windows, drawn ONCE and reused for all "
            "4 calibration rules (paired comparison). On each resample: calibrate "
            "the threshold on in-bag windows, evaluate corrected-router cpWER on "
            "the out-of-bag windows (RQ44's out_of_bag_cpwer). Detector, bootstrap "
            "draw, OOB evaluator, and the baseline rule are imported verbatim from "
            "RQ44's module."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated": n_hall,
        "n_clean": n_clean,
        "hallucination_label_rule": "always_separated_cpwer > 1.0",
        "routing_rule": (
            "lang_id_entropy >= threshold -> route MIXED (always_mixed_cpwer); "
            "else route SEPARATED (always_separated_cpwer). HIGH lang-id entropy = "
            "diverse multilingual gibberish = hallucination (RQ13/RQ16/RQ25/RQ44 "
            "convention)."
        ),
        "calibration_rules": {
            "max_sens_at_90_spec": "RQ44 baseline: max sensitivity at >= 90% specificity.",
            "youdens_j": "Maximise J = sensitivity + specificity - 1 (smooth ROC criterion).",
            "f1": "Maximise F1 = 2*prec*rec/(prec+rec) (smooth precision/recall criterion).",
            "cost_aware": ("Minimise expected cpWER (flagged->mixed, unflagged->separated). "
                           "Oracle-style: uses reference cpWER as the calibration objective "
                           "on labelled data; cpWER is NOT a routing input."),
        },
        "mode_definition": (
            "mode = distinct threshold value with bootstrap frequency >= 5% "
            "(count_modes helper, min_fraction=0.05). This is the explicit "
            "kill-condition definition for H48a/b/c."
        ),
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "resample_size": n,
            "paired": True,
            "expected_oob_size": round(n * ((1 - 1 / n) ** n), 4),
        },
        "rq44_reference": {
            "median_oob_cpwer": RQ44_OOB_CPWER_MEDIAN,
            "n_distinct_thresholds": RQ44_N_DISTINCT_THRESHOLDS,
            "baseline_rule": "max sensitivity at >= 90% specificity",
            "note": ("RQ44 ran B=10000; RQ48 runs B=2000 with the same seed, so "
                     "RQ48's baseline is the first 2000 of RQ44's 10000 resamples."),
        },
        "in_sample_calibration": in_sample,
        "per_rule": {k: {kk: vv for kk, vv in v.items() if kk != "per_bootstrap"}
                     for k, v in per_rule.items()},
        "hypothesis_verdicts": hypothesis_verdicts,
    }

    # ----------------------------------------------------------- write JSON
    summary_with_arrays: dict[str, Any] = dict(summary)
    summary_with_arrays["per_bootstrap"] = {
        k: per_rule[k]["per_bootstrap"] for k in per_rule
    }
    OUT_JSON.write_text(
        json.dumps(summary_with_arrays, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- write CSV
    csv_fields = [
        "rule", "hypothesis", "in_sample_threshold", "in_sample_expected_cpwer",
        "thr_median", "thr_p2_5", "thr_p97_5", "thr_interval_width",
        "thr_n_unique", "thr_n_modes_5pct",
        "oob_cpwer_median", "oob_cpwer_mean", "oob_cpwer_p2_5", "oob_cpwer_p97_5",
        "oob_frac_below_1_10", "hypothesis_supported",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for rule in RULES:
            key = rule["key"]
            s = per_rule[key]["summary"]
            td = s["threshold_distribution"]
            od = s["oob_cpwer_distribution"]
            hyp = rule["hypothesis"]
            supported = ""
            if hyp is not None:
                supported = "yes" if hypothesis_verdicts[hyp]["supported"] else "no"
            wr.writerow({
                "rule": key,
                "hypothesis": hyp or "",
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
                "hypothesis_supported": supported,
            })

    # ----------------------------------------------------------- console
    print(f"=== RQ48: Calibration rule comparison (AISHELL-4, {n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucination label: always_separated_cpwer > 1.0 -> {n_hall} hall / {n_clean} clean")
    print(f"Bootstrap: B={N_BOOT}, seed={SEED}, resample_size={n}, paired across rules")
    print()
    print("In-sample calibration (full 77 windows, per rule):")
    for rule in RULES:
        key = rule["key"]
        isam = in_sample[key]
        extra = ""
        if isam.get("youdens_j") is not None:
            extra = f"  J={isam['youdens_j']}"
        elif isam.get("f1") is not None:
            extra = f"  F1={isam['f1']}"
        elif isam.get("calibration_cost") is not None:
            extra = f"  cost={isam['calibration_cost']}"
        print(f"  {key:22s} thr={isam['threshold']:.4f}  cpWER={isam['expected_cpwer']:.4f}"
              f"  sens={isam['sensitivity']:.4f} spec={isam['specificity']:.4f}{extra}")
    print()
    print("Bootstrap threshold + OOB cpWER distributions (B=2000, paired resamples):")
    for rule in RULES:
        key = rule["key"]
        td = per_rule[key]["summary"]["threshold_distribution"]
        od = per_rule[key]["summary"]["oob_cpwer_distribution"]
        print(f"  --- {key} ({rule['name']}) ---")
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
    print("Hypothesis verdicts:")
    for h, v in hypothesis_verdicts.items():
        print(f"  {h} ({v['statement']}): "
              f"{'SUPPORTED' if v['supported'] else 'KILLED'}")
        if h == "H48c":
            print(f"       n_modes={v['n_modes_5pct']} (<= {v['max_modes']} ? "
                  f"{v['modes_ok']})  median_oob_cpwer={v['median_oob_cpwer']:.4f} "
                  f"(< {v['rq44_median_oob_cpwer']} ? {v['cpwer_ok']})")
        else:
            print(f"       n_modes={v['n_modes_5pct']} (<= {v['max_modes']} ? "
                  f"{v['supported']})")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
