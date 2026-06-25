# RQ27: Bootstrap .632+ Bound — Binary-KL Bound via Bootstrap De-optimisation

> Label: `experimental/frontier` — Closes #928. Builds on RQ17 (PR #913), RQ20 (PR #918), RQ24 (PR #925).
> Reanalysis only (no Whisper / no ASR run); reuses RQ17's per-track LZ78 entropy rates and
> RQ20's k-NN KL estimator.

## Executive Summary

RQ24 (PR #925) found that cross-validating the LZ-ROC threshold de-optimises it but
**overcorrects**: the CV binary-KL bound (0.639) is tighter than the primary Pinsker
(0.729) yet INVALID — it falls below the empirical LZ-ROC (0.649) because the CV threshold,
selected on less data, produces a higher false-positive rate (0.111 vs 0.074 in-sample).
RQ27 asks whether the bootstrap **.632+** estimator (Efron 1983; Efron & Tibshirani 1997)
— designed to correct optimism without LOO-CV's overcorrection — produces a valid tighter
binary-KL bound.

**The .632+ estimator moves in the right direction but still falls just short of valid.**
The .632+ binary-KL bound is **0.648** — tighter than the primary Pinsker (0.729), so H27a
is SUPPORTED, but it is **0.0007 below the empirical 0.649**, killing H27b by a razor-thin
margin. Compared to CV (0.639, which missed empirical by 0.010), .632+ narrows the gap to
validity by an order of magnitude (miss of 0.0007), confirming it corrects much of the
overcorrection that plagued CV. However, it does not tighten *below* CV — it is looser
(0.648 > 0.639) — so H27c is NOT SUPPORTED. The primary Pinsker bound (0.729) remains the
only valid non-trivial ceiling on repetition-detector sensitivity.

The mechanism is instructive: the in-sample threshold overfits specificity badly — the
out-of-bag FPR (0.116) actually exceeds the no-information FPR (0.099, estimated by
permutation), so the .632+ relative-overfitting rate for FPR saturates at 1.0 and the
adaptive weight collapses to pure OOB (w_fpr = 1.0). The .632+ bound therefore equals the
pure-OOB bound (0.648). The fixed-blend .632 estimator under-corrects (w=0.632 fixed) and
gives an even more optimistic, clearly-invalid bound of 0.603.

| bound | value | valid (>= 0.649) | tighter than 0.729 | tighter than CV 0.639 |
|---|---|---|---|---|
| Gaussian (RQ17) | 0.435 | no (INVALID) | yes | yes |
| Empirical LZ-ROC (in-sample) | 0.649 | yes (reference) | yes | yes |
| DV/Pinsker primary (RQ20) | 0.729 | yes | — | no |
| DV/Pinsker min-direction (RQ20) | 0.636 | no (below empirical) | yes | yes |
| Binary-KL in-sample (RQ20) | 0.555 | no (below empirical) | yes | yes |
| CV binary-KL K=5 (RQ24) | 0.639 | no (overcorrects) | yes | — |
| Bootstrap pure-OOB binary-KL (this study) | 0.648 | no (just below) | yes | no |
| .632 binary-KL (this study) | 0.603 | no (under-corrects) | yes | yes |
| .632+ binary-KL (this study) | 0.648 | no (just below) | yes | no |

## Method

### Data (read-only, not overwritten)

`results/frontier/info_theoretic_detector_bound/bound_verification.csv` (RQ17, PR #913): 64
non-empty tracks (37 hallucinated / 27 clean) with per-track LZ78 entropy rates.

### Reproduction of RQ17/RQ20 baselines

- Empirical LZ-ROC at >= 90% specificity: threshold 4.9549 bits/char, specificity 0.926,
  sensitivity 0.6486 (24/37 detected, 2/27 false positives) — matches RQ17's 0.649.
- k-NN KL estimator (Wang-Kulkarni-Verdu 2009, k=3): D(P||Q) = 0.7922 nats — matches
  RQ20's 0.792. Cross-checks: k=1 gives 1.163, k=5 gives 0.526.
- In-sample binary-KL bound: d(TPR||FPR) <= D(P||Q), inverted at FPR=0.074 -> bound 0.555 —
  matches RQ20's 0.555.

### Bootstrap .632 / .632+ de-optimisation (Efron 1983; Efron & Tibshirani 1997)

1. **B=1000 bootstrap resamples** (seed=42), each of size n=64 drawn with replacement.
2. For each bootstrap sample b:
   - Select the threshold on the bootstrap sample (>= 90% specificity, maximise sensitivity).
   - In-sample rates on the bootstrap sample at threshold_b: TPR_in(b), FPR_in(b).
   - Out-of-bag rates on tracks NOT in bootstrap sample: TPR_oob(b), FPR_oob(b).
3. **.632 estimator** (fixed blend): TPR_632 = 0.368 * mean(TPR_in) + 0.632 * mean(TPR_oob);
   FPR_632 similarly.
4. **.632+ estimator** (adaptive blend), computed on the error scale per Efron & Tibshirani
   (1997):
   - No-information error rate gamma, estimated by B_PERM=1000 label permutations: for each
     permutation, draw a bootstrap, select the threshold on (bootstrap, permuted labels),
     and record the OOB error and OOB FPR. gamma = mean OOB error; gamma_fpr = mean OOB FPR.
   - For TPR: e_in = 1 - mean(TPR_in), e_oob = 1 - mean(TPR_oob). Relative overfitting
     rate R = min(1, max(0, (e_oob - e_in) / (gamma - e_in))). Weight
     w = 0.632 / (1 - 0.368 * R) in [0.632, 1.0]. TPR_632+ = (1-w) * mean(TPR_in) + w * mean(TPR_oob).
   - For FPR (already an error rate): same formula with e_in = mean(FPR_in),
     e_oob = mean(FPR_oob), gamma = gamma_fpr. FPR_632+ = (1-w) * mean(FPR_in) + w * mean(FPR_oob).

### Binary-KL bound

The binary data-processing inequality: `d(TPR || FPR) <= D(P||Q)`, where
`d(x||y) = x*ln(x/y) + (1-x)*ln((1-x)/(1-y))`. Inverted via bisection (tolerance 1e-6) at
the .632 / .632+ FPR and D(P||Q)=0.792. D is a distribution property (threshold-independent)
and is reused unchanged from RQ20.

## Results

### Bootstrap rates table

| quantity | in-sample (mean) | out-of-bag (mean) | no-information (permutation) |
|---|---|---|---|
| TPR | 0.6600 | 0.6133 | 0.0938 |
| FPR | 0.0575 | 0.1159 | 0.0985 |
| overall error | — | — | 0.5675 |

The in-sample TPR (0.660) is higher than the OOB TPR (0.613) — the expected optimism
signature. The in-sample FPR (0.058) is much lower than the OOB FPR (0.116): the threshold
selected on the bootstrap sample overfits specificity badly, and when applied to held-out
tracks the FPR more than doubles. Strikingly, the OOB FPR (0.116) exceeds the
no-information FPR (0.099) — the in-sample threshold is, on held-out data, worse than random
at controlling false positives.

### .632 / .632+ estimates

| estimator | TPR | FPR | weight w | rel. overfitting R |
|---|---|---|---|---|
| .632 (fixed blend) | 0.6305 | 0.0944 | 0.632 (fixed) | — |
| .632+ TPR | 0.6281 | — | 0.6837 | 0.2053 |
| .632+ FPR | — | 0.1159 | 1.0000 | 1.0000 (capped) |

For TPR, the relative overfitting rate is mild (R=0.205), so the .632+ weight moves only
slightly above 0.632 (to 0.684). For FPR, the overfitting is extreme: the OOB FPR exceeds
the no-information FPR, so R saturates at 1.0 and the weight collapses to 1.0 — the .632+
FPR equals the pure OOB FPR (0.116). This is the .632+ estimator correctly refusing to
trust the overfit in-sample FPR.

### Binary-KL bounds

| bound | FPR | value |
|---|---|---|
| Pure OOB | 0.1159 | 0.648 |
| .632 (fixed blend) | 0.0944 | 0.603 |
| .632+ (adaptive blend) | 0.1159 | 0.648 |

Because the .632+ FPR weight saturates at 1.0, the .632+ bound equals the pure-OOB bound
(0.648). The fixed-blend .632 estimator, which still mixes in the overfit in-sample FPR,
gives a lower (more optimistic, more invalid) bound of 0.603.

### Bound comparison

| bound | value | source |
|---|---|---|
| Empirical LZ-ROC (in-sample) | 0.649 | RQ17 (optimistic) |
| DV/Pinsker primary | 0.729 | RQ20 (valid, conservative) |
| CV binary-KL (RQ24) | 0.639 | RQ24 (invalid, overcorrects) |
| .632 binary-KL | 0.603 | this study (under-corrects) |
| .632+ binary-KL | 0.648 | this study (just below empirical) |

## Hypothesis Verdicts

- **H27a — .632+ binary-KL bound < 0.729 (tighter than primary Pinsker): SUPPORTED.**
  The .632+ bound is 0.648 < 0.729. The bootstrap de-optimisation does produce a tighter
  number than the primary Pinsker ceiling.

- **H27b — .632+ binary-KL bound >= 0.649 (valid — above empirical): NOT SUPPORTED.** The
  .632+ bound is 0.6483, which is 0.0007 below the empirical 0.649 (and 0.0003 below the
  recomputed empirical 0.6486). The kill criterion (< 0.649) is met, but only by a
  razor-thin margin. The .632+ estimator narrows the gap-to-validity by an order of
  magnitude relative to CV (miss of 0.0007 vs CV's 0.010), but it does not cross the line.

- **H27c — .632+ bound tighter than CV bound (0.639): NOT SUPPORTED.** The .632+ bound
  (0.648) is LOOSER than the CV bound (0.639), not tighter. The kill criterion
  (.632+ >= 0.639) is met. This is the correct behaviour: .632+ corrects CV's
  overcorrection by moving the bound upward (toward validity), so it cannot be tighter
  than the overcorrected CV bound. Tightening below CV would mean repeating CV's mistake.

## Key honest finding: .632+ corrects the direction but not the magnitude

RQ24's hypothesis was that the threshold-selection optimism documented in RQ20's tighter KL
forms could be removed by de-optimising the threshold. CV overcorrected because the CV
threshold, selected on 50 training tracks, was less stable and produced a higher FPR. RQ27
finds that the .632+ estimator — which blends the optimistic in-sample error with the
pessimistic OOB error and adapts the blend based on the severity of overfitting — moves the
bound in the right direction (0.648 vs CV's 0.639, i.e. upward toward the empirical 0.649)
but still falls 0.0007 short of valid.

The reason .632+ cannot reach validity here is structural: the in-sample threshold
overfits specificity so badly that the OOB FPR (0.116) exceeds the no-information FPR
(0.099). The .632+ estimator correctly identifies this (R_fpr saturates at 1.0, w_fpr = 1.0)
and falls back to the pure OOB FPR, but the pure OOB FPR is itself high enough that the
binary-KL bound at that FPR (0.648) sits just below the empirical sensitivity. No blend of
in-sample and OOB can do better than pure OOB when the in-sample FPR is the overfit
quantity — and pure OOB is already slightly too pessimistic for the binary-KL bound to clear
the empirical reference.

The conclusion is that the DV/Pinsker primary bound (0.729) remains the only valid
non-trivial ceiling on repetition-detector sensitivity. The bootstrap .632+ estimator is
the closest of the de-optimisation approaches (CV 0.639, .632 0.603, .632+ 0.648), but
none clears the empirical 0.649. The threshold-selection optimism is real, and the .632+
estimator corrects most of it, but a residual ~0.001 gap remains because the OOB FPR itself
is inflated by the small clean-class sample (n_neg=27).

## Limitations

1. **Small n.** n_pos=37 / n_neg=27. The OOB set per bootstrap averages 23.5 tracks, with
   only ~10 clean tracks OOB on average, so the OOB FPR is quantised and noisy. A single
   extra false positive moves the OOB FPR by ~0.10. The 0.0007 gap to the empirical
   reference is well within this noise.

2. **B=1000 bootstrap.** Standard, but the .632+ point estimate has its own Monte Carlo
   error. Re-running with a different seed would move the .632+ bound in the third decimal
   place; the razor-thin H27b miss is not robust to this. The pre-registered kill criterion
   (< 0.649) is met at seed=42, but the result is best read as "on the boundary" rather
   than "decisively invalid".

3. **gamma via permutation.** The no-information error rate is estimated by B_PERM=1000
   label permutations, each requiring its own bootstrap and threshold selection. With
   permuted labels the threshold selection is largely arbitrary (no signal), so gamma is
   noisy; gamma_fpr=0.099 is itself an estimate with uncertainty. The cap R_fpr=1.0 is
   robust to this (the OOB FPR exceeds gamma_fpr by 0.017, well outside the noise), but the
   exact .632+ TPR weight (0.684) is sensitive to gamma.

4. **KL estimator bias.** The k-NN KL estimator (k=3) is biased at n=37/27; D(P||Q)=0.792
   may be a slight over-estimate (k=5 gives 0.526). A lower D would lower all binary-KL
   bounds proportionally, making H27b fail by more. D is reused unchanged from RQ20 for
   narrative continuity.

5. **Binary-KL inversion.** Bisection with tolerance 1e-6; the bound is accurate to 6
   decimal places. Not a source of the H27b failure.

6. **.632+ on FPR vs TPR.** The .632+ weight is computed separately for TPR (on the
   miss-rate scale) and FPR (on the FPR scale directly), each with its own gamma. This
   follows the standard per-class formulation; an alternative would be to apply .632+ only
   to the overall accuracy and derive TPR/FPR from a single blend, but that loses the
   class-specific overfitting diagnostic.

7. **delta = 0.05 only.** All bounds are at 95% confidence (inherited from RQ20).

## Reproducibility

```
cd <repo root>
/opt/homebrew/bin/python3 results/frontier/bootstrap_632_bound/bootstrap_632_bound_analysis.py
```

- Dependencies: numpy + stdlib only (no scipy / sklearn / Whisper).
- Determinism: seed = 42 (both bootstrap and permutation loops).
- Runtime: < 1 s.
- Source data: `results/frontier/info_theoretic_detector_bound/bound_verification.csv`
  (RQ17, PR #913, label `experimental/frontier`, read-only).
- Outputs: `bootstrap_632_bound_results.csv`, `bootstrap_632_bound_results.json`,
  `FINDINGS.md`.

## What this changes for the project

RQ24 left an open question: can the threshold-selection optimism documented in RQ20's
tighter KL forms be removed by a de-optimisation method that does not overcorrect like CV?
RQ27 answers **almost**: the bootstrap .632+ estimator (Efron & Tibshirani 1997) corrects
the direction — it moves the bound from CV's overcorrected 0.639 upward to 0.648, an order
of magnitude closer to the empirical 0.649 — but a residual 0.0007 gap remains, so the .632+
binary-KL bound is still technically invalid by the pre-registered kill criterion. The
primary Pinsker bound (0.729) remains the only valid non-trivial ceiling on
repetition-detector sensitivity.

This extends the theoretical refinement thread: RQ17 (Gaussian, invalid), RQ20
(non-parametric, DV/Pinsker 0.729 valid), RQ24 (CV tightening, overcorrects to 0.639),
RQ27 (bootstrap .632+, nearly valid at 0.648). The frontier for a valid tighter ceiling now
hinges on collecting more clean-class tracks (n_neg=27 is the binding constraint: the OOB
FPR is inflated by the small clean sample, and no resampling method can fix a
sample-size-limited FPR). The operative ceiling on repetition-based detectors remains 0.729.
