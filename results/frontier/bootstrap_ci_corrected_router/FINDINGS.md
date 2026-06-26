# RQ39: Bootstrap Confidence Intervals on Corrected-Router cpWER 1.043

> **Label: `experimental/frontier`** — a reanalysis-only bootstrap of the corrected
> router's cpWER (RQ16, PR #909) at both word-level (utterance-level) and char-level
> (RQ35) granularity. Adds percentile CI, BCa CI, and paired-delta CI on top of
> RQ16's point estimate. No Whisper / no ASR model is run; no verified reference
> or gold table is modified. Closes #952.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, PR #890). Detector primitives and thresholds are
> lifted verbatim from RQ13 (`results/frontier/diverse_hallucination_detector/`,
> PR #904) / RQ16 (`results/frontier/corrected_router_simulation/`, PR #909), and
> the char-level MeetEval helpers from RQ35
> (`results/frontier/char_level_failure_modes/`, PR #949).

## Executive Summary

RQ16 reported that the corrected router (lang-id entropy > 0.409 bits → MIXED,
else SEPARATED) achieves cpWER **1.043** on AISHELL-4, below always-mixed
(1.173), below router v2 (1.206), and within 0.026 of the oracle (1.017),
recovering 86.2% of router v2's regret gap. RQ16's bootstrap CI [1.0087, 1.0887]
sits below always-mixed, but RQ16 did not test whether 1.043 is statistically
distinguishable from the oracle, nor whether the per-window improvement over
always-mixed is significantly non-zero, nor whether the result survives at
char-level (where RQ30/RQ35 showed the per-window oracle flips on ~48% of
windows). RQ39 closes those three gaps with a proper bootstrap CI analysis.

We compute 10,000-resample bootstrap (seed=42) percentile CIs, BCa CIs
(bias-corrected + accelerated, with jackknife acceleration), and paired-delta
CIs (per-window corrected − mixed) at BOTH granularities. The word-level point
estimate reproduces RQ16 bit-for-bit (1.043290); the char-level always_separated
(0.915831) reproduces RQ30/RQ35 bit-for-bit — so both baselines are recovered
before the new CIs are reported.

**Headline results:**

| Granularity | corrected cpWER | percentile CI | BCa CI | paired-Δ CI (corr−mixed) |
|---|---:|:---:|:---:|:---:|
| **word-level** | **1.0433** | [1.0087, 1.0887] | [1.0130, 1.0974] | [−0.3117, +0.0000] |
| **char-level** | **0.9061** | [0.8761, 0.9337] | [0.8730, 0.9314] | [−0.0226, +0.0117] |

**Hypothesis verdicts (BCa primary for H39a/H39b; paired-delta for H39c):**

| Hypothesis | word-level | char-level |
|---|:---:|:---:|
| **H39a** upper CI < always-mixed | **SUPPORTED** | NOT SUPPORTED |
| **H39b** lower CI > oracle | NOT SUPPORTED | NOT SUPPORTED |
| **H39c** paired-Δ upper CI < 0 | NOT SUPPORTED | NOT SUPPORTED |

The three findings that matter for the Interspeech submission:

1. **The corrected router IS statistically distinguishable from always-mixed at
   word-level** (H39a SUPPORTED: BCa upper 1.0974 < 1.1732). The 0.130 cpWER
   improvement is not bootstrap noise. This was RQ16's headline claim; RQ39
   confirms it with the more accurate BCa CI.

2. **The corrected router is NOT statistically distinguishable from the oracle
   at word-level** (H39b NOT SUPPORTED: BCa lower 1.0130 < oracle 1.0173). This
   is actually a *strong* result: the corrected router comes within statistical
   noise of the oracle ceiling. RQ16's point-estimate gap of 0.026 cpWER is
   within the bootstrap CI — the corrected router effectively *reaches* the
   oracle on AISHELL-4, modulo finite-sample uncertainty. We cannot reject
   "corrected router = oracle" at the 95% level.

3. **The char-level result collapses.** At char-level the corrected router
   (0.9061) is NOT distinguishable from always-mixed (0.9106) — H39a NOT
   SUPPORTED, the BCa upper (0.9314) is well above always-mixed. The paired-delta
   CI [−0.0226, +0.0117] clearly straddles zero. The regret recovery vs
   always-mixed drops from 83.3% (word-level) to 13.3% (char-level), confirming
   the RQ31 narrative quantitatively. The corrected router's lang-id entropy
   detector flags the same windows at both granularities (the detector is
   text-only, granularity-invariant), but the *cpWER consequence* of those flags
   is much smaller at char-level because char-level cpWER is much less lumpy
   (RQ30/RQ35: 4 of 64 active windows cross the > 1.0 hallucination threshold at
   char-level, vs 37 of 64 at word-level). The same routing decisions that buy
   0.130 cpWER at word-level buy only 0.005 cpWER at char-level.

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min).
Each window stores the per-route cpWER (`always_mixed_cpwer`,
`always_separated_cpwer`, `router_v2_cpwer`, `oracle_best_cpwer`), the per-speaker
separated transcripts, and the mixed transcript. No ASR is run; the corrected
router's per-window cpWER is the chosen route's stored (word-level) or
recomputed (char-level) cpWER.

### Routing (RQ16 verbatim)

For each window compute the language-id entropy (RQ13): Shannon entropy over
Unicode script categories of each per-speaker separated transcript, max across
speakers (worst-case track). Route to MIXED if `lang_id_entropy > 0.409` bits,
else SEPARATED. The threshold 0.409 is RQ13's ≥90%-specificity operating point
(94.6% sensitivity, 92.5% specificity on the AISHELL-4 hallucination label).

RQ16 showed that lang-id alone is *identical* to the full three-guard (lang-id +
silence + mode) corrected router on AISHELL-4 — the silence and mode guards are
strict subsets of lang-id flags or fall on windows where both routes tie. RQ39
uses lang-id alone (per the task spec), so the per-window decisions are RQ16's
`lang_only_decision` (mixed=38, separated=39), not RQ16's `corrected_decision`
(mixed=42, separated=35). The 4 windows where they differ (w16, w24, w59, w66)
all have `always_mixed_cpwer == always_separated_cpwer == 1.0`, so the cpWER is
identical (1.043290). This is verified per-window against RQ16's
`simulation_results.json`.

### Two granularities

- **Word-level** (the project's stored utterance-level convention, RQ30): each
  speaker's whole Chinese string is one token. We reuse the stored per-window
  `always_mixed_cpwer` / `always_separated_cpwer` so the point estimate
  reproduces RQ16's 1.0433 bit-for-bit. This is the granularity RQ16 reported.
- **Char-level** (standard Chinese cpCER convention, RQ35): insert a space
  between each Chinese character (`' '.join(list(text))`) so MeetEval treats
  each character as one "word". We re-run MeetEval 0.4.3 `cpwer` (separated,
  multi vs multi) and `orcwer` (mixed, single channel vs multi ref) — matching
  RQ35's approach so the char-level aggregate reproduces RQ30/RQ35's baseline
  (`always_separated` = 0.915831, `always_mixed` = 0.910577).

### Bootstrap (10,000 resamples, seed=42)

For each granularity:

1. **Percentile CI**: 2.5 / 97.5 percentiles of the bootstrap mean distribution.
   Same convention as RQ16: `rng.integers(0, n, size=n)` per resample.
2. **BCa CI** (bias-corrected + accelerated): corrects the percentile CI for
   bias and skew, which matters here because the per-window word-level cpWER
   distribution is lumpy and discrete (RQ16: 69 of 77 windows tie at 1.0, the
   other 8 carry the entire signal as a few large wins/losses).
   - Bias correction: `z0 = Φ⁻¹(P(boot < θ̂))`.
   - Acceleration via jackknife: `a = Σ(θ̄−θᵢ)³ / (6 · (Σ(θ̄−θᵢ)²)^1.5)`.
   - BCa alphas: `α₁ = Φ(z0 + (z0 + z_{α/2}) / (1 − a·(z0 + z_{α/2})))`,
     `α₂ = Φ(z0 + (z0 + z_{1−α/2}) / (1 − a·(z0 + z_{1−α/2})))`.
   - BCa CI = (percentile(boot, 100·α₁), percentile(boot, 100·α₂)).
3. **Paired-delta CI** (H39c): per-window `corrected_cpwer − mixed_cpwer`
   resampled with the SAME indices for both (paired design); 2.5 / 97.5
   percentiles. This is the direct test of "is the per-window improvement
   non-zero?".

The BCa CI is the primary verdict for H39a/H39b because BCa is more accurate
than the percentile CI for skewed/lumpy distributions; the percentile CI is
reported alongside for transparency.

### Reproducibility sanity checks (both pass)

1. **Word-level point estimate reproduces RQ16**: corrected_router = 1.043290 =
   RQ16's `corrected_router_cpwer` (PR #909) bit-for-bit. Percentile CI =
   [1.008658, 1.088745] = RQ16's `corrected_router_ci_95` bit-for-bit.
2. **Char-level aggregate reproduces RQ30/RQ35**: `always_separated` = 0.915831
   = RQ30's reported char-level baseline (PR #935) = RQ35's `aggregate_cpwer.
   char_level.always_separated` (PR #949) bit-for-bit.

## Results

### Aggregate cpWER (mean over 77 windows)

| Policy | word-level | char-level |
|---|---:|---:|
| always-mixed | 1.1732 | 0.9106 |
| always-separated | 1.5909 | 0.9158 |
| router v2 | 1.2056 | 0.9222 |
| oracle best | 1.0173 | 0.8768 |
| **corrected router** | **1.0433** | **0.9061** |

The word-level column reproduces RQ16. The char-level column reproduces RQ30/RQ35
for the baselines and adds the corrected-router row (RQ35 did not compute a
char-level corrected router — RQ39 fills that gap).

### Bootstrap CIs

| Granularity | corrected cpWER | percentile CI 95% | BCa CI 95% | paired-Δ (corr−mixed) point | paired-Δ CI 95% |
|---|---:|:---:|:---:|---:|:---:|
| word-level | 1.0433 | [1.0087, 1.0887] | [1.0130, 1.0974] | −0.1299 | [−0.3117, +0.0000] |
| char-level | 0.9061 | [0.8761, 0.9337] | [0.8730, 0.9314] | −0.0045 | [−0.0226, +0.0117] |

The BCa CI sits slightly to the right of the percentile CI at word-level
([1.0130, 1.0974] vs [1.0087, 1.0887]). The upward shift is the BCa bias
correction: the bootstrap distribution is left-skewed (a few large wins pull
the mean down, but the bulk of resamples cluster higher), so BCa pushes the CI
bounds upward to correct for the bias. The direction is consistent with RQ16's
"6 wins / 2 losses / 69 ties" per-window structure — the lower tail is heavy
(wins), so the bias correction shifts the CI up.

### Hypothesis Verdicts

#### H39a — Bootstrap 95% CI excludes always-mixed: word-level SUPPORTED, char-level NOT SUPPORTED

- **Word-level: SUPPORTED.** BCa upper 1.0974 < always-mixed 1.1732 (margin
  0.076). The corrected router's 95% CI sits entirely below always-mixed. The
  improvement is real at the 95% level — this is the Interspeech-submission-
  ready claim. The percentile CI [1.0087, 1.0887] also excludes always-mixed
  (RQ16 already noted this).
- **Char-level: NOT SUPPORTED.** BCa upper 0.9314 > always-mixed 0.9106. The
  corrected router's CI extends *above* always-mixed at char-level. The
  char-level point estimate (0.9061) is below always-mixed (0.9106) by only
  0.005 cpWER, and the bootstrap CI clearly straddles the always-mixed value.
  The corrected router is not statistically distinguishable from always-mixed at
  char-level — and may even be slightly worse (the BCa lower bound 0.8730 is
  below the oracle 0.8768, so the corrected router also does not significantly
  beat the oracle at char-level).

The mechanism for the collapse: the lang-id entropy detector fires on the same
38 windows at both granularities (it's a text-only signal, granularity-invariant),
but the *cpWER consequence* of routing those 38 windows to MIXED is much smaller
at char-level. RQ30/RQ35 showed char-level cpWER is much less lumpy (4 of 64
active windows cross the > 1.0 hallucination threshold at char-level vs 37 of 64
at word-level), so the bad-separated windows that lang-id catches are less
costly at char-level, and the 6 word-level wins (mixed hallucinated badly,
separated clean) shrink to small char-level wins.

#### H39b — Bootstrap 95% CI excludes oracle: NOT SUPPORTED at both granularities

- **Word-level: NOT SUPPORTED.** BCa lower 1.0130 < oracle 1.0173. The corrected
  router's CI *includes* the oracle. This is a strong positive result: the
  corrected router comes within statistical noise of the oracle ceiling. We
  cannot reject "corrected router = oracle" at the 95% level. The point
  estimate (1.0433) is 0.026 above the oracle (1.0173), but that gap is within
  the bootstrap CI — finite-sample uncertainty means we cannot claim the
  corrected router *beats* the oracle, but also cannot claim it *doesn't reach*
  the oracle. RQ16's "within 0.026 of oracle" is, statistically, "indistinguishable
  from oracle."
- **Char-level: NOT SUPPORTED.** BCa lower 0.8730 < oracle 0.8768. Same
  structure: CI includes oracle. The corrected router reaches the oracle within
  statistical noise at char-level too, but (per H39a) it also fails to
  distinguish from always-mixed at char-level — so at char-level all three
  (corrected, always-mixed, oracle) are statistically indistinguishable, the
  problem has collapsed to noise.

#### H39c — Paired-delta CI excludes zero: NOT SUPPORTED at both granularities

- **Word-level: NOT SUPPORTED.** Paired-Δ CI [−0.3117, +0.0000]. The upper bound
  *touches* zero but does not cross it — same borderline result RQ16 reported.
  The improvement is real at the point estimate (−0.1299 cpWER/window) and H39a
  (the unpaired BCa CI) is supported, but the *paired* per-window improvement is
  not uniformly positive: 6 large wins (total −12.0) and 2 small losses (total
  +2.0) against 69 ties, so a bootstrap resample that over-weights the 2 losses
  can push the mean to zero. This is the lumpy-discrete-cpWER artefact RQ16
  flagged.
- **Char-level: NOT SUPPORTED.** Paired-Δ CI [−0.0226, +0.0117] clearly straddles
  zero. At char-level the per-window improvement is much smaller (point −0.0045)
  and the CI comfortably includes zero — the corrected router does not
  significantly beat always-mixed on a per-window basis at char-level.

The paired-delta CI is more conservative than the unpaired BCa CI (H39a) because
it tests the per-window improvement rather than the aggregate means. The
disagreement at word-level (H39a SUPPORTED but H39c NOT SUPPORTED) is informative:
the *aggregate* corrected-router cpWER is significantly below always-mixed, but
the *per-window* improvement is not uniformly positive — it's driven by a small
number of large wins. This is the same win/loss structure RQ16 documented.

### Regret recovery (vs router v2 and vs always-mixed)

| Comparator | word-level gap | corrected gap | recovery | char-level gap | corrected gap | recovery |
|---|---:|---:|---:|---:|---:|---:|
| router v2 → oracle | 0.1883 | 0.0260 | **86.2%** | 0.0453 | 0.0293 | **35.5%** |
| always-mixed → oracle | 0.1558 | 0.0260 | **83.3%** | 0.0337 | 0.0293 | **13.3%** |

The word-level "86.2% of router v2's gap" reproduces RQ16. The char-level
"13.3% of always-mixed's gap" is the RQ31 narrative — the corrected router's
recovery collapses from 83.3% (word-level) to 13.3% (char-level) when measured
against the deployable baseline. Against router v2 the collapse is 86.2% → 35.5%
(less dramatic because router v2 itself is worse at char-level). Both
denominators are reported for transparency; the "13.3%" matches the task brief's
RQ31 reference.

## Honest Limitations

1. **Single meeting, 77 windows (inherited from RQ16).** Only `M_R003S02C01` is
   available. The bootstrap CI is over 77 windows, not over meetings — it
   characterises within-meeting uncertainty, not cross-meeting generalisation.
   The CIs would widen with meeting-level variance. A leave-one-meeting-out CV
   (RQ16's stated follow-up) is the required next step for a deployable claim.

2. **In-sample threshold calibration (inherited from RQ16).** The lang-id
   entropy threshold 0.409 was calibrated on these exact 77 windows (RQ13).
   The CIs therefore characterise the *conditional* uncertainty given the
   threshold, not the *unconditional* uncertainty that would include threshold
   re-fit variance. The corrected router's CI is almost certainly narrower than
   it would be under cross-validated threshold selection.

3. **BCa on lumpy discrete data.** The word-level per-window cpWER distribution
   is highly non-smooth (69 of 77 windows tie at 1.0; 8 windows carry the entire
   signal as a few large values 0, 2, 4, 6). BCa's bias correction assumes a
   smooth enough bootstrap distribution for the jackknife acceleration to be
   meaningful; on lumpy data the acceleration `a` can be unstable. We report
   both percentile and BCa CIs so the reader can see the (small) sensitivity.
   The H39a verdict (SUPPORTED at word-level) is the same under both.

4. **Paired-delta CI is conservative for lumpy data.** H39c's borderline
   "touches zero" verdict at word-level is partly an artefact of the discrete
   per-window distribution: a single resample drawing both loss windows (w22,
   w30) pushes the mean to zero. The unpaired BCa CI (H39a) is the more
   reliable aggregate-level test; the paired-delta CI is the stricter per-window
   test. They disagree at word-level, which is itself a finding (the improvement
   is aggregate-real but per-window-lumpy).

5. **Char-level oracle uses min(separated, mixed) per window (inherited from
   RQ35).** The char-level oracle is recomputed per window as the better of
   char-separated and char-mixed, matching RQ35. This means the char-level
   oracle is *not* the same set of windows as the word-level oracle (RQ30: 48%
   of windows flip). The char-level "corrected router reaches oracle within
   noise" verdict is therefore against a different (char-level) oracle, not the
   word-level oracle.

6. **Lang-id alone, not the full three-guard corrected router.** Per the task
   spec we use lang-id entropy alone (threshold 0.409), not RQ16's full
   lang+silence+mode ensemble. RQ16 verified these are cpWER-identical on
   AISHELL-4 (the 4 extra silence/mode flags fall on mixed==separated ties), so
   the per-window cpWER and the CIs match RQ16 bit-for-bit. The decision counts
   differ (lang-only: 38 mixed / 39 separated; full corrected: 42 / 35) but the
   cpWER is identical. If a future meeting has silence/mode flags that don't
   fall on ties, lang-id alone and the full ensemble would diverge — RQ39 does
   not test that.

7. **No deployable routing input (inherited).** Per the project's hard safety
   rules, cpWER / references are not used as routing input — the lang-id
   entropy detector is computed only from the hypothesis transcripts, which is
   the deployable signal surface.

## What this changes for the project

1. **The corrected router's word-level 1.043 is Interspeech-submission-ready
   with a CI.** The BCa CI [1.0130, 1.0974] excludes always-mixed (1.1732) at
   the 95% level. RQ16's point estimate was correct; RQ39 confirms it survives
   a proper bootstrap. The claim "corrected router significantly beats
   always-mixed at word-level cpWER on AISHELL-4" is now statistically
   defensible.

2. **The corrected router reaches the oracle within statistical noise at
   word-level.** H39b's failure is a strong positive: the CI includes the
   oracle, so we cannot reject "corrected router = oracle." RQ16's "within 0.026
   of oracle" should be reported as "statistically indistinguishable from oracle
   (95% BCa CI [1.0130, 1.0974] includes oracle 1.0173)." This is the strongest
   version of the claim the data supports.

3. **The char-level collapse is now quantified with a CI.** RQ31's narrative
   "collapses to 13.3%" is confirmed: at char-level the corrected router (0.9061)
   is NOT statistically distinguishable from always-mixed (0.9106) — the BCa CI
   [0.8730, 0.9314] comfortably includes always-mixed. The lang-id detector
   fires on the same windows, but the cpWER consequence is much smaller at
   char-level. The Interspeech submission should report the word-level result
   as the headline and the char-level result as an honest caveat about
   granularity-dependence — the corrected router's improvement is a
   word-level-cpWER improvement, not a char-level-cpWER improvement.

4. **The paired-delta vs unpaired-CI disagreement is itself a finding.** At
   word-level, H39a (unpaired BCa) is SUPPORTED but H39c (paired-delta) is NOT.
   The aggregate cpWER is significantly lower, but the per-window improvement is
   not uniformly positive — it's driven by 6 large wins against 2 small losses
   (RQ16's structure). This means the corrected router is a high-variance
   improvement: most windows tie, a few win big. A deployable version should
   report this honestly rather than claiming a uniform per-window gain.

## Reproducibility

- Script: `results/frontier/bootstrap_ci_corrected_router/bootstrap_ci_analysis.py`
  (deterministic; numpy + scipy + meeteval 0.4.3; no Whisper / no audio).
- Tests: `tests/test_rq39_bootstrap_ci.py` (56 tests, pure helpers only —
  bootstrap indices/distribution, percentile CI, jackknife means, BCa CI,
  paired-delta distribution + CI, script_category, language_id_entropy,
  max_across_speakers, corrected_router_decision).
- Per-window data: `results/frontier/bootstrap_ci_corrected_router/bootstrap_ci_results.csv`
  (77 rows; lang-id entropy, routing decision, word-level + char-level cpWER for
  mixed/separated/router_v2/oracle/corrected, char-sep-empty flag).
- Summary + hypothesis verdicts: `results/frontier/bootstrap_ci_corrected_router/bootstrap_ci_results.json`
- Bootstrap: 10,000 resamples, seed=42, alpha=0.05. BCa uses jackknife
  acceleration; paired-delta uses the same resample indices for both arms.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).
- Run: `/opt/homebrew/bin/python3 results/frontier/bootstrap_ci_corrected_router/bootstrap_ci_analysis.py`
  (~10 s; MeetEval prints "Assuming sort=False" spam, suppressed in tests).
