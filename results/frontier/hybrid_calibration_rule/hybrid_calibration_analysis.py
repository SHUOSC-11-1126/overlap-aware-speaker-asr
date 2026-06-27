"""RQ51: Hybrid calibration rule for the corrected router.

REANALYSIS ONLY -- no Whisper / no ASR model is run. This script reuses RQ44's
bootstrap framework (PR #963, ``results/frontier/bootstrap_threshold_stability/``),
RQ48's calibration-rule helpers (PR #965,
``results/frontier/calibration_rule_comparison/``), and the same AISHELL-4
external-validation windows (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890).

Motivation (RQ48)
-----------------
RQ48 compared 4 calibration rules for the lang-id entropy threshold on RQ44's
bootstrap framework (B=2000, paired resamples):

- Original ("max sensitivity at >=90% specificity"): 5 modes (>=5% freq),
  width 0.94, median OOB cpWER 1.0539.
- Youden's J: 3 modes, width 0.94, median OOB cpWER 1.0511.
- F1: 2 modes (0.38 62.1%, 0.01 27.6%), width 0.94, median OOB cpWER 1.0513.
- Cost-aware: 2 modes (0.33 51.1%, 0.01 48.7%), width 0.32, median OOB cpWER
  1.0632 (OVER-FITS -- the 0.01 mode swells to 48.7%, over-flagging clean
  windows OOB).

RQ48's decomposition: the high-threshold modes (0.87, 0.95) are rule artefacts
that smoother rules (J, F1) eliminate; the 0.01 "Mode S catch" mode is a
fundamental detector ambiguity that persists under every rule. F1 minimises the
mode count (2) but cannot shrink the interval (still 0.94). Cost-aware shrinks
the interval (0.32) but over-fits (median OOB cpWER 1.063 > 1.056).

RQ51 asks: can a HYBRID rule get the best of both -- F1's mode reduction AND
cost-aware's width reduction -- WITHOUT over-fitting?

The hybrid rule
---------------
Step 1: Calibrate the F1-optimal threshold on the resample (maximise F1). This
        inherits F1's mode-reduction property (eliminates the high-threshold
        artefact modes).

Step 2: Within the F1-optimal threshold's neighbourhood (threshold +/- 0.1),
        select the cost-aware-optimal threshold using an ASYMMETRIC cost that
        penalises routed cpWER > 1.10 (catastrophic outcomes). The asymmetric
        cost is the key innovation: RQ48's pure cost-aware rule minimises mean
        cpWER, which makes over-flagging clean windows "free" in-bag (because
        the over-flagged clean windows have tied mixed==separated cpWER) but
        costly OOB. The asymmetric cost penalises any window whose routed cpWER
        exceeds 1.10, so thresholds that route clean windows to a bad MIXED
        outcome are penalised even when the in-bag mean looks tied. This is
        designed to avoid the 0.01 mode's over-flagging pathology while still
        using cost information to tighten the interval within F1's neighbourhood.

The hybrid threshold for each resample is the Step-2 output. Because Step 2 is
constrained to F1's neighbourhood, the hybrid cannot jump to the high-threshold
artefact modes (0.87, 0.95) -- it inherits F1's mode-reduction. And because
Step 2 uses cost information, it can shift the high mode from 0.38 down toward
0.28-0.33 (within the neighbourhood), shrinking the interval width. The
asymmetric cost is the mechanism intended to keep OOB cpWER <= 1.056.

Method
------
Load the 77 AISHELL-4 windows (read-only). Compute the lang-id entropy detector
score per window (max across separated speaker tracks -- RQ13/RQ16/RQ25/RQ44
verbatim, imported from RQ44's module so thresholds are directly comparable).
Draw B=10000 bootstrap resamples (seed=42, n=77 with replacement). On each
resample: calibrate the hybrid threshold on the in-bag windows, evaluate the
corrected-router cpWER on the out-of-bag (OOB) windows (RQ44's
``out_of_bag_cpwer``).

Pre-registered hypotheses (issue for RQ51)
------------------------------------------
- H51a: The hybrid rule produces <= 2 threshold modes (matches F1's mode count).
        Kill: > 2 modes with >= 5% frequency.
- H51b: The hybrid rule's 2.5/97.5 percentile width < 0.32 (matches cost-aware's
        width). Kill: width >= 0.32.
- H51c: The hybrid rule's median OOB cpWER <= 1.056 (does NOT over-fit, matches
        original). Kill: median OOB cpWER > 1.056.

"Modes" = distinct threshold values whose bootstrap frequency is >= 5% (RQ48's
``count_modes`` helper, ``min_fraction=0.05``). This is the explicit
kill-condition definition.

This script is pure reanalysis (numpy + stdlib only; no scipy / sklearn /
Whisper / meeteval). Detector primitives, the bootstrap index draw, the OOB
cpWER evaluator, and the baseline calibration rule are imported verbatim from
RQ44's module; the F1 rule, confusion-array helpers, mode counter, and
per-rule aggregator are imported verbatim from RQ48's module to guarantee
direct comparability with RQ48's 4-rule comparison.

Label: experimental/frontier. Builds on RQ13 (PR #904), RQ16 (PR #912), RQ25
(PR #929), RQ44 (PR #963), and RQ48 (PR #965).
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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "hybrid_calibration_rule"
OUT_CSV = OUT_DIR / "hybrid_calibration_results.csv"
OUT_JSON = OUT_DIR / "hybrid_calibration_results.json"

# ------------------------------------------ import RQ44's framework (verbatim reuse)
# RQ44 provides: detector (max_across_speakers, language_id_entropy), the
# bootstrap index draw, the OOB cpWER evaluator, percentile_interval, and the
# baseline calibration rule. Reusing these guarantees the ONLY thing that varies
# vs RQ48 is the hybrid calibration criterion.
_RQ44_DIR = PROJECT_ROOT / "results" / "frontier" / "bootstrap_threshold_stability"
sys.path.insert(0, str(_RQ44_DIR))
import bootstrap_threshold_analysis as rq44  # noqa: E402  (path-injected import)

# ------------------------------------------ import RQ48's helpers (verbatim reuse)
# RQ48 provides: calibrate_f1, calibrate_cost_aware, _confusion_arrays,
# _sens_spec, _select_threshold, count_modes, _summarise_rule, RULES, and the
# RQ48 reference constants. Reusing these guarantees the hybrid rule's F1 step
# is byte-identical to RQ48's F1 rule, and the aggregation is directly
# comparable to RQ48's per-rule summaries.
_RQ48_DIR = PROJECT_ROOT / "results" / "frontier" / "calibration_rule_comparison"
sys.path.insert(0, str(_RQ48_DIR))
import calibration_rule_analysis as rq48  # noqa: E402  (path-injected import)

# ------------------------------------------------------------------ constants
# Re-export RQ44/RQ48 constants so thresholds are on the identical grid and the
# hallucination label matches RQ44/RQ48 exactly (37 hallucinated / 40 clean).
THRESHOLD_GRID = rq44.THRESHOLD_GRID            # 0.00, 0.01, ..., 2.00 (201 pts)
EPS = rq44.EPS                                  # 1e-9
CATASTROPHIC_CPWER = rq44.CATASTROPHIC_CPWER    # 1.0 (hallucination label threshold)
TARGET_SPECIFICITY = rq44.TARGET_SPECIFICITY    # 0.90

# RQ51 uses B=10000 (matching RQ44's bootstrap size, larger than RQ48's B=2000)
# for tighter percentile-interval estimates. The seed is the same (42) so the
# first 2000 resamples are identical to RQ48's, and the full 10000 are identical
# to RQ44's.
N_BOOT = 10000
SEED = 42
MIN_MODE_FRACTION = 0.05   # "mode" = distinct threshold with >= 5% frequency

# --- hybrid rule parameters ---------------------------------------------------
# Step 2 neighbourhood: cost-aware refinement is restricted to thresholds within
# +/- NEIGHBORHOOD of the F1-optimal threshold. 0.1 = +/- 0.1 bits (10 grid
# points on either side), wide enough to let cost-aware shift the high mode
# from 0.38 down toward 0.28-0.33, narrow enough to inherit F1's mode-reduction
# (cannot reach the 0.87/0.95 artefact modes).
NEIGHBORHOOD = 0.10
# Asymmetric cost: routed cpWER > CATASTROPHIC_OOB is weighted by PENALTY in the
# cost objective. CATASTROPHIC_OOB = 1.10 (RQ44's H44c kill line; "bad" OOB
# cpWER). PENALTY = 2.0 means a window routed to a cpWER > 1.10 outcome counts
# double in the cost -- this is the mechanism that penalises the 0.01 mode's
# over-flagging of clean windows (which produces cpWER > 1.10 OOB for some
# clean windows even though the in-bag mean looks tied).
CATASTROPHIC_OOB = 1.10
PENALTY = 2.0

# RQ48 reference values (from PR #965 calibration_rule_results.json) -- used by
# the hypothesis kill conditions and the comparison table.
RQ48_BASELINE_N_MODES = 5          # max_sens_at_90_spec: 5 modes (>=5% freq) at B=2000
RQ48_BASELINE_WIDTH = 0.94         # max_sens_at_90_spec: interval width
RQ48_BASELINE_OOB_MEDIAN = 1.0539  # max_sens_at_90_spec: median OOB cpWER
RQ48_F1_N_MODES = 2                # f1: 2 modes (0.38 62.1%, 0.01 27.6%)
RQ48_F1_WIDTH = 0.94               # f1: interval width (unchanged from baseline)
RQ48_F1_OOB_MEDIAN = 1.0513        # f1: median OOB cpWER
RQ48_COST_N_MODES = 2              # cost_aware: 2 modes (0.33 51.1%, 0.01 48.7%)
RQ48_COST_WIDTH = 0.32             # cost_aware: interval width
RQ48_COST_OOB_MEDIAN = 1.0632      # cost_aware: median OOB cpWER (OVER-FITS)
# RQ44's median OOB cpWER at B=10000 (the canonical reference for H51c).
RQ44_OOB_CPWER_MEDIAN = 1.056

# Hypothesis kill thresholds.
H51A_MAX_MODES = 2      # hybrid: kill if > 2 modes (>= 5% frequency)
H51B_MAX_WIDTH = 0.32   # hybrid: kill if width >= 0.32 (must BEAT cost-aware, not tie)
H51C_CPWER_KILL = RQ44_OOB_CPWER_MEDIAN   # hybrid: kill if median OOB cpWER > 1.056

# Detector + bootstrap framework reused verbatim from RQ44.
max_across_speakers = rq44.max_across_speakers
bootstrap_indices = rq44.bootstrap_indices
out_of_bag_cpwer = rq44.out_of_bag_cpwer
percentile_interval = rq44.percentile_interval

# RQ48 helpers reused verbatim.
calibrate_f1 = rq48.calibrate_f1
calibrate_cost_aware = rq48.calibrate_cost_aware
_confusion_arrays = rq48._confusion_arrays
_sens_spec = rq48._sens_spec
_select_threshold = rq48._select_threshold
count_modes = rq48.count_modes


# --------------------------------------------------------------- hybrid rule
def _asymmetric_cost(
    selected_cpwer: np.ndarray,
    catastrophic: float = CATASTROPHIC_OOB,
    penalty: float = PENALTY,
) -> float:
    """Asymmetric expected-cpWER cost over a set of routed windows.

    Each window's routed cpWER is weighted by ``penalty`` if it exceeds
    ``catastrophic`` (default 1.10), else weight 1. The cost is the weighted
    mean. This penalises thresholds that route any window to a catastrophic
    (cpWER > 1.10) outcome -- the mechanism intended to avoid the 0.01 mode's
    over-flagging pathology (RQ48's cost-aware rule made over-flagging "free"
    in-bag because the over-flagged clean windows had tied mixed==separated
    cpWER, but those ties do not hold OOB and some clean windows get cpWER >
    1.10 when routed MIXED)."""
    arr = np.asarray(selected_cpwer, dtype=float)
    weights = np.where(arr > catastrophic, penalty, 1.0)
    if arr.size == 0:
        return float("nan")
    return float(np.average(arr, weights=weights))


def calibrate_hybrid(
    scores: np.ndarray,
    labels: np.ndarray,
    cpwer_mixed: np.ndarray,
    cpwer_separated: np.ndarray,
    grid: list[float] | None = None,
    neighborhood: float = NEIGHBORHOOD,
    catastrophic: float = CATASTROPHIC_OOB,
    penalty: float = PENALTY,
) -> dict[str, Any]:
    """Hybrid calibration rule: F1 for mode reduction + cost-aware for width.

    Step 1: Calibrate the F1-optimal threshold on the resample (maximise F1).
            Inherits F1's mode-reduction (eliminates the 0.87/0.95 artefact
            modes that RQ48 showed are specificity-boundary artefacts).

    Step 2: Within the F1-optimal threshold's neighbourhood
            ``[f1_thr - neighborhood, f1_thr + neighborhood]``, select the
            cost-aware-optimal threshold using the ASYMMETRIC cost
            (``_asymmetric_cost``): minimise the penalty-weighted expected
            cpWER, where windows routed to cpWER > ``catastrophic`` are weighted
            by ``penalty``. This is designed to:
              (a) shift the high mode from 0.38 toward 0.28-0.33 (within the
                  neighbourhood), shrinking the interval width below 0.32; and
              (b) avoid the 0.01 mode's over-flagging pathology by penalising
                  thresholds that route clean windows to cpWER > 1.10.

    The neighbourhood constraint guarantees the hybrid cannot reach the
    high-threshold artefact modes (0.87, 0.95) -- it inherits F1's
    mode-reduction. The asymmetric cost is the mechanism intended to keep OOB
    cpWER <= 1.056 (unlike RQ48's pure cost-aware rule, which over-fit to
    1.063).

    Returns a dict shaped like RQ44/RQ48's calibration output (``threshold,
    sensitivity, specificity, tp, fp, tn, fn``) plus the F1-step threshold
    (``f1_threshold``), the F1 metric, the asymmetric cost at the chosen
    threshold, the neighbourhood bounds, and the number of grid points
    evaluated in Step 2."""
    if grid is None:
        grid = THRESHOLD_GRID
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    mixed = np.asarray(cpwer_mixed, dtype=float)
    sep = np.asarray(cpwer_separated, dtype=float)
    grid_arr = np.asarray(grid, dtype=float)

    # --- Step 1: F1-optimal threshold (verbatim RQ48 calibrate_f1) -------------
    f1_result = calibrate_f1(scores, labels, grid)
    f1_thr = float(f1_result["threshold"])

    # --- Step 2: cost-aware within the F1 neighbourhood (asymmetric cost) ------
    lo = f1_thr - neighborhood
    hi = f1_thr + neighborhood
    # Neighbourhood mask: grid points within [lo, hi] (inclusive, with EPS).
    nb_mask = (grid_arr >= lo - EPS) & (grid_arr <= hi + EPS)
    nb_grid = grid_arr[nb_mask]
    if nb_grid.size == 0:
        # Degenerate: neighbourhood contains no grid points (should not happen
        # with the default grid/neighborhood, but guard anyway). Fall back to
        # the F1 threshold itself.
        nb_grid = np.array([f1_thr], dtype=float)

    # Compute the asymmetric cost at each neighbourhood grid point.
    # flagged (G, n): score >= t  -> route MIXED; else SEPARATED.
    flagged = scores[None, :] >= nb_grid[:, None] - EPS
    selected = np.where(flagged, mixed[None, :], sep[None, :])
    # cost[g] = asymmetric cost over the n calibration windows at threshold g.
    cost = np.array(
        [_asymmetric_cost(selected[g], catastrophic, penalty)
         for g in range(nb_grid.size)],
        dtype=float,
    )

    # Confusion arrays over the FULL grid (for reporting sens/spec/counts at the
    # chosen threshold). We then index by the chosen neighbourhood index.
    tp, fp, tn, fn, n_pos, n_neg = _confusion_arrays(scores, labels, grid)
    sens, spec = _sens_spec(tp, fp, tn, fn, n_pos, n_neg)

    # Select the neighbourhood threshold minimising the asymmetric cost.
    # Tie-breaker: lowest threshold among ties (RQ44/RQ48 convention). Because
    # nb_grid is ascending, np.argmax on the boolean mask gives the first
    # (lowest-threshold) index achieving the minimum.
    best_val = float(np.min(cost))
    best_nb_idx = int(np.argmax(cost <= best_val + EPS))
    chosen_thr = float(nb_grid[best_nb_idx])
    # Map back to the full-grid index for sens/spec/counts.
    full_idx = int(np.argmax(grid_arr >= chosen_thr - EPS))

    out: dict[str, Any] = {
        "threshold": chosen_thr,
        "f1_threshold": f1_thr,
        "neighborhood": [round(float(lo), 6), round(float(hi), 6)],
        "n_neighborhood_grid": int(nb_grid.size),
        "sensitivity": float(sens[full_idx]),
        "specificity": float(spec[full_idx]),
        "tp": int(tp[full_idx]),
        "fp": int(fp[full_idx]),
        "tn": int(tn[full_idx]),
        "fn": int(fn[full_idx]),
        "f1": float(f1_result.get("f1", float("nan"))),
        "asymmetric_cost": float(cost[best_nb_idx]),
        "catastrophic_oob": float(catastrophic),
        "penalty": float(penalty),
    }
    return out


# --------------------------------------------------------------- per-rule aggregation
def _summarise_hybrid(
    thresholds: np.ndarray, oob_cpwer: np.ndarray
) -> dict[str, Any]:
    """Aggregate the bootstrap threshold + OOB cpWER distributions for the
    hybrid rule. Mirrors RQ48's ``_summarise_rule`` so the summary shape is
    directly comparable to RQ48's per-rule summaries."""
    return rq48._summarise_rule(thresholds, oob_cpwer)


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

    # ----------------------------------------------- in-sample hybrid calibration
    in_sample_cal = calibrate_hybrid(
        lang_ent, labels, mixed_cpwer, sep_cpwer
    )
    in_flag = lang_ent >= in_sample_cal["threshold"] - EPS
    in_selected = np.where(in_flag, mixed_cpwer, sep_cpwer)
    in_sample: dict[str, Any] = {
        "threshold": round(float(in_sample_cal["threshold"]), 6),
        "f1_threshold": round(float(in_sample_cal["f1_threshold"]), 6),
        "neighborhood": in_sample_cal["neighborhood"],
        "n_neighborhood_grid": in_sample_cal["n_neighborhood_grid"],
        "sensitivity": round(float(in_sample_cal["sensitivity"]), 6),
        "specificity": round(float(in_sample_cal["specificity"]), 6),
        "tp": int(in_sample_cal["tp"]), "fp": int(in_sample_cal["fp"]),
        "tn": int(in_sample_cal["tn"]), "fn": int(in_sample_cal["fn"]),
        "f1": round(float(in_sample_cal["f1"]), 6),
        "asymmetric_cost": round(float(in_sample_cal["asymmetric_cost"]), 6),
        "expected_cpwer": round(float(in_selected.mean()), 6),
        "catastrophic_oob": float(in_sample_cal["catastrophic_oob"]),
        "penalty": float(in_sample_cal["penalty"]),
    }

    # ----------------------------------------------------------------- bootstrap
    boot_idx = bootstrap_indices(n, N_BOOT, SEED)  # (N_BOOT, n)
    boot_thr = np.empty(N_BOOT, dtype=float)
    boot_f1_thr = np.empty(N_BOOT, dtype=float)
    boot_oob = np.empty(N_BOOT, dtype=float)
    boot_n_oob = np.empty(N_BOOT, dtype=int)
    for b in range(N_BOOT):
        idx = boot_idx[b]
        cal = calibrate_hybrid(
            lang_ent[idx], labels[idx], mixed_cpwer[idx], sep_cpwer[idx]
        )
        thr = float(cal["threshold"])
        boot_thr[b] = thr
        boot_f1_thr[b] = float(cal["f1_threshold"])
        oob = out_of_bag_cpwer(lang_ent, mixed_cpwer, sep_cpwer, thr, idx)
        boot_oob[b] = oob["cpwer"]
        boot_n_oob[b] = oob["n_oob"]

    summary = _summarise_hybrid(boot_thr, boot_oob)

    # ------------------------------------------------------------ hypotheses
    n_modes = summary["threshold_distribution"]["n_modes_5pct"]
    width = summary["threshold_distribution"]["interval_width"]
    oob_med = summary["oob_cpwer_distribution"]["median"]

    h51a_supported = n_modes <= H51A_MAX_MODES
    h51b_supported = width < H51B_MAX_WIDTH
    h51c_supported = oob_med <= H51C_CPWER_KILL

    hypothesis_verdicts = {
        "H51a": {
            "statement": (
                f"Hybrid rule produces <= {H51A_MAX_MODES} threshold modes "
                f"(matches F1's mode count)"
            ),
            "n_modes_5pct": n_modes,
            "max_modes": H51A_MAX_MODES,
            "rq48_f1_n_modes": RQ48_F1_N_MODES,
            "kill": f"> {H51A_MAX_MODES} modes with >= 5% frequency",
            "supported": bool(h51a_supported),
        },
        "H51b": {
            "statement": (
                f"Hybrid rule's 2.5/97.5 percentile width < {H51B_MAX_WIDTH} "
                f"(matches cost-aware's width)"
            ),
            "interval_width": width,
            "max_width": H51B_MAX_WIDTH,
            "rq48_cost_aware_width": RQ48_COST_WIDTH,
            "kill": f"width >= {H51B_MAX_WIDTH}",
            "supported": bool(h51b_supported),
        },
        "H51c": {
            "statement": (
                f"Hybrid rule's median OOB cpWER <= {H51C_CPWER_KILL} "
                f"(does NOT over-fit, matches original)"
            ),
            "median_oob_cpwer": oob_med,
            "max_oob_cpwer": H51C_CPWER_KILL,
            "rq48_cost_aware_oob_median": RQ48_COST_OOB_MEDIAN,
            "rq48_f1_oob_median": RQ48_F1_OOB_MEDIAN,
            "kill": f"median OOB cpWER > {H51C_CPWER_KILL}",
            "supported": bool(h51c_supported),
        },
    }

    # Comparison table vs RQ48's 4 rules (RQ48 values are at B=2000; the hybrid
    # is at B=10000. The qualitative comparison holds because RQ48's eliminated
    # modes were at 13.5%/9.3% -- far above any small-B noise floor).
    rq48_comparison = [
        {"rule": "max_sens_at_90_spec (RQ48 baseline)",
         "n_modes_5pct": RQ48_BASELINE_N_MODES,
         "interval_width": RQ48_BASELINE_WIDTH,
         "median_oob_cpwer": RQ48_BASELINE_OOB_MEDIAN,
         "over_fits": False},
        {"rule": "youdens_j (RQ48)",
         "n_modes_5pct": 3,
         "interval_width": 0.94,
         "median_oob_cpwer": 1.0511,
         "over_fits": False},
        {"rule": "f1 (RQ48)",
         "n_modes_5pct": RQ48_F1_N_MODES,
         "interval_width": RQ48_F1_WIDTH,
         "median_oob_cpwer": RQ48_F1_OOB_MEDIAN,
         "over_fits": False},
        {"rule": "cost_aware (RQ48)",
         "n_modes_5pct": RQ48_COST_N_MODES,
         "interval_width": RQ48_COST_WIDTH,
         "median_oob_cpwer": RQ48_COST_OOB_MEDIAN,
         "over_fits": True},
        {"rule": "hybrid (RQ51, this work)",
         "n_modes_5pct": n_modes,
         "interval_width": width,
         "median_oob_cpwer": oob_med,
         "over_fits": not h51c_supported},
    ]

    out_summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": ("RQ51: Hybrid calibration rule for the corrected router "
               "(F1 for mode reduction + cost-aware-with-asymmetric-cost for "
               "width reduction within F1's neighbourhood)"),
        "builds_on": {
            "RQ13": "results/frontier/diverse_hallucination_detector/ (PR #904)",
            "RQ16": "results/frontier/corrected_router_simulation/ (PR #912)",
            "RQ25": "results/frontier/out_of_sample_router/ (PR #929)",
            "RQ44": "results/frontier/bootstrap_threshold_stability/ (PR #963)",
            "RQ48": "results/frontier/calibration_rule_comparison/ (PR #965)",
        },
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "method": (
            "reanalysis only (no Whisper / no ASR run); B=10000 bootstrap "
            "resamples (seed=42) of the 77 AISHELL-4 windows. On each resample: "
            "(Step 1) calibrate the F1-optimal threshold on in-bag windows; "
            "(Step 2) within the F1 threshold's neighbourhood (+/- 0.1 bits), "
            "select the cost-aware-optimal threshold minimising an asymmetric "
            "expected cpWER (windows routed to cpWER > 1.10 are weighted by "
            "penalty=2.0). Evaluate corrected-router cpWER on the out-of-bag "
            "windows (RQ44's out_of_bag_cpwer). Detector, bootstrap draw, OOB "
            "evaluator, baseline rule, F1 rule, confusion helpers, mode counter, "
            "and per-rule aggregator are imported verbatim from RQ44/RQ48."
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
            "RQ44/RQ48 convention)."
        ),
        "hybrid_rule": {
            "step1": "Calibrate the F1-optimal threshold (maximise F1 = 2*prec*rec/(prec+rec)).",
            "step2": (
                "Within [f1_thr - neighborhood, f1_thr + neighborhood], select the "
                "threshold minimising the asymmetric expected cpWER: each window's "
                "routed cpWER is weighted by `penalty` if it exceeds "
                "`catastrophic_oob`, else weight 1. Tie-break: lowest threshold."
            ),
            "neighborhood": NEIGHBORHOOD,
            "catastrophic_oob": CATASTROPHIC_OOB,
            "penalty": PENALTY,
            "rationale": (
                "F1 eliminates the high-threshold (0.87/0.95) specificity-boundary "
                "artefact modes (RQ48 H48b). Cost-aware-within-neighbourhood shifts "
                "the high mode from 0.38 toward 0.28-0.33, shrinking the interval "
                "width. The asymmetric cost penalises routing any window to cpWER > "
                "1.10, intended to avoid the 0.01 mode's over-flagging pathology "
                "that killed RQ48's H48c (pure cost-aware over-fit to OOB cpWER "
                "1.063)."
            ),
        },
        "mode_definition": (
            "mode = distinct threshold value with bootstrap frequency >= 5% "
            "(count_modes helper, min_fraction=0.05). This is the explicit "
            "kill-condition definition for H51a/b/c, identical to RQ48."
        ),
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "resample_size": n,
            "expected_oob_size": round(n * ((1 - 1 / n) ** n), 4),
        },
        "rq48_reference": {
            "baseline_n_modes": RQ48_BASELINE_N_MODES,
            "baseline_width": RQ48_BASELINE_WIDTH,
            "baseline_oob_median": RQ48_BASELINE_OOB_MEDIAN,
            "f1_n_modes": RQ48_F1_N_MODES,
            "f1_width": RQ48_F1_WIDTH,
            "f1_oob_median": RQ48_F1_OOB_MEDIAN,
            "cost_aware_n_modes": RQ48_COST_N_MODES,
            "cost_aware_width": RQ48_COST_WIDTH,
            "cost_aware_oob_median": RQ48_COST_OOB_MEDIAN,
            "rq44_oob_cpwer_median": RQ44_OOB_CPWER_MEDIAN,
            "note": (
                "RQ48 ran B=2000; RQ51 runs B=10000 (matching RQ44's bootstrap "
                "size) with the same seed. The first 2000 resamples are identical "
                "to RQ48's; the full 10000 are identical to RQ44's."
            ),
        },
        "in_sample_calibration": in_sample,
        "hybrid_summary": summary,
        "rq48_comparison": rq48_comparison,
        "hypothesis_verdicts": hypothesis_verdicts,
    }

    # ----------------------------------------------------------- write JSON
    out_with_arrays: dict[str, Any] = dict(out_summary)
    out_with_arrays["per_bootstrap"] = {
        "thresholds": [round(float(t), 6) for t in boot_thr],
        "f1_thresholds": [round(float(t), 6) for t in boot_f1_thr],
        "oob_cpwer": [round(float(c), 6) if not math.isnan(float(c)) else None
                      for c in boot_oob],
        "n_oob": [int(x) for x in boot_n_oob],
    }
    OUT_JSON.write_text(
        json.dumps(out_with_arrays, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- write CSV
    csv_fields = [
        "rule", "n_modes_5pct", "interval_width", "median_oob_cpwer",
        "over_fits", "hypothesis_supported",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for row in rq48_comparison:
            row = dict(row)
            rule = row["rule"]
            if "hybrid" in rule:
                row["hypothesis_supported"] = (
                    "yes" if (h51a_supported and h51b_supported and h51c_supported)
                    else "partial"
                )
            else:
                row["hypothesis_supported"] = ""
            wr.writerow(row)

    # ----------------------------------------------------------- console
    print(f"=== RQ51: Hybrid calibration rule (AISHELL-4, {n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucination label: always_separated_cpwer > 1.0 -> {n_hall} hall / {n_clean} clean")
    print(f"Bootstrap: B={N_BOOT}, seed={SEED}, resample_size={n}")
    print(f"Hybrid: neighborhood=+/-{NEIGHBORHOOD}, catastrophic_oob={CATASTROPHIC_OOB}, penalty={PENALTY}")
    print()
    print("In-sample hybrid calibration (full 77 windows):")
    print(f"  F1 threshold      : {in_sample['f1_threshold']:.4f}")
    print(f"  neighbourhood     : {in_sample['neighborhood']}  "
          f"({in_sample['n_neighborhood_grid']} grid pts)")
    print(f"  hybrid threshold  : {in_sample['threshold']:.4f}")
    print(f"  sensitivity/spec  : {in_sample['sensitivity']:.4f} / {in_sample['specificity']:.4f}")
    print(f"  F1 / asym cost    : {in_sample['f1']:.4f} / {in_sample['asymmetric_cost']:.4f}")
    print(f"  expected cpWER    : {in_sample['expected_cpwer']:.4f}")
    print()
    print("Bootstrap threshold + OOB cpWER distributions (hybrid, B=10000):")
    td = summary["threshold_distribution"]
    od = summary["oob_cpwer_distribution"]
    print(f"  threshold: median={td['median']:.4f}  "
          f"pct[{td['percentile_2_5']:.4f}, {td['percentile_97_5']:.4f}]  "
          f"width={td['interval_width']:.4f}  "
          f"n_unique={td['n_unique']}  n_modes>=5%={td['n_modes_5pct']}")
    for m in td["modes_5pct"]:
        print(f"    mode thr={m['threshold']:.4f}  count={m['count']}  "
              f"frac={m['fraction']:.3f}")
    print(f"  oob cpWER: median={od['median']:.4f}  mean={od['mean']:.4f}  "
          f"pct[{od['percentile_2_5']:.4f}, {od['percentile_97_5']:.4f}]  "
          f"frac<1.10={od['frac_below_1_10']:.3f}")
    print()
    print("Comparison vs RQ48's 4 rules:")
    print(f"  {'rule':42s} {'modes':>6s} {'width':>7s} {'oob_med':>9s} {'overfits':>9s}")
    for row in rq48_comparison:
        print(f"  {row['rule']:42s} {row['n_modes_5pct']:>6d} "
              f"{row['interval_width']:>7.4f} {row['median_oob_cpwer']:>9.4f} "
              f"{'YES' if row['over_fits'] else 'no':>9s}")
    print()
    print("Hypothesis verdicts:")
    for h, v in hypothesis_verdicts.items():
        print(f"  {h} ({v['statement']}): "
              f"{'SUPPORTED' if v['supported'] else 'KILLED'}")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
