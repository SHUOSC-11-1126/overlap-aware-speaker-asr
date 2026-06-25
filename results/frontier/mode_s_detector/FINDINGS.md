# RQ19: Mode S Detector — Content-Similarity for the Monoscript Hallucination Residual

> **Label: `experimental/frontier`** — a reanalysis-only test of whether transcript-content-similarity
> between the separated and mixed transcripts can catch the 2 Mode S monoscript-Chinese
> hallucinations that escape every surface detector. Does NOT run Whisper or overwrite any verified
> reference / gold table. Closes #914.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, PR #890). Surface-detector primitives and thresholds are lifted
> from RQ13 (`results/frontier/diverse_hallucination_detector/`, PR #904) and RQ16
> (`results/frontier/corrected_router_simulation/`, PR #912).

## Executive Summary

RQ16's corrected router (cpWER 1.043 vs oracle 1.017) still loses on 2 windows (22, 30):
monoscript-Chinese separated hallucinations where lang-id entropy < 0.409 bits, length ratio ~1.02,
CR < 2.4 — no surface detector (which inspects the separated track in isolation) fires. This is the
"Mode S" residual. RQ19 asks whether comparing the separated transcript to the MIXED transcript (a
second hypothesis text from the same audio) exposes the residual.

**The central empirical finding, discovered during analysis, inverts the prior.** Mode S separated
text is NOT gibberish — it is a **near-duplicate of the mixed text** with small character
substitutions (window 22: 那种→那些, 南方户→男生后; window 30: 說說大好→那個都給包包包). Mode S therefore
has **HIGH** content-similarity to mixed, the *opposite* of diverse hallucination (low similarity).
Each feature is calibrated two-sidedly (both orientations tried) so the data chooses the direction.

The high-similarity Mode S profile is **statistically distinct** — 4 of 6 features have permutation
p < 0.05 (best: token-overlap Jaccard, p = 0.0294) — but it is **non-deployable at 90% specificity**
because 10-13 clean single-speaker (or 2-speaker) non-hallucinated tracks ALSO have high
content-similarity to mixed (sep ≈ mix when there is no speaker reordering). Flagging both Mode S
tracks forces specificity down to 70-75%. At 90% specificity the best content-similarity detector
catches **0%** of Mode S; catching 100% requires dropping specificity to ~75%.

| Detector (at 90% specificity) | spec | sens (Mode S, n=2) | sens (all 37) | perm p |
|-------------------------------|-----:|-------------------:|--------------:|-------:|
| bigram Jaccard                | 97.5% | 0.0% | 0.0% | 0.0369 |
| trigram Jaccard               | 97.5% | 0.0% | 0.0% | 0.1252 |
| Levenshtein ratio             | 100%  | 0.0% | 0.0% | 0.0985 |
| shared char ratio             | 97.5% | 0.0% | 0.0% | 0.0303 |
| LCS ratio                     | 97.5% | 0.0% | 0.0% | 0.0295 |
| **token-overlap Jaccard (best)** | 97.5% | 0.0% | 0.0% | **0.0294** |
| lang-id entropy alone (RQ13)  | 92.5% | 0.0% | 94.6% (35/37) | — |
| **combined (best OR lang-id)** | 90.0% | 0.0% | 94.6% (35/37) | — |

**Hypothesis verdicts: H19a NOT SUPPORTED, H19b NOT SUPPORTED, H19c SUPPORTED.** Content-similarity
detects a distinct Mode S profile (H19c) but cannot operationalize it at deployable specificity
(H19a), and combining it with lang-id entropy adds nothing — the combined detector equals lang-id
alone on sensitivity (94.6%, missing the > 95% target by 1 track) and is slightly *worse* on
specificity (90.0% vs 92.5%) because the content-similarity operating point flags 1 clean
near-duplicate non-hallucinated track without catching any hallucinated track. The 2 Mode S windows
remain the residual gap that transcript-only reference-free detectors cannot close.

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min). Each window stores
`separated_text_per_speaker`, `mixed_text`, and the cpWER each route would yield. Hallucination
label: `always_separated_cpwer > 1.0` (37 hallucinated / 40 non-hallucinated, RQ12's split). Mode S
= hallucinated AND `lang_id_entropy < 0.409` AND `length_ratio < 2.0` AND `cr < 2.4` — verified to
be exactly windows 22 and 30, matching RQ16's residual.

### Content-similarity features (computed from stored transcripts only)

For each window the separated transcript is the concatenation of the per-speaker separated texts;
the mixed transcript is `mixed_text`. Six features are computed between them:

1. **Character bigram Jaccard** — |bigrams(sep) ∩ bigrams(mix)| / |union| (set of character bigrams).
2. **Character trigram Jaccard** — same on trigrams.
3. **Length-normalised Levenshtein** — edit_distance(sep, mix) / max(len). High = dissimilar.
4. **Shared character ratio** — |set(sep chars) ∩ set(mix chars)| / |union|.
5. **LCS ratio** — longest common subsequence / max(len). High = sep is a subsequence of mix.
6. **Token-overlap Jaccard** — Jaccard over script-aware token sets (RQ13 tokeniser).

Levenshtein and LCS use stdlib O(n·m) DP; no external deps. All features are order-sensitive
(Levenshtein, LCS) or order-insensitive (Jaccard variants) — the spread across both classes is
deliberate, to test which is robust to speaker reordering.

### Two-sided calibration

Each feature is calibrated **two-sidedly** at >= 90% specificity on the 40 non-hallucinated tracks:
both orientations are tried (flag if score >= t, flag if score <= t). This is necessary because Mode
S's high-similarity direction is not knowable a priori (it turned out to be the *opposite* of diverse
hallucination). Among operating points with specificity >= 90%, the one with maximal Mode S
sensitivity is kept (tiebreak: all-hallucinated sensitivity, then specificity).

### Best detector + combined detector

The best content-similarity detector is the feature with the **lowest permutation p-value** (most
distinct Mode S profile); tiebreak: highest Mode S sensitivity at 90% specificity. This is
token-overlap Jaccard (perm p = 0.0294). The combined detector OR-combines the best detector's
90%-specificity operating point with the RQ13 lang-id entropy detector (threshold 0.409 bits), and
combined sensitivity / specificity are measured on all 77 tracks.

### Permutation test (H19c)

Test statistic = mean(feature | Mode S) − mean(feature | others). The Mode S label is permuted among
the 77 tracks (10,000 permutations, seed=42); p-value (two-sided) = fraction of permutations with
|stat| >= |observed|, with +1 smoothing. Run for all 6 features.

### Statistics

Bootstrap 95% CIs use 10,000 resamples (seed=42) with FIXED full-sample thresholds (threshold
uncertainty not included; reported as a limitation). All code is numpy + stdlib only.

## Results

### Per-detector table (at 90% specificity, two-sided calibration)

| Detector | dir | threshold | spec | sens (Mode S) | sens (all 37) | perm p |
|----------|-----|----------:|-----:|--------------:|--------------:|-------:|
| bigram_jaccard | high | 1.0000 | 97.5% | 0.0% | 0.0% | 0.0369 |
| trigram_jaccard | high | 1.0000 | 97.5% | 0.0% | 0.0% | 0.1252 |
| lev_ratio | none | inf | 100% | 0.0% | 0.0% | 0.0985 |
| shared_char_ratio | high | 1.0000 | 97.5% | 0.0% | 0.0% | 0.0303 |
| lcs_ratio | high | 1.0000 | 97.5% | 0.0% | 0.0% | 0.0295 |
| token_overlap_jaccard | high | 1.0000 | 97.5% | 0.0% | 0.0% | **0.0294** |

At >= 90% specificity every content-similarity detector flags 0 Mode S tracks — the only operating
points that meet 90% specificity are the degenerate "flag only perfect duplicates" (threshold 1.0),
which Mode S (near-duplicate, not identical) does not trigger.

### Ceiling analysis (best detector: token-overlap Jaccard)

Max Mode S sensitivity achievable as the specificity floor is relaxed — this exposes the
deployability gap:

| Specificity floor | Max sens (Mode S) | achieved spec |
|------------------:|------------------:|--------------:|
| >= 0.50 | 100% | 50.0% |
| >= 0.70 | 100% | 70.0% |
| >= 0.80 | 0% | 100% |
| >= 0.90 | 0% | 100% |
| >= 0.95 | 0% | 100% |

Catching both Mode S tracks (100% sensitivity) is achievable only at specificity <= 70%; between
70% and 80% specificity there is no operating point that flags any Mode S track. The discrimination
is bimodal: Mode S sits in a similarity band (token-overlap 0.70-0.76) that overlaps with the
non-hallucinated single-speaker band, and the next-lower hallucinated band is far away.

### Combined detector (best content-similarity OR lang-id entropy, at 90% spec)

| Metric | Value |
|--------|------:|
| sensitivity (all 37 hallucinated) | 94.6% (35/37) |
| specificity (40 non-hallucinated) | 90.0% (36/40) |
| sensitivity (Mode S, n=2) | 0.0% (0/2) |
| bootstrap CI 95% (sensitivity) | [86.2%, 100.0%] |
| bootstrap CI 95% (specificity) | [79.5%, 97.7%] |

The combined detector equals lang-id entropy alone on sensitivity (94.6%) and is slightly *worse* on
specificity (90.0% vs 92.5%) because the content-similarity 90%-spec operating point flags 1 clean
near-duplicate non-hallucinated track (window 12: sep ≡ mix, token-overlap = 1.0) without catching
any hallucinated track. Content-similarity adds a false positive without adding a true positive.

### Permutation test (H19c)

| Feature | Mode S mean | others mean | stat | perm p (two-sided) | n extreme |
|---------|------------:|------------:|-----:|-------------------:|----------:|
| bigram_jaccard | 0.534 | 0.145 | +0.389 | 0.0369 | 368 / 10000 |
| trigram_jaccard | 0.418 | 0.126 | +0.291 | 0.1252 | 1251 / 10000 |
| lev_ratio | 0.275 | 0.686 | −0.411 | 0.0985 | 984 / 10000 |
| shared_char_ratio | 0.709 | 0.194 | +0.515 | 0.0303 | 302 / 10000 |
| lcs_ratio | 0.755 | 0.203 | +0.552 | 0.0295 | 294 / 10000 |
| **token_overlap_jaccard** | 0.727 | 0.194 | +0.534 | **0.0294** | 293 / 10000 |

4 of 6 features have p < 0.05. Mode S is consistently MORE similar to mixed than other tracks
(positive stat for similarity features, negative for the distance feature `lev_ratio`). The profile
is real and statistically distinct — the limitation is that "more similar to mixed" is also the
profile of clean single-speaker tracks, so the distinctness does not translate to deployable
discrimination.

## Hypothesis Verdicts

- **H19a — content-similarity detector achieves > 50% sensitivity on Mode S at > 90% specificity:
  NOT SUPPORTED.** The best detector (token-overlap Jaccard) catches 0% of Mode S at 90%
  specificity (sens = 0.0%, spec = 97.5%, CI [0.0%, 0.0%]). Catching 100% of Mode S requires
  specificity <= 70% (see ceiling analysis). The Mode S high-similarity profile is confounded with
  clean single-speaker non-hallucinated tracks (10-13 of 40 have similarly high similarity).

- **H19b — combining content-similarity with lang-id entropy achieves > 95% sensitivity on all 37
  hallucinated: NOT SUPPORTED.** Combined sensitivity is 94.6% (35/37, CI [86.2%, 100.0%]); lang-id
  alone is also 94.6% (35/37). Content-similarity adds 0 Mode S tracks at 90% specificity, so the
  combined detector equals lang-id alone and misses the > 95% target by 1 track. Combined
  specificity drops slightly to 90.0% (vs lang-id's 92.5%) because content-similarity flags 1 clean
  near-duplicate without catching any hallucinated track.

- **H19c — Mode S tracks have a distinct content-similarity profile (permutation p < 0.05):
  SUPPORTED.** Best feature token-overlap Jaccard: p = 0.0294 (293/10000 extreme). 4 of 6 features
  have p < 0.05 (bigram_jaccard 0.0369, shared_char_ratio 0.0303, lcs_ratio 0.0295,
  token_overlap_jaccard 0.0294). Mode S is MORE similar to mixed than other tracks (near-duplicate),
  which is a distinct profile — but distinct in the high-similarity direction, confounded with clean
  single-speaker tracks. H19c is a statistical-distinctness result, not a deployability result.

## Honest Limitations

1. **n = 2 Mode S tracks (the headline caveat).** The entire analysis rests on 2 windows. Mode S
   sensitivity can only take values 0%, 50%, 100%, and the permutation test's resolution is bounded
   by C(77,2) = 2926 distinct labelings. H19c's p = 0.0294 is "significant" but with n = 2 it should
   be read as suggestive, not definitive. A Mode S count of 2 is also why the ceiling analysis is
   bimodal (0% or 100%): there is no middle ground to estimate a partial sensitivity.

2. **The confound is structural, not statistical.** The non-deployability (H19a/H19b failing) is
   not a small-sample artefact — it is a structural confound: clean single-speaker tracks have
   sep ≈ mix (high content-similarity) for the legitimate reason that there is no speaker
   reordering, exactly the same surface property Mode S has for the illegitimate reason that the
   separator failed and Whisper re-decoded the mixed audio. No content-similarity feature computed
   between sep-concatenated and mix can tell these two cases apart, because the feature that would
   distinguish them (whether the separation actually produced per-speaker content) is precisely what
   is missing. More data would not fix this; a different signal surface (e.g. speaker-attribution
   consistency, or the per-speaker separated length distribution) is needed.

3. **In-sample calibration.** The 90%-specificity thresholds and the lang-id 0.409 threshold are
   calibrated on these exact 77 windows (RQ13/RQ16). The combined detector's 94.6% sensitivity is
   an in-sample estimate. Out-of-sample transfer is untested (single AISHELL-4 meeting).

4. **Permutation test assumes exchangeability.** The 10,000 permutations sample labelings of 2-of-77
   with replacement; the p-value is reported with +1 smoothing and is bounded by the 2926 distinct
   labelings. A two-sided test was used because "distinct profile" is non-directional, though the
   mechanism (Mode S more similar to mixed) is directional — a one-sided test would give a smaller
   p-value but would post-hoc choose the direction.

5. **Sep-concatenation discards speaker structure.** Concatenating per-speaker texts loses the
   speaker-attribution signal that might distinguish Mode S (where the separation failed) from
   clean single-speaker (where it succeeded). A per-speaker content-similarity profile (e.g.
   does each speaker's separated text appear as a contiguous block in the mixed text?) might break
   the confound; this is left to future work.

6. **Oracle-TextGrid-specific.** Mode S arises from oracle-TextGrid separation leaving true silence
   that Whisper fills. A real separator produces residual noise, not true silence, and the
   near-duplicate mechanism may differ.

## Reproducibility

- Script: `python3 results/frontier/mode_s_detector/mode_s_detector_analysis.py` (deterministic;
  numpy + stdlib only; no scipy / sklearn / Whisper). Runs in ~15 s.
- Outputs: `mode_s_results.csv` (per-window: window_id, hallucinated, mode_s, lang_id_entropy,
  length_ratio, cr, bigram_jaccard, trigram_jaccard, lev_ratio, shared_char_ratio, lcs_ratio,
  token_overlap_jaccard, best_detector_flag) and `mode_s_results.json` (summary, per-detector
  calibration + permutation tests + ceiling analysis, combined detector, hypothesis verdicts,
  per-window rows).
- Bootstrap: 10,000 resamples, seed=42. Permutation: 10,000 permutations, seed=42.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

RQ16 showed the corrected router recovers the AISHELL-4 gap mechanistically (cpWER 1.206 → 1.043)
but leaves a 2-window residual (Mode S) that no surface detector catches. RQ19 tested the natural
next idea — compare the separated transcript to the mixed transcript to expose the residual — and
found a **negative deployability result with a positive statistical finding**:

- Mode S DOES have a distinct content-similarity profile (H19c, p ≈ 0.03): it is a near-duplicate of
  the mixed text, not gibberish. This reframes Mode S from "monoscript semantic hallucination" to
  "separator-failure near-duplicate of the mixed decode" — the separator produced essentially the
  mixed audio back, and Whisper re-decoded it with small substitutions.
- But this distinctness is **not deployable** (H19a/H19b fail): the high-similarity profile is
  confounded with clean single-speaker tracks, against which transcript-only content-similarity
  cannot discriminate. At 90% specificity the best detector catches 0% of Mode S; catching 100%
  requires specificity <= 70%.

The residual gap (2 windows, 0.026 cpWER) is therefore **beyond what reference-free
transcript-only content-similarity can close**. The signal surface that would break the confound is
not in the sep-vs-mix text similarity but in whether the separation actually produced per-speaker
content (speaker-attribution consistency, per-speaker length distribution, or the audio-side RQ8
silence gate). Until such a signal is wired in, the corrected router's 1.043 remains the
transcript-only ceiling on AISHELL-4, and Mode S remains the documented residual.
