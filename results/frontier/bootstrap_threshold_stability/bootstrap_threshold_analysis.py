"""RQ44: Bootstrap-aggregated threshold for out-of-sample router stability.

REANALYSIS ONLY -- no Whisper / no ASR model is run. This script reads the
existing AISHELL-4 external-validation results (``results/external_sanity_check/
aishell4/rq1_aishell4_validation_results.json``, label ``external/sanity-check``,
PR #890) and uses bootstrap aggregation (bagging) to produce a stable lang-id
entropy threshold for the corrected router.

Motivation (RQ25, PR #929)
--------------------------
RQ25 showed that the corrected router's lang-id entropy threshold is bimodal and
unstable on small train splits. The 50/50 held-out train split calibrated a
threshold of 0.010 -- two orders of magnitude below RQ16's in-sample 0.409 and
far outside the in-sample range [0.327, 0.491]. The mechanism: the "max
sensitivity at >= 90% specificity" calibration rule is sensitive to whether a
Mode S (low-entropy hallucinated) window lands in the train split. With n=39
train windows, ONE Mode S window forces the threshold from 0.38 to 0.01. This is
a deployability blocker: a single train/test split cannot identify a stable
operating point.

Method (RQ44)
-------------
Instead of one train/test split, draw B=10000 bootstrap resamples (seed=42) of
the n=77 windows (with replacement). On each resample, calibrate the lang-id
entropy threshold that maximises sensitivity at >= 90% specificity (same rule as
RQ13/RQ16/RQ25). Aggregate the B thresholds:

  - median threshold (the bagged operating point)
  - 2.5 / 97.5 percentile interval (threshold uncertainty)
  - mode(s) of the threshold distribution (exposes bimodality)

Out-of-sample validation: for each bootstrap resample, the windows NOT drawn
(the out-of-bag, OOB, set) are held out. The corrected router's cpWER is
computed on the OOB windows at the resample's calibrated threshold. This gives a
distribution of 10000 held-out cpWER values -- the bagged out-of-sample cpWER.

Routing rule (RQ13/RQ16/RQ25 convention)
----------------------------------------
HIGH lang-id entropy = diverse multilingual gibberish = hallucination. The
detector flags the separated track when ``lang_id_entropy >= threshold``:

    if lang_id_entropy >= threshold -> route MIXED  (cpWER = always_mixed_cpwer)
    else                            -> route SEPARATED (cpWER = always_separated_cpwer)

The corrected router's per-window cpWER is the chosen route's stored cpWER.

Pre-registered hypotheses (issue #958)
--------------------------------------
- H44a: median bootstrap threshold in [0.30, 0.50] (covers RQ25's 0.38 in-sample
        and RQ16's 0.409). Kill: outside [0.30, 0.50].
- H44b: 2.5/97.5 percentile interval width < 0.20 (bagging stabilises the
        threshold). Kill: width >= 0.20.
- H44c: median held-out (OOB) cpWER < 1.10. Kill: >= 1.10.

This script is pure reanalysis (numpy + stdlib only; scipy / sklearn / Whisper
are NOT required). The detector primitives (``script_category``,
``language_id_entropy``) are lifted verbatim from RQ13/RQ16/RQ25 so thresholds
are directly comparable.

Label: experimental/frontier. Closes #958. Builds on RQ13 (PR #904), RQ16
(PR #912), and RQ25 (PR #929).
"""
from __future__ import annotations

import csv
import json
import math
import unicodedata
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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "bootstrap_threshold_stability"
OUT_CSV = OUT_DIR / "bootstrap_threshold_results.csv"
OUT_JSON = OUT_DIR / "bootstrap_threshold_results.json"

# ------------------------------------------------------------------ constants
CATASTROPHIC_CPWER = 1.0    # cpWER > 1.0 => insertions dominate (hallucination label)
TARGET_SPECIFICITY = 0.90   # calibrate the threshold to >= 90% specificity
THRESHOLD_GRID = [round(0.01 * i, 2) for i in range(0, 201)]  # 0.00, 0.01, ..., 2.00
N_BOOT = 10000
SEED = 42
EPS = 1e-9

# RQ25's in-sample threshold on the 77 windows (0.01 grid) = 0.38; RQ16 reported
# 0.409 (RQ13's exact operating point). H44a tests whether the bootstrap MEDIAN
# lands in [0.30, 0.50] -- a band that covers both.
RQ25_IN_SAMPLE_THRESHOLD = 0.38
RQ16_IN_SAMPLE_THRESHOLD = 0.409
RQ25_IN_SAMPLE_CPWER = 1.043
H44A_LO, H44A_HI = 0.30, 0.50
# H44b: 2.5/97.5 percentile interval width must be < 0.20 for the threshold to
# be considered stable under bagging.
H44B_MAX_WIDTH = 0.20
# H44c: median held-out (OOB) cpWER must be < 1.10 (same kill threshold as RQ25's H25a).
H44C_MAX_CPWER = 1.10


# ------------------------------------------------------------- script detection
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13/RQ16/RQ25 verbatim).

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


# --------------------------------------------------------------- the detector
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


def max_across_speakers(window: dict[str, Any]) -> float:
    """Max of ``language_id_entropy`` over the per-speaker separated transcripts
    (worst-case speaker track; RQ12/RQ13 convention). Empty/whitespace speaker
    texts are effectively skipped."""
    vals = [
        language_id_entropy(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


# --------------------------------------------------------------- pure helpers
def bootstrap_indices(n: int, n_boot: int, seed: int) -> np.ndarray:
    """Return an ``(n_boot, n)`` int array of bootstrap resample indices.

    Each row is an independent bootstrap resample: ``n`` indices drawn with
    replacement from ``{0, ..., n-1}``. Deterministic for a given seed."""
    rng = np.random.default_rng(seed)
    return rng.integers(0, n, size=(n_boot, n))


def calibrate_threshold_at_spec(
    scores: np.ndarray,
    labels: np.ndarray,
    grid: list[float] | None = None,
    target_spec: float = TARGET_SPECIFICITY,
) -> dict[str, Any]:
    """Sweep threshold over ``grid`` (default THRESHOLD_GRID); select the threshold
    with specificity >= ``target_spec`` and maximal sensitivity. Tie-breaker:
    higher specificity, then lower threshold (more sensitive).

    Convention (RQ13/RQ16/RQ25): ``score >= threshold`` flags the window as
    hallucinated. Sensitivity = TP / (TP + FN); specificity = TN / (TN + FP).

    Returns the chosen threshold plus its sensitivity, specificity, and
    confusion counts. Faithful copy of RQ25's ``calibrate_threshold`` with the
    target specificity parameterised, so thresholds are directly comparable.
    """
    if grid is None:
        grid = THRESHOLD_GRID
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=int)
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    n_pos = int(len(pos))
    n_neg = int(len(neg))
    best: dict[str, Any] | None = None
    for t in grid:
        fp = int(np.sum(neg >= t - EPS))
        tp = int(np.sum(pos >= t - EPS))
        tn = n_neg - fp
        fn = n_pos - tp
        spec = (tn / n_neg) if n_neg > 0 else 1.0
        sens = (tp / n_pos) if n_pos > 0 else 0.0
        if spec >= target_spec - EPS:
            cand = {
                "threshold": float(t),
                "sensitivity": float(sens),
                "specificity": float(spec),
                "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            }
            if best is None:
                best = cand
            else:
                # Maximise sensitivity; tie-break by higher specificity, then
                # lower threshold (more sensitive, fewer false negatives).
                if sens > best["sensitivity"] + EPS:
                    best = cand
                elif abs(sens - best["sensitivity"]) <= EPS:
                    if spec > best["specificity"] + EPS:
                        best = cand
                    elif abs(spec - best["specificity"]) <= EPS and t < best["threshold"]:
                        best = cand
    if best is None:
        # No threshold satisfies the specificity target -> fall back to the
        # highest threshold (most conservative: flag nothing).
        t_max = float(grid[-1]) if grid else 1.0
        best = {
            "threshold": t_max, "sensitivity": 0.0, "specificity": 1.0,
            "tp": 0, "fp": 0, "tn": n_neg, "fn": n_pos,
        }
    return best


def percentile_interval(
    values: np.ndarray, lo: float = 2.5, hi: float = 97.5
) -> tuple[float, float]:
    """Return the ``(lo, hi)`` percentile interval of ``values`` using numpy's
    default linear interpolation. Returns ``(nan, nan)`` for empty input."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return (float("nan"), float("nan"))
    return (float(np.percentile(arr, lo)), float(np.percentile(arr, hi)))


def out_of_bag_cpwer(
    scores: np.ndarray,
    mixed_cpwer: np.ndarray,
    sep_cpwer: np.ndarray,
    threshold: float,
    in_bag_idx: np.ndarray,
) -> dict[str, Any]:
    """Compute the corrected-router cpWER on the out-of-bag (OOB) windows --
    those NOT present in the bootstrap resample ``in_bag_idx`` -- at the given
    ``threshold``.

    Routing: ``score >= threshold`` => route MIXED (``mixed_cpwer``); else
    SEPARATED (``sep_cpwer``). Returns a dict with the mean selected cpWER over
    the OOB windows (``nan`` if there are none), the OOB size, and the
    mixed/separated decision counts."""
    n = len(scores)
    all_idx = np.arange(n)
    in_bag_set = np.unique(np.asarray(in_bag_idx, dtype=int))
    oob_mask = ~np.isin(all_idx, in_bag_set)
    oob_scores = scores[oob_mask]
    oob_mixed = mixed_cpwer[oob_mask]
    oob_sep = sep_cpwer[oob_mask]
    n_oob = int(oob_mask.sum())
    if n_oob == 0:
        return {"cpwer": float("nan"), "n_oob": 0,
                "n_flagged_mixed": 0, "n_separated": 0}
    flagged = oob_scores >= threshold - EPS
    selected = np.where(flagged, oob_mixed, oob_sep)
    return {
        "cpwer": float(selected.mean()),
        "n_oob": n_oob,
        "n_flagged_mixed": int(flagged.sum()),
        "n_separated": int((~flagged).sum()),
    }


def threshold_distribution(thresholds: np.ndarray, top_k: int = 5) -> dict[str, Any]:
    """Summarise the bootstrap threshold distribution: the modal value, its
    count and fraction, the number of distinct thresholds, the top-``top_k``
    most frequent values, and the "modes" -- values whose count is within 10%
    of the maximum count (to expose bimodality)."""
    arr = np.asarray(thresholds, dtype=float)
    n = int(arr.size)
    if n == 0:
        return {"mode": float("nan"), "mode_count": 0, "mode_fraction": 0.0,
                "n_unique": 0, "modes_within_10pct": [], "top_values": []}
    uniq, counts = np.unique(arr, return_counts=True)
    order = np.argsort(-counts)  # descending by count
    uniq = uniq[order]
    counts = counts[order]
    max_count = int(counts[0])
    modes = [
        (float(u), int(c), float(c / n))
        for u, c in zip(uniq, counts)
        if c >= max_count * 0.90
    ]
    top = [
        (float(u), int(c), float(c / n))
        for u, c in zip(uniq[:top_k], counts[:top_k])
    ]
    return {
        "mode": float(uniq[0]),
        "mode_count": max_count,
        "mode_fraction": float(max_count / n),
        "n_unique": int(uniq.size),
        "modes_within_10pct": modes,
        "top_values": top,
    }


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    windows = data["windows"]
    n = len(windows)

    # Per-window signals.
    lang_ent = np.array([max_across_speakers(w) for w in windows], dtype=float)
    mixed_cpwer = np.array([float(w["always_mixed_cpwer"]) for w in windows], dtype=float)
    sep_cpwer = np.array([float(w["always_separated_cpwer"]) for w in windows], dtype=float)
    rv2_cpwer = np.array([float(w["router_v2_cpwer"]) for w in windows], dtype=float)
    oracle_cpwer = np.array([float(w["oracle_best_cpwer"]) for w in windows], dtype=float)
    labels = (sep_cpwer > CATASTROPHIC_CPWER).astype(int)  # 1 = hallucinated
    n_hall = int(labels.sum())
    n_clean = int((labels == 0).sum())

    # --------------------------------------------- in-sample baseline (RQ25 reproduction)
    in_sample = calibrate_threshold_at_spec(lang_ent, labels)
    in_flag = lang_ent >= in_sample["threshold"] - EPS
    in_selected = np.where(in_flag, mixed_cpwer, sep_cpwer)
    in_sample_cpwer = float(in_selected.mean())

    # ----------------------------------------------------------------- bootstrap
    boot_idx = bootstrap_indices(n, N_BOOT, SEED)  # (N_BOOT, n)
    boot_thresholds = np.empty(N_BOOT, dtype=float)
    boot_oob_cpwer = np.empty(N_BOOT, dtype=float)
    boot_n_oob = np.empty(N_BOOT, dtype=int)
    boot_oob_flagged = np.empty(N_BOOT, dtype=int)
    boot_oob_separated = np.empty(N_BOOT, dtype=int)
    for b in range(N_BOOT):
        idx = boot_idx[b]
        cal = calibrate_threshold_at_spec(lang_ent[idx], labels[idx])
        thr = cal["threshold"]
        boot_thresholds[b] = thr
        oob = out_of_bag_cpwer(lang_ent, mixed_cpwer, sep_cpwer, thr, idx)
        boot_oob_cpwer[b] = oob["cpwer"]
        boot_n_oob[b] = oob["n_oob"]
        boot_oob_flagged[b] = oob["n_flagged_mixed"]
        boot_oob_separated[b] = oob["n_separated"]

    # ------------------------------------------- aggregate threshold distribution
    thr_median = float(np.median(boot_thresholds))
    thr_mean = float(np.mean(boot_thresholds))
    thr_std = float(np.std(boot_thresholds))
    thr_lo, thr_hi = percentile_interval(boot_thresholds, 2.5, 97.5)
    thr_min = float(np.min(boot_thresholds))
    thr_max = float(np.max(boot_thresholds))
    thr_width = thr_hi - thr_lo
    thr_dist = threshold_distribution(boot_thresholds)

    # ----------------------------------------------- OOB cpWER distribution
    valid_mask = ~np.isnan(boot_oob_cpwer)
    valid_oob = boot_oob_cpwer[valid_mask]
    n_valid = int(valid_mask.sum())
    oob_median = float(np.median(valid_oob))
    oob_mean = float(np.mean(valid_oob))
    oob_lo, oob_hi = percentile_interval(valid_oob, 2.5, 97.5)
    oob_min = float(np.min(valid_oob))
    oob_max = float(np.max(valid_oob))
    oob_p25, oob_p75 = percentile_interval(valid_oob, 25, 75)
    oob_frac_below_110 = float(np.mean(valid_oob < H44C_MAX_CPWER))
    oob_frac_below_insample = float(np.mean(valid_oob < in_sample_cpwer))
    oob_n_oob_mean = float(np.mean(boot_n_oob[valid_mask]))

    # ------------------------------------------------------------ hypotheses
    h44a_supported = (H44A_LO - EPS) <= thr_median <= (H44A_HI + EPS)
    h44b_supported = thr_width < H44B_MAX_WIDTH
    h44c_supported = oob_median < H44C_MAX_CPWER

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ44: Bootstrap-aggregated threshold for out-of-sample router stability",
        "closes_issue": 958,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "builds_on": {
            "RQ13": "results/frontier/diverse_hallucination_detector/ (PR #904)",
            "RQ16": "results/frontier/corrected_router_simulation/ (PR #912)",
            "RQ25": "results/frontier/out_of_sample_router/ (PR #929)",
        },
        "method": (
            "reanalysis only (no Whisper / no ASR run); B=10000 bootstrap resamples "
            "(seed=42) of the 77 AISHELL-4 windows. On each resample: calibrate the "
            "lang-id entropy threshold maximising sensitivity at >= 90% specificity "
            "(RQ13/RQ16/RQ25 rule). Aggregate thresholds (median, 2.5/97.5 pct "
            "interval, modes). Out-of-bag windows held out per resample; corrected-"
            "router cpWER computed on the OOB set at the resample's threshold."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated": n_hall,
        "n_clean": n_clean,
        "hallucination_label_rule": "always_separated_cpwer > 1.0",
        "routing_rule": (
            "lang_id_entropy >= threshold -> route MIXED (always_mixed_cpwer); "
            "else route SEPARATED (always_separated_cpwer). HIGH lang-id entropy = "
            "diverse multilingual gibberish = hallucination (RQ13/RQ16/RQ25 convention)."
        ),
        "calibration_rule": (
            "sweep threshold 0.0-2.0 bits in 0.01 steps; select threshold maximising "
            "sensitivity at >= 90% specificity. Tie-breaker: higher specificity, then "
            "lower threshold."
        ),
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": SEED,
            "resample_size": n,
            # P(window i is OOB) = (1 - 1/n)^n -> expected OOB size.
            "expected_oob_size": round(n * ((1 - 1 / n) ** n), 4),
        },
        "in_sample_reproduction": {
            "RQ25_threshold": RQ25_IN_SAMPLE_THRESHOLD,
            "RQ16_threshold": RQ16_IN_SAMPLE_THRESHOLD,
            "threshold": in_sample["threshold"],
            "sensitivity": in_sample["sensitivity"],
            "specificity": in_sample["specificity"],
            "cpwer": round(in_sample_cpwer, 6),
            "RQ25_cpwer_reference": RQ25_IN_SAMPLE_CPWER,
            "tp": in_sample["tp"], "fp": in_sample["fp"],
            "tn": in_sample["tn"], "fn": in_sample["fn"],
            "note": "Calibrated and evaluated on all 77 windows (in-sample). Reproduces RQ25.",
        },
        "threshold_distribution": {
            "median": round(thr_median, 6),
            "mean": round(thr_mean, 6),
            "std": round(thr_std, 6),
            "min": round(thr_min, 6),
            "max": round(thr_max, 6),
            "percentile_2_5": round(thr_lo, 6),
            "percentile_97_5": round(thr_hi, 6),
            "interval_width": round(thr_width, 6),
            "mode": round(thr_dist["mode"], 6),
            "mode_count": thr_dist["mode_count"],
            "mode_fraction": round(thr_dist["mode_fraction"], 6),
            "n_unique": thr_dist["n_unique"],
            "modes_within_10pct": [
                {"threshold": round(t, 6), "count": c, "fraction": round(f, 6)}
                for t, c, f in thr_dist["modes_within_10pct"]
            ],
            "top_values": [
                {"threshold": round(t, 6), "count": c, "fraction": round(f, 6)}
                for t, c, f in thr_dist["top_values"]
            ],
        },
        "oob_cpwer_distribution": {
            "n_valid_resamples": n_valid,
            "mean_oob_size": round(oob_n_oob_mean, 4),
            "median": round(oob_median, 6),
            "mean": round(oob_mean, 6),
            "min": round(oob_min, 6),
            "max": round(oob_max, 6),
            "percentile_2_5": round(oob_lo, 6),
            "percentile_97_5": round(oob_hi, 6),
            "iqr": [round(oob_p25, 6), round(oob_p75, 6)],
            "frac_below_1_10": round(oob_frac_below_110, 6),
            "frac_below_in_sample_cpwer": round(oob_frac_below_insample, 6),
        },
        "hypothesis_verdicts": {
            "H44a": {
                "statement": "median bootstrap threshold in [0.30, 0.50]",
                "median_threshold": round(thr_median, 6),
                "range": [H44A_LO, H44A_HI],
                "supported": bool(h44a_supported),
            },
            "H44b": {
                "statement": "2.5/97.5 percentile interval width < 0.20 (bagging stabilises threshold)",
                "interval": [round(thr_lo, 6), round(thr_hi, 6)],
                "width": round(thr_width, 6),
                "kill_threshold": H44B_MAX_WIDTH,
                "supported": bool(h44b_supported),
            },
            "H44c": {
                "statement": "median held-out (OOB) cpWER < 1.10",
                "median_oob_cpwer": round(oob_median, 6),
                "oob_cpwer_ci_95": [round(oob_lo, 6), round(oob_hi, 6)],
                "frac_oob_below_1_10": round(oob_frac_below_110, 6),
                "kill_threshold": H44C_MAX_CPWER,
                "supported": bool(h44c_supported),
            },
        },
    }

    # ----------------------------------------------------------- per-bootstrap CSV
    csv_fields = [
        "bootstrap_id", "threshold", "n_in_bag", "n_oob",
        "n_oob_flagged_mixed", "n_oob_separated", "oob_cpwer",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for b in range(N_BOOT):
            cpw = boot_oob_cpwer[b]
            wr.writerow({
                "bootstrap_id": b,
                "threshold": round(float(boot_thresholds[b]), 6),
                "n_in_bag": n,
                "n_oob": int(boot_n_oob[b]),
                "n_oob_flagged_mixed": int(boot_oob_flagged[b]),
                "n_oob_separated": int(boot_oob_separated[b]),
                "oob_cpwer": "" if math.isnan(float(cpw)) else round(float(cpw), 6),
            })

    # ----------------------------------------------------------- write JSON
    summary_with_arrays = dict(summary)
    summary_with_arrays["per_bootstrap"] = {
        "thresholds": [round(float(t), 6) for t in boot_thresholds],
        "oob_cpwer": [round(float(c), 6) if not math.isnan(float(c)) else None
                       for c in boot_oob_cpwer],
        "n_oob": [int(x) for x in boot_n_oob],
    }
    OUT_JSON.write_text(
        json.dumps(summary_with_arrays, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- console
    print(f"=== RQ44: Bootstrap threshold stability (AISHELL-4, {n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucination label: always_separated_cpwer > 1.0 -> {n_hall} hall / {n_clean} clean")
    print(f"Bootstrap: B={N_BOOT}, seed={SEED}, resample_size={n}")
    print()
    print("In-sample reproduction (calibrate + evaluate on all 77, RQ25 reference):")
    print(f"  threshold         : {in_sample['threshold']:.4f}  (RQ25 reported 0.38, RQ16 0.409)")
    print(f"  sensitivity       : {in_sample['sensitivity']:.4f}")
    print(f"  specificity       : {in_sample['specificity']:.4f}")
    print(f"  corrected cpWER   : {in_sample_cpwer:.6f}  (RQ25 reported 1.043)")
    print()
    print("Bootstrap threshold distribution (B=10000):")
    print(f"  median            : {thr_median:.4f}")
    print(f"  mean / std        : {thr_mean:.4f} / {thr_std:.4f}")
    print(f"  2.5 / 97.5 pct    : [{thr_lo:.4f}, {thr_hi:.4f}]  width={thr_width:.4f}")
    print(f"  min / max         : [{thr_min:.4f}, {thr_max:.4f}]")
    print(f"  mode              : {thr_dist['mode']:.4f}  "
          f"(count={thr_dist['mode_count']}, frac={thr_dist['mode_fraction']:.3f})")
    print(f"  n_unique          : {thr_dist['n_unique']}")
    print("  modes (within 10% of max count):")
    for t, c, f in thr_dist["modes_within_10pct"]:
        print(f"    threshold={t:.4f}  count={c}  frac={f:.3f}")
    print("  top 5 values:")
    for t, c, f in thr_dist["top_values"]:
        print(f"    threshold={t:.4f}  count={c}  frac={f:.3f}")
    print()
    print("Out-of-bag cpWER distribution (held-out per resample):")
    print(f"  n valid resamples : {n_valid} / {N_BOOT}")
    print(f"  mean OOB size     : {oob_n_oob_mean:.2f} windows")
    print(f"  median            : {oob_median:.6f}")
    print(f"  mean              : {oob_mean:.6f}")
    print(f"  2.5 / 97.5 pct    : [{oob_lo:.4f}, {oob_hi:.4f}]")
    print(f"  min / max         : [{oob_min:.4f}, {oob_max:.4f}]")
    print(f"  frac < 1.10       : {oob_frac_below_110:.4f}")
    print(f"  frac < in-sample  : {oob_frac_below_insample:.4f}  (in-sample cpWER={in_sample_cpwer:.4f})")
    print()
    print("Hypothesis verdicts:")
    print(f"  H44a (median threshold in [0.30, 0.50]): "
          f"{'SUPPORTED' if h44a_supported else 'KILLED'}  "
          f"(median={thr_median:.4f})")
    print(f"  H44b (pct interval width < 0.20):        "
          f"{'SUPPORTED' if h44b_supported else 'KILLED'}  "
          f"(width={thr_width:.4f}, interval=[{thr_lo:.4f}, {thr_hi:.4f}])")
    print(f"  H44c (median OOB cpWER < 1.10):          "
          f"{'SUPPORTED' if h44c_supported else 'KILLED'}  "
          f"(median OOB cpWER={oob_median:.4f}, CI=[{oob_lo:.4f}, {oob_hi:.4f}])")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
