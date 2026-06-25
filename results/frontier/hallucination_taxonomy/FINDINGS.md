# RQ14: Hallucination Taxonomy on AISHELL-4 — 37 Hallucinated Separated Tracks

> **Label: `experimental/frontier`** — reanalysis-only finer decomposition of the 37
> AISHELL-4 separated tracks that hallucinate (cpWER > 1.0). No Whisper / no ASR
> model is run; this reads the existing AISHELL-4 external-validation results and
> classifies each hallucinated track into a mutually exclusive mode.
> Closes #902. Builds directly on RQ12 (`results/frontier/router_failure_modes/`,
> PR #900), which found 37 / 77 separated tracks hallucinate but lumped 36 of them
> into a single underspecified "CR-missed (diverse)" bucket. This module decomposes
> that bucket. See also `results/frontier/causal_hallucination_probe/FINDINGS.md`
> (finding #21, the confident-attractor mechanism behind Mode R).

## Executive Summary

RQ12's "diverse hallucination" bucket is **not one phenomenon**. Decomposing the 37
hallucinated separated tracks by reference-free surface features (Unicode-script
mixing, compression ratio, transcript-length ratio vs the mixed track) yields a
**five-mode taxonomy** in which the dominant mode is **insertion-dominated** (long
hallucinated transcripts where the mixed decoder emitted nothing), not the
multilingual gibberish that RQ12's illustrative window-0 quote suggested:

| Mode | n | Share | Bootstrap 95% CI | Mean cpWER | Mean CR | Mean TTR | Mean lang-ent (bits) |
|---|--:|------:|---:|------:|------:|------:|------:|
| **insertion_dominated** | 19 | **51.4%** | [35.1%, 67.6%] | 2.11 | 1.15 | 0.731 | 0.91 |
| **substitution_dominated** | 9 | 24.3% | [10.8%, 37.8%] | 2.15 | 1.37 | 0.637 | 0.68 |
| **multilingual_mixing** (≥3 scripts) | 4 | 10.8% | [2.7%, 21.6%] | 2.92 | 1.10 | 0.689 | 1.29 |
| **semantic_drift** (residual) | 4 | 10.8% | [2.7%, 21.6%] | 2.44 | 0.94 | 0.773 | 1.11 |
| **repetition** (CR > 2.4, Mode R) | 1 | 2.7% | [0.0%, 8.1%] | 1.67 | 2.97 | 0.464 | 0.55 |
| **Total** | **37** | 100% | — | — | — | — | — |

**Hypothesis verdicts:**

- **H14a (multilingual mixing > 50%): NOT SUPPORTED.** Multilingual mixing is only
  10.8% (CI [2.7%, 21.6%]). The vivid "multilingual gibberish" framing in RQ12
  (window 0: `美國生活差幾個岩... 카메 mad將會...`) is the *minority* surface form;
  the majority of the "diverse" bucket is single-script (Han ± Latin) long
  insertion.
- **H14b (repetition < 10%): SUPPORTED.** Only 1 / 37 tracks (2.7%, CI [0.0%,
  8.1%]) has CR > 2.4 — the repetitive confident-attractor (Mode R, finding #21).
  This independently reproduces RQ12's H12b (CR sensitivity 2.7%) from the
  taxonomy side.
- **H14c (distinct CR profiles per mode): SUPPORTED.** A permutation test on the
  between-mode variance of CR gives **p = 0.0016** (observed between-group SS 3.727
  vs null mean 0.678). The modes have genuinely different CR signatures: the
  repetition mode sits at CR ≈ 2.97 while every other mode sits at CR ≤ 1.37.

## The detector finding — language-id entropy, not CR

The mode × detector matrix is the actionable result. Across all 37 hallucinated
tracks, Whisper's default CR guard (CR > 2.4) catches **2.7%**; a **language-id
entropy** guard (Shannon entropy over the 6-bucket script distribution, > 0.5
bits) catches **81.1%**; a character TTR guard (> 0.7) catches **45.9%**; the
union of any of the three catches **83.8%**.

| Mode (n) | CR > 2.4 | lang-ent > 0.5 | TTR > 0.7 | any |
|---|--:|--:|--:|--:|
| multilingual_mixing (4) | 0.0% | **100.0%** | 25.0% | 100.0% |
| repetition (1) | **100.0%** | 100.0% | 0.0% | 100.0% |
| insertion_dominated (19) | 0.0% | **89.5%** | 57.9% | 89.5% |
| substitution_dominated (9) | 0.0% | 55.6% | 33.3% | 55.6% |
| semantic_drift (4) | 0.0% | 75.0% | 50.0% | 100.0% |
| **OVERALL (37)** | **2.7%** | **81.1%** | **45.9%** | **83.8%** |

**A script-based language-id entropy detector is ~30× more sensitive than CR on
AISHELL-4 hallucination** (81.1% vs 2.7%). CR is the right detector *only* for the
repetition tail (the one Mode R track); it is blind to the other 36. The
insertion-dominated majority (89.5% caught by lang-ent) is the precise mechanism
behind RQ12's "CR signal does not transfer" finding — it transfers because the
dominant mode is single-script *insertion*, which inflates language-id entropy
(Han + Latin mixing within the inserted text) but not compressibility. The
uncovered tail (16.2%, mostly substitution_dominated) is the hard residual: short,
single-script, low-entropy, low-TTR substitutions that no cheap surface detector
flags.

## Method

### Data source (read-only, not overwritten)

`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
(label `external/sanity-check`, PR #890): 77 windows × 30 s from AISHELL-4 meeting
M_R003S02C01 (6 speakers, oracle-TextGrid separation, Whisper-tiny, MeetEval
cpWER/orcWER). Each window stores the per-speaker separated transcripts, the mixed
transcript, mixed/separated cpWER, and lengths. A track is *hallucinated* iff
`always_separated_cpwer > 1.0` — the same 37-track set RQ12 used.

### Reference-free features (computed from stored text only; no audio, no Whisper)

- **max CR** — Whisper-style `len(utf8)/len(zlib)` on each per-speaker concatenated
  separated transcript, max across speakers. Same **lower-bound proxy** as RQ12
  (concatenation dilutes CR vs Whisper's per-segment max).
- **distinct scripts** — count of language-script buckets present (Han / Latin /
  Hiragana / Katakana / Hangul); digits, punctuation, emoji, whitespace do not
  count as language scripts.
- **language-id entropy** — Shannon entropy (bits) over the 6-bucket script
  distribution + an "Other" bucket. 0 = single script; `log2(6) ≈ 2.586` = uniform
  over all 6 scripts.
- **character TTR** — `|distinct chars| / |total chars|` over non-whitespace chars
  (Whisper `<|...|>` tag artifacts and `<#>` separators stripped). Low TTR =
  repetitive; high TTR = diverse.
- **length ratio** — `separated_total_length / max(mixed_text_length, 1)`. When the
  mixed track is empty (common at NoOverlap silence gaps) this collapses to the
  separated length, which is `>> 2.0` for hallucinated windows.

### Mode assignment (mutually exclusive, by precedence)

| # | Mode | Condition | Intuition |
|---|------|-----------|-----------|
| 1 | `multilingual_mixing` | ≥ 3 distinct scripts | Han + Latin + any of Hiragana/Katakana/Hangul |
| 2 | `repetition` | max CR > 2.4 (and < 3 scripts) | Mode R, finding #21; the confident-attractor loop |
| 3 | `insertion_dominated` | length ratio > 2.0 | separated ≫ mixed → word insertion / long hallucination |
| 4 | `substitution_dominated` | 1.0 ≤ length ratio ≤ 2.0 | comparable length, high char count → substitutions |
| 5 | `semantic_drift` | length ratio < 1.0 | residual: single-script, not repetition, short vs mixed |

The length-ratio cut at 2.0 sits in an **empirical gap** in the data: among
non-empty mixed tracks the ratios cluster at ≤ 1.73, with a few clear outliers at
2.36 / 3.31 / 3.32 and the empty-mixed cases (which collapse to the separated
length, all ≥ 9) falling well above. The 1.0 substitution/drift cut separates
"comparable-to-mixed" from "shorter-than-mixed" transcripts. Both cuts are
documented operational heuristics, not validated categories — see Limitations.

### Statistics

- **Bootstrap 95% CIs** on mode proportions and on per-mode mean CR: 10,000
  resamples, seed=42, resampling the 37 tracks with replacement.
- **H14c permutation test**: statistic = between-group sum of squares of CR
  (`Σ_mode n_mode·(mean_CR_mode − grand_mean)²`); null = permute mode labels among
  the 37 tracks, 10,000 permutations, seed=42; p = fraction of null ≥ observed.

## What the 37 tracks look like (mode by mode)

- **insertion_dominated (19, 51.4%)** — the bulk. 16 of 19 have an *empty* mixed
  track (`mixed_text_length == 0`): at NoOverlap silence gaps the mixed decoder
  emits nothing, while the oracle-separated track feeds Whisper a long
  silence-padded segment that triggers a long single-script (Han ± Latin)
  hallucinated transcript (e.g. w18's `"大小的表演怎么能把那个师..."`, w65's
  `"你能化的?你能化的?你能化的?..."`). Mean cpWER 2.11, mean CR 1.15 (far below
  2.4), mean lang-ent 0.91 bits. This is the real content of RQ12's "diverse"
  bucket.
- **substitution_dominated (9, 24.3%)** — comparable-length single-script tracks
  where cpWER > 1 is driven by character substitutions rather than length
  inflation (e.g. w22, w30, w48). Mean CR 1.37, mean lang-ent 0.68. This is the
  **hardest mode to detect** (any-detector coverage 55.6%): short, single-script,
  low-entropy, low-TTR — no cheap surface signal flags it.
- **multilingual_mixing (4, 10.8%)** — the vivid case RQ12 quoted (w00, w51, w68,
  w73), mixing Han + Latin + Hiragana/Hangul. Highest mean cpWER (2.92) but the
  *minority* surface form. 100% caught by lang-ent (entropy 1.29–1.42 bits).
- **semantic_drift (4, 10.8%)** — residual: single-script, shorter than the mixed
  track (ratio < 1.0), e.g. w05 (`窩執列電型尺寸直播主意...`, 36 chars vs 84 mixed),
  w41, w42, w45. Highest mean cpWER (2.44) but small n. "Semantically unrelated" is
  *inferred* from low length ratio + single script, not measured (no embeddings).
- **repetition (1, 2.7%)** — the single CR-caught track (w18, CR 2.97, the only
  HeavyOverlap hallucination). This is Mode R from finding #21 — the confident
  repetition attractor the silence-aware gate was designed for.

## What this changes for the project

1. **RQ12's "diverse" bucket is mostly insertion, not multilingual mixing.** The
   headline refinement: the dominant hallucination mode on AISHELL-4 is
   single-script *insertion* (51.4%), where the separated track emits a long wrong
   transcript into a silence gap while the mixed track emits nothing. Multilingual
   mixing is real but is the minority (10.8%). This sharpens RQ12's H12c doubt:
   the silence-aware gate targets Mode R (repetition, 2.7%); the actual failure
   mass is insertion-dominated, which is a *different* mechanism.
2. **Language-id entropy is the deployable detector for AISHELL-4, not CR.** A
   script-distribution entropy guard (> 0.5 bits) catches 81.1% of hallucinated
   separated tracks vs CR's 2.7% — a ~30× sensitivity gain, computed from the same
   stored text with no model. This is the concrete detector RQ12 called for ("the
   project needs a detector for *diverse* hallucination, e.g. language-id
   entropy"). The uncovered 16.2% tail is the substitution_dominated mode, which
   needs a stronger (non-surface) signal.
3. **The modes are statistically distinguishable.** H14c (p=0.0016) means the
   taxonomy is not arbitrary — the modes have different CR signatures, justifying
   mode-specific detectors rather than one universal guard. CR is mode-2-specific
   (repetition); lang-ent is mode-1/3-specific (multilingual + insertion); the
   substitution tail needs its own approach.

## Honest limitations

1. **Single meeting, n=37.** Only M_R003S02C01 was available; bootstrap CIs on
   mode proportions are wide (e.g. insertion_dominated [35.1%, 67.6%],
   multilingual [2.7%, 21.6%]). Point estimates are stable, but per-mode fractions
   are indicative, not precise. Modes with n=1 (repetition) or n=4
   (multilingual, drift) have especially wide or degenerate CIs.
2. **Length-ratio heuristics are operational, not validated.** The 2.0
   insertion/substitution cut and the 1.0 substitution/drift cut sit in empirical
   gaps but are not principled. A few edge cases (e.g. w21: 9 chars separated vs 0
   mixed → classified insertion_dominated despite a short transcript) show the
   boundary fuzz. A clustering or embedding-based taxonomy would be more robust.
3. **CR is a lower-bound proxy** on concatenated per-speaker text (see RQ12). True
   Whisper per-segment CR may be higher, so the repetition-mode count (1) is a
   conservative lower bound; the qualitative conclusion (repetition is the
   minority) is robust because the gap (2.7% vs 10%) is small and the proxy bias
   works against H14b.
4. **Language-id entropy is script-based, not a true language identifier.** It
   cannot distinguish, e.g., English-only drift from Han-only drift within a
   single script, and the 0.5-bit threshold is a heuristic (~10% minority script
   in a 2-script mix). A real language-ID model would be more accurate but is out
   of scope (numpy + stdlib only; no Whisper, no audio).
5. **Semantic drift is a residual catch-all.** "Semantically unrelated" is
   *inferred* from low length ratio + single script, not measured directly (no
   embeddings, no semantic similarity). The label is a hypothesis, not a
   measurement.
6. **Oracle-TextGrid separation; Whisper-tiny only.** The mode mix is specific to
   oracle separation (true silence gaps) and the tiny model. A real separator
   (residual noise) or a stronger model may produce a different mix — this is a
   hypothesis to test, not an assumption.

## Reproducibility

- Script: `results/frontier/hallucination_taxonomy/taxonomy_analysis.py`
- Per-track classification + features: `results/frontier/hallucination_taxonomy/taxonomy_results.csv`
- Summary + CIs + detectability matrix + hypothesis verdicts:
  `results/frontier/hallucination_taxonomy/taxonomy_results.json`
- Run: `python3 results/frontier/hallucination_taxonomy/taxonomy_analysis.py`
  (numpy + stdlib only; no scipy, no Whisper, no audio; deterministic, seed=42).
