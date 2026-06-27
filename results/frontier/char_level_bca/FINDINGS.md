# RQ55: Char-level BCa CI on the Corrected Router

> **Label: `experimental/frontier`** — a reanalysis-only bootstrap of the corrected
> router's char-level cpWER. RQ39 (PR #960) computed the word-level BCa CI
> `[1.0130, 1.0974]` and found it *includes* the oracle (1.0173): the corrected
> router reaches the oracle within statistical noise at word-level. RQ31 (PR #950)
> showed char-level cpWER shrinks the separation tax ~79.5x (0.418 → 0.005) and
> that Mode S disappears at char-level. RQ55 asks whether the char-level BCa CI —
> which is narrower — excludes the char-level oracle, which would be a stronger
> statistical claim than RQ39's word-level "reaches oracle within noise." No
> Whisper / no ASR model is run; no verified reference or gold table is modified.
> Closes #978.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, PR #890). Detector primitives and char-level
> MeetEval helpers are lifted verbatim from RQ31
> (`results/frontier/char_level_cpwer_revalidation/`, PR #950) / RQ13 / RQ16, and
> the bootstrap / BCa CI framework is lifted verbatim from RQ39
> (`results/frontier/bootstrap_ci_corrected_router/`, PR #960).

## Executive Summary

RQ39 found that the corrected router's **word-level** BCa CI `[1.0130, 1.0974]`
includes the oracle (1.0173): the corrected router is statistically
indistinguishable from the oracle ceiling at word-level — a strong positive
("reaches oracle within noise") but not a "beats oracle" claim. RQ31 showed
char-level cpWER shrinks the separation tax ~79.5x, raising the question: at
char-level, where cpWER is less lumpy, does the corrected router's BCa CI — now
narrower — exclude the oracle?

RQ55 computes the char-level BCa CI (10,000 resamples, seed=42, jackknife
acceleration) on the corrected router (lang-id entropy threshold 0.38; verified
identical routing to RQ13's 0.409 operating point — no window has entropy in
(0.38, 0.409]) and tests three pre-registered hypotheses against the char-level
oracle. The char-level corrected-router point estimate (0.9061) and BCa CI
`[0.8730, 0.9314]` reproduce RQ39's char-level analysis bit-for-bit, confirming
reproducibility. The word-level BCa CI `[1.0130, 1.0974]` also reproduces RQ39
exactly.

**Headline results:**

| Granularity | corrected cpWER | percentile CI | BCa CI | BCa width |
|---|---:|:---:|:---:|---:|
| **word-level** | **1.0433** | [1.0087, 1.0887] | [1.0130, 1.0974] | 0.0844 |
| **char-level** | **0.9061** | [0.8761, 0.9337] | [0.8730, 0.9314] | 0.0584 |

**Hypothesis verdicts:**

| Hypothesis | Verdict | Detail |
|---|:---:|---|
| **H55a** char BCa CI excludes oracle | **KILLED** | BCa `[0.8730, 0.9314]` includes oracle 0.8768 |
| **H55b** char BCa width < word BCa width (0.0844) | **SUPPORTED** | char width 0.0584 < word width 0.0844 (31% narrower) |
| **H55c** corrected char < mixed char | **SUPPORTED** | 0.9061 < 0.9106, Δ = −0.0045 (paired CI straddles zero) |

The three findings that matter:

1. **The char-level BCa CI does NOT exclude the oracle (H55a KILLED).** The
   corrected router's char-level BCa CI `[0.8730, 0.9314]` includes the char-level
   oracle (0.8768). The BCa *lower* bound (0.8730) dips below the oracle (0.8768)
   by 0.0038 — a BCa bias-correction artefact on lumpy data, not evidence that the
   corrected router *beats* the oracle (per construction `corrected >= oracle`
   every window, since oracle = min(mixed, separated) and the corrected router
   picks one of mixed/separated). The narrower char-level CI does not buy a
   "beats oracle" claim; the corrected router still only *reaches* the oracle
   within statistical noise at char-level, exactly as at word-level.

2. **The char-level BCa CI IS narrower than the word-level BCa CI (H55b
   SUPPORTED).** Char-level BCa width 0.0584 vs word-level 0.0844 — a 31%
   reduction. This is the expected consequence of RQ30/RQ35's finding that
   char-level cpWER is less lumpy (4 of 64 active windows cross the > 1.0
   hallucination threshold at char-level vs 37 of 64 at word-level): a smoother
   per-window distribution gives a tighter bootstrap. But the narrower CI is not
   narrow *enough* to exclude the oracle — the oracle sits inside the CI in both
   granularities.

3. **The corrected router still beats always-mixed at the char-level point
   estimate (H55c SUPPORTED), but not significantly.** Corrected char-level
   cpWER 0.9061 < always-mixed 0.9106 (Δ = −0.0045). However, the paired-delta
   CI `[−0.0226, +0.0117]` clearly straddles zero, so the per-window improvement
   is not statistically significant — confirming RQ39's H39c char-level finding.
   The recovery fraction vs always-mixed's gap to oracle is 13.3% (RQ31's
   narrative), vs 83.3% at word-level.

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min).
Each window stores the per-route word-level cpWER
(`always_mixed_cpwer`, `always_separated_cpwer`, `oracle_best_cpwer`), the
per-speaker separated transcripts, and the mixed transcript. No ASR is run; the
corrected router's per-window char-level cpWER is the chosen route's recomputed
char-level cpWER.

### Routing (lang-id entropy threshold 0.38)

For each window compute the language-id entropy (RQ13): Shannon entropy over
Unicode script categories of each per-speaker separated transcript, max across
speakers (worst-case track). Route to MIXED if `lang_id_entropy > 0.38` bits,
else SEPARATED.

**Threshold verification:** The RQ55 task spec specifies threshold 0.38, which
differs from RQ13/RQ16/RQ31/RQ39's 0.409. We verified that on AISHELL-4 no window
has lang-id entropy in (0.38, 0.409] (the entropy distribution is bimodal: 0 for
clean monoscript Chinese, > 0.5 for diverse multilingual gibberish), so the
routing decisions are identical at both thresholds: 38 MIXED, 39 SEPARATED. The
char-level corrected-router cpWER (0.906097) and BCa CI `[0.873026, 0.931406]`
therefore reproduce RQ39's char-level analysis bit-for-bit, and the word-level
BCa CI `[1.012987, 1.097403]` reproduces RQ39's word-level analysis bit-for-bit.

### Char-level cpWER (RQ31 convention)

Char-level tokenisation: `' '.join(list(text))` for each Chinese string (the
standard cpCER convention — Chinese has no word delimiter, so each character is
a token). We re-run MeetEval 0.4.3 `cpwer` (separated, multi vs multi) and
`orcwer` (mixed, single channel vs multi ref), using RQ31's `safe_cpwer` /
`safe_orcwer` (with meeteval import guards and the project's empty-sentinel
convention). The char-level always-separated aggregate (0.915831) reproduces
RQ30/RQ35's baseline bit-for-bit.

### Bootstrap (10,000 resamples, seed=42)

1. **Percentile CI**: 2.5 / 97.5 percentiles of the bootstrap mean distribution.
   Same convention as RQ16/RQ39: `rng.integers(0, n, size=n)` per resample.
2. **BCa CI** (bias-corrected + accelerated): corrects the percentile CI for
   bias and skew (lifted verbatim from RQ39).
   - Bias correction: `z0 = Φ⁻¹(P(boot < θ̂))`.
   - Acceleration via jackknife: `a = Σ(θ̄−θᵢ)³ / (6 · (Σ(θ̄−θᵢ)²)^1.5)`.
   - BCa alphas: `α₁ = Φ(z0 + (z0 + z_{α/2}) / (1 − a·(z0 + z_{α/2})))`,
     `α₂ = Φ(z0 + (z0 + z_{1−α/2}) / (1 − a·(z0 + z_{1−α/2})))`.
   - BCa CI = (percentile(boot, 100·α₁), percentile(boot, 100·α₂)).
3. **Paired-delta CI** (H55c context): per-window `corrected_char − mixed_char`
   resampled with the SAME indices for both (paired design); 2.5 / 97.5
   percentiles.

The BCa CI is the primary verdict for H55a/H55b; the percentile CI is reported
alongside for transparency.

### Reproducibility sanity checks (all pass)

1. **Word-level BCa CI reproduces RQ39**: `[1.012987, 1.097403]` = RQ39's
   `word_level.bca_ci_95` (PR #960) bit-for-bit.
2. **Char-level BCa CI reproduces RQ39**: `[0.873026, 0.931406]` = RQ39's
   `char_level.bca_ci_95` bit-for-bit.
3. **Char-level baselines reproduce RQ30/RQ35**: `always_separated` = 0.915831
   = RQ30's char-level baseline (PR #935) bit-for-bit.
4. **Threshold 0.38 == 0.409 routing**: verified — no window has entropy in
   (0.38, 0.409]; both give 38 MIXED / 39 SEPARATED.

## Results

### Aggregate cpWER (mean over 77 windows)

| Policy | word-level | char-level |
|---|---:|---:|
| always-mixed | 1.1732 | 0.9106 |
| always-separated | 1.5909 | 0.9158 |
| oracle best | 1.0173 | 0.8768 |
| **corrected router** | **1.0433** | **0.9061** |

The word-level column reproduces RQ16/RQ39. The char-level column reproduces
RQ30/RQ35/RQ39 for the baselines and the corrected router.

### Bootstrap CIs (corrected router)

| Granularity | corrected cpWER | percentile CI 95% | BCa CI 95% | BCa width | paired-Δ (corr−mixed) CI 95% |
|---|---:|:---:|:---:|---:|:---:|
| word-level | 1.0433 | [1.0087, 1.0887] | [1.0130, 1.0974] | 0.0844 | [−0.3117, +0.0000] |
| char-level | 0.9061 | [0.8761, 0.9337] | [0.8730, 0.9314] | 0.0584 | [−0.0226, +0.0117] |

The char-level BCa CI is 31% narrower than the word-level BCa CI (0.0584 vs
0.0844). The narrowing is the expected consequence of char-level cpWER being
less lumpy (RQ30/RQ35: smoother per-window distribution → tighter bootstrap).

### Hypothesis Verdicts

#### H55a — char-level BCa CI excludes oracle: KILLED

- **KILLED.** Char-level BCa CI `[0.8730, 0.9314]` includes the char-level
  oracle (0.8768). The BCa lower bound (0.8730) is 0.0038 *below* the oracle
  (0.8768) — a BCa bias-correction artefact on lumpy data, not evidence that the
  corrected router *beats* the oracle. Per construction `corrected_char >=
  oracle_char` every window (oracle = min(mixed, separated); corrected router
  picks one of mixed/separated), so the corrected router can at most *tie* the
  oracle in aggregate. The BCa lower bound dipping below oracle reflects the
  bias correction pushing the CI left on a left-skewed bootstrap distribution,
  not a real "corrected router beats oracle" signal.
- The corrected router therefore *reaches* the oracle within statistical noise
  at char-level, exactly as at word-level (RQ39 H39b). The narrower char-level
  CI does not upgrade the claim from "reaches oracle within noise" to "beats
  oracle."

#### H55b — char-level BCa width < word-level BCa width: SUPPORTED

- **SUPPORTED.** Char-level BCa width 0.0584 < word-level BCa width 0.0844
  (RQ39's reference). The char-level CI is 31% narrower. This confirms that
  char-level cpWER's smoother per-window distribution (RQ30/RQ35) produces a
  tighter bootstrap — but the narrower CI is still not narrow enough to exclude
  the oracle (H55a KILLED).

#### H55c — corrected char < mixed char: SUPPORTED (point estimate), NOT significant

- **SUPPORTED (point estimate).** Char-level corrected-router cpWER 0.9061 <
  char-level always-mixed cpWER 0.9106, Δ = −0.0045. The corrected router still
  beats always-mixed at the char-level point estimate.
- **NOT statistically significant.** The paired-delta CI `[−0.0226, +0.0117]`
  straddles zero, so the per-window improvement is not statistically
  significant — confirming RQ39's H39c char-level finding. The corrected
  router's char-level win is a point-estimate win, not a statistical win.

### Regret recovery (vs always-mixed's gap to oracle)

| Granularity | mixed gap | corrected gap | recovery |
|---|---:|---:|---:|
| word-level | 0.1558 | 0.0260 | 83.3% |
| char-level | 0.0337 | 0.0293 | 13.3% |

The char-level "13.3% of always-mixed's gap" reproduces RQ31's narrative — the
corrected router's recovery collapses from 83.3% (word-level) to 13.3%
(char-level) when measured against the deployable baseline.

## Honest Limitations

1. **Single meeting, 77 windows (inherited from RQ16/RQ39).** Only
   `M_R003S02C01` is available. The bootstrap CI is over 77 windows, not over
   meetings — it characterises within-meeting uncertainty, not cross-meeting
   generalisation.

2. **In-sample threshold calibration (inherited).** The lang-id entropy
   threshold 0.38 (verified identical to RQ13's 0.409) was calibrated on these
   exact 77 windows. The CIs characterise the *conditional* uncertainty given
   the threshold, not the *unconditional* uncertainty that would include
   threshold re-fit variance.

3. **BCa on lumpy discrete data (inherited from RQ39).** The char-level
   per-window cpWER distribution is less lumpy than word-level (RQ30/RQ35), but
   still discrete. BCa's bias correction can push the lower bound below the
   oracle on left-skewed data — this is why H55a's BCa lower bound (0.8730) is
   below the oracle (0.8768) despite `corrected >= oracle` per window by
   construction. We report both percentile and BCa CIs so the reader can see
   the sensitivity; the percentile CI `[0.8761, 0.9337]` also includes the
   oracle (0.8768), with the lower bound 0.8761 just below oracle 0.8768.

4. **Char-level oracle uses min(separated, mixed) per window (inherited from
   RQ35).** The char-level oracle is recomputed per window as the better of
   char-separated and char-mixed. The char-level oracle is *not* the same set
   of windows as the word-level oracle (RQ30: 48% of windows flip).

5. **Threshold 0.38 == 0.409 on this dataset.** No window has entropy in
   (0.38, 0.409], so the routing is identical. RQ55's results therefore
   reproduce RQ39's char-level analysis bit-for-bit. The threshold choice does
   not affect the verdict on this dataset; on a different meeting where windows
   fall in (0.38, 0.409], the two thresholds would diverge.

6. **No deployable routing input (inherited).** Per the project's hard safety
   rules, cpWER / references are not used as routing input — the lang-id
   entropy detector is computed only from the hypothesis transcripts, which is
   the deployable signal surface.

## What this changes for the project

1. **The char-level BCa CI does NOT exclude the oracle.** RQ55 closes the
   question raised by RQ31's separation-tax shrinkage: even though char-level
   cpWER shrinks the tax ~79.5x and the BCa CI narrows by 31%, the corrected
   router still only *reaches* the oracle within statistical noise at
   char-level — it does not *beat* the oracle. The "beats oracle" claim is not
   available at either granularity. The strongest defensible claim remains
   RQ39's word-level "statistically indistinguishable from oracle (95% BCa CI
   includes oracle)."

2. **The narrower char-level CI is a real tightening but not a qualitative
   upgrade.** H55b confirms the char-level BCa CI is 31% narrower than the
   word-level CI (0.0584 vs 0.0844). This is consistent with char-level cpWER
   being less lumpy (RQ30/RQ35). But the oracle sits inside the CI at both
   granularities, so the narrower CI does not change the qualitative verdict.

3. **The corrected router's char-level advantage over always-mixed is a
   point-estimate win, not a statistical win.** H55c is SUPPORTED at the point
   estimate (0.9061 < 0.9106) but the paired-delta CI straddles zero
   `[−0.0226, +0.0117]`. The Interspeech submission should report the word-level
   result as the headline (where both the unpaired BCa CI H39a and the
   point-estimate H55c hold) and the char-level result as an honest caveat
   about granularity-dependence — the corrected router's improvement is a
   word-level-cpWER improvement, not a char-level-cpWER improvement.

## Reproducibility

- Script: `results/frontier/char_level_bca/char_level_bca_analysis.py`
  (deterministic; numpy + scipy + meeteval 0.4.3; no Whisper / no audio).
- Tests: `tests/test_char_level_bca.py` (78 tests; pure helpers + MeetEval-guarded
  integration tests that assert the output JSON reproduces RQ39's char-level and
  word-level BCa CIs bit-for-bit).
- Per-window data: `results/frontier/char_level_bca/char_level_bca_results.csv`
  (77 rows; lang-id entropy, routing decision, word-level + char-level cpWER for
  mixed/separated/oracle/corrected, char-level residual).
- Summary + hypothesis verdicts: `results/frontier/char_level_bca/char_level_bca_results.json`
- Bootstrap: 10,000 resamples, seed=42, alpha=0.05. BCa uses jackknife
  acceleration; paired-delta uses the same resample indices for both arms.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).
- Run: `/opt/homebrew/bin/python3 results/frontier/char_level_bca/char_level_bca_analysis.py`
  (~10 s; MeetEval prints "Assuming sort=False" spam, suppressed in tests).
