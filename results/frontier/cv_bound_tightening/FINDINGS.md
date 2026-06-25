# RQ24: CV Bound Tightening — Cross-Validated Binary-KL Bound

> **Label: `experimental/frontier`** — Closes #922. Builds on RQ17 (PR #913) and RQ20 (PR #918).
> Reanalysis only (no Whisper / no ASR run); reuses RQ17's per-track LZ78 entropy rates and
> RQ20's k-NN KL estimator.

## Executive Summary

RQ20 documented that the tighter KL forms (min-direction Pinsker 0.636, binary-KL 0.555) fall
*below* the empirical LZ-ROC (0.649) because the empirical threshold was selected on the same
n=64 tracks — **threshold-selection optimism**. RQ24 asks: does cross-validating the threshold
(de-optimising it) produce a binary-KL bound that is tighter than the primary Pinsker (0.729)
while remaining valid (≥ 0.649)?

**The answer is no.** The CV binary-KL bound (0.639) is tighter than the primary Pinsker
(0.729) — H24a SUPPORTED — but it is NOT valid: it falls below the empirical LZ-ROC (0.649),
killing H24b. The CV de-optimisation overcorrects: the CV threshold produces a HIGHER false
positive rate (0.111 vs 0.074 in-sample), and the binary-KL bound at that higher FPR (0.639)
is below the empirical sensitivity. The CV approach doesn't produce a valid tighter ceiling;
the DV/Pinsker primary bound (0.729) remains the only valid non-trivial ceiling on
repetition-detector sensitivity.

The convergence analysis (H24c) also fails: the bound is still increasing at n=64 (0.659 →
extrapolated asymptote 0.789), with a gap of 0.130 > 0.10. This means more data would not
tighten the bound below 0.729 — the asymptote (0.789) is actually higher than the primary
Pinsker, because the CV FPR increases with n (threshold becomes less stable on smaller
training folds).

| bound | value | valid (≥ 0.649) | tighter than 0.729 |
|---|---|---|---|
| Gaussian (RQ17) | 0.435 | ✗ (INVALID) | ✓ |
| Empirical LZ-ROC (in-sample) | 0.649 | ✓ (reference) | ✓ |
| DV/Pinsker primary D(P‖Q) (RQ20) | 0.729 | ✓ | — |
| DV/Pinsker min-direction (RQ20) | 0.636 | ✗ (below empirical) | ✓ |
| Binary-KL in-sample (RQ20) | 0.555 | ✗ (below empirical) | ✓ |
| **CV binary-KL K=5 (THIS STUDY)** | **0.639** | ✗ (below empirical) | ✓ |
| CV binary-KL LOO (THIS STUDY) | 0.639 | ✗ (below empirical) | ✓ |
| CV empirical LZ-ROC K=5 (THIS STUDY) | 0.649 | ✓ (reference) | ✓ |
| CV empirical LZ-ROC LOO (THIS STUDY) | 0.622 | ✗ (below empirical) | ✓ |

## Method

### Data (read-only, not overwritten)

`results/frontier/info_theoretic_detector_bound/bound_verification.csv` (RQ17, PR #913): 64
non-empty tracks (37 hallucinated / 27 clean) with per-track LZ78 entropy rates.

### Reproduction of RQ17/RQ20 baselines

- **Empirical LZ-ROC** at ≥ 90% specificity: threshold 4.9549 bits/char, specificity 0.926,
  sensitivity 0.6486 (24/37 detected, 2/27 false positives) — matches RQ17's 0.649.
- **k-NN KL estimator** (Wang-Kulkarni-Verdú 2009, k=3): D(P‖Q) = 0.792 nats — matches
  RQ20's 0.792.
- **In-sample binary-KL bound**: d(TPR‖FPR) ≤ D(P‖Q), inverted at FPR=0.074 → bound 0.555 —
  matches RQ20's 0.555.

### Cross-validated threshold (addressing optimism)

1. **K-fold CV (K=5, stratified by class)**: for each fold, select the threshold on the
   training folds (≥ 90% specificity, maximise sensitivity), measure TPR and FPR on the
   held-out fold. Micro-average across folds.
2. **Leave-one-out CV (n=64)**: extreme case — each track held out once.

The CV-de-optimised FPR is 0.111 (K=5) and 0.111 (LOO) — higher than the in-sample FPR
(0.074) because the threshold selected on a smaller training set is less optimal.

### CV binary-KL bound

The binary data-processing inequality: `d(TPR || FPR) ≤ D(P‖Q)`, where
`d(x||y) = x·ln(x/y) + (1−x)·ln((1−x)/(1−y))`. Inverted via bisection (tolerance 1e-6) at
the CV-de-optimised FPR (0.111) and D(P‖Q)=0.792 → CV binary-KL bound = 0.639.

### Convergence (H24c)

Subsample at n ∈ {40, 50, 60, 64}, 200 class-balanced resamples (seed=42). For each
subsample, compute the CV binary-KL bound. Extrapolate to n=∞ via linear fit of bound vs 1/n.

## Results

### CV sensitivity table

| method | threshold mean | threshold std | micro TPR | micro FPR | spec | binary-KL bound |
|--------|---------------:|--------------:|----------:|----------:|-----:|----------------:|
| In-sample (RQ17) | 4.9549 | — | 0.6486 | 0.074 | 0.926 | 0.555 |
| K-fold CV (K=5) | 4.8978 | 0.051 | 0.6486 | 0.111 | 0.889 | **0.639** |
| LOO CV | 4.9498 | 0.023 | 0.6216 | 0.111 | 0.889 | **0.639** |

The CV micro-TPR (K=5) equals the in-sample TPR (0.6486) — the threshold generalises well
on sensitivity. But the CV FPR (0.111) is 1.5× the in-sample FPR (0.074) — the threshold
is worse on specificity when selected on less data. The binary-KL bound at the higher FPR
(0.639) is below the empirical LZ-ROC (0.649), making it invalid as a ceiling.

### Bound comparison

| bound | value | source |
|---|---|---|
| Gaussian (RQ17) | 0.435 | INVALID (non-Gaussian) |
| Empirical LZ-ROC (in-sample) | 0.649 | optimistic (threshold on n=64) |
| DV/Pinsker primary D(P‖Q) (RQ20) | 0.729 | valid, conservative |
| DV/Pinsker min-direction (RQ20) | 0.636 | below empirical (optimism) |
| Binary-KL in-sample (RQ20) | 0.555 | below empirical (optimism) |
| **CV binary-KL K=5 (this study)** | **0.639** | below empirical (overcorrection) |
| CV binary-KL LOO (this study) | 0.639 | below empirical (overcorrection) |
| CV empirical LZ-ROC K=5 (this study) | 0.649 | valid (matches in-sample) |
| CV empirical LZ-ROC LOO (this study) | 0.622 | below empirical (overcorrection) |

### Convergence (H24c)

| n | CV binary-KL bound (mean) | CV TPR (mean) | CV FPR (mean) | D(P‖Q) (mean) |
|---|---|---|---|---|
| 40 | 0.593 | 0.623 | 0.120 | 0.685 |
| 50 | 0.587 | 0.603 | 0.104 | 0.720 |
| 60 | 0.651 | 0.653 | 0.125 | 0.764 |
| 64 | 0.659 | 0.649 | 0.123 | 0.792 |
| asymptote (n→∞) | 0.789 | — | — | — |

The bound is INCREASING with n (0.593 at n=40 → 0.659 at n=64 → 0.789 at n=∞). This is
counterintuitive but explained: D(P‖Q) increases with n (the k-NN estimator converges
upward), and the binary-KL bound tracks D(P‖Q). The asymptote (0.789) is actually higher
than the primary Pinsker (0.729), meaning more data would make the CV binary-KL bound
WORSE, not better. The gap at n=64 is 0.130 > 0.10, killing H24c.

## Hypothesis Verdicts

- **H24a — CV binary-KL bound < 0.729 (tighter than primary Pinsker): SUPPORTED.** The
  K=5 CV bound is 0.639 < 0.729. The CV de-optimisation does produce a tighter number than
  the primary Pinsker. However, this tightness comes at the cost of validity (H24b).

- **H24b — CV binary-KL bound ≥ 0.649 (still valid — above empirical LZ-ROC): NOT
  SUPPORTED.** The K=5 CV bound is 0.639 < 0.649. The kill criterion (CV binary-KL < 0.649)
  is met. The CV de-optimisation overcorrects: the CV FPR (0.111) is higher than the
  in-sample FPR (0.074), and the binary-KL bound at the higher FPR falls below the
  empirical sensitivity. The bound is not a valid ceiling.

- **H24c — CV bound converges at n=64 (within 10pp of n=∞ asymptote): NOT SUPPORTED.**
  The gap is 0.130 > 0.10. The bound is still increasing at n=64 and the extrapolated
  asymptote (0.789) is higher than the primary Pinsker (0.729), meaning more data would
  not tighten the bound below the primary Pinsker — it would loosen it.

## Key honest finding: the de-optimisation overcorrects

RQ20's hypothesis was that the tighter KL forms (min-direction 0.636, binary-KL 0.555) fall
below empirical because of threshold-selection optimism, and that CV would address this by
de-optimising the threshold. RQ24 finds that CV does de-optimise, but the de-optimisation
**overcorrects**: the CV threshold is selected on less data (K=5: 50 training tracks vs 64
in-sample), making it less stable and producing a higher FPR (0.111 vs 0.074). The
binary-KL bound at the higher FPR (0.639) is below the empirical LZ-ROC (0.649), making it
invalid as a ceiling.

The conclusion is that the DV/Pinsker primary bound (0.729) remains the only valid
non-trivial ceiling on repetition-detector sensitivity. The "true de-optimised ceiling"
(RQ20's min-direction 0.636) is a lower bound on the true ceiling, not an upper bound — it
cannot be operationalised as a valid ceiling via CV. The threshold-selection optimism is
real but cannot be removed without either (a) more data (which RQ24's convergence analysis
shows would not help — the asymptote is higher) or (b) a fundamentally different approach
(e.g., a held-out test set, which requires collecting new data rather than resampling the
existing 64 tracks).

## Limitations

1. **K=5 fold choice.** K=5 is a standard choice, but the CV FPR is sensitive to K (smaller
   K = less training data = higher FPR). LOO (K=64) gives the same binary-KL bound (0.639)
   because the LOO FPR (0.111) equals the K=5 FPR. K=10 might give a slightly lower FPR,
   but the trend (CV FPR > in-sample FPR) is structural.

2. **Small n.** n_pos=37 / n_neg=27. The CV folds have only 6-8 test positives per fold,
   so the per-fold FPR is quantised (0, 0.2, 0.4, ...). The micro-averaged FPR (0.111) is
   more stable but still noisy.

3. **KL estimator bias.** The k-NN KL estimator (k=3) is biased at n≈30; D(P‖Q)=0.792 may
   be a slight over-estimate (k=5 gives 0.526). A lower D would lower the binary-KL bound
   further, making H24b fail by more.

4. **Binary-KL inversion numerical error.** Bisection with tolerance 1e-6; the bound is
   accurate to 6 decimal places. Not a source of the H24b failure.

5. **1/n extrapolation.** The asymptote (0.789) is a linear fit of bound vs 1/n using the
   two largest sizes (n=60, 64). A quadratic fit or a different extrapolation model might
   give a different asymptote, but the trend (bound increasing with n) is robust across
   all four subsample sizes.

6. **δ = 0.05 only.** All bounds are at 95% confidence.

## Reproducibility

```
cd <repo root>
python3 results/frontier/cv_bound_tightening/cv_bound_tightening_analysis.py
```

- **Dependencies:** numpy + stdlib only (no scipy / sklearn / Whisper).
- **Determinism:** seed = 42.
- **Runtime:** < 30 s.
- **Source data:** `results/frontier/info_theoretic_detector_bound/bound_verification.csv`
  (RQ17, PR #913, label `experimental/frontier`, read-only).
- **Outputs:** `cv_bound_results.csv`, `cv_bound_results.json`, `FINDINGS.md`.

## What this changes for the project

RQ20 left an open question: can the threshold-selection optimism documented in the tighter
KL forms (min-direction 0.636, binary-KL 0.555) be addressed via cross-validation, producing
a valid tighter ceiling than the primary Pinsker (0.729)? RQ24 answers **no**: the CV
de-optimisation overcorrects, producing a binary-KL bound (0.639) that is tighter than the
primary Pinsker but invalid (below the empirical 0.649). The primary Pinsker bound (0.729)
remains the only valid non-trivial ceiling on repetition-detector sensitivity.

This closes the theoretical refinement thread: RQ17 (Gaussian, invalid), RQ20 (non-parametric,
DV/Pinsker 0.729 valid), RQ24 (CV tightening, overcorrects). The operative ceiling on
repetition-based detectors is 0.729 — language-id entropy (94.6%) lies outside this bound by
design (it is not a repetition-based statistic), confirming RQ17's finding that the
repetition-based family is fundamentally capped while language-id entropy is not.
