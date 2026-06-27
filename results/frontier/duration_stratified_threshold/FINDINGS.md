# RQ57: Window-Duration Stratified Threshold for Reduced Modality

> **Label: `experimental/frontier`** — reanalysis-only test of whether stratifying the
> lang-id entropy threshold by window duration (total separated text length) reduces
> the 6-modality that RQ44 (PR #963) observed in the pooled bootstrap threshold
> distribution. No Whisper / no ASR model is run; this reads the existing AISHELL-4
> external-validation results and re-runs the RQ44 bootstrap recipe separately on
> two duration strata. Builds on RQ13 (PR #904), RQ16 (PR #912), RQ25 (PR #929),
> RQ38 (PR #948), RQ44 (PR #963), and RQ49 (PR #968).
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, PR #890). Closes #975.

## Executive Summary

Stratifying the corrected router's lang-id entropy threshold by window duration
(short vs long, split at the median total separated text length = 81 chars) does
**not** reduce the threshold modality and **makes the out-of-sample cpWER worse**.
Both strata retain **3 modes** (≥ 5% frequency), exceeding the H57a bar of ≤ 2
modes per stratum. The combined stratified router's median OOB cpWER (**1.106061**)
is **higher** than RQ44's pooled median (1.055556) — stratification by duration
**hurts** deployment cpWER, killing H57b. The two strata do have **significantly
different** threshold distributions (Mann-Whitney U two-sided p ≈ 0.0, z = −117.39),
so H57c is supported: short and long windows calibrate to genuinely different
operating points — but that difference does not help, it hurts.

**H57a (both strata ≤ 2 modes): KILLED (3 modes in each stratum). H57b (combined
OOB cpWER < 1.056): KILLED (1.106061 ≥ 1.056, stratification is worse). H57c
(strata differ, Mann-Whitney p < 0.05): SUPPORTED (p ≈ 0.0).**

The scientifically useful result is the **negative** one, and it sharpens RQ49's
conclusion. RQ49 showed speaker-count stratification does not reduce modality (the
≤2-speaker stratum retained 4 modes). RQ57 shows duration stratification also does
not reduce modality (both strata retain 3 modes) — and is actively harmful to OOB
cpWER. The long-duration stratum (38 windows, 71.1% hallucination rate) calibrates
a high threshold (0.95) that lets hallucinated windows through to the separated
route, driving the combined OOB cpWER up. Duration is therefore **not** an
effective stratification lever either; the modality is intrinsic to the calibration
rule's sensitivity to small-sample composition, not to a feature that can be
stratified away.

## Method

1. **Duration proxy** per window = total separated text length (sum of all
   `separated_text_per_speaker` track string lengths). This is the transcript-level
   duration surrogate available in the existing JSON; longer total separated text
   implies more speech content in the 30s window, which proxies for more speaker
   overlap / more hallucination opportunity. Cross-checked against the JSON's stored
   `separated_total_length` field (zero mismatches across all 77 windows).
2. **Stratify** the 77 windows at the median duration (81 chars) into short
   (stratum 1, ≤ 81) and long (stratum 2, > 81).
3. **Per stratum**: B = 10,000 bootstrap resamples (seed = 42, n = stratum_size
   with replacement). On each resample: calibrate the lang-id entropy threshold
   maximising sensitivity at ≥ 90% specificity (RQ13/RQ16/RQ25/RQ44 rule, verbatim)
   on the in-bag windows; evaluate the corrected-router cpWER on the out-of-bag
   windows; count threshold modes (≥ 5% frequency).
4. **Stratified router**: on each aligned bootstrap resample, calibrate a threshold
   for BOTH strata, then evaluate the COMBINED OOB cpWER — each OOB window is routed
   by its OWN stratum's threshold. The combined OOB pools the OOB windows from both
   strata.
5. **Mann-Whitney U** two-sided test on the two strata's bootstrap threshold
   distributions (normal approximation with continuity + tie correction; numpy +
   stdlib only, no scipy — consistent with RQ44/RQ49's pure-reanalysis convention).

Detector primitives (`script_category`, `language_id_entropy`, `max_across_speakers`)
and the calibration rule (`calibrate_threshold_at_spec`) are lifted **verbatim** from
RQ44/RQ49 so thresholds are directly comparable. numpy + stdlib only. A within-script
pooled bootstrap at matched B=10,000, seed=42 reproduces RQ44's 6 unique / 5 modes
(≥5%) / width 0.94 / OOB median 1.055556 exactly, confirming the comparison is
apples-to-apples.

## Stratification

| Stratum | Rule | n | Hallucinated | Hallucination rate | Duration range | Duration median |
|---|---|--:|--:|---:|---:|---:|
| 1 (short) | duration ≤ 81 chars | 39 | 10 | 25.6% | [0, 81] | 34.0 |
| 2 (long) | duration > 81 chars | 38 | 27 | 71.1% | [84, 201] | 118.5 |

The long-duration stratum has a **2.8× higher** hallucination rate (71.1% vs 25.6%),
confirming the motivating hypothesis that longer windows (more total separated text)
harbour more hallucination. But this asymmetry is precisely what hurts the stratified
router: the long stratum has only 11 clean windows, which calibrates a high threshold
(0.95) that under-flags hallucinated long windows.

## In-sample reproduction (RQ44 reference)

| Calibration | Threshold | Sensitivity | Specificity | cpWER |
|---|---:|---:|---:|---:|
| Pooled (all 77) | 0.3800 | — | — | 1.043290 |
| Stratum 1 (short) | 0.3300 | 1.0000 | 0.9655 | — |
| Stratum 2 (long) | 0.9500 | 0.8148 | 1.0000 | — |

The pooled in-sample threshold (0.38) and cpWER (1.043290) reproduce RQ44/RQ25
exactly. The short stratum calibrates a slightly lower threshold (0.33, full
sensitivity); the long stratum calibrates a much higher threshold (0.95) because its
few clean windows sit just below 0.95 entropy, so the ≥ 90%-specificity rule pins
the threshold there — at the cost of sensitivity (81.5%, missing 5 of 27
hallucinated long windows).

## Threshold distributions (B=10,000, seed=42)

### Pooled (matched B=10,000; reproduces RQ44's B=10,000)

| Statistic | Pooled (B=10,000) | RQ44 (B=10,000) |
|---|---:|---:|
| median | 0.3800 | 0.38 |
| 2.5 / 97.5 pct | [0.0100, 0.9500] | [0.01, 0.95] |
| width | 0.9400 | 0.94 |
| n_unique | 6 | 6 |
| modes (≥5%) | 5 | 5 |
| OOB cpWER median | 1.055556 | 1.055556 |

The within-script pooled bootstrap reproduces RQ44's 6-unique / 5-modes / width-0.94
/ OOB-median-1.055556 exactly, confirming the matched-B comparison is valid.

### Stratum 1 (short duration, ≤ 81 chars)

| Statistic | Value |
|---|---:|
| median | 0.3300 |
| 2.5 / 97.5 pct | [0.0100, 0.8400] |
| width | 0.8300 (vs pooled 0.94) |
| n_unique | 3 |
| **modes (≥5%)** | **3** |
| OOB cpWER median | 1.041667 |
| OOB cpWER mean | 1.104309 |
| OOB frac < 1.10 | 0.6193 |

Stratum-1 modes (≥5%): `0.33` (58.88%), `0.01` (33.57%), `0.84` (7.55%). The width
narrows slightly (0.83 vs 0.94) and the number of unique thresholds drops from 6 to
3, but **3 modes remain**, exceeding the H57a bar of ≤ 2. The `0.01` mode (33.57%)
is the Mode-S-driven collapse (when the Mode S windows dominate the in-bag clean
set, the threshold collapses to flag everything); the `0.33` and `0.84` modes are
the within-stratum operating-point ambiguities.

### Stratum 2 (long duration, > 81 chars)

| Statistic | Value |
|---|---:|
| median | 0.9500 |
| 2.5 / 97.5 pct | [0.3800, 0.9500] |
| width | 0.6200 (vs pooled 0.94) |
| n_unique | 5 |
| **modes (≥5%)** | **3** |
| OOB cpWER median | 1.098039 |
| OOB cpWER mean | 1.114358 |
| OOB frac < 1.10 | 0.5022 |

Stratum-2 modes (≥5%): `0.95` (56.57%), `0.38` (25.43%), `0.87` (15.20%). The width
narrows more (0.62 vs 0.94) but **3 modes remain**, exceeding the H57a bar of ≤ 2.
The long stratum's OOB cpWER median (1.098) is worse than the short stratum's
(1.042) because the high threshold (0.95) under-flags hallucinated long windows.

## Combined stratified-router OOB cpWER

| Statistic | Combined (stratified) | RQ44 pooled (B=10,000) |
|---|---:|---:|
| n valid resamples | 10,000 / 10,000 | 10,000 |
| **median** | **1.106061** | **1.055556** |
| mean | 1.109208 | — |
| 2.5 / 97.5 pct | [1.0000, 1.2500] | — |
| frac < 1.10 | 0.4687 | 0.7604 |
| frac < RQ44 (1.056) | 0.2680 | — |

The combined stratified router's median OOB cpWER (**1.106061**) is **higher** than
RQ44's pooled median (1.055556) and higher than the matched-B pooled median
(1.055556). Stratification by duration **hurts** the OOB cpWER: only 46.87% of
resamples land below 1.10 (vs RQ44's 76.04%), and only 26.8% land below RQ44's
median. The mechanism: the long stratum's high threshold (0.95) routes too many
hallucinated long windows to the separated track, and these high-cpWER windows
dominate the combined OOB.

## Mann-Whitney U test (H57c)

| Statistic | Value |
|---|---:|
| U statistic (stratum 1) | 3,487,272.5 |
| z-score | −117.392775 |
| **p-value (two-sided)** | **≈ 0.0** |
| n_x (stratum 1) | 10,000 |
| n_y (stratum 2) | 10,000 |

The two strata's bootstrap threshold distributions are **significantly different**
(p ≈ 0.0, z = −117.4). Stratum 1 (short) centers on `0.33` / `0.01`; stratum 2
(long) centers on `0.95` / `0.38`. The negative z indicates stratum 1's thresholds
are systematically lower than stratum 2's. H57c is supported: short and long windows
calibrate to genuinely different operating points. (With n = 10,000 per stratum, the
test is extremely sensitive; the substantive question is whether that difference
helps — and it does not, per H57b.)

## Hypothesis Verdicts

| Hypothesis | Statement | Result | Kill | Supported? |
|---|---|---:|---|---|
| H57a | Both strata threshold modes (≥5%) ≤ 2 | 3 / 3 | > 2 in either | **KILLED** |
| H57b | Combined OOB cpWER < 1.056 | 1.106061 | ≥ 1.056 | **KILLED** |
| H57c | Strata differ (Mann-Whitney p < 0.05) | p ≈ 0.0 | ≥ 0.05 | **SUPPORTED** |

## Interpretation

1. **Duration stratification is not an effective lever for threshold stability.**
   Both strata retain 3 modes (≥ 5%), exceeding the H57a bar of ≤ 2. The modality is
   not separable by duration: the short stratum's 3 modes (`0.33`, `0.01`, `0.84`)
   and the long stratum's 3 modes (`0.95`, `0.38`, `0.87`) are each driven by the
   within-stratum calibration-rule sensitivity to small-sample composition, not by a
   duration-separated feature.

2. **Duration stratification actively hurts OOB cpWER.** The combined OOB cpWER
   (1.106061) is higher than RQ44's pooled (1.055556). The mechanism: the long
   stratum (38 windows, 71.1% hallucination rate, only 11 clean) calibrates a high
   threshold (0.95) that under-flags hallucinated long windows — 5 of 27 are missed
   in-sample (sensitivity 81.5%). These high-cpWER false negatives dominate the
   combined OOB. The pooled threshold (0.38) catches more of them. Stratification
   trades a single threshold that is mediocre everywhere for two thresholds where
   the long-stratum one is worse than mediocre.

3. **The strata ARE genuinely different (H57c supported).** Short windows calibrate
   to low thresholds (0.33 / 0.01) and have a low hallucination rate (25.6%); long
   windows calibrate to high thresholds (0.95 / 0.38) and have a high hallucination
   rate (71.1%). Duration is a *descriptive* feature (it correlates with
   hallucination rate) but not a *therapeutic* stratification lever — it does not
   isolate the modality, and the stratum-specific thresholds it produces are worse
   than the pooled one.

4. **Convergent negative evidence with RQ49.** RQ49 (speaker count) and RQ57
   (duration) are two *different* stratification levers, and both fail to reduce the
   modality. This is strong evidence that the 6-modality is intrinsic to the
   `calibrate_threshold_at_spec` rule's sensitivity to small-sample composition
   (each stratum's clean/hallucinated boundary moves with the in-bag draw), not to
   a confound that a single stratification variable can remove. The next lever to
   try is not another stratification variable but a *different calibration rule*
   (e.g. a shrinkage / regularised rule, or a rule that does not collapse to the
   extreme thresholds 0.01 / 0.95 under small-sample imbalance) — which RQ48's
   calibration-rule comparison already began exploring.

## Reproducibility

- Pure reanalysis (numpy + stdlib only; no scipy / sklearn / Whisper). Deterministic
  for a given seed.
- Pooled bootstrap at matched B=10,000, seed=42 reproduces RQ44's published 6 unique
  / 5 modes (≥5%) / width 0.94 / OOB median 1.055556 exactly (the
  `pooled_bootstrap_matched` block in the JSON).
- 101 unit tests in `tests/test_duration_stratified.py` pin the pure helpers
  (`script_category`, `language_id_entropy`, `max_across_speakers`,
  `duration_proxy`, `stratify_by_duration`, `mann_whitney_u_test`,
  `calibrate_threshold_at_spec`, `combined_oob_cpwer`, `bootstrap_stratified`,
  `count_modes`, `percentile_interval`), the in-sample 0.38 reproduction, the
  duration split, the pooled reproduction, and the result-file contract.

## Outputs

- `results/frontier/duration_stratified_threshold/duration_stratified_analysis.py`
- `results/frontier/duration_stratified_threshold/duration_stratified_results.json`
- `results/frontier/duration_stratified_threshold/duration_stratified_results.csv`
- `results/frontier/duration_stratified_threshold/FINDINGS.md`
- `tests/test_duration_stratified.py`
