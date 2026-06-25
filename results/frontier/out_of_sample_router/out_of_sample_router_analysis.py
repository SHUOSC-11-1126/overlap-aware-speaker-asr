"""RQ25: Out-of-sample corrected router on AISHELL-4.

REANALYSIS ONLY -- no Whisper / no ASR model is run. This script reads the existing
AISHELL-4 external-validation results (``results/external_sanity_check/aishell4/
rq1_aishell4_validation_results.json``, label ``external/sanity-check``, PR #890) and
tests whether the language-id entropy threshold (0.409 bits, RQ16 / PR #912)
generalizes to a held-out AISHELL-4 split.

RQ16 found that the corrected router (lang-id entropy at threshold 0.409 bits)
recovers AISHELL-4 cpWER to 1.043, but the threshold was calibrated on the same 77
windows used for evaluation -- in-sample. This study implements stratified 50/50
train/test, K-fold CV (K=5), and leave-one-out CV to estimate out-of-sample
validity.

Routing rule (RQ13/RQ16 convention)
-----------------------------------
HIGH lang-id entropy = diverse multilingual gibberish = hallucination. The detector
flags the separated track when ``lang_id_entropy >= threshold`` (this matches RQ13's
operating-point definition and RQ16's corrected router). The router then routes to
MIXED; otherwise it routes to SEPARATED:

    if lang_id_entropy >= threshold -> route MIXED  (cpWER = always_mixed_cpwer)
    else                            -> route SEPARATED (cpWER = always_separated_cpwer)

This is the convention required for H25c (threshold within 20% of in-sample
threshold [0.327, 0.491], centred on RQ16's 0.409) to be a meaningful test.

Pre-registered hypotheses (issue #926)
--------------------------------------
- H25a: out-of-sample corrected router cpWER < 1.10 on held-out test split.
        Kill: cpWER >= 1.10.
- H25b: out-of-sample sensitivity on test split > 80%.
        Kill: sensitivity <= 80%.
- H25c: out-of-sample threshold within 20% of in-sample threshold [0.327, 0.491].
        Kill: threshold outside [0.327, 0.491].

Method
------
1. Compute ``lang_id_entropy`` per window (max across per-speaker separated tracks;
   RQ13/RQ12 worst-case-speaker convention). The detector primitive is lifted verbatim
   from RQ13/RQ16 so thresholds are directly comparable.
2. Hallucination label: ``always_separated_cpwer > 1.0`` (37 hallucinated / 40 clean).
3. Stratified 50/50 split (seed=42): 19/18 hallucinated + 20/20 clean per split
   (train=39, test=38).
4. Calibrate on train: sweep threshold 0.0-2.0 bits in 0.01 steps; select threshold
   maximising sensitivity at >= 90% specificity.
5. Evaluate on test: apply train-calibrated threshold; measure cpWER, sensitivity,
   specificity.
6. K-fold CV (K=5, stratified): repeat calibration/evaluation 5 times; average test
   cpWER and sensitivity (micro- and macro-averaged).
7. LOO-CV: each window held out once; macro-average cpWER and micro-average
   sensitivity over the 77 held-out predictions.

cpWER computation
-----------------
The corrected router's per-window cpWER is the chosen route's stored cpWER
(``always_mixed_cpwer`` if flagged, ``always_separated_cpwer`` otherwise), averaged
over the evaluation set.

Statistics
----------
Bootstrap 95% CI on test cpWER (10,000 resamples, seed=42) of the per-window selected
cpWERs at the FROZEN train-calibrated threshold. Threshold uncertainty is not included
in the CI (a limitation, noted in FINDINGS.md). numpy + stdlib only.

Label: experimental/frontier. Closes #926. Builds on RQ13 (PR #904) and RQ16 (PR #912).
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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "out_of_sample_router"
OUT_CSV = OUT_DIR / "out_of_sample_results.csv"
OUT_JSON = OUT_DIR / "out_of_sample_results.json"

# ------------------------------------------------------------------ constants
CATASTROPHIC_CPWER = 1.0    # cpWER > 1.0 => insertions dominate (hallucination label)
TARGET_SPECIFICITY = 0.90   # calibrate the threshold to >= 90% specificity
THRESHOLD_GRID = [round(0.01 * i, 2) for i in range(0, 201)]  # 0.00, 0.01, ..., 2.00
K_FOLDS = 5
N_BOOT = 10000
SEED = 42
EPS = 1e-9

# RQ16's in-sample threshold (RQ13's >= 90%-specificity operating point on the 77
# windows): 0.409073 bits. H25c tests whether the out-of-sample threshold lands within
# 20% of this, i.e. in [0.327, 0.491].
RQ16_IN_SAMPLE_THRESHOLD = 0.409
H25C_LO, H25C_HI = 0.327, 0.491  # 0.409 * 0.8, 0.409 * 1.2
RQ16_IN_SAMPLE_CPWER = 1.043     # RQ16 reported corrected-router cpWER (lang-id alone)


# ------------------------------------------------------------- script detection
def script_category(ch: str) -> str:
    """Map a character to a coarse Unicode script category (RQ13/RQ16 verbatim).

    Uses ``unicodedata.name``. Whitespace -> "Space"; punctuation/symbols -> "Punct";
    control/unknown -> "Other". Sufficient to separate Han / Latin / Hiragana /
    Katakana / Hangul / Cyrillic / Arabic / Greek / Digit, which are exactly the
    scripts RQ12/RQ13 observed in AISHELL-4 hallucination."""
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


def max_across_speakers(window: dict[str, Any]) -> float:
    """Max of ``language_id_entropy`` over the per-speaker separated transcripts
    (worst-case speaker track; RQ12/RQ13 convention). Empty/whitespace speaker texts
    are effectively skipped."""
    vals = [
        language_id_entropy(str(t))
        for t in window.get("separated_text_per_speaker", {}).values()
        if t is not None and str(t).strip()
    ]
    return max(vals) if vals else 0.0


# --------------------------------------------------------- threshold calibration
def calibrate_threshold(
    scores: np.ndarray, labels: np.ndarray, grid: list[float] | None = None
) -> dict[str, Any]:
    """Sweep threshold over ``grid`` (default THRESHOLD_GRID); select the threshold
    with specificity >= TARGET_SPECIFICITY and maximal sensitivity. Tie-breaker:
    higher specificity, then lower threshold (more sensitive).

    Convention (RQ13/RQ16): ``score >= threshold`` flags the window as hallucinated.
    Sensitivity = TP / (TP + FN); specificity = TN / (TN + FP).

    Returns the chosen threshold plus its sensitivity, specificity, and confusion
    counts on the calibration set.
    """
    if grid is None:
        grid = THRESHOLD_GRID
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
        if spec >= TARGET_SPECIFICITY - EPS:
            cand = {
                "threshold": float(t),
                "sensitivity": float(sens),
                "specificity": float(spec),
                "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            }
            if best is None:
                best = cand
            else:
                # Maximise sensitivity; tie-break by higher specificity, then lower
                # threshold (more sensitive, fewer false negatives if all else equal).
                if sens > best["sensitivity"] + EPS:
                    best = cand
                elif abs(sens - best["sensitivity"]) <= EPS:
                    if spec > best["specificity"] + EPS:
                        best = cand
                    elif abs(spec - best["specificity"]) <= EPS and t < best["threshold"]:
                        best = cand
    if best is None:
        # No threshold satisfies the specificity target -> fall back to the highest
        # threshold (most conservative: flag nothing). Sensitivity = 0, specificity = 1.
        t_max = float(grid[-1]) if grid else 1.0
        best = {
            "threshold": t_max, "sensitivity": 0.0, "specificity": 1.0,
            "tp": 0, "fp": 0, "tn": n_neg, "fn": n_pos,
        }
    return best


# --------------------------------------------------------- evaluation at threshold
def evaluate_at_threshold(
    scores: np.ndarray, labels: np.ndarray,
    mixed_cpwer: np.ndarray, sep_cpwer: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    """Apply ``threshold`` (score >= threshold => flag => MIXED) and return per-set
    metrics: confusion matrix, sensitivity, specificity, corrected-router cpWER
    (mean of selected per-window cpWERs), and the array of selected cpWERs."""
    flagged = scores >= threshold - EPS
    tp = int(np.sum(flagged & (labels == 1)))
    fp = int(np.sum(flagged & (labels == 0)))
    tn = int(np.sum(~flagged & (labels == 0)))
    fn = int(np.sum(~flagged & (labels == 1)))
    n_pos = tp + fn
    n_neg = fp + tn
    sens = (tp / n_pos) if n_pos > 0 else 0.0
    spec = (tn / n_neg) if n_neg > 0 else 1.0
    selected = np.where(flagged, mixed_cpwer, sep_cpwer)
    return {
        "threshold": float(threshold),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "sensitivity": float(sens),
        "specificity": float(spec),
        "cpwer": float(selected.mean()) if len(selected) > 0 else 0.0,
        "selected_cpwer": selected.tolist(),
        "n_flagged_mixed": int(np.sum(flagged)),
        "n_separated": int(np.sum(~flagged)),
    }


# --------------------------------------------------------------------- bootstrap
def bootstrap_cpwer_ci(
    selected_cpwer: np.ndarray, n_boot: int = N_BOOT, seed: int = SEED
) -> tuple[float, float]:
    """Bootstrap 95% CI for the mean of the per-window selected cpWERs (resample with
    replacement). The threshold is FROZEN -- this CI captures only the cpWER-sampling
    variance, not threshold-calibration variance."""
    rng = np.random.default_rng(seed)
    n = len(selected_cpwer)
    if n == 0:
        return 0.0, 0.0
    means = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        means[b] = float(selected_cpwer[idx].mean())
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# --------------------------------------------------------- stratified split helpers
def stratified_5050_split(
    labels: np.ndarray, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Stratified 50/50 train/test split. Within each class, shuffle (seed-controlled)
    and take the first half for train, second half for test. For 37 positives this
    yields 19 train / 18 test; for 40 negatives 20 train / 20 test."""
    rng = np.random.default_rng(seed)
    pos = np.where(labels == 1)[0]
    neg = np.where(labels == 0)[0]
    rng.shuffle(pos)
    rng.shuffle(neg)
    n_pos_tr = len(pos) // 2 if len(pos) % 2 == 0 else (len(pos) + 1) // 2  # ceil for train
    n_neg_tr = len(neg) // 2 if len(neg) % 2 == 0 else (len(neg) + 1) // 2
    # The task specifies 19/18 + 20/20: take ceil(pos/2) for train (19) and floor(pos/2)
    # for test (18); split negatives evenly (20/20).
    train_idx = np.concatenate([pos[:n_pos_tr], neg[:n_neg_tr]])
    test_idx = np.concatenate([pos[n_pos_tr:], neg[n_neg_tr:]])
    return train_idx, test_idx


def stratified_kfold_indices(
    labels: np.ndarray, k: int, seed: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Stratified K-fold split (no sklearn). Returns list of (train_idx, test_idx).
    Within each class the indices are shuffled (deterministic, seed-controlled) then
    partitioned into k contiguous chunks. Fold j's test set = chunk j of each class
    concatenated."""
    rng = np.random.default_rng(seed)
    pos = np.where(labels == 1)[0]
    neg = np.where(labels == 0)[0]
    rng.shuffle(pos)
    rng.shuffle(neg)
    folds: list[tuple[np.ndarray, np.ndarray]] = []
    pos_chunks = np.array_split(pos, k)
    neg_chunks = np.array_split(neg, k)
    for j in range(k):
        test_idx = np.concatenate([pos_chunks[j], neg_chunks[j]])
        train_pos = np.concatenate([pos_chunks[m] for m in range(k) if m != j])
        train_neg = np.concatenate([neg_chunks[m] for m in range(k) if m != j])
        train_idx = np.concatenate([train_pos, train_neg])
        folds.append((train_idx, test_idx))
    return folds


# --------------------------------------------------------- cross-validation drivers
def kfold_cv(
    scores: np.ndarray, labels: np.ndarray,
    mixed_cpwer: np.ndarray, sep_cpwer: np.ndarray,
    k: int, seed: int,
) -> dict[str, Any]:
    """K-fold stratified CV. On each fold: calibrate threshold on the training folds
    (>= 90% specificity, max sensitivity), evaluate cpWER/sensitivity/specificity on
    the held-out fold. Macro-average cpWER = mean of per-fold cpWERs weighted by fold
    size (= mean over all held-out windows of the selected cpWER). Micro-averaged
    sensitivity/specificity pool all held-out predictions."""
    folds = stratified_kfold_indices(labels, k, seed)
    per_fold: list[dict[str, Any]] = []
    selected_per_window = np.empty(len(scores), dtype=float)
    pred_flagged = np.zeros(len(scores), dtype=bool)
    thresholds: list[float] = []
    for j, (train_idx, test_idx) in enumerate(folds):
        cal = calibrate_threshold(scores[train_idx], labels[train_idx])
        thr = cal["threshold"]
        thresholds.append(thr)
        ev = evaluate_at_threshold(
            scores[test_idx], labels[test_idx],
            mixed_cpwer[test_idx], sep_cpwer[test_idx], thr,
        )
        per_fold.append({
            "fold": j,
            "n_train": int(len(train_idx)),
            "n_test": int(len(test_idx)),
            "n_test_pos": int(np.sum(labels[test_idx] == 1)),
            "n_test_neg": int(np.sum(labels[test_idx] == 0)),
            "train_threshold": thr,
            "train_sensitivity": cal["sensitivity"],
            "train_specificity": cal["specificity"],
            "tp": ev["tp"], "fp": ev["fp"], "tn": ev["tn"], "fn": ev["fn"],
            "sensitivity": ev["sensitivity"],
            "specificity": ev["specificity"],
            "cpwer": ev["cpwer"],
            "n_flagged_mixed": ev["n_flagged_mixed"],
            "n_separated": ev["n_separated"],
        })
        selected_per_window[test_idx] = np.array(ev["selected_cpwer"])
        pred_flagged[test_idx] = scores[test_idx] >= thr - EPS
    # Micro-averaged confusion matrix across all folds.
    tp = int(np.sum(pred_flagged & (labels == 1)))
    fp = int(np.sum(pred_flagged & (labels == 0)))
    tn = int(np.sum(~pred_flagged & (labels == 0)))
    fn = int(np.sum(~pred_flagged & (labels == 1)))
    n_pos = tp + fn
    n_neg = fp + tn
    micro_sens = (tp / n_pos) if n_pos > 0 else 0.0
    micro_spec = (tn / n_neg) if n_neg > 0 else 1.0
    macro_sens = float(np.mean([f["sensitivity"] for f in per_fold]))
    macro_spec = float(np.mean([f["specificity"] for f in per_fold]))
    macro_cpwer = float(selected_per_window.mean())
    return {
        "method": f"{k}-fold stratified CV",
        "k": k,
        "seed": seed,
        "per_fold": per_fold,
        "thresholds": thresholds,
        "threshold_mean": float(np.mean(thresholds)),
        "threshold_std": float(np.std(thresholds)),
        "threshold_min": float(np.min(thresholds)),
        "threshold_max": float(np.max(thresholds)),
        "macro_cpwer": macro_cpwer,
        "macro_sensitivity": macro_sens,
        "macro_specificity": macro_spec,
        "micro_sensitivity": float(micro_sens),
        "micro_specificity": float(micro_spec),
        "micro_tp": tp, "micro_fp": fp, "micro_tn": tn, "micro_fn": fn,
        "selected_cpwer_per_window": selected_per_window.tolist(),
    }


def loo_cv(
    scores: np.ndarray, labels: np.ndarray,
    mixed_cpwer: np.ndarray, sep_cpwer: np.ndarray,
) -> dict[str, Any]:
    """Leave-one-out CV. Each window held out once; threshold selected on the
    remaining n-1 windows (>= 90% specificity, max sensitivity). The held-out window
    is then classified at that threshold. Macro-cpWER = mean over all 77 selected
    cpWERs; micro sensitivity/specificity pool all 77 predictions."""
    n = len(scores)
    selected = np.empty(n, dtype=float)
    pred_flagged = np.zeros(n, dtype=bool)
    thresholds: list[float] = []
    per_track: list[dict[str, Any]] = []
    all_idx = np.arange(n)
    for i in range(n):
        train_idx = np.delete(all_idx, i)
        cal = calibrate_threshold(scores[train_idx], labels[train_idx])
        thr = cal["threshold"]
        thresholds.append(thr)
        flag = bool(scores[i] >= thr - EPS)
        pred_flagged[i] = flag
        sel = float(mixed_cpwer[i]) if flag else float(sep_cpwer[i])
        selected[i] = sel
        per_track.append({
            "idx": int(i),
            "score": float(scores[i]),
            "label": int(labels[i]),
            "threshold": thr,
            "pred_flagged": flag,
            "selected_cpwer": sel,
        })
    tp = int(np.sum(pred_flagged & (labels == 1)))
    fp = int(np.sum(pred_flagged & (labels == 0)))
    tn = int(np.sum(~pred_flagged & (labels == 0)))
    fn = int(np.sum(~pred_flagged & (labels == 1)))
    n_pos = tp + fn
    n_neg = fp + tn
    micro_sens = (tp / n_pos) if n_pos > 0 else 0.0
    micro_spec = (tn / n_neg) if n_neg > 0 else 1.0
    return {
        "method": "leave-one-out CV",
        "k": n,
        "per_track": per_track,
        "thresholds": thresholds,
        "threshold_mean": float(np.mean(thresholds)),
        "threshold_std": float(np.std(thresholds)),
        "threshold_min": float(np.min(thresholds)),
        "threshold_max": float(np.max(thresholds)),
        "macro_cpwer": float(selected.mean()),
        "micro_sensitivity": float(micro_sens),
        "micro_specificity": float(micro_spec),
        "macro_sensitivity": float(micro_sens),  # n folds of size 1 -> macro == micro
        "macro_specificity": float(micro_spec),
        "micro_tp": tp, "micro_fp": fp, "micro_tn": tn, "micro_fn": fn,
        "selected_cpwer_per_window": selected.tolist(),
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

    # ------------------------------------------------- in-sample baseline (RQ16 reproduction)
    in_sample = calibrate_threshold(lang_ent, labels)
    in_sample_eval = evaluate_at_threshold(lang_ent, labels, mixed_cpwer, sep_cpwer,
                                           in_sample["threshold"])
    in_sample_ci = bootstrap_cpwer_ci(
        np.array(in_sample_eval["selected_cpwer"], dtype=float)
    )

    # --------------------------------------------- stratified 50/50 split (seed=42)
    train_idx, test_idx = stratified_5050_split(labels, SEED)
    train_scores, test_scores = lang_ent[train_idx], lang_ent[test_idx]
    train_labels, test_labels = labels[train_idx], labels[test_idx]
    train_mixed, test_mixed = mixed_cpwer[train_idx], mixed_cpwer[test_idx]
    train_sep, test_sep = sep_cpwer[train_idx], sep_cpwer[test_idx]

    train_cal = calibrate_threshold(train_scores, train_labels)
    test_eval = evaluate_at_threshold(test_scores, test_labels,
                                      test_mixed, test_sep, train_cal["threshold"])
    # In-sample (train) cpWER at the train-calibrated threshold, for optimism reference.
    train_eval = evaluate_at_threshold(train_scores, train_labels,
                                       train_mixed, train_sep, train_cal["threshold"])
    test_ci = bootstrap_cpwer_ci(np.array(test_eval["selected_cpwer"], dtype=float))

    # ------------------------------------------------------------- K-fold CV (K=5)
    kfold = kfold_cv(lang_ent, labels, mixed_cpwer, sep_cpwer, K_FOLDS, SEED)
    kfold_ci = bootstrap_cpwer_ci(np.array(kfold["selected_cpwer_per_window"], dtype=float))

    # ----------------------------------------------------------------- LOO-CV
    loo = loo_cv(lang_ent, labels, mixed_cpwer, sep_cpwer)
    loo_ci = bootstrap_cpwer_ci(np.array(loo["selected_cpwer_per_window"], dtype=float))

    # ----------------------------------------------------- hypothesis verdicts
    test_cpwer = test_eval["cpwer"]
    test_sens = test_eval["sensitivity"]
    train_threshold = train_cal["threshold"]
    h25a_supported = test_cpwer < 1.10
    h25b_supported = test_sens > 0.80
    h25c_supported = (H25C_LO - EPS) <= train_threshold <= (H25C_HI + EPS)

    # Always-mixed / always-separated / oracle baselines on the test split.
    always_mixed_test = float(test_mixed.mean())
    always_sep_test = float(test_sep.mean())
    oracle_test = float(np.minimum(test_mixed, test_sep).mean())

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ25: Out-of-sample corrected router on AISHELL-4",
        "closes_issue": 926,
        "source_data": str(SRC_JSON.relative_to(PROJECT_ROOT)),
        "source_label": "external/sanity-check",
        "builds_on": {
            "RQ13": "results/frontier/diverse_hallucination_detector/ (PR #904)",
            "RQ16": "results/frontier/corrected_router_simulation/ (PR #912)",
        },
        "method": (
            "reanalysis only (no Whisper / no ASR run); lang-id entropy detector "
            "(RQ13/RQ16) calibrated on a stratified train split and evaluated on a "
            "held-out test split, plus K-fold CV (K=5) and LOO-CV."
        ),
        "meeting_id": data["meeting_id"],
        "n_windows": n,
        "n_hallucinated": n_hall,
        "n_clean": n_clean,
        "hallucination_label_rule": "always_separated_cpwer > 1.0",
        "routing_rule": (
            "lang_id_entropy >= threshold -> route MIXED (always_mixed_cpwer); "
            "else route SEPARATED (always_separated_cpwer). HIGH lang-id entropy = "
            "diverse multilingual gibberish = hallucination (RQ13/RQ16 convention)."
        ),
        "calibration_rule": (
            "sweep threshold 0.0-2.0 bits in 0.01 steps; select threshold maximising "
            "sensitivity at >= 90% specificity on the train split. Tie-breaker: higher "
            "specificity, then lower threshold."
        ),
        "in_sample_threshold_reference": {
            "RQ16_threshold": RQ16_IN_SAMPLE_THRESHOLD,
            "RQ16_cpwer": RQ16_IN_SAMPLE_CPWER,
            "H25c_range": [H25C_LO, H25C_HI],
            "note": "H25c tests whether the out-of-sample threshold lands within +/-20% of RQ16's 0.409.",
        },
        "in_sample_reproduction": {
            "threshold": in_sample["threshold"],
            "sensitivity": in_sample["sensitivity"],
            "specificity": in_sample["specificity"],
            "cpwer": in_sample_eval["cpwer"],
            "cpwer_ci_95": [round(in_sample_ci[0], 6), round(in_sample_ci[1], 6)],
            "tp": in_sample_eval["tp"], "fp": in_sample_eval["fp"],
            "tn": in_sample_eval["tn"], "fn": in_sample_eval["fn"],
            "n_flagged_mixed": in_sample_eval["n_flagged_mixed"],
            "n_separated": in_sample_eval["n_separated"],
            "note": "Calibrated and evaluated on all 77 windows (in-sample). Reproduces RQ16.",
        },
        "stratified_5050_split": {
            "seed": SEED,
            "n_train": int(len(train_idx)),
            "n_test": int(len(test_idx)),
            "n_train_hallucinated": int(train_labels.sum()),
            "n_train_clean": int((train_labels == 0).sum()),
            "n_test_hallucinated": int(test_labels.sum()),
            "n_test_clean": int((test_labels == 0).sum()),
        },
        "train_calibration": {
            "threshold": train_cal["threshold"],
            "sensitivity": train_cal["sensitivity"],
            "specificity": train_cal["specificity"],
            "tp": train_cal["tp"], "fp": train_cal["fp"],
            "tn": train_cal["tn"], "fn": train_cal["fn"],
            "train_cpwer_at_threshold": train_eval["cpwer"],
        },
        "test_evaluation": {
            "threshold_applied": train_cal["threshold"],
            "tp": test_eval["tp"], "fp": test_eval["fp"],
            "tn": test_eval["tn"], "fn": test_eval["fn"],
            "sensitivity": test_eval["sensitivity"],
            "specificity": test_eval["specificity"],
            "corrected_router_cpwer": test_eval["cpwer"],
            "corrected_router_cpwer_ci_95": [round(test_ci[0], 6), round(test_ci[1], 6)],
            "n_flagged_mixed": test_eval["n_flagged_mixed"],
            "n_separated": test_eval["n_separated"],
            "baselines_on_test": {
                "always_mixed_cpwer": round(always_mixed_test, 6),
                "always_separated_cpwer": round(always_sep_test, 6),
                "oracle_best_cpwer": round(oracle_test, 6),
                "router_v2_cpwer": round(float(rv2_cpwer[test_idx].mean()), 6),
            },
        },
        "kfold_cv": {
            "k": K_FOLDS,
            "seed": SEED,
            "macro_cpwer": round(kfold["macro_cpwer"], 6),
            "macro_cpwer_ci_95": [round(kfold_ci[0], 6), round(kfold_ci[1], 6)],
            "macro_sensitivity": round(kfold["macro_sensitivity"], 6),
            "macro_specificity": round(kfold["macro_specificity"], 6),
            "micro_sensitivity": round(kfold["micro_sensitivity"], 6),
            "micro_specificity": round(kfold["micro_specificity"], 6),
            "micro_tp": kfold["micro_tp"], "micro_fp": kfold["micro_fp"],
            "micro_tn": kfold["micro_tn"], "micro_fn": kfold["micro_fn"],
            "threshold_mean": round(kfold["threshold_mean"], 6),
            "threshold_std": round(kfold["threshold_std"], 6),
            "threshold_min": round(kfold["threshold_min"], 6),
            "threshold_max": round(kfold["threshold_max"], 6),
            "per_fold": kfold["per_fold"],
        },
        "loo_cv": {
            "macro_cpwer": round(loo["macro_cpwer"], 6),
            "macro_cpwer_ci_95": [round(loo_ci[0], 6), round(loo_ci[1], 6)],
            "micro_sensitivity": round(loo["micro_sensitivity"], 6),
            "micro_specificity": round(loo["micro_specificity"], 6),
            "macro_sensitivity": round(loo["macro_sensitivity"], 6),
            "macro_specificity": round(loo["macro_specificity"], 6),
            "micro_tp": loo["micro_tp"], "micro_fp": loo["micro_fp"],
            "micro_tn": loo["micro_tn"], "micro_fn": loo["micro_fn"],
            "threshold_mean": round(loo["threshold_mean"], 6),
            "threshold_std": round(loo["threshold_std"], 6),
            "threshold_min": round(loo["threshold_min"], 6),
            "threshold_max": round(loo["threshold_max"], 6),
        },
        "hypothesis_verdicts": {
            "H25a": {
                "statement": "out-of-sample corrected router cpWER < 1.10 on held-out test split",
                "test_cpwer": round(test_cpwer, 6),
                "kill_threshold": 1.10,
                "supported": bool(h25a_supported),
                "bootstrap_ci_95": [round(test_ci[0], 6), round(test_ci[1], 6)],
            },
            "H25b": {
                "statement": "out-of-sample sensitivity on test split > 80%",
                "test_sensitivity": round(test_sens, 6),
                "kill_threshold": 0.80,
                "supported": bool(h25b_supported),
                "tp": test_eval["tp"], "fn": test_eval["fn"],
                "n_test_hallucinated": int(test_labels.sum()),
            },
            "H25c": {
                "statement": "out-of-sample threshold within 20% of in-sample threshold [0.327, 0.491]",
                "train_threshold": round(train_threshold, 6),
                "in_sample_reference": RQ16_IN_SAMPLE_THRESHOLD,
                "range": [H25C_LO, H25C_HI],
                "supported": bool(h25c_supported),
            },
        },
    }

    # ----------------------------------------------------------- per-window CSV
    # Build per-window rows for the 50/50 split + LOO selected cpWERs.
    loo_sel = np.array(loo["selected_cpwer_per_window"], dtype=float)
    loo_thr = np.array(loo["thresholds"], dtype=float)
    kfold_sel = np.array(kfold["selected_cpwer_per_window"], dtype=float)
    split_assignment = np.empty(n, dtype=object)
    split_assignment[train_idx] = "train"
    split_assignment[test_idx] = "test"
    csv_fields = [
        "window_id", "lang_id_entropy", "hallucination_label",
        "always_mixed_cpwer", "always_separated_cpwer", "router_v2_cpwer",
        "oracle_best_cpwer",
        "split_5050",
        "in_sample_threshold", "in_sample_flagged", "in_sample_selected_cpwer",
        "train_threshold_applied_to_test", "test_flagged", "test_selected_cpwer",
        "kfold_threshold_for_window", "kfold_selected_cpwer",
        "loo_threshold_for_window", "loo_flagged", "loo_selected_cpwer",
    ]
    rows: list[dict[str, Any]] = []
    for i, w in enumerate(windows):
        in_flag = bool(lang_ent[i] >= in_sample["threshold"] - EPS)
        test_flag = bool(lang_ent[i] >= train_cal["threshold"] - EPS)
        loo_flag = bool(lang_ent[i] >= loo_thr[i] - EPS)
        rows.append({
            "window_id": w["window_id"],
            "lang_id_entropy": round(float(lang_ent[i]), 6),
            "hallucination_label": int(labels[i]),
            "always_mixed_cpwer": round(float(mixed_cpwer[i]), 6),
            "always_separated_cpwer": round(float(sep_cpwer[i]), 6),
            "router_v2_cpwer": round(float(rv2_cpwer[i]), 6),
            "oracle_best_cpwer": round(float(oracle_cpwer[i]), 6),
            "split_5050": split_assignment[i],
            "in_sample_threshold": round(in_sample["threshold"], 6),
            "in_sample_flagged": in_flag,
            "in_sample_selected_cpwer": round(float(mixed_cpwer[i] if in_flag else sep_cpwer[i]), 6),
            "train_threshold_applied_to_test": round(train_cal["threshold"], 6),
            "test_flagged": test_flag,
            "test_selected_cpwer": round(float(mixed_cpwer[i] if test_flag else sep_cpwer[i]), 6),
            "kfold_threshold_for_window": "",
            "kfold_selected_cpwer": round(float(kfold_sel[i]), 6),
            "loo_threshold_for_window": round(float(loo_thr[i]), 6),
            "loo_flagged": loo_flag,
            "loo_selected_cpwer": round(float(loo_sel[i]), 6),
        })
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in csv_fields})

    # ----------------------------------------------------------- write JSON
    summary_with_rows = dict(summary)
    summary_with_rows["per_window"] = rows
    OUT_JSON.write_text(
        json.dumps(summary_with_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # ----------------------------------------------------------- console
    print(f"=== RQ25: Out-of-sample corrected router (AISHELL-4, {n} windows) ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_JSON.relative_to(PROJECT_ROOT)}")
    print(f"Hallucination label: always_separated_cpwer > 1.0 -> {n_hall} hallucinated / {n_clean} clean")
    print()
    print("In-sample reproduction (calibrate + evaluate on all 77, RQ16 reference):")
    print(f"  threshold         : {in_sample['threshold']:.4f}  (RQ16 reported 0.409)")
    print(f"  sensitivity       : {in_sample['sensitivity']:.4f}")
    print(f"  specificity       : {in_sample['specificity']:.4f}")
    print(f"  corrected cpWER   : {in_sample_eval['cpwer']:.6f}  CI=[{in_sample_ci[0]:.4f}, {in_sample_ci[1]:.4f}]  (RQ16 reported 1.043)")
    print()
    print("Stratified 50/50 split (seed=42):")
    print(f"  train: {len(train_idx)} windows ({int(train_labels.sum())} hall / {int((train_labels==0).sum())} clean)")
    print(f"  test : {len(test_idx)} windows ({int(test_labels.sum())} hall / {int((test_labels==0).sum())} clean)")
    print()
    print("Train calibration (sweep 0.0-2.0 in 0.01 steps, max sens at >=90% spec):")
    print(f"  train threshold   : {train_cal['threshold']:.4f}  (H25c range [{H25C_LO}, {H25C_HI}])")
    print(f"  train sensitivity : {train_cal['sensitivity']:.4f}")
    print(f"  train specificity : {train_cal['specificity']:.4f}")
    print(f"  train cpWER @ thr : {train_eval['cpwer']:.6f}  (in-sample optimism reference)")
    print()
    print("Test evaluation at train-calibrated threshold:")
    print(f"  test threshold    : {train_cal['threshold']:.4f}")
    print(f"  test sensitivity  : {test_eval['sensitivity']:.4f}  (TP={test_eval['tp']}, FN={test_eval['fn']})")
    print(f"  test specificity  : {test_eval['specificity']:.4f}  (FP={test_eval['fp']}, TN={test_eval['tn']})")
    print(f"  test corrected cpWER : {test_eval['cpwer']:.6f}  CI=[{test_ci[0]:.4f}, {test_ci[1]:.4f}]")
    print(f"  test always-mixed    : {always_mixed_test:.6f}")
    print(f"  test always-separated: {always_sep_test:.6f}")
    print(f"  test oracle best     : {oracle_test:.6f}")
    print(f"  test router v2       : {float(rv2_cpwer[test_idx].mean()):.6f}")
    print(f"  test decisions: mixed={test_eval['n_flagged_mixed']}, separated={test_eval['n_separated']}")
    print()
    print(f"K-fold CV (K={K_FOLDS}, seed={SEED}):")
    print(f"  macro cpWER       : {kfold['macro_cpwer']:.6f}  CI=[{kfold_ci[0]:.4f}, {kfold_ci[1]:.4f}]")
    print(f"  macro sensitivity : {kfold['macro_sensitivity']:.4f}  (micro {kfold['micro_sensitivity']:.4f})")
    print(f"  macro specificity : {kfold['macro_specificity']:.4f}  (micro {kfold['micro_specificity']:.4f})")
    print(f"  threshold mean    : {kfold['threshold_mean']:.4f}  std={kfold['threshold_std']:.4f}  "
          f"min={kfold['threshold_min']:.4f}  max={kfold['threshold_max']:.4f}")
    for f in kfold["per_fold"]:
        print(f"    fold {f['fold']}: n_test={f['n_test']} ({f['n_test_pos']}pos/{f['n_test_neg']}neg) "
              f"thr={f['train_threshold']:.4f} sens={f['sensitivity']:.4f} spec={f['specificity']:.4f} "
              f"cpwer={f['cpwer']:.6f}")
    print()
    print("LOO-CV (n=77):")
    print(f"  macro cpWER       : {loo['macro_cpwer']:.6f}  CI=[{loo_ci[0]:.4f}, {loo_ci[1]:.4f}]")
    print(f"  micro sensitivity : {loo['micro_sensitivity']:.4f}  (TP={loo['micro_tp']}, FN={loo['micro_fn']})")
    print(f"  micro specificity : {loo['micro_specificity']:.4f}  (FP={loo['micro_fp']}, TN={loo['micro_tn']})")
    print(f"  threshold mean    : {loo['threshold_mean']:.4f}  std={loo['threshold_std']:.4f}  "
          f"min={loo['threshold_min']:.4f}  max={loo['threshold_max']:.4f}")
    print()
    print("Hypothesis verdicts:")
    print(f"  H25a (test cpWER < 1.10): "
          f"{'SUPPORTED' if h25a_supported else 'KILLED'}  "
          f"(test cpWER={test_cpwer:.4f}, CI=[{test_ci[0]:.4f}, {test_ci[1]:.4f}])")
    print(f"  H25b (test sensitivity > 80%): "
          f"{'SUPPORTED' if h25b_supported else 'KILLED'}  "
          f"(test sens={test_sens:.4f}, TP={test_eval['tp']}/18)")
    print(f"  H25c (train threshold in [0.327, 0.491]): "
          f"{'SUPPORTED' if h25c_supported else 'KILLED'}  "
          f"(train thr={train_cal['threshold']:.4f})")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
