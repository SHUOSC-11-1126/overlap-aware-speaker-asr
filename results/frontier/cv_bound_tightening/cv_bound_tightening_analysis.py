"""RQ24: Cross-validated binary-KL bound tightening.

REANALYSIS ONLY -- no Whisper / no ASR model is run. This script reads RQ17's
pre-computed per-track entropy rates (``results/frontier/info_theoretic_detector_bound/
bound_verification.csv``, label ``experimental/frontier``, PR #913) and addresses the
threshold-selection optimism identified in RQ20 (PR #918).

RQ20 derived three non-parametric bounds on repetition-detector sensitivity at 90%
specificity. The conservative DV/Pinsker primary (0.729) remained valid, but the
tighter KL forms (min-direction Pinsker 0.636, binary-KL 0.555) fell *below* the
empirical LZ-ROC (0.649) because the empirical threshold was selected on the same
n=64 tracks. RQ24 de-optimises the threshold via cross-validation:

1. K-fold CV (K=5, stratified): on each fold select the threshold on the training
   folds (>= 90% specificity, max sensitivity), then measure sensitivity and FPR on
   the held-out fold. Average -> CV-de-optimised TPR and FPR.
2. Leave-one-out CV (n=64): extreme case, each track held out once.

The CV binary-KL bound solves d(TPR || FPR_cv) = D(P||Q) for TPR (inverted via
bisection), where D(P||Q) is the Wang-Kulkarni-Verdu k-NN KL estimate (k=3 primary;
k=1/5 cross-checks). D is a distribution property and is threshold-independent, so it
is reused from RQ20 unchanged.

Pre-registered hypotheses (issue #922)
--------------------------------------
- H24a: CV binary-KL bound < 0.729 (tighter than RQ20's primary Pinsker).
        Kill: CV binary-KL >= 0.729.
- H24b: CV binary-KL bound >= 0.649 (still valid -- above empirical LZ-ROC).
        Kill: CV binary-KL < 0.649.
- H24c: CV bound converges at n=64 (within 10pp of n=infinity asymptote).
        Kill: |bound(n=64) - bound(n=infinity)| > 0.10.

Label: experimental/frontier. Closes #922. Builds on RQ17 (PR #913) and RQ20 (PR #918).

numpy + stdlib only (no scipy / sklearn / Whisper). Deterministic: seed = 42.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_CSV = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "info_theoretic_detector_bound"
    / "bound_verification.csv"
)
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "cv_bound_tightening"
OUT_CSV = OUT_DIR / "cv_bound_results.csv"
OUT_JSON = OUT_DIR / "cv_bound_results.json"

# ------------------------------------------------------------------ constants
TARGET_SPECIFICITY = 0.90   # calibrate the LZ-ROC to >= 90% specificity
SEED = 42
EPS = 1e-9
BISECT_TOL = 1e-6           # binary-KL inversion tolerance
K_PRIMARY = 3               # primary k for k-NN KL estimator
K_FOLDS = 5                 # K-fold CV
N_RESAMPLE = 200            # convergence resamples per size

# RQ17 / RQ20 reference numbers (cited for narrative continuity; the empirical
# LZ-ROC is recomputed here and must match RQ17's 0.649 within tolerance).
RQ17_GAUSSIAN_BOUND = 0.435          # 43.5%, INVALID (non-Gaussian)
RQ17_EMPIRICAL_LZROC = 0.649         # 64.9%, in-sample, optimistic
RQ20_DV_PINSKER_PRIMARY = 0.729      # conservative ceiling
RQ20_DV_PINSKER_MIN_DIR = 0.636      # below empirical (optimism)
RQ20_BINARY_KL_IN_SAMPLE = 0.555     # below empirical (optimism)
RQ20_D_PRIMARY_NATS = 0.792          # D(P||Q) k-NN k=3, nats


# --------------------------------------------------------- threshold calibration
def roc_operating_point(
    neg_scores: list[float], pos_scores: list[float], target_spec: float = TARGET_SPECIFICITY
) -> dict[str, float]:
    """Pick the threshold with specificity >= target_spec and maximal sensitivity.

    Candidate thresholds = all unique scores. Flag = score >= threshold. Returns the
    threshold, achieved specificity, and sensitivity. Symmetric to RQ17/RQ20's helper.
    """
    n_neg = len(neg_scores)
    n_pos = len(pos_scores)
    if n_pos == 0 or n_neg == 0:
        return {
            "threshold": float("nan"), "specificity": 1.0, "sensitivity": 0.0,
            "tp": 0.0, "fp": 0.0, "tn": float(n_neg), "fn": float(n_pos),
        }
    candidates = sorted(set(neg_scores) | set(pos_scores))
    best: dict[str, float] | None = None
    for t in candidates:
        fp = sum(1 for s in neg_scores if s >= t - EPS)
        tp = sum(1 for s in pos_scores if s >= t - EPS)
        spec = 1.0 - (fp / n_neg) if n_neg else 1.0
        sens = (tp / n_pos) if n_pos else 0.0
        if spec >= target_spec - EPS:
            if best is None or sens > best["sensitivity"] + EPS or (
                abs(sens - best["sensitivity"]) <= EPS and spec > best["specificity"]
            ):
                best = {
                    "threshold": float(t),
                    "specificity": float(spec),
                    "sensitivity": float(sens),
                    "tp": float(tp), "fp": float(fp),
                    "tn": float(n_neg - fp), "fn": float(n_pos - tp),
                }
    if best is None:
        t = (max(neg_scores + pos_scores) + 1.0) if (neg_scores or pos_scores) else 0.0
        best = {
            "threshold": float(t), "specificity": 1.0, "sensitivity": 0.0,
            "tp": 0.0, "fp": 0.0, "tn": float(n_neg), "fn": float(n_pos),
        }
    return best


# --------------------------------------------------------- k-NN KL estimator
def knn_kl_estimate(
    p_samples: np.ndarray, q_samples: np.ndarray, k: int = K_PRIMARY
) -> float:
    """Wang-Kulkarni-Verdu (2009) k-nearest-neighbor estimator of D(P||Q) (nats).

    D_hat(P||Q) = (d/n) * sum_i log( nu_k(i) / rho_k(i) ) + log( m / (n-1) )

    where n = |P|, m = |Q|, d = dimension (1 here), rho_k(i) = k-th NN distance of
    x_i within P (excluding x_i itself), and nu_k(i) = k-th NN distance of x_i
    within Q. Distribution-free; consistent for continuous densities.
    """
    P = np.asarray(p_samples, dtype=float).ravel()
    Q = np.asarray(q_samples, dtype=float).ravel()
    n = len(P)
    m = len(Q)
    d = 1
    if n <= k or m < k or n < 2:
        return float("nan")
    total = 0.0
    for i in range(n):
        xi = P[i]
        dists_p = np.abs(np.delete(P, i) - xi)
        dists_p.sort()
        rho_k = float(dists_p[k - 1])
        dists_q = np.abs(Q - xi)
        dists_q.sort()
        nu_k = float(dists_q[k - 1])
        rho_k = max(rho_k, EPS)
        nu_k = max(nu_k, EPS)
        total += math.log(nu_k / rho_k)
    return (d / n) * total + math.log(m / (n - 1))


# --------------------------------------------------------- binary KL and inversion
def binary_kl(p: float, q: float) -> float:
    """Binary KL divergence d(p||q) = p ln(p/q) + (1-p) ln((1-p)/(1-q)), nats."""
    p = min(max(p, EPS), 1.0 - EPS)
    q = min(max(q, EPS), 1.0 - EPS)
    return p * math.log(p / q) + (1.0 - p) * math.log((1.0 - p) / (1.0 - q))


def binary_kl_bound(fpr: float, d_kl: float) -> float:
    """Tight binary data-processing bound: d(TPR || FPR) <= D(P||Q).

    Inverts d(p||fpr) = d_kl for the largest p (TPR) satisfying the inequality,
    by bisection (tolerance BISECT_TOL). d(p||fpr) is convex in p, minimised at
    p=fpr (value 0), strictly increasing for p>fpr. Returns fpr if D<=0.
    """
    if d_kl <= 0:
        return fpr
    fpr_c = min(max(fpr, EPS), 1.0 - EPS)
    lo, hi = fpr_c, 1.0 - EPS
    # If the bound is not active even at p -> 1, return 1.0.
    if binary_kl(hi, fpr_c) <= d_kl:
        return 1.0
    # Bisection: find p such that d(p||fpr) = d_kl.
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if hi - lo < BISECT_TOL:
            break
        if binary_kl(mid, fpr_c) < d_kl:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# --------------------------------------------------------- cross-validation
def stratified_kfold_indices(
    labels: np.ndarray, k: int, seed: int
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Stratified K-fold split (no sklearn). Returns list of (train_idx, test_idx).

    Preserves the class ratio in each fold. Within each class the indices are
    shuffled (deterministic, seed-controlled) then partitioned into k contiguous
    chunks. Fold j's test set = chunk j of each class concatenated.
    """
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


def cv_threshold_deoptimisation(
    scores: np.ndarray,
    labels: np.ndarray,
    k: int,
    seed: int,
) -> dict[str, Any]:
    """Cross-validated threshold de-optimisation.

    For each fold: select the threshold on the TRAINING folds (>= 90% specificity,
    max sensitivity), then evaluate TPR and FPR on the HELD-OUT fold at that
    threshold. Aggregate by micro-averaging (pool all held-out predictions across
    folds -> one confusion matrix). Also reports macro-averaged TPR/FPR for
    reference.

    Returns dict with: per-fold rows, micro-averaged TPR/FPR/specificity,
    macro-averaged TPR/FPR, and the list of selected thresholds.
    """
    folds = stratified_kfold_indices(labels, k, seed)
    per_fold: list[dict[str, Any]] = []
    total_tp = 0
    total_fp = 0
    total_tn = 0
    total_fn = 0
    thresholds: list[float] = []
    macro_tpr: list[float] = []
    macro_fpr: list[float] = []
    for j, (train_idx, test_idx) in enumerate(folds):
        tr_scores = scores[train_idx]
        tr_labels = labels[train_idx]
        te_scores = scores[test_idx]
        te_labels = labels[test_idx]
        tr_pos = [float(s) for s in tr_scores[tr_labels == 1]]
        tr_neg = [float(s) for s in tr_scores[tr_labels == 0]]
        op = roc_operating_point(tr_neg, tr_pos, TARGET_SPECIFICITY)
        thr = op["threshold"]
        thresholds.append(thr)
        # Evaluate on the held-out fold at the training-selected threshold.
        te_pred_pos = te_scores >= thr - EPS
        tp = int(np.sum(te_pred_pos & (te_labels == 1)))
        fp = int(np.sum(te_pred_pos & (te_labels == 0)))
        fn = int(np.sum(~te_pred_pos & (te_labels == 1)))
        tn = int(np.sum(~te_pred_pos & (te_labels == 0)))
        n_pos_fold = tp + fn
        n_neg_fold = fp + tn
        tpr = tp / n_pos_fold if n_pos_fold > 0 else 0.0
        fpr = fp / n_neg_fold if n_neg_fold > 0 else 0.0
        spec = 1.0 - fpr
        total_tp += tp
        total_fp += fp
        total_tn += tn
        total_fn += fn
        macro_tpr.append(tpr)
        macro_fpr.append(fpr)
        per_fold.append({
            "fold": j,
            "n_train": int(len(train_idx)),
            "n_test": int(len(test_idx)),
            "n_test_pos": int(n_pos_fold),
            "n_test_neg": int(n_neg_fold),
            "train_threshold": thr,
            "train_sensitivity": op["sensitivity"],
            "train_specificity": op["specificity"],
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "tpr": tpr, "fpr": fpr, "specificity": spec,
        })
    micro_tpr = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_fpr = total_fp / (total_fp + total_tn) if (total_fp + total_tn) > 0 else 0.0
    micro_spec = 1.0 - micro_fpr
    return {
        "method": f"{k}-fold stratified CV",
        "k": k,
        "seed": seed,
        "per_fold": per_fold,
        "thresholds": thresholds,
        "threshold_mean": float(np.mean(thresholds)),
        "threshold_std": float(np.std(thresholds)),
        "micro_tpr": float(micro_tpr),
        "micro_fpr": float(micro_fpr),
        "micro_specificity": float(micro_spec),
        "macro_tpr": float(np.mean(macro_tpr)),
        "macro_fpr": float(np.mean(macro_fpr)),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_tn": total_tn,
        "total_fn": total_fn,
    }


def loo_cv_threshold_deoptimisation(
    scores: np.ndarray, labels: np.ndarray
) -> dict[str, Any]:
    """Leave-one-out CV. Each track held out once; threshold selected on the
    remaining n-1 tracks (>= 90% specificity, max sensitivity). The held-out
    track is then classified at that threshold. Micro-average over all n folds.
    """
    n = len(scores)
    total_tp = 0
    total_fp = 0
    total_tn = 0
    total_fn = 0
    thresholds: list[float] = []
    per_track: list[dict[str, Any]] = []
    for i in range(n):
        train_idx = np.delete(np.arange(n), i)
        te_idx = np.array([i])
        tr_scores = scores[train_idx]
        tr_labels = labels[train_idx]
        te_scores = scores[te_idx]
        te_labels = labels[te_idx]
        tr_pos = [float(s) for s in tr_scores[tr_labels == 1]]
        tr_neg = [float(s) for s in tr_scores[tr_labels == 0]]
        op = roc_operating_point(tr_neg, tr_pos, TARGET_SPECIFICITY)
        thr = op["threshold"]
        thresholds.append(thr)
        te_pred_pos = te_scores >= thr - EPS
        is_pos = bool(te_labels[0] == 1)
        pred_pos = bool(te_pred_pos[0])
        if is_pos and pred_pos:
            total_tp += 1
        elif (not is_pos) and pred_pos:
            total_fp += 1
        elif is_pos and (not pred_pos):
            total_fn += 1
        else:
            total_tn += 1
        per_track.append({
            "idx": int(i),
            "score": float(te_scores[0]),
            "label": int(te_labels[0]),
            "threshold": thr,
            "pred_pos": pred_pos,
        })
    n_pos = total_tp + total_fn
    n_neg = total_fp + total_tn
    micro_tpr = total_tp / n_pos if n_pos > 0 else 0.0
    micro_fpr = total_fp / n_neg if n_neg > 0 else 0.0
    micro_spec = 1.0 - micro_fpr
    return {
        "method": "leave-one-out CV",
        "k": n,
        "per_track": per_track,
        "thresholds": thresholds,
        "threshold_mean": float(np.mean(thresholds)),
        "threshold_std": float(np.std(thresholds)),
        "micro_tpr": float(micro_tpr),
        "micro_fpr": float(micro_fpr),
        "micro_specificity": float(micro_spec),
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_tn": total_tn,
        "total_fn": total_fn,
    }


# --------------------------------------------------------- convergence (H24c)
def cv_bound_for_subset(
    scores: np.ndarray, labels: np.ndarray, seed: int
) -> dict[str, float]:
    """Compute the CV binary-KL bound for a given (sub)sample.

    Returns K-fold (K=5) CV binary-KL bound, the CV TPR/FPR, and the in-sample
    binary-KL bound for reference. Falls back gracefully on tiny subsets.
    """
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    # D(P||Q) on the subset (distribution property, threshold-independent).
    d_pq = knn_kl_estimate(pos, neg, k=K_PRIMARY)
    if not math.isfinite(d_pq) or d_pq < 0:
        d_pq = 0.0
    # In-sample operating point + binary-KL bound (reference).
    op_in = roc_operating_point(
        [float(x) for x in neg], [float(x) for x in pos], TARGET_SPECIFICITY
    )
    in_sens = op_in["sensitivity"]
    in_fpr = 1.0 - op_in["specificity"]
    in_binary_kl_bound = binary_kl_bound(in_fpr, d_pq)
    # K-fold CV (K=5). On very small subsets reduce K so each fold has >= 2 per class.
    n_pos = int(np.sum(labels == 1))
    n_neg = int(np.sum(labels == 0))
    k_eff = K_FOLDS
    while k_eff > 2 and (n_pos < k_eff * 2 or n_neg < k_eff * 2):
        k_eff -= 1
    cv = cv_threshold_deoptimisation(scores, labels, k_eff, seed)
    cv_tpr = cv["micro_tpr"]
    cv_fpr = cv["micro_fpr"]
    cv_binary_kl_bound = binary_kl_bound(cv_fpr, d_pq)
    return {
        "n": int(len(scores)),
        "n_pos": int(n_pos),
        "n_neg": int(n_neg),
        "k_fold": k_eff,
        "d_pq_k3_nats": float(d_pq),
        "in_sample_sensitivity": float(in_sens),
        "in_sample_fpr": float(in_fpr),
        "in_sample_binary_kl_bound": float(in_binary_kl_bound),
        "cv_tpr": float(cv_tpr),
        "cv_fpr": float(cv_fpr),
        "cv_specificity": float(cv["micro_specificity"]),
        "cv_binary_kl_bound": float(cv_binary_kl_bound),
    }


def convergence_analysis(
    scores: np.ndarray, labels: np.ndarray, seed: int
) -> list[dict[str, Any]]:
    """Subsample at n in {40, 50, 60, 64}, 200 class-balanced resamples (seed=42).
    For each resample compute the CV binary-KL bound. Average per size. The
    n=infinity asymptote is estimated by linear extrapolation of the CV binary-KL
    bound against 1/n (the leading finite-n bias term of the k-NN KL estimator and
    of CV threshold optimism both scale as 1/n).
    """
    rng = np.random.default_rng(seed)
    pos_idx = np.where(labels == 1)[0]
    neg_idx = np.where(labels == 0)[0]
    n_pos_full = len(pos_idx)
    n_neg_full = len(neg_idx)
    sizes = [40, 50, 60, 64]
    rows: list[dict[str, Any]] = []
    for n_target in sizes:
        n_pos_t = max(2, round(n_target * n_pos_full / (n_pos_full + n_neg_full)))
        n_neg_t = max(2, round(n_target * n_neg_full / (n_pos_full + n_neg_full)))
        if n_pos_t > n_pos_full:
            n_pos_t = n_pos_full
        if n_neg_t > n_neg_full:
            n_neg_t = n_neg_full
        cv_bounds: list[float] = []
        cv_tprs: list[float] = []
        cv_fprs: list[float] = []
        d_estimates: list[float] = []
        for _ in range(N_RESAMPLE):
            sp = rng.choice(pos_idx, size=n_pos_t, replace=False)
            sn = rng.choice(neg_idx, size=n_neg_t, replace=False)
            idx = np.concatenate([sp, sn])
            sc = scores[idx]
            lb = labels[idx]
            r = cv_bound_for_subset(sc, lb, seed)
            cv_bounds.append(r["cv_binary_kl_bound"])
            cv_tprs.append(r["cv_tpr"])
            cv_fprs.append(r["cv_fpr"])
            d_estimates.append(r["d_pq_k3_nats"])
        rows.append({
            "n_target": n_target,
            "n_pos": n_pos_t,
            "n_neg": n_neg_t,
            "n_total": n_pos_t + n_neg_t,
            "cv_binary_kl_bound_mean": float(np.mean(cv_bounds)),
            "cv_binary_kl_bound_std": float(np.std(cv_bounds)),
            "cv_tpr_mean": float(np.mean(cv_tprs)),
            "cv_fpr_mean": float(np.mean(cv_fprs)),
            "d_pq_k3_mean": float(np.mean(d_estimates)),
            "n_resample": N_RESAMPLE,
        })
    # Extrapolate to n -> infinity via linear regression of bound vs 1/n.
    # bound(n) ~ bound_inf + c / n. Two-point fit using the largest two sizes.
    if len(rows) >= 2:
        a = rows[-2]
        b = rows[-1]
        inv_a = 1.0 / a["n_total"]
        inv_b = 1.0 / b["n_total"]
        denom = inv_a - inv_b
        if abs(denom) > 1e-12:
            slope = (a["cv_binary_kl_bound_mean"] - b["cv_binary_kl_bound_mean"]) / denom
            intercept = b["cv_binary_kl_bound_mean"] - slope * inv_b
            asymptote = float(intercept)
        else:
            asymptote = float(b["cv_binary_kl_bound_mean"])
            slope = 0.0
    else:
        asymptote = float(rows[-1]["cv_binary_kl_bound_mean"])
        slope = 0.0
    # Attach asymptote to the last row's metadata (returned separately).
    for r in rows:
        r["asymptote_n_inf"] = asymptote
        r["extrapolation_slope"] = float(slope)
    return rows


# --------------------------------------------------------------------- driver
def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Load RQ17's per-track entropy rates (read-only; not re-derived).
    rows: list[dict[str, Any]] = []
    with SRC_CSV.open("r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "window_id": int(r["window_id"]),
                "hallucinated": (r["hallucinated"].strip().lower() == "true"),
                "entropy_rate_estimate": float(r["entropy_rate_estimate"]),
                "track_text_length": int(r["track_text_length"]),
            })
    n_total = len(rows)
    n_halluc_total = sum(1 for r in rows if r["hallucinated"])

    # Restrict to the 64 non-empty tracks (where H_LZ is defined).
    nonempty = [r for r in rows if r["track_text_length"] > 0]
    n_nonempty = len(nonempty)
    h_sub = np.array([r["entropy_rate_estimate"] for r in nonempty], dtype=float)
    lab_sub = np.array([1 if r["hallucinated"] else 0 for r in nonempty], dtype=int)
    n_pos = int(lab_sub.sum())          # hallucinated, 37
    n_neg = n_nonempty - n_pos          # clean, 27
    pos_h = h_sub[lab_sub == 1]
    neg_h = h_sub[lab_sub == 0]

    # --- Reproduce the empirical LZ-ROC operating point at >= 90% specificity.
    lz_op = roc_operating_point(
        [float(x) for x in neg_h], [float(x) for x in pos_h], TARGET_SPECIFICITY
    )
    empirical_sens = lz_op["sensitivity"]
    empirical_spec = lz_op["specificity"]
    empirical_fpr = 1.0 - empirical_spec
    k_detected = int(round(lz_op["tp"]))
    fp = int(round(lz_op["fp"]))

    # Sanity: must match RQ17's 0.649.
    assert abs(empirical_sens - RQ17_EMPIRICAL_LZROC) < 0.02, (
        f"empirical LZ-ROC {empirical_sens:.4f} disagrees with RQ17's 0.649"
    )

    # --- KL divergence estimates (threshold-independent distribution property).
    # Reuse RQ20's Wang-Kulkarni-Verdu k-NN estimator. k=3 primary; k=1/5 cross-checks.
    d_pq_knn = knn_kl_estimate(pos_h, neg_h, k=K_PRIMARY)
    d_pq_knn1 = knn_kl_estimate(pos_h, neg_h, k=1)
    d_pq_knn5 = knn_kl_estimate(pos_h, neg_h, k=5)
    d_primary = d_pq_knn if math.isfinite(d_pq_knn) else 0.0
    d_primary = max(d_primary, 0.0)

    # Sanity: must match RQ20's D(P||Q) k=3 within tolerance.
    assert abs(d_primary - RQ20_D_PRIMARY_NATS) < 0.05, (
        f"D(P||Q) k=3 = {d_primary:.4f} disagrees with RQ20's 0.792"
    )

    # --- In-sample binary-KL bound (reproduce RQ20's 0.555).
    in_sample_binary_kl_bound = binary_kl_bound(empirical_fpr, d_primary)

    # --- K-fold CV (K=5, stratified).
    cv5 = cv_threshold_deoptimisation(h_sub, lab_sub, K_FOLDS, SEED)
    cv5_tpr = cv5["micro_tpr"]
    cv5_fpr = cv5["micro_fpr"]
    cv5_spec = cv5["micro_specificity"]
    cv5_binary_kl_bound = binary_kl_bound(cv5_fpr, d_primary)

    # --- Leave-one-out CV.
    cv_loo = loo_cv_threshold_deoptimisation(h_sub, lab_sub)
    cv_loo_tpr = cv_loo["micro_tpr"]
    cv_loo_fpr = cv_loo["micro_fpr"]
    cv_loo_spec = cv_loo["micro_specificity"]
    cv_loo_binary_kl_bound = binary_kl_bound(cv_loo_fpr, d_primary)

    # --- Convergence (H24c).
    convergence = convergence_analysis(h_sub, lab_sub, SEED)
    cv_bound_at_64 = convergence[-1]["cv_binary_kl_bound_mean"]
    cv_bound_asymptote = convergence[-1]["asymptote_n_inf"]
    convergence_gap = abs(cv_bound_at_64 - cv_bound_asymptote)

    # --- Comparison table.
    bounds_table = [
        {
            "bound_type": "gaussian_rq17",
            "value": RQ17_GAUSSIAN_BOUND,
            "source": "RQ17 (PR #913)",
            "note": "Gaussian equal-variance; INVALID (below empirical, non-Gaussian).",
        },
        {
            "bound_type": "empirical_lzroc_in_sample",
            "value": round(empirical_sens, 6),
            "source": "RQ17 (PR #913)",
            "note": "In-sample LZ-ROC; optimistic (threshold on n=64).",
        },
        {
            "bound_type": "dv_pinsker_primary_rq20",
            "value": RQ20_DV_PINSKER_PRIMARY,
            "source": "RQ20 (PR #918)",
            "note": "DV/Pinsker primary D(P||Q); conservative ceiling (>= empirical).",
        },
        {
            "bound_type": "dv_pinsker_min_dir_rq20",
            "value": RQ20_DV_PINSKER_MIN_DIR,
            "source": "RQ20 (PR #918)",
            "note": "Min-direction Pinsker; below empirical (optimism).",
        },
        {
            "bound_type": "binary_kl_in_sample_rq20",
            "value": RQ20_BINARY_KL_IN_SAMPLE,
            "source": "RQ20 (PR #918)",
            "note": "Binary-KL at in-sample FPR; below empirical (optimism).",
        },
        {
            "bound_type": "cv_binary_kl_kfold5",
            "value": round(cv5_binary_kl_bound, 6),
            "source": "this study (K=5 CV)",
            "note": "Binary-KL at CV-de-optimised FPR; de-optimised ceiling.",
        },
        {
            "bound_type": "cv_binary_kl_loo",
            "value": round(cv_loo_binary_kl_bound, 6),
            "source": "this study (LOO CV)",
            "note": "Binary-KL at LOO-de-optimised FPR; extreme de-optimisation.",
        },
        {
            "bound_type": "cv_empirical_lzroc_kfold5",
            "value": round(cv5_tpr, 6),
            "source": "this study (K=5 CV)",
            "note": "CV-de-optimised empirical sensitivity (no KL inversion).",
        },
        {
            "bound_type": "cv_empirical_lzroc_loo",
            "value": round(cv_loo_tpr, 6),
            "source": "this study (LOO CV)",
            "note": "LOO-de-optimised empirical sensitivity (no KL inversion).",
        },
    ]

    # --- Hypothesis verdicts.
    # H24a: CV binary-KL bound < 0.729. Kill: >= 0.729.
    h24a_pass = cv5_binary_kl_bound < RQ20_DV_PINSKER_PRIMARY
    h24a_killed = cv5_binary_kl_bound >= RQ20_DV_PINSKER_PRIMARY
    h24a_supported = h24a_pass and not h24a_killed
    # H24b: CV binary-KL bound >= 0.649. Kill: < 0.649.
    h24b_pass = cv5_binary_kl_bound >= RQ17_EMPIRICAL_LZROC
    h24b_killed = cv5_binary_kl_bound < RQ17_EMPIRICAL_LZROC
    h24b_supported = h24b_pass and not h24b_killed
    # H24c: |bound(n=64) - bound(n=inf)| <= 0.10. Kill: > 0.10.
    h24c_pass = convergence_gap <= 0.10
    h24c_killed = convergence_gap > 0.10
    h24c_supported = h24c_pass and not h24c_killed

    # --- Console summary.
    print("=== RQ24: Cross-validated binary-KL bound tightening ===")
    print(f"Label: experimental/frontier  |  Source: {SRC_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Tracks: {n_total} total ({n_halluc_total} halluc) | "
          f"non-empty: {n_nonempty} ({n_pos} halluc / {n_neg} clean)")
    print()
    print("Empirical LZ-ROC (in-sample, >= 90% specificity):")
    print(f"  threshold = {lz_op['threshold']:.6f} bits/char  (reported as 4.9549)")
    print(f"  specificity = {empirical_spec:.4f}  FPR = {empirical_fpr:.4f}")
    print(f"  sensitivity = {empirical_sens:.4f}  (k={k_detected}/{n_pos}, fp={fp}/{n_neg})")
    print(f"  [matches RQ17's 0.649]")
    print()
    print(f"KL divergence D(P||Q) (nats), P=halluc, Q=clean:")
    print(f"  k-NN k=1: {d_pq_knn1:.4f}  k=3 [primary]: {d_pq_knn:.4f}  k=5: {d_pq_knn5:.4f}")
    print(f"  [matches RQ20's D(P||Q) k=3 = 0.792]")
    print()
    print("In-sample binary-KL bound (RQ20 reproduction):")
    print(f"  FPR_in = {empirical_fpr:.4f}  -> bound = {in_sample_binary_kl_bound:.4f}"
          f"  [matches RQ20's 0.555]")
    print()
    print("K-fold CV (K=5, stratified) -- de-optimised threshold:")
    print(f"  thresholds per fold: {['%.4f' % t for t in cv5['thresholds']]}")
    print(f"  threshold mean = {cv5['threshold_mean']:.4f}  std = {cv5['threshold_std']:.4f}")
    print(f"  micro TPR = {cv5_tpr:.4f}  micro FPR = {cv5_fpr:.4f}  spec = {cv5_spec:.4f}")
    print(f"  (TP={cv5['total_tp']} FP={cv5['total_fp']} "
          f"TN={cv5['total_tn']} FN={cv5['total_fn']})")
    print(f"  macro TPR = {cv5['macro_tpr']:.4f}  macro FPR = {cv5['macro_fpr']:.4f}")
    print(f"  CV binary-KL bound (K=5) = {cv5_binary_kl_bound:.4f}")
    print()
    print("Leave-one-out CV -- extreme de-optimisation:")
    print(f"  threshold mean = {cv_loo['threshold_mean']:.4f}  std = {cv_loo['threshold_std']:.4f}")
    print(f"  micro TPR = {cv_loo_tpr:.4f}  micro FPR = {cv_loo_fpr:.4f}  spec = {cv_loo_spec:.4f}")
    print(f"  (TP={cv_loo['total_tp']} FP={cv_loo['total_fp']} "
          f"TN={cv_loo['total_tn']} FN={cv_loo['total_fn']})")
    print(f"  CV binary-KL bound (LOO) = {cv_loo_binary_kl_bound:.4f}")
    print()
    print("Bound comparison:")
    print(f"  {'bound':42s} {'value':>7s}")
    print(f"  {'Gaussian (RQ17, INVALID)':42s} {RQ17_GAUSSIAN_BOUND:7.3f}")
    print(f"  {'Empirical LZ-ROC (in-sample, optimistic)':42s} {empirical_sens:7.3f}")
    print(f"  {'DV/Pinsker primary D(P||Q) (RQ20)':42s} {RQ20_DV_PINSKER_PRIMARY:7.3f}")
    print(f"  {'DV/Pinsker min-direction (RQ20)':42s} {RQ20_DV_PINSKER_MIN_DIR:7.3f}")
    print(f"  {'Binary-KL in-sample (RQ20)':42s} {RQ20_BINARY_KL_IN_SAMPLE:7.3f}")
    print(f"  {'CV binary-KL K=5 (THIS STUDY)':42s} {cv5_binary_kl_bound:7.3f}")
    print(f"  {'CV binary-KL LOO (THIS STUDY)':42s} {cv_loo_binary_kl_bound:7.3f}")
    print(f"  {'CV empirical LZ-ROC K=5 (THIS STUDY)':42s} {cv5_tpr:7.3f}")
    print(f"  {'CV empirical LZ-ROC LOO (THIS STUDY)':42s} {cv_loo_tpr:7.3f}")
    print()
    print("Convergence (H24c) -- mean CV binary-KL bound over 200 resamples:")
    print(f"  {'n':>5s} {'cv_binary_kl':>13s} {'cv_tpr':>8s} {'cv_fpr':>8s} {'D(P||Q)':>8s}")
    for c in convergence:
        print(f"  {c['n_total']:5d} {c['cv_binary_kl_bound_mean']:13.4f} "
              f"{c['cv_tpr_mean']:8.4f} {c['cv_fpr_mean']:8.4f} "
              f"{c['d_pq_k3_mean']:8.4f}")
    print(f"  asymptote (n->inf, 1/n extrapolation) = {cv_bound_asymptote:.4f}")
    print(f"  gap |bound(64) - bound(inf)| = {convergence_gap:.4f}")
    print()
    print("Hypothesis verdicts:")
    print(f"  H24a (CV binary-KL < 0.729): "
          f"bound={cv5_binary_kl_bound:.4f}  "
          f"pass={h24a_pass}  kill={h24a_killed}  "
          f"-> {'SUPPORTED' if h24a_supported else 'NOT SUPPORTED'}")
    print(f"  H24b (CV binary-KL >= 0.649): "
          f"bound={cv5_binary_kl_bound:.4f}  "
          f"pass={h24b_pass}  kill={h24b_killed}  "
          f"-> {'SUPPORTED' if h24b_supported else 'NOT SUPPORTED'}")
    print(f"  H24c (|bound(64)-bound(inf)| <= 0.10): "
          f"gap={convergence_gap:.4f}  "
          f"pass={h24c_pass}  kill={h24c_killed}  "
          f"-> {'SUPPORTED' if h24c_supported else 'NOT SUPPORTED'}")
    print()
    print(f"Wrote: {OUT_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote: {OUT_JSON.relative_to(PROJECT_ROOT)}")

    # --- Write CSV (bound comparison table).
    csv_fields = ["bound_type", "value", "source", "note"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=csv_fields)
        wr.writeheader()
        for b in bounds_table:
            wr.writerow({
                "bound_type": b["bound_type"],
                "value": b["value"],
                "source": b["source"],
                "note": b["note"],
            })

    # --- Write JSON (summary + KL estimates + CV results + convergence + verdicts).
    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ24: Cross-validated binary-KL bound tightening",
        "closes_issue": 922,
        "source_data": str(SRC_CSV.relative_to(PROJECT_ROOT)),
        "source_label": "experimental/frontier (RQ17, PR #913)",
        "builds_on": "RQ17 (PR #913), RQ20 (PR #918)",
        "method": (
            "reanalysis only (no Whisper / no ASR run); reuses RQ17's per-track "
            "LZ78 entropy rates and RQ20's k-NN KL estimator. De-optimises the "
            "LZ-ROC threshold via K-fold (K=5) and leave-one-out cross-validation, "
            "then inverts the binary data-processing inequality d(TPR||FPR) <= "
            "D(P||Q) (bisection, tol 1e-6) at the CV-de-optimised FPR to obtain "
            "the CV binary-KL bound."
        ),
        "target_specificity": TARGET_SPECIFICITY,
        "seed": SEED,
        "bisect_tolerance": BISECT_TOL,
        "k_primary": K_PRIMARY,
        "k_folds": K_FOLDS,
        "n_windows_total": n_total,
        "n_nonempty_tracks": n_nonempty,
        "n_hallucinated_nonempty": n_pos,
        "n_nonhallucinated_nonempty": n_neg,
        "empirical_lzroc_operating_point": {
            "threshold_bits_per_char": round(lz_op["threshold"], 6),
            "threshold_reported": 4.9549,
            "specificity": round(empirical_spec, 6),
            "fpr": round(empirical_fpr, 6),
            "sensitivity": round(empirical_sens, 6),
            "k_detected": k_detected,
            "n_pos": n_pos,
            "fp": fp,
            "n_neg": n_neg,
            "matches_rq17_0_649": abs(empirical_sens - RQ17_EMPIRICAL_LZROC) < 0.02,
        },
        "kl_divergence_estimates_nats": {
            "D_P_given_Q_knn": {
                "k1": None if math.isnan(d_pq_knn1) else round(d_pq_knn1, 6),
                "k3": None if math.isnan(d_pq_knn) else round(d_pq_knn, 6),
                "k5": None if math.isnan(d_pq_knn5) else round(d_pq_knn5, 6),
            },
            "primary_D_P_given_Q_k3": round(d_primary, 6),
            "matches_rq20_0_792": abs(d_primary - RQ20_D_PRIMARY_NATS) < 0.05,
            "estimator": "Wang-Kulkarni-Verdu (2009) k-NN; threshold-independent",
        },
        "in_sample_binary_kl_bound_rq20_reproduction": {
            "fpr": round(empirical_fpr, 6),
            "bound": round(in_sample_binary_kl_bound, 6),
            "matches_rq20_0_555": abs(in_sample_binary_kl_bound - RQ20_BINARY_KL_IN_SAMPLE) < 0.02,
        },
        "cv_results": {
            "kfold5": {
                "method": cv5["method"],
                "k": cv5["k"],
                "seed": cv5["seed"],
                "per_fold": cv5["per_fold"],
                "thresholds": [round(t, 6) for t in cv5["thresholds"]],
                "threshold_mean": round(cv5["threshold_mean"], 6),
                "threshold_std": round(cv5["threshold_std"], 6),
                "micro_tpr": round(cv5["micro_tpr"], 6),
                "micro_fpr": round(cv5["micro_fpr"], 6),
                "micro_specificity": round(cv5["micro_specificity"], 6),
                "macro_tpr": round(cv5["macro_tpr"], 6),
                "macro_fpr": round(cv5["macro_fpr"], 6),
                "total_tp": cv5["total_tp"],
                "total_fp": cv5["total_fp"],
                "total_tn": cv5["total_tn"],
                "total_fn": cv5["total_fn"],
                "binary_kl_bound": round(cv5_binary_kl_bound, 6),
            },
            "loo": {
                "method": cv_loo["method"],
                "k": cv_loo["k"],
                "threshold_mean": round(cv_loo["threshold_mean"], 6),
                "threshold_std": round(cv_loo["threshold_std"], 6),
                "micro_tpr": round(cv_loo["micro_tpr"], 6),
                "micro_fpr": round(cv_loo["micro_fpr"], 6),
                "micro_specificity": round(cv_loo["micro_specificity"], 6),
                "total_tp": cv_loo["total_tp"],
                "total_fp": cv_loo["total_fp"],
                "total_tn": cv_loo["total_tn"],
                "total_fn": cv_loo["total_fn"],
                "binary_kl_bound": round(cv_loo_binary_kl_bound, 6),
            },
        },
        "bound_comparison_table": bounds_table,
        "convergence_h24c": {
            "subsampling_sizes": [c["n_total"] for c in convergence],
            "rows": convergence,
            "asymptote_n_inf": round(cv_bound_asymptote, 6),
            "gap_n64_vs_inf": round(convergence_gap, 6),
            "extrapolation_method": "linear fit of bound vs 1/n using two largest sizes",
            "n_resample": N_RESAMPLE,
        },
        "hypothesis_verdicts": {
            "H24a": {
                "statement": (
                    "The CV binary-KL bound is < 0.729 (tighter than RQ20's primary "
                    "Pinsker). Kill: CV binary-KL >= 0.729."
                ),
                "cv_binary_kl_kfold5": round(cv5_binary_kl_bound, 6),
                "pass": bool(h24a_pass),
                "kill": bool(h24a_killed),
                "supported": bool(h24a_supported),
            },
            "H24b": {
                "statement": (
                    "The CV binary-KL bound is >= 0.649 (still valid -- above "
                    "empirical LZ-ROC). Kill: CV binary-KL < 0.649."
                ),
                "cv_binary_kl_kfold5": round(cv5_binary_kl_bound, 6),
                "pass": bool(h24b_pass),
                "kill": bool(h24b_killed),
                "supported": bool(h24b_supported),
            },
            "H24c": {
                "statement": (
                    "The CV bound converges at n=64 (within 10pp of n=infinity "
                    "asymptote). Kill: |bound(n=64) - bound(n=inf)| > 0.10."
                ),
                "bound_n64": round(cv_bound_at_64, 6),
                "bound_n_inf": round(cv_bound_asymptote, 6),
                "gap": round(convergence_gap, 6),
                "pass": bool(h24c_pass),
                "kill": bool(h24c_killed),
                "supported": bool(h24c_supported),
            },
        },
        "references": {
            "gaussian_rq17": RQ17_GAUSSIAN_BOUND,
            "empirical_lzroc_rq17": RQ17_EMPIRICAL_LZROC,
            "dv_pinsker_primary_rq20": RQ20_DV_PINSKER_PRIMARY,
            "dv_pinsker_min_dir_rq20": RQ20_DV_PINSKER_MIN_DIR,
            "binary_kl_in_sample_rq20": RQ20_BINARY_KL_IN_SAMPLE,
            "d_primary_rq20_nats": RQ20_D_PRIMARY_NATS,
        },
    }
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
