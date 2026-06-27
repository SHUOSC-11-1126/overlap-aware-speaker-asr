# RQ61: Shrinkage Threshold Calibration

> **Label: `experimental/frontier`** — Closes #985. Builds on RQ13 (PR #904), RQ16
> (PR #912), RQ25 (PR #929), RQ44 (PR #963), RQ48 (PR #969), RQ49, and RQ57.
> Reanalysis only (no Whisper / no ASR / no LLM); reuses RQ44's lang-id entropy
> detector, bootstrap draw, and OOB cpWER evaluator verbatim, RQ48's `count_modes`
> verbatim, and the existing AISHELL-4 external-validation windows (PR #890). Does
> NOT overwrite any verified reference / gold table.

## Executive Summary

RQ44 (PR #963) showed the corrected router's lang-id entropy threshold
distribution is **5-modal** (≥ 5% frequency; "6-modal" counting all distinct
values) over [0.01, 0.95] under the "max sensitivity at ≥ 90% specificity"
calibration rule (H44b KILLED, width 0.94). RQ48 (PR #969) decomposed the
modality: the high-threshold modes (0.87, 0.95) are rule artefacts that smoother
rules (Youden's J, F1) eliminate, but the low-threshold "Mode S catch" mode
(0.01) persists under **every** rule RQ48 tried — RQ48 concluded it is
"calibration-rule-invariant," a fundamental detector ambiguity. RQ49
(speaker-count stratification) and RQ57 (duration stratification) both FAILED to
reduce the modality by slicing the data; RQ57 explicitly recommended "a different
calibration rule (shrinkage/regularised), not another stratification variable."
RQ61 tests whether a **Bayesian shrinkage prior** on the threshold — maximise
`sensitivity − λ·|threshold − 0.38|` at ≥ 90% specificity, with `prior_mean =
0.38` (RQ44's bootstrap median) — reduces the modality.

**Two of three pre-registered hypotheses are supported; the shrinkage prior is a
partial but real improvement over RQ44, and it overturns RQ48's "0.01 mode is
calibration-rule-invariant" conclusion:**

| Hypothesis | Verdict | Test statistic (λ=1.0) | Kill threshold |
|---|---|---:|---|
| H61a: ≤ 2 modes (vs RQ44's 5) | **KILLED** | 3 modes (≥ 5% freq) | > 2 modes |
| H61b: OOB cpWER ≤ 1.056 (matches RQ44) | **SUPPORTED** | 1.0517 (improved) | > 1.056 |
| H61c: width < 0.94 (RQ44's width) | **SUPPORTED** | 0.49 (improved) | ≥ 0.94 |

The best λ is **1.0** (fewest modes, narrowest width, lowest OOB cpWER; all λ are
deployable so the selection is by fewest modes → narrowest width → smallest λ).
At λ=1.0 the threshold distribution is **3-modal** {0.38 (74.2%), 0.84 (16.3%),
0.87 (7.4%)} with percentile interval [0.38, 0.87] (width 0.49) and median OOB
cpWER 1.0517 — *below* RQ44's 1.056. H61a is killed because three modes remain,
but the shrinkage prior achieves a **2-mode reduction (5 → 3)** and a **half-width
collapse (0.94 → 0.49)** while *improving* out-of-sample cpWER.

The headline mechanism, visible only because λ=0.0 reproduces RQ44 byte-for-byte
(5 modes, width 0.94, OOB 1.0556 — the paired-bootstrap anchor), is a **clean
decomposition of which modes shrinkage can and cannot remove**:

- **The 0.01 "Mode S catch" mode — which RQ48 said NO calibration rule could
  remove — is ELIMINATED by shrinkage, even at λ=0.01.** RQ48's "Mode S is
  calibration-rule-invariant" conclusion is overturned: a regularised objective
  that penalises distance from the prior flips those resamples away from 0.01
  toward the nearest feasible threshold (0.14 at low λ, then 0.38 at higher λ).
  Shrinkage resolves the low-threshold ambiguity RQ48 declared fundamental.
- **The 0.33 mode (cpWER-equivalent to 0.38) merges into 0.38** — the penalty
  breaks the tie toward the prior (0.38), collapsing the 0.33/0.38 split.
- **The high-threshold modes (0.84, 0.87) PERSIST at every λ.** These are the
  modes RQ48 traced to the discontinuous "≥ 90% specificity" boundary: in
  resamples where the 0.38 threshold's specificity drops below 0.90 (clean
  windows with entropy ≥ 0.38 land in-bag), 0.38 is **infeasible**. Shrinkage
  pulls toward 0.38 but cannot select an infeasible threshold, so it picks the
  *lowest feasible* threshold (closest to 0.38 within the feasible set) — which
  is 0.84 / 0.87 in those resamples. No λ removes them: the hard specificity
  constraint, not the calibration objective, generates them.

**Bottom line.** The shrinkage prior is the first calibration modification to
reduce RQ44's modality *and* improve both width and OOB cpWER simultaneously.
It kills the Mode S ambiguity RQ48 called fundamental (H61b/H61c supported with
improvements), but H61a is killed because the two high-threshold specificity-
constraint modes survive (3 modes, not ≤ 2). The residual 2 high-threshold modes
are exactly the rule artefacts RQ48 showed Youden's J / F1 eliminate — so the
natural next step is to **combine shrinkage with a smooth rule** (shrinkage +
F1), which should collapse the distribution to ≤ 2 modes. RQ57's recommendation
is validated: a regularised calibration rule is the right lever, and the
deployable recommendation is unchanged from RQ44 — **deploy 0.38** — now
reinforced by a shrinkage-calibrated threshold that is more stable *and* better
out-of-sample than the un-regularised baseline.

## Method

### Data (read-only, not overwritten)

`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
(label `external/sanity-check`, PR #890): 77 windows of 30 s from AISHELL-4
meeting `M_R003S02C01`. Hallucination label: `always_separated_cpwer > 1.0` → 37
hallucinated / 40 clean (RQ12/RQ13/RQ16/RQ25/RQ44/RQ48).

### Detector, routing rule, and bootstrap framework (reused verbatim from RQ44)

To guarantee the **only** thing varying across λ is the regularisation strength,
RQ61 imports RQ44's module directly:

- **Detector**: `max_across_speakers(window)` = max `language_id_entropy` over
  the per-speaker separated transcripts (RQ13/RQ16/RQ25/RQ44 verbatim).
- **Routing rule**: `lang_id_entropy >= threshold` → route MIXED
  (`always_mixed_cpwer`); else → SEPARATED (`always_separated_cpwer`).
- **Bootstrap draw**: `bootstrap_indices(n, B, seed)` — RQ44's exact function.
  RQ61 draws **one** (B=10000, seed=42, n=77) index array and reuses it for all 5
  λ values, so the comparison is **paired**: each resample sees the same
  in-bag/OOB split under every λ. **λ=0.0 is therefore the first 10000 of RQ44's
  10000 resamples** (same seed, same B) — it reproduces RQ44's threshold
  distribution byte-for-byte (the anchor).
- **OOB cpWER evaluator**: `out_of_bag_cpwer(...)` — RQ44's exact function.
- **Mode counter**: `count_modes` — RQ48's exact function (≥ 5% frequency
  definition), reused verbatim.

### The shrinkage calibration rule

Sweep the same grid {0.00, 0.01, ..., 2.00} (201 points) and flag
`score >= threshold`. For each grid threshold `t` with specificity ≥ 0.90,
compute the **regularised objective**:

    objective(t) = sensitivity(t) − λ · |t − prior_mean|,   prior_mean = 0.38

Select the threshold maximising the objective. Tie-break: higher objective →
higher specificity → lower threshold (the last via the first True in the
ascending grid). The penalty `λ·|t − 0.38|` pulls the threshold toward the prior:
when two thresholds tie (or nearly tie) on sensitivity, the one closer to 0.38
wins. At **λ = 0** the objective reduces to pure sensitivity and the tie-break
matches RQ44's `calibrate_threshold_at_spec` exactly (max sensitivity at
≥ 90% specificity, tie-break higher specificity then lower threshold) — this
equivalence is verified by a direct unit test (`test_lam_zero_matches_rq44_*`) on
the real data and a 50-resample bootstrap draw. λ ∈ {0.0, 0.01, 0.1, 0.5, 1.0}.

`prior_mean = 0.38` is RQ44's bootstrap median threshold (the bagged operating
point RQ44 recommended deploying). The shrinkage prior therefore regularises
*toward the deployable operating point*, not toward an arbitrary centre.

### Best-λ selection

Among deployable λ (median OOB cpWER ≤ 1.056, RQ44's value): pick the fewest
modes (≥ 5%), then the narrowest percentile-interval width, then the smallest λ
(least regularisation, most faithful to the data). If no λ is deployable, pick
the one whose OOB cpWER is closest to (and ≤) 1.056.

### Statistics

B=10000 bootstrap resamples, seed=42, paired across λ. numpy + stdlib only (no
scipy / sklearn / Whisper / meeteval / LLM). Runtime ≈ 2.5 s for all 5 λ × B=10000
(the confusion-matrix sweep is computed once per resample and reused across λ).

## Results

### In-sample calibration (full 77 windows, per λ)

| λ | threshold | expected cpWER | sensitivity | specificity | penalty | objective |
|---:|---:|---:|---:|---:|---:|---:|
| 0.0 | 0.380 | 1.0433 | 0.946 | 0.925 | 0.000 | 0.946 |
| 0.01 | 0.380 | 1.0433 | 0.946 | 0.925 | 0.000 | 0.946 |
| 0.1 | 0.380 | 1.0433 | 0.946 | 0.925 | 0.000 | 0.946 |
| 0.5 | 0.380 | 1.0433 | 0.946 | 0.925 | 0.000 | 0.946 |
| 1.0 | 0.380 | 1.0433 | 0.946 | 0.925 | 0.000 | 0.946 |

All λ calibrate the **same in-sample operating point (0.38)** — the prior is
feasible in-sample (spec 0.925 ≥ 0.90), and no threshold beats 0.38 on
sensitivity at ≥ 90% specificity, so the penalty never changes the in-sample
choice. The in-sample corrected cpWER (1.0433) matches RQ25/RQ44/RQ48 exactly.
The shrinkage effect appears only under bootstrap resampling, where resample
composition changes feasibility.

### Bootstrap threshold + OOB cpWER distributions (B=10000, paired)

| λ | thr median | thr pct [2.5, 97.5] | thr width | n unique | **n modes ≥ 5%** | OOB cpWER median | OOB cpWER mean | frac < 1.10 | H61a | H61b | H61c |
|---:|---:|---|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 0.0 | 0.380 | [0.010, 0.950] | 0.940 | 6 | **5** | 1.0556 | 1.0692 | 0.760 | ✗ | ✓ | ✗ |
| 0.01 | 0.380 | [0.140, 0.870] | 0.730 | 6 | **4** | 1.0536 | 1.0643 | 0.791 | ✗ | ✓ | ✓ |
| 0.1 | 0.380 | [0.140, 0.870] | 0.730 | 6 | **4** | 1.0536 | 1.0642 | 0.793 | ✗ | ✓ | ✓ |
| 0.5 | 0.380 | [0.320, 0.870] | 0.550 | 6 | **3** | 1.0533 | 1.0616 | 0.823 | ✗ | ✓ | ✓ |
| **1.0** | 0.380 | [0.380, 0.870] | **0.490** | 5 | **3** | **1.0517** | 1.0601 | 0.837 | ✗ | ✓ | ✓ |

RQ44 reference: 6 unique, 5 modes (≥ 5%), width 0.94, OOB cpWER 1.056.

Mode tables (threshold / count / fraction, sorted by descending frequency):

**λ=0.0** (RQ44 baseline reproduced, 5 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.38 | 6044 | 60.4% |
| 0.87 | 1451 | 14.5% |
| 0.01 | 899 | 9.0% |
| 0.95 | 844 | 8.4% |
| 0.33 | 573 | 5.7% |

**λ=0.01** (4 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.38 | 6647 | 66.5% |
| 0.84 | 1630 | 16.3% |
| 0.87 | 738 | 7.4% |
| 0.14 | 660 | 6.6% |

**λ=0.1** (4 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.38 | 6676 | 66.8% |
| 0.84 | 1630 | 16.3% |
| 0.87 | 738 | 7.4% |
| 0.14 | 631 | 6.3% |

**λ=0.5** (3 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.38 | 7190 | 71.9% |
| 0.84 | 1630 | 16.3% |
| 0.87 | 738 | 7.4% |

**λ=1.0** (best, 3 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.38 | 7422 | 74.2% |
| 0.84 | 1630 | 16.3% |
| 0.87 | 738 | 7.4% |

### Reading the results

1. **λ=0.0 reproduces RQ44 exactly** (5 modes, width 0.94, OOB 1.0556, identical
   mode counts). This is the paired-bootstrap anchor: the same seed/B draw as
   RQ44, so any difference at λ>0 is purely the shrinkage penalty.

2. **Shrinkage eliminates the 0.01 "Mode S catch" mode.** At λ=0.0 the 0.01 mode
   is 9.0% of resamples (the resamples where in-bag composition makes 0.01 the
   only threshold that catches the 2 low-entropy Mode S windows). At λ=0.01 it
   is **gone** — replaced by a 0.14 mode (6.6%): the penalty `λ·|0.01−0.38| =
   0.0037` is small, but it is enough to flip resamples where 0.01 and 0.14
   nearly tie on sensitivity toward 0.14 (closer to 0.38). At λ≥0.5 the 0.14
   mode is itself pulled up to 0.38 (the penalty `0.5·|0.14−0.38| = 0.12` now
   exceeds the sensitivity gap). **This overturns RQ48's conclusion that the
   0.01 mode is "calibration-rule-invariant"** — a regularised objective removes
   it. RQ48's smoother rules (Youden's J, F1) could not, because they have no
   mechanism to penalise distance from a prior; shrinkage does.

3. **Shrinkage collapses the 0.33 mode into 0.38.** At λ=0.0, 0.33 (5.7%) is
   cpWER-equivalent to 0.38 but selected when the tie-break lands there. The
   penalty breaks the tie toward 0.38 (penalty 0 at 0.38 vs 0.005 at 0.33), so
   at λ>0 the 0.33 mass moves to 0.38.

4. **The high-threshold modes (0.84, 0.87) persist at every λ.** These are the
   modes RQ48 traced to the discontinuous "≥ 90% specificity" boundary. In
   resamples where 0.38's specificity drops below 0.90 (clean windows with
   entropy ≥ 0.38 land in-bag), 0.38 is **infeasible**. Shrinkage pulls toward
   0.38 but cannot select an infeasible threshold; it picks the *lowest feasible*
   threshold (closest to 0.38 within the feasible set), which is 0.84 / 0.87 in
   those resamples. The 0.95 mode (8.4% at λ=0.0) merges into 0.84 (the penalty
   prefers the lower of two feasible high thresholds), but 0.84 + 0.87 together
   remain 23.7% of resamples at λ=1.0. No λ removes them: the **hard specificity
   constraint**, not the calibration objective, generates them.

5. **OOB cpWER improves monotonically with λ** (1.0556 → 1.0536 → 1.0536 →
   1.0533 → 1.0517). The shrinkage-chosen thresholds are closer to 0.38, which is
   the good operating point (RQ44 showed the 0.38 mode gives median OOB cpWER
   1.043 with 97% < 1.10). By moving mass out of the bad 0.01/0.95 modes toward
   0.38, shrinkage improves out-of-sample cpWER. At λ=1.0, 83.7% of resamples are
   below 1.10 (vs 76.0% at λ=0.0).

6. **Width improves monotonically with λ** (0.94 → 0.73 → 0.73 → 0.55 → 0.49) as
   the low end of the percentile interval rises from 0.01 to 0.38 (the 0.01 mode
   is eliminated) and the high end falls from 0.95 to 0.87 (the 0.95 mode merges
   into 0.84). At λ=1.0 the interval is [0.38, 0.87] — half of RQ44's width.

## Hypothesis Verdicts

- **H61a — ≤ 2 modes: KILLED.** At the best λ (1.0), the distribution has 3
  modes ≥ 5% (0.38 74.2%, 0.84 16.3%, 0.87 7.4%). The shrinkage prior reduced
  RQ44's 5 modes to 3 — eliminating the 0.01 Mode S mode and the 0.33/0.95 modes
  — but the two high-threshold specificity-constraint modes (0.84, 0.87) survive
  because 0.38 is infeasible in those resamples. The kill is informative: it
  localises the residual modality to the **hard ≥ 90% specificity constraint**,
  not to the calibration objective. A smooth rule (Youden's J / F1, per RQ48)
  removes exactly these high-threshold modes; combining shrinkage with a smooth
  rule is the predicted path to ≤ 2 modes.

- **H61b — OOB cpWER ≤ 1.056: SUPPORTED (and improved).** At λ=1.0 the median
  OOB cpWER is **1.0517 < 1.056** — below RQ44's value, not merely equal. The
  shrinkage prior improves out-of-sample deployability because it moves mass from
  the bad-threshold modes (0.01, 0.95) into the good 0.38 mode. 83.7% of
  resamples are below 1.10 (vs 76.0% for RQ44). H61b is supported at **every** λ
  (all five are ≤ 1.056), so the deployability condition is robust to the
  regularisation strength.

- **H61c — width < 0.94: SUPPORTED (and improved).** At λ=1.0 the percentile
  interval is [0.38, 0.87], width **0.49 < 0.94** — roughly half of RQ44's width.
  The low end rises from 0.01 to 0.38 (Mode S mode eliminated) and the high end
  falls from 0.95 to 0.87 (0.95 merges into 0.84). H61c is supported at every
  λ > 0 (λ=0.01 already gives width 0.73). The shrinkage prior substantially
  stabilises the threshold, addressing H44b's kill directly.

**Best λ = 1.0** (deployable; fewest modes = 3; narrowest width = 0.49; then
smallest λ among ties — though λ=0.5 also has 3 modes, λ=1.0 has the narrower
width and lower OOB cpWER). All hypotheses are evaluated at λ=1.0; per-λ
verdicts are in the JSON for traceability.

## Honest Limitations

1. **Single meeting, 77 windows.** As in RQ44/RQ48, all resamples draw from the
   same 77 windows of `M_R003S02C01`. The 0.84/0.87 high-threshold modes are
   driven by this meeting's clean windows with entropy ≥ 0.38 that drag 0.38's
   specificity below 0.90 in some resamples; a different meeting would produce a
   different high-threshold structure. RQ61 answers "does a shrinkage prior
   reduce the modality under resampling of this meeting?" — it does NOT answer
   "does the shrinkage threshold transfer to a new meeting?". Multi-meeting
   calibration remains the prerequisite (RQ25/RQ44/RQ48 conclusion).

2. **H61a killed by the specificity constraint, not by shrinkage's weakness.**
   The 3 residual modes at λ=1.0 are 0.38 (feasible-prior) + 0.84/0.87
   (infeasible-prior fallbacks). No λ can remove the latter because the ≥ 90%
   specificity constraint is hard. The kill localises the residual modality
   precisely: it is the **same high-threshold rule artefact RQ48 identified**,
   and RQ48 showed Youden's J / F1 eliminate it. The natural next experiment
   (shrinkage + F1) is therefore predicted to reach ≤ 2 modes; RQ61 does not run
   it (out of scope: one clear module per RQ).

3. **Prior is RQ44's bootstrap median, not an external Bayes prior.** `prior_mean
   = 0.38` is data-derived (RQ44's bagged median on this meeting). A fully
   Bayesian treatment would place a prior over the threshold informed by
   multi-meeting data; RQ61's "shrinkage" is a regularised point-estimate
   calibration toward a data-derived centre, which is the deployable
   interpretation of RQ57's "shrinkage/regularised" recommendation. The prior is
   feasible in-sample (spec 0.925), so the in-sample choice is 0.38 at every λ;
   the shrinkage effect is purely a bootstrap-resampling phenomenon.

4. **λ grid is coarse (5 values).** The mode count plateaus at 3 for λ ∈ {0.5,
   1.0}; a finer grid (e.g. λ=2.0, 5.0) might collapse 0.84/0.87 further *if*
   higher λ makes a lower feasible threshold win — but the persistence of 0.84
   (16.3%) and 0.87 (7.4%) at λ=1.0 with identical counts to λ=0.5 suggests
   these resamples have NO feasible threshold below 0.84, so larger λ cannot
   help. This is testable in a follow-up but is unlikely to change H61a.

5. **Same detector limitation as RQ44/RQ48.** RQ61 changes only the calibration
   objective, not the detector. The 0.01 mode (now eliminated by shrinkage)
   existed because the lang-id entropy detector cannot distinguish Mode S
   (monoscript Chinese semantic hallucination) from clean Chinese on the entropy
   axis. Shrinkage removes the *calibration symptom* (the 0.01 threshold) by
   penalising distance from 0.38; it does NOT give the detector the ability to
   separate Mode S. A complementary Mode S detector (RQ19) remains the
   principled fix.

6. **cpWER is utterance-level.** As in RQ44/RQ48 (limitation 6/7), cpWER passes
   each speaker's full Chinese utterance as a single token; cpWER > 1.0 measures
   extra inserted speaker-streams, not character accuracy. A char-level
   re-validation (RQ31/RQ35) remains the follow-up before claiming
   generalisation at character granularity.

7. **λ=0 equivalence is empirical, not analytical.** The unit test
   `test_lam_zero_matches_rq44_on_small_bootstrap` verifies the λ=0 ↔ RQ44
   equivalence on a 50-resample draw and the in-sample data; the full B=10000
   match is confirmed by the identical mode table (5 modes, identical counts to
   RQ44's reported 6044/1451/899/844/573). The equivalence rests on matching
   tie-break semantics (higher objective → higher specificity → lower threshold),
   which the tests pin.

## Reproducibility

- Script:
  `/opt/homebrew/bin/python3 results/frontier/shrinkage_threshold_calibration/shrinkage_threshold_analysis.py`
  (deterministic; numpy + stdlib only; no scipy / sklearn / Whisper / meeteval /
  LLM). Runtime ≈ 2.5 s for all 5 λ × B=10000.
- Tests: `/opt/homebrew/bin/python3 -m unittest tests.test_shrinkage_threshold -v`
  (78 tests; pins `shrinkage_objective`, `calibrate_shrinkage`,
  `_summarise_lambda`, `select_best_lambda`, the λ=0 ↔ RQ44 equivalence
  (in-sample + 50-resample bootstrap), the shrinkage "pull toward prior" effect
  on synthetic Mode-S-style data, the verbatim reuse of RQ44's bootstrap
  framework and RQ48's `count_modes`, module constants, the H61a/b/c kill
  conditions, and a real-data smoke test reproducing RQ44's 0.38 threshold and
  1.043 cpWER).
- Outputs:
  - `shrinkage_threshold_results.csv` — per-λ summary (in-sample
    threshold/cpWER, threshold median/percentiles/width/n_unique/n_modes≥5%, OOB
    cpWER median/mean/percentiles/frac<1.10/frac<RQ44, H61a/b/c verdicts).
  - `shrinkage_threshold_results.json` — full summary (in-sample calibration per
    λ, per-λ threshold + OOB cpWER distributions with mode tables, per-λ
    hypothesis verdicts, best-λ selection, headline hypothesis verdicts) plus
    `per_bootstrap` arrays (thresholds, oob_cpwer, n_oob) for all 5 λ for
    reproducibility.
- Bootstrap: B=10000, seed=42, paired across λ (same resample indices for all 5
  λ). λ=0.0 reproduces RQ44's B=10000 draw exactly.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

RQ44 left a 6-modal threshold distribution that RQ48 decomposed into rule
artefacts (high-threshold modes) + a "fundamental" Mode S mode (0.01). RQ49/RQ57
showed stratification cannot reduce it. RQ57 recommended a regularised
calibration rule. RQ61 **validates that recommendation and sharpens the
decomposition**:

1. **Shrinkage is the first lever to reduce RQ44's modality AND improve both
   width and OOB cpWER.** At λ=1.0: 5 → 3 modes, width 0.94 → 0.49, OOB 1.056 →
   1.0517. H61b and H61c supported with improvements; H61a killed (3 > 2). The
   deployable recommendation is unchanged — **deploy 0.38** — now reinforced by
   a shrinkage-calibrated threshold that is more stable *and* better
   out-of-sample than the un-regularised baseline.

2. **RQ48's "0.01 mode is calibration-rule-invariant" conclusion is OVERTURNED.**
   RQ48 tried 3 alternative calibration rules (Youden's J, F1, cost-aware); none
   removed the 0.01 Mode S mode, and RQ48 concluded it is a fundamental detector
   ambiguity. RQ61 shows a **regularised objective** (penalise distance from the
   prior) eliminates it — even at λ=0.01. The distinction: RQ48's rules change
   *what is optimised*; shrinkage changes *how ties are broken* (toward the
   prior). The 0.01 mode was not fundamental — it was a tie-breaking choice that
   shrinkage redirects. This re-opens the 0.01 mode as a calibration-targetable
   symptom (while the underlying Mode S detector limitation, RQ19, remains).

3. **The residual modality is precisely localised.** At λ=1.0 the 3 modes are
   0.38 (feasible-prior) + 0.84/0.87 (infeasible-prior fallbacks). The latter
   are the **same high-threshold rule artefacts RQ48 showed Youden's J / F1
   eliminate**. The natural next experiment is therefore **shrinkage + a smooth
   rule** (e.g. maximise `F1 − λ·|t − 0.38|`): shrinkage kills the 0.01 mode, the
   smooth rule kills the 0.84/0.87 modes, and the combination is predicted to
   reach ≤ 2 modes (H61a's target). This is a concrete, low-risk follow-up
   (RQ62 candidate) that RQ61's decomposition directly motivates.

4. **RQ57's "shrinkage/regularised" recommendation is validated.** After RQ49
   (speaker-count) and RQ57 (duration) stratification both failed, RQ57 proposed
   a different calibration rule as the next lever. RQ61 confirms: a regularised
   calibration rule reduces modality where two stratification variables could
   not. The lever is the calibration objective, not the data slice.
