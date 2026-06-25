# RQ31: Char-level cpWER Re-validation of the Corrected Router

> **Label: `experimental/frontier`** — a reanalysis-only re-run of RQ16's corrected router
> simulation using character-level cpWER (the standard Chinese cpCER convention) instead of
> the utterance-level cpWER that inflated the separation tax ~80x (RQ30, PR #934). Does NOT run
> Whisper or overwrite any verified reference / gold table. Closes #938.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, PR #890). Detector primitives and thresholds are lifted verbatim
> from RQ13 / RQ16. Char-level tokenisation matches RQ30's char-level arm.

## Executive Summary

RQ30 discovered that every prior AISHELL-4 routing study (RQ1, RQ8, RQ12, RQ13, RQ16, RQ25, RQ29)
computed cpWER at the wrong granularity for Chinese: whole speaker strings were passed to MeetEval
as a single "word" (no whitespace => 1 token per speaker), instead of the standard cpCER convention
where each character is a token. This inflated the separation tax ~80x (0.418 word vs 0.005 char)
and scrambled per-window ordering (Spearman rho ~ 0.1).

This study re-runs RQ16's corrected router at character level. The corrected router is RQ16's
lang-id-entropy-only ablation (threshold 0.409 bits): route to MIXED if `lang_id_entropy > 0.409`,
else SEPARATED. RQ16 showed this single guard is identical to the full three-guard corrected router
on AISHELL-4 (the silence and mode guards are redundant), so lang-id-alone IS the corrected router
for this meeting.

**The corrected router still beats always-mixed at char level (H31a, pointwise), but its advantage
shrinks 29x — from -0.130 cpWER/window at word level to -0.004 at char level.** The lang-id
detector's recovery of the mixed→oracle gap collapses from 86.2% (word) to 13.3% (char), killing
H31b. Most strikingly, **Mode S disappears entirely at char level (H31c killed)**: the two
monoscript-Chinese windows (22, 30) that were the corrected router's only word-level losses are no
longer failures — at char level the separated route is actually *better* (window 22) or *equal*
(window 30). The residual failure mode migrates from Mode S to a new, different pattern: 7
clean-Chinese windows where separation degrades the char-level transcript without triggering any
hallucination detector.

| Policy | cpWER (word, RQ16) | cpWER (char, RQ31) | Δ (char − word) |
|--------|-------------------:|-------------------:|----------------:|
| always-mixed | 1.1732 | 0.9106 | −0.2626 |
| always-separated | 1.5909 | 0.9158 | −0.6751 |
| router v2 | 1.2056 | 0.9222 | −0.2834 |
| **corrected router** | **1.0433** | **0.9061** | **−0.1372** |
| oracle best | 1.0173 | 0.8768 | −0.1405 |

The separation tax (separated − mixed) shrinks from 0.418 (word) to 0.005 (char), a 79.5x reduction.
With the tax nearly gone, there is little for the router to recover, and the corrected router's
in-sample-calibrated threshold overcorrects — routing 38 windows to mixed when separated would have
been the char-level oracle for 22 of them.

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min). Each window stores
the per-speaker reference text, per-speaker separated ASR text, and mixed ASR text. No ASR is run.

### Char-level cpWER

For each window, char-level cpWER is computed with MeetEval 0.4.3's `cpwer` (separated) and `orcwer`
(mixed) using character-level tokenisation: `' '.join(list(text))` for each Chinese string. This is
the standard Chinese cpCER convention (Chinese has no word delimiter, so each character IS a token)
and matches RQ30's char-level arm verbatim. Empty/whitespace-only speaker texts are skipped (matches
the project's `compute_cpwer`); empty input returns the sentinel (1.0, −1, −1).

The four char-level baselines reproduce RQ30's cross-reference exactly:
- always_mixed_char: 0.910577 (RQ30: 0.910577)
- always_separated_char: 0.915831 (RQ30: 0.915831)
- router_v2_char: 0.922196 (RQ30: 0.922196)
- oracle_char: 0.876847 (RQ30: 0.876847)

### Corrected router

The corrected router is RQ16's lang-id-entropy-only ablation. The `language_id_entropy` detector
(RQ13, Shannon entropy over Unicode script categories) is computed verbatim from the per-speaker
separated transcripts, aggregated by MAX across speakers (worst-case track). Threshold **0.409 bits**
(RQ13's ≥90%-specificity operating point; 94.6% sensitivity, 92.5% specificity). Decision: if
`lang_id_entropy > 0.409` → route to MIXED; else → SEPARATED. RQ16 found this is identical to the
full three-guard corrected router on AISHELL-4 (silence and mode guards are redundant), so the
lang-id-only router IS the corrected router here.

The corrected router routes 38 windows to mixed and 39 to separated (at word level RQ16's full
router routed 42/35, but the 4 extra mixed flags were on tie windows where both routes scored 1.0).

### Statistics

Per-window char-level cpWER is averaged over the 77 windows for each policy. Bootstrap 95% CIs use
10,000 resamples (seed=42). H31b's recovery fraction `(mixed − corrected) / (mixed − oracle)` is
bootstrapped per-resample from resampled means. H31c's Mode S share is bootstrapped as
`sum(residual_i for i in {22,30}) / sum(residual_i)`, guarded against zero total residual.

## Results

### Aggregate char-level cpWER (mean over 77 windows, 95% bootstrap CI)

| Policy | cpWER | CI 95% |
|--------|------:|:------|
| always-mixed | 0.9106 | [0.8840, 0.9356] |
| always-separated | 0.9158 | [0.8784, 0.9551] |
| router v2 | 0.9222 | [0.8891, 0.9564] |
| **corrected router** | **0.9061** | [0.8761, 0.9337] |
| oracle best | 0.8768 | [0.8479, 0.9039] |

The corrected router (0.9061) sits below always-mixed (0.9106) and well below router v2 (0.9222),
but only 0.029 above oracle (0.8768). The absolute advantage over always-mixed is −0.0045 cpWER per
window — vs −0.130 at word level.

### Corrected router vs always-mixed (per window)

15 wins, 55 ties, 7 losses. The 15 wins are windows where the lang-id detector correctly routes to
separated and separated beats mixed at char level (e.g. window 3: mixed 0.72, sep 0.67). The 7
losses are all clean-Chinese windows (lang_id_entropy = 0.000) routed to separated where separation
degrades the char-level transcript — the new residual failure mode (see below).

### Mode S disappears

The central RQ31 finding. At word level (RQ16), windows 22 and 30 were the corrected router's only
losses vs always-mixed — monoscript-Chinese separated hallucinations (separated cpWER 2.0 vs mixed
1.0) that escaped every reference-free guard. They accounted for ~100% of the word-level residual
(total residual 2.002, Mode S 2.0).

At char level, Mode S is gone:

| Window | lang_id_entropy | decision | mixed_char | separated_char | corrected_char | oracle_char | residual |
|-------:|----------------:|:---------|-----------:|---------------:|---------------:|------------:|---------:|
| 22 | 0.144 | separated | 0.5424 | 0.4915 | 0.4915 | 0.4915 | 0.0000 |
| 30 | 0.323 | separated | 0.8027 | 0.8027 | 0.8027 | 0.8027 | 0.0000 |

Window 22's separated track is actually *better* than mixed at char level (0.49 vs 0.54) — the
"hallucination" that scored 2.0 at word level (2 errors / 1 token) is a 49% char-level error rate,
which beats mixed's 54%. Window 30 ties. Both windows route to separated (low entropy), pick the
oracle, and contribute zero residual. The word-level Mode S failure was an artefact of
utterance-level tokenisation, not a real separation failure.

### The new residual: clean-Chinese separated-track degradation

With Mode S gone, the char-level residual (corrected − oracle = 2.252 total) comes from two sources:

1. **Separated-route losses (7 windows, residual 0.830):** clean-Chinese windows (ent = 0.000) where
   the corrected router picks separated but mixed is better at char level. Three have separated
   char-cpWER = 1.0 (complete char-level failure: w1 0.81 vs 1.00, w62 0.78 vs 1.00, w75 0.77 vs
   1.00). These are NOT diverse hallucinations — lang-id entropy is zero — so no guard fires. This
   is a failure mode the RQ13/RQ16 detector surface cannot see.

2. **Mixed-route overcorrection (22 windows, residual 1.422):** windows where the lang-id detector
   fires (high entropy) and routes to mixed, but separated was actually the char-level oracle. At
   word level these same windows had separated cpWER >> mixed (diverse hallucinations), so routing
   to mixed was correct. At char level the diverse-hallucination penalty shrinks (the tax is 80x
   smaller), so the separated track becomes competitive — but the detector, calibrated on the
   inflated word-level tax, still routes to mixed. The largest single residual contributor is
   window 11 (ent 0.563, mixed 1.00 vs sep 0.69, residual 0.306): the lang-id detector flags it
   as a hallucination, but at char level the separated track is the better route.

The mixed-route overcorrection (1.422) is larger than the separated-route losses (0.830). This is
the structural reason H31b fails: the detector's threshold was calibrated against the 80x-inflated
word-level tax, so it overroutes to mixed at char level, forfeiting the separated wins it was
designed to capture.

### Per-window ordering: word vs char (RQ30 replication)

Spearman rho between stored word-level and our char-level per-window cpWER: separated +0.108, mixed
−0.204. The word-level metric does not preserve the char-level ordering (RQ30's finding replicated).
This is why the corrected router's per-window win/loss pattern inverts between granularities.

## Hypothesis Verdicts

- **H31a — char-level corrected router cpWER < char-level always-mixed cpWER: SUPPORTED (pointwise;
  CI borderline).** Corrected 0.9061 vs mixed 0.9106, Δ = −0.0045. Bootstrap CI [−0.0226, +0.0117]:
  the upper bound crosses zero. The improvement is real at the point estimate (15 wins vs 7 losses,
  net −0.0045/window) but the margin is 29x smaller than at word level (−0.130) and the high
  variance from lumpy char-level cpWER values keeps the CI straddling zero. The corrected router
  still helps, but barely.

- **H31b — lang-id entropy detector recovers > 80% of the gap to oracle at char level: NOT
  SUPPORTED (KILLED).** Recovery = (mixed − corrected) / (mixed − oracle) = (0.9106 − 0.9061) /
  (0.9106 − 0.8768) = **13.3%** (bootstrap CI [−47.5%, +52.1%]). At word level the same detector
  recovered 86.2% of router v2's regret gap. The collapse has a simple arithmetic cause: the
  mixed→oracle gap shrinks from 0.156 (word) to 0.034 (char), so there is little gap to recover,
  and the detector's 22 mixed-route overcorrections (where separated was the char-level oracle) eat
  into the recovery. The detector's value proposition rested on the inflated word-level separation
  tax.

- **H31c — Mode S accounts for > 50% of char-level residual: NOT SUPPORTED (KILLED).** Mode S
  share = 0.0 / 2.252 = **0.0%** (bootstrap CI [0.0%, 0.0%]). Mode S does not exist at char level.
  Windows 22 and 30 — the corrected router's only word-level losses and ~100% of the word-level
  residual — are char-level wins or ties (separated is better or equal). The word-level Mode S
  "monoscript-Chinese hallucination" was an artefact of utterance-level tokenisation: scoring 2
  errors against 1 token yields cpWER 2.0, but scoring the same errors against ~50 characters
  yields cpWER ~0.49, which is competitive. The char-level residual migrates to a different,
  unrelated failure mode (clean-Chinese separated-track degradation + mixed-route overcorrection).

## Honest Limitations

1. **In-sample calibration (inherited from RQ13/RQ16).** The lang-id entropy threshold 0.409 was
   calibrated on these exact 77 windows. RQ31 does not re-calibrate — it reuses the frozen threshold
   to test whether the *word-level* conclusions survive at char level. They do not (H31b, H31c
   killed). A char-level-calibrated threshold might recover more of the gap, but that would be a
   different study (and would still be in-sample on a single meeting).

2. **Single meeting, 77 windows.** M_R003S02C01 is 1 of 20 AISHELL-4 test meetings. The char-level
   cpWER values are less lumpy than word-level (continuous rather than {0,1,2,4,6}) but the sample
   is still small and the H31a CI reflects this.

3. **Corrected router is lang-id-only.** RQ16 found the silence and mode guards are redundant once
   lang-id is in the ensemble (on AISHELL-4), so lang-id-alone == full corrected router at word
   level. This study uses lang-id-only. If the silence/mode guards were included, they would not
   change the Mode S finding (they also miss windows 22/30) but could shift the mixed-route
   overcorrection count. The task specification defines the corrected router as lang-id-only.

4. **No re-calibration at char level.** The threshold 0.409 was chosen for word-level cpWER. At char
   level the optimal operating point may differ. This study deliberately does NOT re-tune, because
   the research question is "do the word-level conclusions survive at char level?" — not "what is
   the best char-level router?".

5. **Char-level cpWER still includes `<#>` markers and punctuation.** Both the reference and
   hypothesis texts contain `<#>` segment-boundary markers and Chinese punctuation. Neither is
   normalised. This is consistent with RQ30's char-level arm and does not affect the within-study
   comparison, but a cleaner cpCER would strip them (a separate research question, RQ30
   discrepancy D3).

6. **No deployable routing input.** Per the project's hard safety rules, cpWER / references are not
   used as routing input — the lang-id entropy detector is computed only from the hypothesis
   transcripts, which is the deployable signal surface.

## Reproducibility

- Script: `results/frontier/char_level_cpwer_revalidation/char_level_revalidation_analysis.py`
  (deterministic; numpy + scipy + MeetEval 0.4.3).
- Run: `/opt/homebrew/bin/python3 results/frontier/char_level_cpwer_revalidation/char_level_revalidation_analysis.py`
- Outputs: `char_level_revalidation_results.csv` (per-window char-level cpWER, lang-id entropy,
  decisions, residuals) and `char_level_revalidation_results.json` (summary, baselines, bootstrap
  CIs, hypothesis verdicts, Mode S analysis, per-window rows).
- Bootstrap: 10,000 resamples, seed=42.
- Tests: `tests/test_char_level_revalidation.py` (41 tests; 30 pure-Python unit tests for
  detectors / decision rule / bootstrap helpers / segment builders, 11 MeetEval-guarded integration
  tests that re-run the analysis and assert output well-formedness and RQ30 cross-reference).
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

RQ16's headline result — that a corrected router recovers 86.2% of router v2's regret gap to oracle,
with Mode S as the residual floor — **does not survive char-level re-validation**. The 86.2% recovery
collapses to 13.3%, and Mode S vanishes entirely. The corrected router still beats always-mixed
(H31a, pointwise) but by a 29x-smaller margin whose bootstrap CI touches zero.

The mechanism is arithmetically simple: the separation tax shrinks 79.5x at char level (0.418 →
0.005), so the mixed→oracle gap the router is trying to close shrinks from 0.156 to 0.034. The
lang-id detector's threshold was calibrated against the inflated word-level tax, so it overroutes to
mixed (22 windows where separated was the char-level oracle), forfeiting the recovery. Mode S — the
word-level residual floor — was a tokenisation artefact: 2 errors against 1 token is cpWER 2.0, but
2 errors against 50 characters is cpWER 0.04, which is competitive.

The negative findings are the scientifically informative ones. RQ30 showed the word-level metric
inflates the separation tax 80x and scrambles per-window ordering; RQ31 shows that the corrected
router's entire value proposition — the 86.2% recovery, the Mode S residual story — was a
consequence of that inflation. At the correct granularity for Chinese, the router has very little
to recover, and the specific failure mode (Mode S) that bounded what transcript-only detectors
could achieve was not real. The new char-level residual (clean-Chinese separated-track degradation +
mixed-route overcorrection) is a different problem that the RQ13/RQ16 detector surface does not
address, and would require a char-level-calibrated detector or a fundamentally different signal
(acoustic, not transcript-only) to close.
