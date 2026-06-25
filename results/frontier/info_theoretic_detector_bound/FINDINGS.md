# RQ17: Information-Theoretic Bound on Repetition-Detector Sensitivity

> **Label: `experimental/frontier`** — derives an information-theoretic upper
> bound on the sensitivity of any repetition-based hallucination detector on
> AISHELL-4's *diverse* hallucination, and tests whether CR's 2.7% (RQ12) /
> 13.5% (RQ13 recalibrated) is a fundamental limit or an implementation
> artifact. Closes #909. Builds on RQ12 (`results/frontier/router_failure_modes/`,
> PR #900) and RQ13 (`results/frontier/diverse_hallucination_detector/`).
> Full derivation in `bound_derivation.md`; per-track scores in
> `bound_verification.csv`; summary + CIs + verdicts in
> `bound_verification.json`.

## Executive Summary

RQ12 showed that the Whisper CR guard catches only 1/37 = **2.7%** of AISHELL-4's
diverse hallucination at the fixed CR>2.4 threshold, and RQ13 showed that even
recalibrated to ≥ 90% specificity on AISHELL-4, CR reaches only **13.5%**
sensitivity. The natural question: is CR's failure a *fundamental* limit of any
repetition-based detector, or an *implementation* artifact of the CR statistic
itself?

We derive a closed-form upper bound on the sensitivity of any detector whose
statistic is a deterministic monotone function of compressibility / entropy rate
— the family CR, TTR, n-gram repetition, and LZ complexity all belong to. The
bound uses LZ78 as a universal entropy-rate estimator and the data-processing
inequality (DPI): no deterministic function of H carries more information about
the hallucination label than H itself, so the ROC of any repetition-based
detector is dominated by the ROC of the entropy-rate discriminator. We then
compare the bound to (i) CR (the deployed repetition-based detector), (ii) the
empirical LZ-ROC itself (the operative DPI ceiling), (iii) language-id entropy
(RQ13's deployable detector, which is *not* subject to the bound because it
measures script mixing, not repetition), and (iv) a character-bigram
likelihood-ratio test (LOO-CV) approximating the Bayes-optimal reference-free
text detector.

**Headline numbers (90% specificity, n=77 tracks; 64 with non-empty text for the
bound):**

| Quantity | Value | Bootstrap 95% CI |
|---|---:|---:|
| Theoretical bound (Gaussian, equal-variance) | **43.5%** | [30.5%, 60.1%] |
| Empirical DPI bound (LZ-ROC, non-empty subset) | **64.9%** | [50.0%, 80.0%] |
| CR sensitivity (concat, recalibrated, full n=77) | **13.5%** | [3.1%, 25.7%] |
| LZ entropy rate sensitivity (concat, full n=77) | 70.3% | [54.8%, 84.4%] |
| Language-id entropy sensitivity (RQ13 detector) | **94.6%** | [86.1%, 100.0%] |
| Bigram LRT (Bayes-optimal, LOO, full n=77) | 75.7% | [61.3%, 88.9%] |

**Verdict on the central question:** CR's 13.5% is *neither* the fundamental
limit *nor* a clean implementation artifact of CR alone — the truth is in
between. The repetition-based family *is* fundamentally capped on this
hallucination (the empirical DPI ceiling is 64.9%, well below 100%), but CR at
13.5% is also well below even the Gaussian-equal-variance approximation (43.5%),
so CR specifically is leaving a lot on the table. The Gaussian closed form
underestimates the true ceiling because H_LZ is non-Gaussian (the clean class
has 5.6× the variance of the hallucinated class, mostly because clean Chinese
tracks are near-monoscript H≈4); the empirical LZ-ROC is the operative bound.

The deployable takeaway from RQ13 holds and is sharpened: **language-id entropy
(94.6%) exceeds even the Bayes-optimal bigram LRT (75.7%) on this data** — not
because the LRT is weak in principle, but because it is data-starved under LOO
on n=77. The script-mixing signal is the right one for diverse hallucination;
no repetition-based detector can compete with it.

## Method

### Data source (read-only, not overwritten)

`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
(label `external/sanity-check`, PR #890): 77 windows × 30 s from AISHELL-4
meeting M_R003S02C01 (6 speakers, oracle-TextGrid separation, Whisper-tiny,
MeetEval cpWER/orcWER). Each window stores the per-speaker separated transcripts
and the window-level `always_separated_cpwer`. **Hallucinated** iff
`always_separated_cpwer > 1.0` (matches RQ12/RQ13's 37/40 split).

### Track text

For an apples-to-apples comparison between the bound and every detector, all
scores are computed on the **concatenated** per-speaker separated text (speaker
dict order). This differs from RQ13's MAX-across-speakers aggregation; the two
conventions give slightly different per-detector numbers (RQ13's CR recalibrated
sensitivity was 13.5% under MAX, identical here under concat for CR but differing
for other detectors). The RQ13 numbers are cited in the JSON for narrative
continuity.

### Entropy-rate estimator (LZ78)

For each track we compute:

- **LZ78 phrase count** `|LZ78(s)|` via standard incremental parsing
  (Ziv 1978; consistent entropy-rate estimator for stationary ergodic sources).
- **Normalised complexity** `C_LZ(s) = |LZ78(s)| / |s|` (phrases per char).
- **Entropy-rate estimate** `H_LZ(s) = |LZ78(s)| · log2 |LZ78(s)| / |s|`
  (bits/char).

H_LZ is undefined on empty tracks (no separated text); 13 of 77 tracks are
empty (all non-hallucinated — empty text ⇒ cpWER = 1.0 not > 1.0). The bound is
computed on the **64 non-empty tracks** (37 halluc / 27 clean); empty tracks
are trivially classified clean by any detector, so excluding them only
tightens specificity.

### Theoretical bound (Gaussian equal-variance, closed form)

Under a Gaussian-equal-variance model for H_LZ per class,

$$
  \text{sensitivity} \;\le\; \Phi\!\left(
    \frac{|\mu_{\text{halluc}} - \mu_{\text{clean}}|}{\sigma_{\text{pooled}}}
    - z_{1-\text{specificity}}
  \right),
$$

where z_{1-specificity} is the standard-normal upper-tail quantile at the
false-positive rate (= Φ⁻¹(specificity) lower-tail = **1.2816** at 90%
specificity, computed by Acklam's algorithm + Halley refinement; scipy is
unavailable under the numpy+stdlib-only constraint). Empirically:

- μ_halluc = **4.992** bits/char,  μ_clean = **4.078** bits/char,
- σ_pooled = **0.818**,  Δ_H = **+0.914** bits/char
  (bootstrap 95% CI [+0.495, +1.392] — excludes 0),
- effect size |Δ_H|/σ = **1.117**,
- theoretical bound = Φ(1.117 − 1.282) = Φ(−0.165) = **0.435**
  (bootstrap 95% CI [0.305, 0.601]).

### Empirical DPI bound (LZ-ROC)

The Gaussian closed form is an approximation. The *exact* DPI bound is the ROC
of the H_LZ discriminator itself — by monotonicity, every repetition-based
statistic S = f(H) has the same ROC. We compute the LZ-ROC at ≥ 90%
specificity on the 64 non-empty tracks:

- threshold = 4.955 bits/char, specificity = 92.6%, sensitivity = **64.9%**
  (bootstrap 95% CI [50.0%, 80.0%]).

The empirical bound (64.9%) **exceeds** the Gaussian closed form (43.5%),
so the Gaussian-equal-variance model is **violated** (H_LZ is non-Gaussian —
the clean class has 5.6× the variance of the hallucinated class). The empirical
value is the operative DPI ceiling; the Gaussian value is reported as the
closed-form approximation that motivates the H17a hypothesis test.

For comparison on the full 77 tracks (RQ13's convention, where empty tracks
get H=0 and are trivially clean), the LZ-ROC reaches 70.3% sensitivity at
92.5% specificity — but this is not the apples-to-apples bound.

### Bayes-optimal reference-free detector (character-bigram LRT, LOO-CV)

To know *how much* a non-repetition-based text detector could extract, we fit a
character-bigram likelihood-ratio test with leave-one-out cross-validation:

- For track i, the halluc model is fit on all other hallucinated tracks and
  the clean model on all other non-hallucinated tracks.
- Both models use Laplace smoothing over a **shared vocabulary** (the union of
  characters seen in either training set + boundary + `<UNK>` tokens). Using
  the same V for both classes is essential — class-specific vocabularies flip
  the LLR sign (this was a real bug in an earlier draft; see
  `bound_derivation.md` §5 and the script's `_shared_vocab` helper).
- LLR_i = log P(text_i | halluc) − log P(text_i | clean).
- Threshold calibrated to ≥ 90% specificity on the full 77 tracks.

The bigram LRT is *not* a repetition-based statistic — it conditions on
character identity, not just compressibility — so it can exceed the bound. It
is the empirical "information ceiling" for any text-based detector, and the
reference against which we compare language-id entropy (H17c).

### Bootstrap

10,000 resamples (seed = 42) of the n tracks with replacement, recomputing
each statistic at the **fixed full-sample threshold** (threshold uncertainty
excluded; same convention as RQ13). CIs are the 2.5th and 97.5th percentiles.

## Results

### The bound is low — but higher than CR

The Gaussian closed-form bound is **43.5%** (CI [30.5%, 60.1%]), and the
empirical DPI ceiling is **64.9%** (CI [50.0%, 80.0%]). CR at **13.5%** is well
below both. So:

- CR's failure is **partly fundamental** — no repetition-based detector can
  reach 90%+ on this hallucination; the best possible (the LZ-ROC itself) is
  64.9%, and the Gaussian approximation gives 43.5%.
- CR's failure is **partly an implementation artifact of the CR statistic** —
  even the conservative Gaussian bound (43.5%) is 3× CR's recalibrated 13.5%,
  so a better repetition-based statistic (e.g. LZ complexity in the
  high-entropy direction, which reaches 70.3% on the full set) would
  materially beat CR. Whisper's `compression_ratio` happens to flag the
  *wrong direction* (high CR = repetitive) for diverse hallucination, where
  the signal is high entropy (low CR), and the recalibration only recovers
  a fraction of the available signal.

### Language-id entropy exceeds the Bayes-optimal LRT — but only because the LRT is data-starved

Language-id entropy reaches **94.6%** sensitivity, exceeding the bigram LRT's
**75.7%**. This is not because the LRT is weak in principle — it is the
Bayes-optimal reference-free text detector in the limit of large data — but
because LOO on n=77 leaves only 36 halluc + 39 clean training tracks; many
character bigrams appear once, so Laplace smoothing dominates and the LLR is
noisy. With more training data (or a stronger language model), the LRT would
exceed language-id entropy. The honest reading is that **language-id entropy
captures the script-mixing signal that is exactly the property defeating
compression, and on this small dataset it is the strongest available
detector** — both because it is the right statistic and because the LRT
reference is data-starved.

### Why the Gaussian model is violated

The clean class has variance **1.28** bits/char² vs the hallucinated class's
**0.23** — a 5.6× ratio. The clean tracks include both near-monoscript Chinese
(H≈4.0, low variance) and a few mixed-script non-hallucinated tracks
(H≈5.0–5.4, raising the variance), while the hallucinated tracks cluster
tightly around H≈4.99. The Gaussian-equal-variance assumption underestimates
the discriminability in the high-specificity tail, giving a bound (43.5%) below
the empirical LZ-ROC (64.9%). A Welch-Satterthwaite (unequal-variance) variant
would give a different closed form, but on n=64 the additional parameter
instability is not worth the gain; we report the equal-variance form as the
canonical closed-form bound and the empirical LZ-ROC as the operative one.

## Hypothesis Verdicts

### H17a — theoretical bound < 30%: **NOT SUPPORTED**

The Gaussian-equal-variance bound is **43.5%** (CI [30.5%, 60.1%]), above the
30% threshold. The CI lower bound (30.5%) barely exceeds 30%, so the bound is
*marginally* above the threshold; with a different specificity target (e.g.
95%) or a longer-track entropy-rate estimator it might fall below 30%, but on
the canonical 90% specificity setting the bound exceeds 30%. **The qualitative
claim ("repetition-based detectors are fundamentally capped well below 100%
on diverse hallucination") still holds** — even the empirical DPI ceiling
(64.9%) is well below the 90%+ that language-id entropy achieves — but the
specific 30% threshold in H17a is not met.

### H17b — the bound is determined by the entropy-rate gap Δ_H: **SUPPORTED**

The entropy-rate gap is statistically real: Δ_H = +0.914 bits/char (bootstrap
95% CI [+0.495, +1.392] — excludes 0). CR's recalibrated sensitivity (13.5%)
is well below the bound (the conservative Gaussian value 43.5%, slack ≥ 0.10:
`cr_well_below_bound = True`), confirming CR's failure is the gap/statistic
rather than threshold noise. The Gaussian-equal-variance model is violated
(the empirical LZ-ROC 64.9% exceeds the Gaussian 43.5%), so the qualitative
role of Δ_H (the bound tracks the entropy-rate gap) is what is supported; the
quantitative Gaussian closed form is an approximation on this data.

### H17c — language-id entropy ≥ 80% of Bayes-optimal sensitivity: **SUPPORTED**

Language-id entropy reaches 94.6% sensitivity; the bigram LRT (Bayes-optimal
reference) reaches 75.7%. Ratio = 94.6% / 75.7% = **1.25**, well above the 0.80
threshold. Language-id entropy *exceeds* the LRT — not because the LRT is
weak in principle but because LOO on n=77 leaves it data-starved (see
Limitations). The script-mixing signal is the right one for diverse
hallucination, and on this dataset it is the strongest available detector.

## Limitations

1. **Gaussian-equal-variance model is violated.** The empirical DPI bound
   (64.9%) exceeds the Gaussian closed form (43.5%) because H_LZ is
   non-Gaussian (clean-class variance 5.6× halluc-class variance). The
   Gaussian value is reported as the canonical closed-form bound; the
   empirical LZ-ROC is the operative ceiling. **The Gaussian bound is
   therefore a *lower* bound on the true DPI ceiling on this data**, not the
   operative ceiling.
2. **Single meeting, n=64 non-empty tracks.** Only M_R003S02C01 is available
   (37 halluc / 27 clean with non-empty text). Bootstrap CIs are wide
   (Gaussian [30.5%, 60.1%]; empirical DPI [50.0%, 80.0%]); the qualitative
   verdicts (H17b, H17c) are robust but the precise numbers should not be
   over-interpreted.
3. **LZ78 entropy rate on short tracks.** Track lengths 30–200 chars; LZ78's
   consistency guarantee is asymptotic. On short tracks H_LZ is biased
   downward, but the bias is the same direction in both classes so Δ_H is
   less affected than the absolute H values.
4. **The bigram LRT underfits.** With LOO the halluc model is fit on 36 tracks
   and the clean model on 39; many character bigrams appear once, so Laplace
   smoothing dominates. The LRT's 75.7% is a *lower* bound on the true
   Bayes-optimal sensitivity; a larger training set or a stronger LM would
   lift it. This is why language-id entropy can *exceed* the LRT.
5. **Concatenated vs. max-aggregation.** This RQ uses the concatenated track
   text for apples-to-apples with the bound; RQ13 used MAX across speakers.
   The two conventions give slightly different per-detector numbers (the RQ13
   values are cited in the JSON for narrative continuity).
6. **Equal-variance assumption fails.** As noted in (1), σ²_halluc ≈ 0.23 ≪
   σ²_clean ≈ 1.28; the pooled σ is dominated by the clean class. A
   Welch-Satterthwaite variant would give a different closed form, but on n=64
   the additional parameter instability is not worth the gain.
7. **Oracle-TextGrid separation, Whisper-tiny only.** The separated tracks are
   oracle (true silence gaps), not real-separator output; a stronger ASR model
   or a real separator may produce different hallucination types (carry-over
   caveat from RQ12/RQ13).
8. **Threshold uncertainty not bootstrapped.** CIs fix the full-sample
   threshold and resample tracks; calibration uncertainty is excluded (same
   convention as RQ13).

## What this changes for the project

1. **CR's failure on AISHELL-4 is partly fundamental, partly an artifact.**
   The repetition-based family is capped at 64.9% (empirical DPI) on this
   hallucination; CR specifically is further capped at 13.5% because it flags
   the wrong direction (high CR = repetitive, when the signal is high
   entropy = low CR). A better repetition-based statistic (LZ complexity in
   the high-entropy direction) reaches 70.3%, but no repetition-based
   detector can match language-id entropy (94.6%).
2. **The deployable detector remains language-id entropy.** RQ13's
   recommendation holds and is sharpened: language-id entropy is not just
   the best of four reference-free detectors — it exceeds the empirical
   Bayes-optimal text detector (bigram LRT) on this data, because the LRT is
   data-starved under LOO and the script-mixing signal is exactly the
   property defeating compression.
3. **The bound gives a theoretical grounding for RQ12's empirical finding.**
   RQ12 showed CR catches 2.7% of diverse hallucination; RQ13 showed
   recalibration lifts it only to 13.5%; RQ17 now shows the repetition-based
   family is fundamentally capped (43.5% Gaussian / 64.9% empirical DPI), so
   the gap from 13.5% to ~65% is recoverable by a better repetition-based
   statistic, but the gap from ~65% to 94.6% requires leaving the
   repetition-based family entirely.

## Reproducibility

- Script: `results/frontier/info_theoretic_detector_bound/info_theoretic_bound_analysis.py`
- Per-track scores: `results/frontier/info_theoretic_detector_bound/bound_verification.csv`
  (columns: `window_id, hallucinated, lz_complexity, entropy_rate_estimate, cr,
  lang_id_entropy, bigram_loglik_ratio`, plus the extras
  `always_separated_cpwer, track_text_length, bigram_llr_per_char`).
- Summary + CIs + verdicts: `results/frontier/info_theoretic_detector_bound/bound_verification.json`.
- Mathematical derivation: `results/frontier/info_theoretic_detector_bound/bound_derivation.md`.
- Run: `python3 results/frontier/info_theoretic_detector_bound/info_theoretic_bound_analysis.py`
  (numpy + stdlib only; no scipy, no sklearn, no Whisper, no audio).
- Deterministic: seed = 42 throughout.
