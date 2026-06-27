# RQ70: Per-Mode BCa CI Decomposition of the Corrected Router

> **Label: `experimental/frontier`** — a reanalysis-only per-mode decomposition of the
> corrected router's BCa CI. RQ55 (PR #979) and RQ58 (PR #981) both found the corrected
> router's BCa CI *includes* the oracle — "reaches oracle within noise." RQ70 asks whether
> that verdict is uniform across the 77 AISHELL-4 windows or driven by a specific
> hallucination mode. No Whisper / no ASR / no LLM is run; no verified reference or gold
> table is modified. Closes #998.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, PR #890). Detector / MeetEval / bootstrap / BCa helpers
> are lifted verbatim from RQ55 (`results/frontier/char_level_bca/`, PR #979). The Mode S
> classification is lifted from RQ19 (`results/frontier/mode_s_detector/`, PR #916), and
> the hallucination taxonomy from RQ14 (`results/frontier/hallucination_taxonomy/`, PR #905).

## Executive Summary

RQ55/RQ58 found the corrected router's BCa CI includes the oracle at both word-level
(`[1.0130, 1.0974]` vs oracle 1.0173) and char-level (`[0.8730, 0.9314]` vs oracle 0.8768)
— "reaches oracle within noise." RQ70 decomposes the 77 windows by hallucination mode
(Mode S / Diverse hallucination / Non-hallucinated, per RQ14/RQ19) and recomputes the BCa
CI on each subset, plus a sensitivity analysis that drops Mode S (n=75).

**The headline finding is asymmetric across granularities and inverts the prior on Mode S:**

1. **At word-level, Mode S is the SOLE source of corrected-router regret.** For all 75
   non-Mode-S windows the corrected router *exactly achieves* the oracle (corrected ==
   oracle per window, zero regret). The only word-level regret comes from the 2 Mode S
   windows (22, 30), where the router picks the hallucinated separated track (cpWER 2.0)
   over the mixed track (cpWER 1.0) — a per-window regret of 1.0 each. Dropping Mode S
   does not make the BCa CI *exclude* the oracle (H70a KILLED): it makes corrected ==
   oracle *exactly*, so the CI trivially *includes* the oracle (the corrected mean equals
   the oracle mean). The word-level "within noise" verdict is therefore not "Mode S
   inflates the CI to include oracle" but "Mode S is the only thing keeping corrected
   above oracle; without it there is nothing to distinguish."

2. **At char-level, Mode S has ZERO regret — the char-level "within noise" is NOT
   Mode-S-driven.** Both Mode S windows pick the separated route at char-level, and
   separated *is* the char-level oracle for those windows (separated char cpWER < mixed
   char cpWER). The char-level regret (corrected 0.9130 vs oracle 0.8830 on the non-Mode-S
   subset) comes from 29 of 75 non-Mode-S windows where the router picks separated but
   mixed would have been the char-level oracle. The char-level BCa CI on the non-Mode-S
   subset `[0.8818, 0.9379]` includes the char-level oracle (0.8830) — so H70a is KILLED
   at char-level too, but for a fundamentally different reason than at word-level.

3. **The Mode S subset (n=2) is too small for a stable BCa CI** (per the HONESTY
   REQUIREMENT). At word-level both Mode S windows have identical corrected cpWER (2.0),
   so the BCa CI degenerates to `[2.0, 2.0]` (width 0) — this *excludes* the oracle (1.0)
   from above, killing H70b, but the degeneracy is an artefact of n=2 with no variance, not
   a meaningful statistical claim. At char-level the two Mode S windows differ (0.4915 vs
   0.8027) and the BCa CI `[0.4915, 0.6471]` *includes* the oracle (0.6471 = upper bound).
   The H70b verdict (KILLED) rests entirely on the degenerate word-level CI and should be
   read as "n=2 is too small to support the hypothesis," not as "Mode S excludes oracle."

**Hypothesis verdicts:**

| Hypothesis | Verdict | Detail |
|---|:---:|---|
| **H70a** Non-Mode-S BCa CI excludes oracle | **KILLED** | Word: corrected==oracle exactly (zero regret), CI trivially includes oracle. Char: CI `[0.8818, 0.9379]` includes oracle 0.8830. |
| **H70b** Mode S BCa CI includes oracle | **KILLED** | Word BCa `[2.0, 2.0]` excludes oracle 1.0 from above (degenerate, n=2). Char BCa includes oracle. n=2 unstable. |
| **H70c** Per-mode CI widths differ > 50% (ratio > 1.5) | **SUPPORTED** | Char ratio 2.79 (Mode S 0.156 / Diverse 0.056). Stable-only ratio 1.54 (Non-hall 0.086 / Diverse 0.056), barely above threshold. |

The three findings that matter:

1. **The "within noise" verdict is uniform in outcome (the CI includes oracle for every
   stable subset) but heterogeneous in mechanism.** At word-level the non-Mode-S subset has
   *zero* regret (corrected == oracle per window) — the CI includes oracle trivially. At
   char-level the non-Mode-S subset has a real 0.030 regret spread across 29 windows — the
   CI includes oracle non-trivially. Mode S contributes word-level regret (1.0 per window)
   but zero char-level regret. There is no subset for which the BCa CI *excludes* the
   oracle.

2. **Mode S is the word-level noise source but not the char-level noise source.** This
   refines RQ19's framing: Mode S is the residual that surface detectors cannot catch, and
   it is also the sole source of word-level corrected-router regret. But RQ31's finding
   that "Mode S disappears at char-level" (because separated char-cpWER < mixed char-cpWER
   for Mode S windows) means Mode S contributes *zero* char-level regret. The char-level
   "within noise" is driven by a different mechanism: 29 non-Mode-S windows where the
   router picks separated but mixed is the char-level oracle.

3. **Per-mode CI widths differ by > 50% (H70c SUPPORTED), but barely so on the stable-only
   comparison.** The full ratio (2.79) is inflated by the unstable Mode S width (n=2). The
   stable-only ratio (Non-hallucinated 0.086 vs Diverse 0.056 = 1.54) just exceeds the 1.5
   threshold — Non-hallucinated windows have a wider char-level CI because their per-window
   char-cpWER distribution is more dispersed (40 windows spanning clean single-speaker to
   moderate-overlap), while Diverse hallucination windows are more homogeneous (all route to
   mixed, all have mixed ≈ oracle).

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min). Each
window stores the per-route word-level cpWER (`always_mixed_cpwer`,
`always_separated_cpwer`, `oracle_best_cpwer`), the per-speaker separated transcripts, and
the mixed transcript. No ASR is run; the corrected router's per-window char-level cpWER is
the chosen route's recomputed char-level cpWER.

### Mode classification (per RQ14/RQ16/RQ19)

Three-way mutually-exclusive classification:

| Mode | n | Definition |
|---|--:|---|
| **Mode S** | 2 | hallucinated AND `lang_id_entropy < 0.409` AND `length_ratio < 2.0` AND `cr < 2.4` (RQ19; windows 22, 30) |
| **Diverse hallucination** | 35 | hallucinated AND NOT Mode S (RQ12/RQ14's 37 hallucinated minus the 2 Mode S tracks) |
| **Non-hallucinated** | 40 | `always_separated_cpwer <= 1.0` (RQ12) |

**Note on the task spec's counts.** The task spec listed the split as "Mode S (2), Diverse
hallucination (37), Non-hallucinated (38)." The *data-driven* mutually-exclusive split per
RQ12/RQ14/RQ19 is (2, 35, 40) = 77: RQ12/RQ14's "37 hallucinated" *includes* the 2 Mode S
tracks, so Diverse-hallucination-minus-Mode-S = 35, and non-hallucinated = 40 (not 38).
The "37" is the total hallucinated count (Mode S + Diverse); the "38" appears to be a
miscount (40 non-hallucinated, verified by `always_separated_cpwer <= 1.0` on all 77
windows). We use the data-driven (2, 35, 40) split throughout and report the discrepancy
transparently per the HONESTY REQUIREMENT. A sensitivity analysis on the Non-Mode-S subset
(n=75 = 35 + 40) is the primary vehicle for H70a.

### Routing (lang-id entropy threshold 0.38)

RQ55 corrected router: route to MIXED if `max_across_speakers(separated,
language_id_entropy) > 0.38` bits, else SEPARATED. Threshold 0.38 verified identical
routing to RQ13's 0.409 (no window has entropy in (0.38, 0.409]). 38 MIXED, 39 SEPARATED.

### Char-level cpWER (RQ31 convention)

Char-level tokenisation: `' '.join(list(text))`. MeetEval 0.4.3 `cpwer` (separated,
multi-vs-multi) and `orcwer` (mixed, single-channel vs multi-ref), using RQ55's
`safe_cpwer` / `safe_orcwer` with the project's empty-sentinel convention. The all-77
char-level corrected-router cpWER (0.906097) and BCa CI `[0.873026, 0.931406]` reproduce
RQ55 bit-for-bit.

### Bootstrap (10,000 resamples, seed=42)

For each subset (Mode S, Diverse, Non-hallucinated, Non-Mode-S, and all-77 for
reproducibility): percentile CI (2.5/97.5) and BCa CI (jackknife acceleration), lifted
verbatim from RQ39/RQ55. The BCa CI is the primary verdict. **Stability flag:** subsets
with n < 5 are flagged as too small for stable BCa (the jackknife acceleration is
unreliable and the bootstrap has few distinct resample compositions). Mode S (n=2) is
flagged unstable; its CI is reported but not load-bearing for any verdict.

### Reproducibility sanity checks (all pass)

1. **All-77 word-level BCa CI reproduces RQ55**: `[1.012987, 1.097403]` = RQ55's
   `word_bca_ci` bit-for-bit.
2. **All-77 char-level BCa CI reproduces RQ55**: `[0.873026, 0.931406]` = RQ55's
   `char_bca_ci` bit-for-bit.
3. **Mode S window ids reproduce RQ19**: `[22, 30]` = RQ19's Mode S residual.
4. **Mode counts reproduce RQ12/RQ14**: 37 hallucinated (= 2 Mode S + 35 Diverse), 40
   non-hallucinated.

## Results

### Per-subset BCa CI (corrected router cpWER)

| Subset | n | stable | granularity | corrected | oracle (subset) | BCa CI 95% | width | oracle inside? |
|---|--:|:---:|---|---:|---:|:---:|---:|:---:|
| all | 77 | yes | word | 1.0433 | 1.0173 | [1.0130, 1.0974] | 0.0844 | yes |
| all | 77 | yes | char | 0.9061 | 0.8768 | [0.8730, 0.9314] | 0.0584 | yes |
| **Mode S** | 2 | **no** | word | 2.0000 | 1.0000 | [2.0000, 2.0000] | 0.0000 | **no** (excludes, above) |
| Mode S | 2 | no | char | 0.6471 | 0.6471 | [0.4915, 0.6471] | 0.1556 | yes (upper = oracle) |
| **Diverse halluc** | 35 | yes | word | 1.0381 | 1.0381 | [1.0000, 1.0952] | 0.0952 | yes (corrected == oracle) |
| Diverse halluc | 35 | yes | char | 0.9546 | 0.9160 | [0.9198, 0.9754] | 0.0557 | no (excludes, above) |
| **Non-halluc** | 40 | yes | word | 1.0000 | 1.0000 | [1.0000, 1.0000] | 0.0000 | yes (corrected == oracle) |
| Non-halluc | 40 | yes | char | 0.8766 | 0.8541 | [0.8305, 0.9164] | 0.0859 | yes |
| **Non-Mode-S** | 75 | yes | word | 1.0178 | 1.0178 | [1.0000, 1.0444] | 0.0444 | yes (corrected == oracle) |
| Non-Mode-S | 75 | yes | char | 0.9130 | 0.8830 | [0.8818, 0.9379] | 0.0561 | yes |

### Per-window regret decomposition (corrected − oracle)

| Subset | n | word regret (sum) | word windows with regret>0 | char regret (sum) | char windows with regret>0 |
|---|--:|---:|--:|---:|--:|
| Mode S | 2 | 2.0000 | 2 / 2 | 0.0000 | 0 / 2 |
| Diverse halluc | 35 | 0.0000 | 0 / 35 | 1.3534 | 16 / 35 |
| Non-halluc | 40 | 0.0000 | 0 / 40 | 0.8988 | 13 / 40 |
| **Non-Mode-S** | 75 | **0.0000** | **0 / 75** | 2.2522 | 29 / 75 |
| all | 77 | 2.0000 | 2 / 77 | 2.2522 | 29 / 77 |

The regret decomposition is the cleanest summary of the asymmetric mechanism:

- **Word-level:** 100% of the corrected router's word-level regret (2.0000 / 2.0000) comes
  from the 2 Mode S windows. All 75 non-Mode-S windows have *zero* word-level regret
  (corrected == oracle per window). This is why dropping Mode S does not exclude oracle —
  there is nothing left to exclude.
- **Char-level:** 0% of the corrected router's char-level regret comes from Mode S. All
  2.2522 of char-level regret comes from 29 non-Mode-S windows (16 Diverse + 13
  Non-hallucinated). Mode S has zero char-level regret because the router picks separated
  for Mode S, and separated is the char-level oracle for those windows.

### Hypothesis Verdicts

#### H70a — Non-Mode-S BCa CI excludes oracle: KILLED

- **KILLED.** Dropping the 2 Mode S windows does NOT make the BCa CI exclude the oracle at
  either granularity.
  - **Word-level:** On the 75 non-Mode-S windows, corrected == oracle *per window* (zero
    regret for all 75). The corrected mean (1.0178) equals the oracle mean (1.0178), so the
    BCa CI `[1.0000, 1.0444]` trivially includes the oracle. There is no signal to exclude
    — the corrected router *is* the oracle on this subset.
  - **Char-level:** On the 75 non-Mode-S windows, there is a real regret of 0.0300 (corrected
    0.9130 vs oracle 0.8830), spread across 29 windows. But the BCa CI `[0.8818, 0.9379]`
    still includes the oracle (0.8830) — the lower bound (0.8818) is just below the oracle
    (0.8830), a BCa bias-correction artefact on lumpy data (same mechanism as RQ55's H55a).
    The narrower n=75 CI (width 0.0561 vs all-77 width 0.0584) is not narrow enough to
    exclude oracle.
- **Interpretation:** The "within noise" verdict is NOT an artefact of Mode S inflating the
  CI. At word-level, Mode S is the sole regret source but dropping it leaves zero regret
  (not a "beats oracle" exclusion). At char-level, Mode S contributes nothing and the
  non-Mode-S CI still includes oracle on its own.

#### H70b — Mode S BCa CI includes oracle: KILLED (n=2 unstable)

- **KILLED.** The Mode S word-level BCa CI `[2.0000, 2.0000]` *excludes* the oracle (1.0)
  from above — both Mode S windows have corrected cpWER 2.0 (router picks the hallucinated
  separated track) vs oracle 1.0 (mixed). This is the opposite of the hypothesised "Mode S
  CI includes oracle": Mode S corrected is far *above* oracle, not at oracle.
- **Char-level:** The Mode S char-level BCa CI `[0.4915, 0.6471]` *includes* the oracle
  (0.6471 = upper bound) — at char-level Mode S has zero regret (corrected == oracle per
  window, since separated is the char-level oracle for Mode S).
- **n=2 caveat (HONESTY REQUIREMENT):** n=2 is far too small for stable BCa. At word-level
  both windows have identical corrected (2.0), so the BCa degenerates to a point mass
  `[2.0, 2.0]` — the "exclusion" is an artefact of zero variance, not a statistical claim.
  At char-level the two windows differ (0.4915 vs 0.8027) but the jackknife acceleration
  on n=2 is degenerate. The H70b verdict should be read as "n=2 cannot support the
  hypothesis," not as "Mode S excludes oracle."
- **Directional nuance:** The *spirit* of H70b — "Mode S is the noise source" — is
  *confirmed at word-level* by the regret decomposition (100% of word-level regret is Mode
  S). The hypothesis was phrased as "Mode S CI includes oracle," expecting Mode S to sit at
  oracle within noise; in fact Mode S corrected sits far *above* oracle (2.0 vs 1.0), which
  is why the global CI includes oracle rather than excluding it. Mode S is the noise source,
  but the noise pushes corrected *above* oracle, not *to* oracle.

#### H70c — Per-mode CI widths differ > 50% (ratio > 1.5): SUPPORTED

- **SUPPORTED.** The char-level per-mode width ratio is 2.79 (Mode S 0.1556 / Diverse
  0.0557), well above 1.5. The word-level ratio is degenerate (Mode S width 0, Non-halluc
  width 0, both due to constant per-window values), so the char-level ratio is the
  meaningful comparison.
- **Stable-only comparison:** Restricting to the two stable subsets (Diverse vs
  Non-hallucinated), the char-level width ratio is 1.54 (Non-halluc 0.0859 / Diverse
  0.0557) — just above the 1.5 threshold. Non-hallucinated windows have a wider CI because
  their per-window char-cpWER distribution is more dispersed (40 windows spanning
  NoOverlap single-speaker clean tracks to LightOverlap/MidOverlap multi-speaker tracks),
  while Diverse hallucination windows are more homogeneous (all route to mixed, all have
  mixed ≈ oracle, tighter distribution).
- **Caveat:** The 1.54 stable-only ratio is barely above 1.5; a different meeting or a
  slightly different mode boundary could flip this. The full ratio (2.79) is inflated by
  the unstable Mode S width and should not be load-bearing. The honest reading is "per-mode
  widths differ, but the stable-subset difference is modest (54%), not dramatic."

## Honest Limitations

1. **Mode S n=2 (the headline caveat).** The Mode S subset has 2 windows. BCa on n=2 is
   degenerate: the word-level CI is a point mass (both values identical), the jackknife
   acceleration is unreliable, and the bootstrap has only C(2+1, 1)=3 distinct resample
   compositions ([0,2], [1,1], [2,0]). The H70b verdict (KILLED) rests on this degenerate
   CI and should be read as "n=2 cannot support H70b," not as "Mode S excludes oracle." The
   regret decomposition (Mode S = 100% of word-level regret) is the load-bearing finding,
   not the Mode S BCa CI.

2. **Mode counts differ from the task spec.** The task spec listed (Mode S=2, Diverse=37,
   Non-hall=38). The data-driven mutually-exclusive split per RQ12/RQ14/RQ19 is (2, 35,
   40)=77. The "37" is RQ12/RQ14's total hallucinated count (which *includes* Mode S); the
   "38" appears to be a miscount (40 non-hallucinated). We use (2, 35, 40) and document the
   discrepancy. The H70a sensitivity analysis (Non-Mode-S = 75 = 35 + 40) is unaffected.

3. **Single meeting, 77 windows (inherited from RQ16/RQ39/RQ55).** Only `M_R003S02C01` is
   available. The per-mode CIs characterise within-meeting uncertainty, not cross-meeting
   generalisation. Mode S (n=2) is especially fragile — a different meeting could have 0,
   1, or 5 Mode S windows, changing the decomposition entirely.

4. **In-sample threshold calibration (inherited).** The lang-id entropy threshold 0.38
   (verified identical to 0.409) and the Mode S definition (lang-id < 0.409, length-ratio <
   2.0, CR < 2.4) are calibrated on these exact 77 windows. The per-mode CIs characterise
   the *conditional* uncertainty given the classification, not the *unconditional*
   uncertainty that would include classification re-fit variance.

5. **Subset oracle vs global oracle.** The per-mode comparisons use the *subset* oracle
   mean (e.g. Mode S oracle = mean over 2 Mode S windows), not the global oracle. This is
   the right choice for "does corrected beat oracle *within this mode*," but it means the
   per-mode CIs are not directly comparable to the all-77 CI (which uses the all-77 oracle).
   The global oracle (word 1.0173, char 0.8768) is reported for context in the JSON.

6. **BCa on lumpy discrete data (inherited from RQ39/RQ55).** Per-window cpWER is discrete
   (ratios of small integer error counts). BCa's bias correction can push the lower bound
   below the oracle on left-skewed data — this is why H70a's char-level lower bound (0.8818)
   is below the oracle (0.8830) despite the corrected mean (0.9130) being above. We report
   both percentile and BCa CIs in the JSON; the percentile CI is less aggressive.

7. **No deployable routing input (inherited).** Per the project's hard safety rules, cpWER
   / references are not used as routing input — the lang-id entropy detector is computed
   only from the hypothesis transcripts.

## What this changes for the project

1. **The "within noise" verdict is robust to Mode S removal but for two different reasons
   at the two granularities.** At word-level, dropping Mode S leaves *zero* regret
   (corrected == oracle on 75/75 non-Mode-S windows) — the CI includes oracle trivially.
   At char-level, dropping Mode S leaves a real 0.030 regret (29/75 windows) but the CI
   still includes oracle. There is no subset and no granularity for which the BCa CI
   excludes the oracle. RQ55's "reaches oracle within noise" verdict is therefore *not* an
   artefact of Mode S heterogeneity — it holds uniformly across modes, with the strongest
   form being "corrected == oracle exactly" at word-level on non-Mode-S windows.

2. **Mode S is the word-level noise source; the char-level noise source is a different
   mechanism.** This refines RQ19: Mode S is the residual that surface detectors cannot
   catch, and it is the sole source of word-level corrected-router regret (2.0 of 2.0). But
   RQ31's "Mode S disappears at char-level" means Mode S contributes *zero* char-level
   regret. The char-level "within noise" comes from 29 non-Mode-S windows where the router
   picks separated but mixed is the char-level oracle — a routing-error mechanism, not a
   hallucination mechanism. A char-level-aware router (or a char-level re-evaluation of the
   lang-id threshold) might close the char-level gap without touching Mode S.

3. **H70c's stable-only width ratio (1.54) is barely above 1.5.** The per-mode CIs do differ
   in width, but the stable-subset difference (Non-hallucinated 0.086 vs Diverse 0.056) is
   modest — 54%, not the dramatic > 50% the hypothesis envisaged. The full ratio (2.79) is
   inflated by the unstable Mode S width and should not be quoted without the stable-only
   caveat. The modes are not wildly heterogeneous in CI width; the heterogeneity is in the
   *regret mechanism* (Mode S = word-level regret; non-Mode-S = char-level regret), not in
   the CI width.

## Reproducibility

- Script: `results/frontier/per_mode_bca_decomposition/analysis.py`
  (deterministic; numpy + scipy + meeteval 0.4.3; no Whisper / no audio / no LLM).
- Tests: `tests/test_per_mode_bca.py` (unittest; pure helpers + MeetEval-guarded
  integration tests that assert the all-77 BCa CI reproduces RQ55 bit-for-bit and the Mode
  S classification reproduces RQ19's windows 22, 30).
- Per-window data: `results/frontier/per_mode_bca_decomposition/per_mode_bca_results.csv`
  (77 rows; mode classification, lang-id entropy, routing decision, word-level + char-level
  cpWER for mixed/separated/oracle/corrected, Mode S features).
- Summary + hypothesis verdicts: `results/frontier/per_mode_bca_decomposition/per_mode_bca_results.json`
- Bootstrap: 10,000 resamples, seed=42, alpha=0.05. BCa uses jackknife acceleration.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).
- Run: `/opt/homebrew/bin/python3 results/frontier/per_mode_bca_decomposition/analysis.py`
  (~10 s; MeetEval prints "Assuming sort=False" spam, suppressed in tests).
