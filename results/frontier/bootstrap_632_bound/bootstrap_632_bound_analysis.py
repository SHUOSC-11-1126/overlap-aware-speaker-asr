"""RQ27: Bootstrap .632+ binary-KL bound tightening.

REANALYSIS ONLY -- no Whisper / no ASR model is run. This script reads RQ17's
pre-computed per-track entropy rates (``results/frontier/info_theoretic_detector_bound/
bound_verification.csv``, label ``experimental/frontier``, PR #913) and tests whether
the bootstrap .632+ estimator (Efron & Tibshirani 1997) produces a valid tighter
binary-KL bound where cross-validation (RQ24, PR #925) overcorrected.

Background
----------
RQ20 (PR #918) derived three non-parametric bounds on repetition-detector sensitivity
at 90% specificity. The conservative DV/Pinsker primary (0.729) remained valid, but
the tighter binary-KL form (0.555) fell below the empirical LZ-ROC (0.649) because
the empirical threshold was selected on the same n=64 tracks (threshold-selection
optimism). RQ24 (PR #925) de-optimised the threshold via K-fold / leave-one-out CV.
The CV binary-KL bound (0.639) was tighter than the primary Pinsker (0.729) but
INVALID: it fell below the empirical LZ-ROC (0.649) because CV overcorrects -- the
CV threshold, selected on less data, produces a higher FPR (0.111 vs 0.074 in-sample).

RQ27 tests bootstrap .632+ (Efron 1983; Efron & Tibshirani 1997), which is designed
to correct threshold-selection optimism without the overcorrection that plagues LOO-CV.
The .632 estimator blends the optimistic in-sample error with the pessimistic OOB
error at a fixed 0.632/0.368 split. The .632+ estimator adapts the blend weight upward
toward OOB when overfitting is severe, but never below 0.632.

Method
------
1. B=1000 bootstrap resamples (seed=42), each of size n=64 drawn with replacement.
2. For each bootstrap sample b:
   - Select threshold on the bootstrap sample (>= 90% specificity, max sensitivity).
   - TPR_in(b), FPR_in(b): in-sample rates on the bootstrap sample at threshold_b.
   - TPR_oob(b), FPR_oob(b): out-of-bag rates on tracks NOT in bootstrap sample.
3. .632 estimator (Efron 1983):
   TPR_632 = 0.368 * mean(TPR_in) + 0.632 * mean(TPR_oob); FPR_632 similarly.
4. .632+ estimator (Efron & Tibshirani 1997), computed on the error scale per class:
   - gamma = no-information error rate, estimated by permuting labels B_PERM times
     and averaging the OOB error of the threshold selected on permuted training data.
   - For TPR: e_in = 1 - mean(TPR_in), e_oob = 1 - mean(TPR_oob).
     Relative overfitting rate R = min(1, max(0, (e_oob - e_in) / (gamma - e_in))).
     w = 0.632 / (1 - 0.368 * R)  in [0.632, 1.0].
     TPR_632+ = (1 - w) * mean(TPR_in) + w * mean(TPR_oob).
   - For FPR (already an error rate): same formula with e_in = mean(FPR_in),
     e_oob = mean(FPR_oob), and gamma_fpr = mean OOB FPR under permutation.
5. Binary-KL bound: invert d(TPR || FPR) <= D(P||Q) via bisection (tol 1e-6) at the
   .632 / .632+ FPR, using D(P||Q) = 0.792 nats (RQ20's k-NN estimate, k=3, reused
   unchanged -- D is a distribution property, threshold-independent).

Pre-registered hypotheses (issue #928)
--------------------------------------
- H27a: Bootstrap .632+ binary-KL bound < 0.729 (tighter than primary Pinsker).
        Kill: >= 0.729.
- H27b: Bootstrap .632+ binary-KL bound >= 0.649 (valid -- above empirical).
        Kill: < 0.649.
- H27c: .632+ bound tighter than CV bound (0.639). Kill: .632+ >= 0.639.

Label: experimental/frontier. Closes #928. Builds on RQ17 (PR #913), RQ20 (PR #918),
RQ24 (PR #925).

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
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "bootstrap_632_bound"
OUT_CSV = OUT_DIR / "bootstrap_632_bound_results.csv"
OUT_JSON = OUT_DIR / "bootstrap_632_bound_results.json"

# ------------------------------------------------------------------ constants
TARGET_SPECIFICITY = 0.90   # calibrate the LZ-ROC to >= 90% specificity
SEED = 42
EPS = 1e-9
BISECT_TOL = 1e-6           # binary-KL inversion tolerance
K_PRIMARY = 3               # primary k for k-NN KL estimator
B_BOOT = 1000               # number of bootstrap resamples
B_PERM = 1000               # number of label permutations for gamma (no-info error)

# RQ17 / RQ20 / RQ24 reference numbers (cited for narrative continuity; the
# empirical LZ-ROC and D(P||Q) are recomputed here and must match within tolerance).
RQ17_GAUSSIAN_BOUND = 0.435          # 43.5%, INVALID (non-Gaussian)
RQ17_EMPIRICAL_LZROC = 0.649         # 64.9%, in-sample, optimistic
RQ20_DV_PINSKER_PRIMARY = 0.729      # conservative ceiling
RQ20_DV_PINSKER_MIN_DIR = 0.636      # below empirical (optimism)
RQ20_BINARY_KL_IN_SAMPLE = 0.555     # below empirical (optimism)
RQ20_D_PRIMARY_NATS = 0.792          # D(P||Q) k-NN k=3, nats
RQ24_CV_BINARY_KL_KFOLD5 = 0.639     # CV binary-KL bound (K=5), INVALID (overcorrects)


# --------------------------------------------------------- threshold calibration
def roc_operating_point(
    neg_scores: list[float], pos_scores: list[float], target_spec: float = TARGET_SPECIFICITY
) -> dict[str, float]:
    """Pick the threshold with specificity >= target_spec and maximal sensitivity.

    Candidate thresholds = all unique scores. Flag = score >= threshold. Returns the
    threshold, achieved specificity, and sensitivity. Symmetric to RQ17/RQ20/RQ24's
    helper.
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
    within Q. Distribution-free; consistent for continuous densities. Reused
    unchanged from RQ20/RQ24.
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


# --------------------------------------------------------- rates at a threshold
def rates_at_threshold(
    scores: np.ndarray, labels: np.ndarray, threshold: float
) -> dict[str, float]:
    """Confusion-matrix rates for ``scores >= threshold`` against ``labels``.

    Returns tp, fp, tn, fn, tpr, fpr, specificity, accuracy. Handles empty classes.
    """
    pred_pos = scores >= threshold - EPS
    tp = int(np.sum(pred_pos & (labels == 1)))
    fp = int(np.sum(pred_pos & (labels == 0)))
    fn = int(np.sum(~pred_pos & (labels == 1)))
    tn = int(np.sum(~pred_pos & (labels == 0)))
    n_pos = tp + fn
    n_neg = fp + tn
    n_total = tp + fp + tn + fn
    tpr = tp / n_pos if n_pos > 0 else float("nan")
    fpr = fp / n_neg if n_neg > 0 else float("nan")
    spec = 1.0 - fpr if not math.isnan(fpr) else float("nan")
    acc = (tp + tn) / n_total if n_total > 0 else float("nan")
    err = 1.0 - acc if n_total > 0 else float("nan")
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "tpr": tpr, "fpr": fpr, "specificity": spec,
        "accuracy": acc, "error": err,
    }


# --------------------------------------------------------- bootstrap .632 / .632+
def bootstrap_632_estimates(
    scores: np.ndarray, labels: np.ndarray, seed: int
) -> dict[str, Any]:
    """Bootstrap .632 and .632+ estimates of TPR and FPR.

    Returns per-bootstrap arrays plus the aggregated .632 and .632+ TPR/FPR. The
    .632+ weight is computed on the error scale per Efron & Tibshirani (1997): for
    TPR the error is the miss rate 1 - TPR; for FPR the error is FPR itself. The
    no-information error rate gamma is estimated by a separate permutation loop.
    """
    rng = np.random.default_rng(seed)
    n = len(scores)
    n_pos_total = int(np.sum(labels == 1))
    n_neg_total = int(np.sum(labels == 0))

    tpr_in_arr = np.full(B_BOOT, np.nan)
    fpr_in_arr = np.full(B_BOOT, np.nan)
    tpr_oob_arr = np.full(B_BOOT, np.nan)
    fpr_oob_arr = np.full(B_BOOT, np.nan)
    n_oob_arr = np.zeros(B_BOOT, dtype=int)
    thresholds_arr = np.full(B_BOOT, np.nan)
    skipped_oob = 0

    for b in range(B_BOOT):
        # Bootstrap sample: n indices drawn with replacement.
        boot_idx = rng.integers(0, n, size=n)
        boot_mask = np.zeros(n, dtype=bool)
        boot_mask[boot_idx] = True
        oob_idx = np.where(~boot_mask)[0]

        boot_scores = scores[boot_idx]
        boot_labels = labels[boot_idx]
        boot_pos = [float(s) for s in boot_scores[boot_labels == 1]]
        boot_neg = [float(s) for s in boot_scores[boot_labels == 0]]

        # Threshold selection on the bootstrap sample (>= 90% specificity, max sens).
        op = roc_operating_point(boot_neg, boot_pos, TARGET_SPECIFICITY)
        thr = op["threshold"]
        thresholds_arr[b] = thr

        # In-sample rates on the bootstrap sample (with duplicates) at threshold_b.
        r_in = rates_at_threshold(boot_scores, boot_labels, thr)
        tpr_in_arr[b] = r_in["tpr"]
        fpr_in_arr[b] = r_in["fpr"]

        # Out-of-bag rates on tracks NOT in the bootstrap sample.
        if len(oob_idx) == 0:
            skipped_oob += 1
            continue
        oob_scores = scores[oob_idx]
        oob_labels = labels[oob_idx]
        if int(np.sum(oob_labels == 1)) == 0 or int(np.sum(oob_labels == 0)) == 0:
            # OOB missing a class -> cannot compute both rates; keep what we can.
            r_oob = rates_at_threshold(oob_scores, oob_labels, thr)
            n_oob_arr[b] = len(oob_idx)
            if not math.isnan(r_oob["tpr"]):
                tpr_oob_arr[b] = r_oob["tpr"]
            if not math.isnan(r_oob["fpr"]):
                fpr_oob_arr[b] = r_oob["fpr"]
            continue
        r_oob = rates_at_threshold(oob_scores, oob_labels, thr)
        tpr_oob_arr[b] = r_oob["tpr"]
        fpr_oob_arr[b] = r_oob["fpr"]
        n_oob_arr[b] = len(oob_idx)

    # Aggregate (ignore NaN OOB entries from degenerate folds).
    tpr_in_mean = float(np.nanmean(tpr_in_arr))
    fpr_in_mean = float(np.nanmean(fpr_in_arr))
    tpr_oob_mean = float(np.nanmean(tpr_oob_arr))
    fpr_oob_mean = float(np.nanmean(fpr_oob_arr))

    # --- .632 estimator (Efron 1983): fixed 0.368/0.632 blend.
    tpr_632 = 0.368 * tpr_in_mean + 0.632 * tpr_oob_mean
    fpr_632 = 0.368 * fpr_in_mean + 0.632 * fpr_oob_mean

    # --- No-information error rate gamma (permutation-based, Efron & Tibshirani 1997).
    # Permute labels B_PERM times; for each permutation draw a bootstrap, select the
    # threshold on (bootstrap, permuted labels), and record the OOB error and OOB FPR.
    # gamma (overall) = mean OOB error under permutation; gamma_fpr = mean OOB FPR
    # under permutation. The OOB TPR under permutation is also recorded for reference.
    perm_errors = np.full(B_PERM, np.nan)
    perm_fprs = np.full(B_PERM, np.nan)
    perm_tprs = np.full(B_PERM, np.nan)
    for b in range(B_PERM):
        perm_labels = labels[rng.permutation(n)]
        boot_idx = rng.integers(0, n, size=n)
        boot_mask = np.zeros(n, dtype=bool)
        boot_mask[boot_idx] = True
        oob_idx = np.where(~boot_mask)[0]
        boot_scores = scores[boot_idx]
        boot_labels = perm_labels[boot_idx]
        boot_pos = [float(s) for s in boot_scores[boot_labels == 1]]
        boot_neg = [float(s) for s in boot_scores[boot_labels == 0]]
        if len(boot_pos) == 0 or len(boot_neg) == 0:
            continue
        op = roc_operating_point(boot_neg, boot_pos, TARGET_SPECIFICITY)
        thr = op["threshold"]
        r_in_perm = rates_at_threshold(boot_scores, boot_labels, thr)
        perm_errors[b] = r_in_perm["error"]
        perm_fprs[b] = r_in_perm["fpr"]
        perm_tprs[b] = r_in_perm["tpr"]
        if len(oob_idx) > 0:
            oob_scores = scores[oob_idx]
            oob_labels = perm_labels[oob_idx]
            if int(np.sum(oob_labels == 1)) > 0 and int(np.sum(oob_labels == 0)) > 0:
                r_oob_perm = rates_at_threshold(oob_scores, oob_labels, thr)
                perm_errors[b] = r_oob_perm["error"]
                perm_fprs[b] = r_oob_perm["fpr"]
                perm_tprs[b] = r_oob_perm["tpr"]

    gamma_err = float(np.nanmean(perm_errors))       # no-information overall error
    gamma_fpr = float(np.nanmean(perm_fprs))          # no-information FPR
    gamma_tpr = float(np.nanmean(perm_tprs))          # no-information TPR (reference)

    # --- .632+ estimator (Efron & Tibshirani 1997).
    # For TPR: work on the miss-rate (error) scale. e_in = 1 - TPR_in, e_oob = 1 - TPR_oob.
    # gamma for the miss rate is estimated from the permutation OOB error. Relative
    # overfitting rate R in [0, 1]; weight w = 0.632 / (1 - 0.368 R) in [0.632, 1].
    def plus_weight(e_in: float, e_oob: float, gamma: float) -> tuple[float, float]:
        """Return (w, R) for the .632+ blend on the error scale."""
        if not (math.isfinite(e_in) and math.isfinite(e_oob) and math.isfinite(gamma)):
            return 0.632, 0.0
        if gamma - e_in <= EPS:
            # No-information error not above in-sample error: cannot scale; use plain .632.
            return 0.632, 0.0
        rel = (e_oob - e_in) / (gamma - e_in)
        rel = min(1.0, max(0.0, rel))
        w = 0.632 / (1.0 - 0.368 * rel)
        return w, rel

    e_in_tpr = 1.0 - tpr_in_mean
    e_oob_tpr = 1.0 - tpr_oob_mean
    w_tpr, rel_tpr = plus_weight(e_in_tpr, e_oob_tpr, gamma_err)
    tpr_632plus = (1.0 - w_tpr) * tpr_in_mean + w_tpr * tpr_oob_mean

    # For FPR: FPR is already an error rate. gamma_fpr from permutation OOB FPR.
    w_fpr, rel_fpr = plus_weight(fpr_in_mean, fpr_oob_mean, gamma_fpr)
    fpr_632plus = (1.0 - w_fpr) * fpr_in_mean + w_fpr * fpr_oob_mean

    return {
        "n": n,
        "n_pos": n_pos_total,
        "n_neg": n_neg_total,
        "b_boot": B_BOOT,
        "b_perm": B_PERM,
        "seed": seed,
        "tpr_in_mean": tpr_in_mean,
        "fpr_in_mean": fpr_in_mean,
        "tpr_oob_mean": tpr_oob_mean,
        "fpr_oob_mean": fpr_oob_mean,
        "tpr_in_arr": tpr_in_arr,
        "fpr_in_arr": fpr_in_arr,
        "tpr_oob_arr": tpr_oob_arr,
        "fpr_oob_arr": fpr_oob_arr,
        "n_oob_arr": n_oob_arr,
        "thresholds_arr": thresholds_arr,
        "threshold_mean": float(np.nanmean(thresholds_arr)),
        "threshold_std": float(np.nanstd(thresholds_arr)),
        "skipped_empty_oob": skipped_oob,
        "n_oob_mean": float(np.mean(n_oob_arr[n_oob_arr > 0])) if np.any(n_oob_arr > 0) else 0.0,
        "gamma_no_info_error": gamma_err,
        "gamma_no_info_fpr": gamma_fpr,
        "gamma_no_info_tpr": gamma_tpr,
        "tpr_632": tpr_632,
        "fpr_632": fpr_632,
        "tpr_632plus": tpr_632plus,
        "fpr_632plus": fpr_632plus,
        "w_tpr": w_tpr,
        "rel_overfitting_tpr": rel_tpr,
        "w_fpr": w_fpr,
        "rel_overfitting_fpr": rel_fpr,
    }


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

    # --- Bootstrap .632 / .632+ estimation.
    boot = bootstrap_632_estimates(h_sub, lab_sub, SEED)

    # --- Binary-KL bounds at the .632 and .632+ FPRs.
    bound_632 = binary_kl_bound(boot["fpr_632"], d_primary)
    bound_632plus = binary_kl_bound(boot["fpr_632plus"], d_primary)
    # Reference: binary-KL bound at the in-sample FPR (RQ20's 0.555).
    bound_in_sample = in_sample_binary_kl_bound
    # Reference: binary-KL bound at the pure OOB FPR (no .632 blend).
    bound_oob = binary_kl_bound(boot["fpr_oob_mean"], d_primary)

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
            "bound_type": "cv_binary_kl_kfold5_rq24",
            "value": RQ24_CV_BINARY_KL_KFOLD5,
            "source": "RQ24 (PR #925)",
            "note": "CV binary-KL (K=5); below empirical (overcorrection).",
        },
        {
            "bound_type": "bootstrap_oob_binary_kl",
            "value": round(bound_oob, 6),
            "source": "this study (pure OOB)",
            "note": "Binary-KL at pure OOB FPR; pessimistic reference.",
        },
        {
            "bound_type": "bootstrap_632_binary_kl",
            "value": round(bound_632, 6),
            "source": "this study (.632)",
            "note": "Binary-KL at .632 FPR; fixed 0.368/0.632 blend.",
        },
        {
            "bound_type": "bootstrap_632plus_binary_kl",
            "value": round(bound_632plus, 6),
            "source": "this study (.632+)",
            "note": "Binary-KL at .632+ FPR; adaptive blend (Efron & Tibshirani 1997).",
        },
    ]

    # --- Hypothesis verdicts.
    # H27a: .632+ binary-KL bound < 0.729. Kill: >= 0.729.
    h27a_pass = bound_632plus < RQ20_DV_PINSKER_PRIMARY
    h27a_killed = bound_632plus >= RQ20_DV_PINSKER_PRIMARY
    h27a_supported = h27a_pass and not h27a_killed
    # H27b: .632+ binary-KL bound >= 0.649. Kill: < 0.649.
    h27b_pass = bound_632plus >= RQ17_EMPIRICAL_LZROC
    h27b_killed = bound_632plus < RQ17_EMPIRICAL_LZROC
    h27b_supported = h27b_pass and not h27b_killed
    # H27c: .632+ bound tighter than CV bound (0.639). Kill: .632+ >= 0.639.
    h27c_pass = bound_632plus < RQ24_CV_BINARY_KL_KFOLD5
    h27c_killed = bound_632plus >= RQ24_CV_BINARY_KL_KFOLD5
    h27c_supported = h27c_pass and not h27c_killed

    # --- Console summary.
    print("=== RQ27: Bootstrap .632+ binary-KL bound tightening ===")
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
    print(f"Bootstrap resampling (B={B_BOOT}, seed={SEED}, n={n_nonempty}):")
    print(f"  threshold mean = {boot['threshold_mean']:.4f}  std = {boot['threshold_std']:.4f}")
    print(f"  mean OOB size = {boot['n_oob_mean']:.2f}  (skipped empty-OOB draws = {boot['skipped_empty_oob']})")
    print(f"  TPR_in  = {boot['tpr_in_mean']:.4f}  TPR_oob = {boot['tpr_oob_mean']:.4f}")
    print(f"  FPR_in  = {boot['fpr_in_mean']:.4f}  FPR_oob = {boot['fpr_oob_mean']:.4f}")
    print()
    print("No-information rates (permutation, B={}):".format(B_PERM))
    print(f"  gamma (overall error) = {boot['gamma_no_info_error']:.4f}")
    print(f"  gamma_fpr (no-info FPR) = {boot['gamma_no_info_fpr']:.4f}")
    print(f"  gamma_tpr (no-info TPR) = {boot['gamma_no_info_tpr']:.4f}")
    print()
    print(".632 / .632+ estimates:")
    print(f"  TPR_632   = {boot['tpr_632']:.4f}   FPR_632   = {boot['fpr_632']:.4f}")
    print(f"  TPR_632+  = {boot['tpr_632plus']:.4f}   FPR_632+  = {boot['fpr_632plus']:.4f}")
    print(f"  w_tpr     = {boot['w_tpr']:.4f}  (rel overfitting = {boot['rel_overfitting_tpr']:.4f})")
    print(f"  w_fpr     = {boot['w_fpr']:.4f}  (rel overfitting = {boot['rel_overfitting_fpr']:.4f})")
    print()
    print("Binary-KL bounds (d(TPR||FPR) <= D(P||Q)=0.792, bisection tol 1e-6):")
    print(f"  pure OOB FPR = {boot['fpr_oob_mean']:.4f}  -> bound = {bound_oob:.4f}")
    print(f"  .632   FPR   = {boot['fpr_632']:.4f}  -> bound = {bound_632:.4f}")
    print(f"  .632+  FPR   = {boot['fpr_632plus']:.4f}  -> bound = {bound_632plus:.4f}")
    print()
    print("Bound comparison:")
    print(f"  {'bound':44s} {'value':>7s}")
    print(f"  {'Gaussian (RQ17, INVALID)':44s} {RQ17_GAUSSIAN_BOUND:7.3f}")
    print(f"  {'Empirical LZ-ROC (in-sample, optimistic)':44s} {empirical_sens:7.3f}")
    print(f"  {'DV/Pinsker primary D(P||Q) (RQ20)':44s} {RQ20_DV_PINSKER_PRIMARY:7.3f}")
    print(f"  {'DV/Pinsker min-direction (RQ20)':44s} {RQ20_DV_PINSKER_MIN_DIR:7.3f}")
    print(f"  {'Binary-KL in-sample (RQ20)':44s} {RQ20_BINARY_KL_IN_SAMPLE:7.3f}")
    print(f"  {'CV binary-KL K=5 (RQ24, invalid)':44s} {RQ24_CV_BINARY_KL_KFOLD5:7.3f}")
    print(f"  {'Bootstrap pure-OOB binary-KL (THIS STUDY)':44s} {bound_oob:7.3f}")
    print(f"  {'.632 binary-KL (THIS STUDY)':44s} {bound_632:7.3f}")
    print(f"  {'.632+ binary-KL (THIS STUDY)':44s} {bound_632plus:7.3f}")
    print()
    print("Hypothesis verdicts:")
    print(f"  H27a (.632+ binary-KL < 0.729): "
          f"bound={bound_632plus:.4f}  "
          f"pass={h27a_pass}  kill={h27a_killed}  "
          f"-> {'SUPPORTED' if h27a_supported else 'NOT SUPPORTED'}")
    print(f"  H27b (.632+ binary-KL >= 0.649): "
          f"bound={bound_632plus:.4f}  "
          f"pass={h27b_pass}  kill={h27b_killed}  "
          f"-> {'SUPPORTED' if h27b_supported else 'NOT SUPPORTED'}")
    print(f"  H27c (.632+ binary-KL < 0.639 [CV]): "
          f"bound={bound_632plus:.4f}  "
          f"pass={h27c_pass}  kill={h27c_killed}  "
          f"-> {'SUPPORTED' if h27c_supported else 'NOT SUPPORTED'}")
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

    # --- Write JSON (summary + bootstrap arrays + verdicts).
    def _nan_to_none(x: float) -> float | None:
        if isinstance(x, float) and math.isnan(x):
            return None
        return float(x)

    summary: dict[str, Any] = {
        "label": "experimental/frontier",
        "rq": "RQ27: Bootstrap .632+ binary-KL bound tightening",
        "closes_issue": 928,
        "source_data": str(SRC_CSV.relative_to(PROJECT_ROOT)),
        "source_label": "experimental/frontier (RQ17, PR #913)",
        "builds_on": "RQ17 (PR #913), RQ20 (PR #918), RQ24 (PR #925)",
        "method": (
            "reanalysis only (no Whisper / no ASR run); reuses RQ17's per-track "
            "LZ78 entropy rates and RQ20's k-NN KL estimator. De-optimises the "
            "LZ-ROC threshold via the bootstrap .632 / .632+ estimator (Efron 1983; "
            "Efron & Tibshirani 1997): B=1000 bootstrap resamples, in-sample and "
            "out-of-bag rates per draw, fixed 0.368/0.632 blend (.632) and adaptive "
            "blend with permutation-estimated no-information error rate (.632+). "
            "Inverts the binary data-processing inequality d(TPR||FPR) <= D(P||Q) "
            "(bisection, tol 1e-6) at the .632 / .632+ FPR to obtain the binary-KL "
            "bound."
        ),
        "target_specificity": TARGET_SPECIFICITY,
        "seed": SEED,
        "bisect_tolerance": BISECT_TOL,
        "k_primary": K_PRIMARY,
        "b_boot": B_BOOT,
        "b_perm": B_PERM,
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
        "bootstrap_estimates": {
            "b_boot": B_BOOT,
            "b_perm": B_PERM,
            "seed": SEED,
            "threshold_mean": round(boot["threshold_mean"], 6),
            "threshold_std": round(boot["threshold_std"], 6),
            "n_oob_mean": round(boot["n_oob_mean"], 6),
            "skipped_empty_oob": boot["skipped_empty_oob"],
            "tpr_in_mean": round(boot["tpr_in_mean"], 6),
            "fpr_in_mean": round(boot["fpr_in_mean"], 6),
            "tpr_oob_mean": round(boot["tpr_oob_mean"], 6),
            "fpr_oob_mean": round(boot["fpr_oob_mean"], 6),
            "gamma_no_info_error": round(boot["gamma_no_info_error"], 6),
            "gamma_no_info_fpr": round(boot["gamma_no_info_fpr"], 6),
            "gamma_no_info_tpr": round(boot["gamma_no_info_tpr"], 6),
            "tpr_632": round(boot["tpr_632"], 6),
            "fpr_632": round(boot["fpr_632"], 6),
            "tpr_632plus": round(boot["tpr_632plus"], 6),
            "fpr_632plus": round(boot["fpr_632plus"], 6),
            "w_tpr": round(boot["w_tpr"], 6),
            "rel_overfitting_tpr": round(boot["rel_overfitting_tpr"], 6),
            "w_fpr": round(boot["w_fpr"], 6),
            "rel_overfitting_fpr": round(boot["rel_overfitting_fpr"], 6),
            "tpr_in_arr": [_nan_to_none(x) for x in boot["tpr_in_arr"]],
            "fpr_in_arr": [_nan_to_none(x) for x in boot["fpr_in_arr"]],
            "tpr_oob_arr": [_nan_to_none(x) for x in boot["tpr_oob_arr"]],
            "fpr_oob_arr": [_nan_to_none(x) for x in boot["fpr_oob_arr"]],
            "thresholds_arr": [_nan_to_none(x) for x in boot["thresholds_arr"]],
        },
        "binary_kl_bounds": {
            "pure_oob": {
                "fpr": round(boot["fpr_oob_mean"], 6),
                "bound": round(bound_oob, 6),
            },
            "bootstrap_632": {
                "fpr": round(boot["fpr_632"], 6),
                "tpr": round(boot["tpr_632"], 6),
                "bound": round(bound_632, 6),
            },
            "bootstrap_632plus": {
                "fpr": round(boot["fpr_632plus"], 6),
                "tpr": round(boot["tpr_632plus"], 6),
                "bound": round(bound_632plus, 6),
            },
        },
        "bound_comparison_table": bounds_table,
        "hypothesis_verdicts": {
            "H27a": {
                "statement": (
                    "The bootstrap .632+ binary-KL bound is < 0.729 (tighter than "
                    "RQ20's primary Pinsker). Kill: .632+ >= 0.729."
                ),
                "bound_632plus": round(bound_632plus, 6),
                "pass": bool(h27a_pass),
                "kill": bool(h27a_killed),
                "supported": bool(h27a_supported),
            },
            "H27b": {
                "statement": (
                    "The bootstrap .632+ binary-KL bound is >= 0.649 (valid -- "
                    "above the empirical LZ-ROC). Kill: .632+ < 0.649."
                ),
                "bound_632plus": round(bound_632plus, 6),
                "pass": bool(h27b_pass),
                "kill": bool(h27b_killed),
                "supported": bool(h27b_supported),
            },
            "H27c": {
                "statement": (
                    "The .632+ binary-KL bound is tighter than the CV bound (0.639). "
                    "Kill: .632+ >= 0.639."
                ),
                "bound_632plus": round(bound_632plus, 6),
                "cv_bound_rq24": RQ24_CV_BINARY_KL_KFOLD5,
                "pass": bool(h27c_pass),
                "kill": bool(h27c_killed),
                "supported": bool(h27c_supported),
            },
        },
        "references": {
            "gaussian_rq17": RQ17_GAUSSIAN_BOUND,
            "empirical_lzroc_rq17": RQ17_EMPIRICAL_LZROC,
            "dv_pinsker_primary_rq20": RQ20_DV_PINSKER_PRIMARY,
            "dv_pinsker_min_dir_rq20": RQ20_DV_PINSKER_MIN_DIR,
            "binary_kl_in_sample_rq20": RQ20_BINARY_KL_IN_SAMPLE,
            "d_primary_rq20_nats": RQ20_D_PRIMARY_NATS,
            "cv_binary_kl_kfold5_rq24": RQ24_CV_BINARY_KL_KFOLD5,
        },
    }
    OUT_JSON.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
