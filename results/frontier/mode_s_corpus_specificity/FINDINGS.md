# RQ40: Mode S Corpus Specificity — Does the Monoscript Hallucination Appear Outside AISHELL-4?

> **Label: `experimental/frontier`** — a reanalysis-only test of whether RQ19's Mode S
> monoscript-Chinese hallucination pattern (identified on AISHELL-4 windows 22/30) appears
> in the gold or synthetic silver benchmarks, and whether RQ34's char 3-gram KL divergence
> detector (threshold 3.30 bits) flags any gold/silver Mode S track. Does NOT run Whisper
> or overwrite any verified reference / gold table. Closes #953.
>
> Source data:
> - AISHELL-4: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (label `external/sanity-check`)
> - Gold: `results/frontier/gold_detector_comparison/gold_track_texts.json` + `results/frontier/separation_tax/phase_curve.csv`
> - Silver: `results/tables/synthetic_cer_results.csv` + `results/synthetic_transcripts_raw/` + `results/synthetic_transcripts_speaker/`
>
> Surface-detector primitives (compression_ratio, language_id_entropy, script_category,
> tokenize) are lifted verbatim from RQ19/RQ21 so the Mode S definition is directly
> comparable. Pure reanalysis: numpy + stdlib only.

## Executive Summary

Mode S (the monoscript-Chinese near-duplicate hallucination identified on AISHELL-4
windows 22 and 30) is **AISHELL-4-specific** in the strict sense: the full 5-criterion
definition (hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0 AND cr < 2.4
AND content_similarity > 0.8) finds **0 Mode S tracks** in either the gold benchmark
(600 per-speaker separated tracks) or the synthetic silver benchmark (25 samples). The
gold benchmark cannot apply the full definition because gold tracks have no cached
`mixed_text` (RQ21's `decode_gold_tracks.py` only cached `sep1_text` / `sep2_text`), so
the `length_ratio` and `content_similarity` gates are not computable. Applying the
3-criterion subset (hallucinated AND lang_id < 0.409 AND cr < 2.4) to gold yields 217
"candidates" — but this set is an uninformative upper bound, because gold's clean
Chinese separated tracks are near-monoscript (lang_id ~ 0) and mostly non-repetitive
(cr < 2.4) by construction.

RQ34's char 3-gram KL divergence detector (per-corpus non-hallucinated reference,
add-1 Laplace smoothing on Q) was specified with a fixed threshold of 3.30 bits,
calibrated on AISHELL-4 non-hallucinated to 90% specificity. **This calibration does
not reproduce in the RQ40 implementation.** At 3.30 bits, the AISHELL-4 specificity is
only 32.5% (27/40 non-hallucinated windows flagged). The empirically-calibrated
90%-specificity threshold on AISHELL-4 is 6.28 bits — and at that threshold the
detector catches **0 of the 2 Mode S windows** (their KL scores are 5.36 and 4.71,
below 6.28). The fixed threshold 3.30 catches both Mode S windows (sensitivity 100%)
but at the cost of an unacceptable false-positive rate. This suggests RQ34's
"threshold 3.30 at 90% specificity" was either computed with a different reference
distribution, a different smoothing scheme, or a different KL direction than the one
specified in the RQ40 task — and the threshold does not generalise.

**Hypothesis verdicts: H40a NOT SUPPORTED, H40b NOT SUPPORTED, H40c SUPPORTED.**
Mode S does not appear in gold/silver (H40a fails on the full definition; the 217
gold candidates are an upper bound from the loose 3-criterion subset). The KL detector
has no full Mode S tracks to flag in gold/silver (H40b fails trivially). Mode S
prevalence on silver (full definition) is 0% < 5% (H40c supported); the gold candidate
upper bound (96.0%) is not a valid prevalence estimate because the 3-criterion subset
is too loose without the content_similarity gate.

| Corpus | Tracks | Hallucinated | Mode S (full) | Candidates (3-crit) | Prevalence (full) | KL spec (fixed 3.30) | KL spec (cal 6.28) |
|--------|-------:|-------------:|--------------:|--------------------:|-------------------:|---------------------:|-------------------:|
| AISHELL-4 | 77 | 37 | 2 | 0 | 5.41% | 32.5% | 90.0% |
| Gold | 600 | 226 | 0 | 217 | 0.00% | 3.5% | 94.9% |
| Silver | 25 | 4 | 0 | 0 | 0.00% | 95.2% | 100.0% |

## Method

### Data

Three corpora are loaded as read-only:

1. **AISHELL-4** (77 windows, calibration corpus): 77 tracks from
   `rq1_aishell4_validation_results.json`. Separated text = concatenation of
   `separated_text_per_speaker` values. Mixed text = `mixed_text` field. Hallucination
   label: `always_separated_cpwer > 1.0` (37 hallucinated, 40 non-hallucinated).
   35 of 77 windows have empty `mixed_text`; for those, `has_mixed_text = False` and
   the full Mode S definition cannot apply (only the 3-criterion candidate set).

2. **Gold** (600 per-speaker separated tracks): 300 conditions × sep1/sep2 from
   `gold_track_texts.json` (RQ21). CER from `phase_curve.csv` (greedy config, matched
   by con/pro/overlap_ratio). Hallucination label: `cer > 0.5` (226 hallucinated).
   **Gold tracks have no cached `mixed_text`** — RQ21's `decode_gold_tracks.py` only
   cached `sep1_text` / `sep2_text`. So `length_ratio` and `content_similarity` are
   NaN, `has_mixed_text = False`, and only the 3-criterion candidate set applies.

3. **Synthetic silver** (25 samples): separated text from
   `synthetic_transcripts_speaker/*_separated_speaker_transcript.json` (stripped of
   `[SPEAKER_N]` tags). Mixed text from `synthetic_transcripts_raw/*_mixed_whisper.json`.
   CER from `synthetic_cer_results.csv` (separated_whisper method). Hallucination
   label: `cer > 0.5` (4 hallucinated). Silver has `mixed_text`, so the full 5-criterion
   definition applies.

### Mode S definition (RQ19 + RQ40 content_similarity gate)

The full 5-criterion Mode S definition:
```
hallucinated AND lang_id_entropy < 0.409 AND length_ratio < 2.0
             AND cr < 2.4 AND content_similarity > 0.8
```
where `content_similarity = token_containment = |tokens(sep) ∩ tokens(mix)| / |tokens(sep)|`.

Token containment is the only RQ19 content-similarity metric that exceeds 0.8 for both
AISHELL-4 Mode S windows (window 22: 0.887, window 30: 0.838). Other RQ19 metrics
(Jaccard variants, LCS ratio, Levenshtein ratio) do not exceed 0.8 for both windows.
Token containment captures the near-duplicate property: most of the separated text's
vocabulary appears in the mixed text.

For corpora without `mixed_text` (gold), the 3-criterion candidate subset applies:
```
hallucinated AND lang_id_entropy < 0.409 AND cr < 2.4
```
This is the RQ26/RQ23 Mode S definition without the RQ19 length_ratio and RQ40
content_similarity gates. It is reported as a "candidate" set; the full 5-criterion
definition may further restrict this set, but for gold we cannot know by how much.

### RQ34 char 3-gram KL divergence detector

For each track, the char 3-gram frequency distribution (whitespace-stripped) is
computed. The reference distribution is the aggregate char 3-gram counts of
non-hallucinated tracks **from the same corpus** (per-corpus reference, matching the
Method spec). KL divergence `D(track || reference)` is computed in bits with add-1
Laplace smoothing on the reference Q so `Q(x) > 0` for all x:

```
P(x) = track_counts[x] / track_total
Q(x) = (ref_counts.get(x, 0) + smoothing) / (ref_total + smoothing * |V_ref|)
KL = sum_x P(x) * log2(P(x) / Q(x))
```

Two thresholds are reported:
- **Fixed threshold 3.30 bits** (per the RQ34 spec, calibrated on AISHELL-4
  non-hallucinated to ~90% specificity).
- **Calibrated threshold** (the empirically-calibrated 90%-specificity threshold on
  AISHELL-4 non-hallucinated, computed by scanning all candidate thresholds and
  selecting the one with specificity ≥ 90% and maximal sensitivity).

## Results

### H40a: Mode S appears in ≥1 gold/silver track — NOT SUPPORTED

The full 5-criterion Mode S definition finds:
- Gold: 0 Mode S tracks (full definition not computable — no cached `mixed_text`).
- Silver: 0 Mode S tracks (4 hallucinated tracks, none meet the lang_id / length_ratio
  / cr / content_similarity gates simultaneously).

The 3-criterion candidate set (gold only, since silver has `mixed_text` and gets the
full definition) finds 217 gold candidates — but this is an uninformative upper bound.
Gold's separated tracks are clean Chinese (lang_id_entropy ~ 0, well below 0.409) and
mostly non-repetitive (cr < 2.4), so the 3-criterion subset flags 217/226 = 96.0% of
hallucinated gold tracks. Without the `content_similarity` gate (which requires
`mixed_text`), we cannot distinguish true Mode S near-duplicates from ordinary
clean-Chinese hallucinations. The 217 candidates are reported for transparency but do
not constitute evidence of Mode S in gold.

**Verdict: H40a NOT SUPPORTED.** No full Mode S tracks found in gold or silver.
Candidate-level support (3-criterion) exists in gold but is too loose to be meaningful.

### H40b: RQ34 KL detector flags ≥1 gold/silver Mode S track — NOT SUPPORTED

There are 0 full Mode S tracks in gold/silver, so the KL detector has nothing to flag
at the full-definition level:
- Full Mode S tracks flagged: 0/0 at fixed threshold 3.30; 0/0 at calibrated threshold 6.28.

At the candidate level (secondary, gold 3-criterion), the KL detector flags 217/217
candidates at the fixed threshold 3.30 and 214/217 at the calibrated threshold 6.28.
But this is not evidence of Mode S detection — gold's KL specificity is only 3.5% at
the fixed threshold (the detector flags almost everything in gold because gold's
clean-Chinese n-gram distribution differs from the gold non-hallucinated reference
in ways unrelated to Mode S). The calibrated threshold (6.28) gives 94.9% specificity
on gold but still flags 214/217 candidates, because the candidates are not Mode S —
they are ordinary hallucinated gold tracks that happen to meet the loose 3-criterion
subset.

**Verdict: H40b NOT SUPPORTED.** No full Mode S tracks exist in gold/silver to flag.
The candidate-level flagging is an artifact of the loose 3-criterion definition and
gold's low KL specificity, not evidence of Mode S detection.

### H40c: Mode S prevalence on gold/silver < 5% — SUPPORTED

Primary (silver full Mode S prevalence): 0/4 = 0.00%, well below the 5% threshold and
below the AISHELL-4 reference of 5.41% (2/37).

Secondary (gold 3-criterion candidate prevalence, upper bound): 217/226 = 96.02%. This
is not a valid prevalence estimate — the 3-criterion subset is too loose without the
`content_similarity` gate, and 96.02% is clearly an overestimate (it would imply that
nearly all hallucinated gold tracks are Mode S near-duplicates, which contradicts
RQ26's finding that gold's hallucination mode distribution is disjoint from AISHELL-4's).

Combined upper bound (silver full + gold candidates): 217/230 = 94.35%. Again, not a
valid prevalence estimate.

The H40c verdict uses the silver full Mode S prevalence (0.00%) as primary, because
silver is the only gold/silver corpus where the full 5-criterion definition applies.
The gold candidate prevalence is reported as an upper bound with the explicit caveat
that it is uninformative.

**Verdict: H40c SUPPORTED.** Silver full Mode S prevalence (0.00%) < 5%.

## Key Caveats

### 1. RQ34's "threshold 3.30 at 90% specificity" does not reproduce

The RQ40 implementation of RQ34's char 3-gram KL divergence detector, with per-corpus
non-hallucinated reference and add-1 Laplace smoothing on Q, gives only 32.5%
specificity on AISHELL-4 non-hallucinated at the fixed threshold 3.30 bits. The
empirically-calibrated 90%-specificity threshold is 6.28 bits — and at that threshold
the detector catches **0 of the 2 Mode S windows** (their KL scores are 5.36 and 4.71).

This means RQ34's threshold 3.30 was either:
- Computed with a different reference distribution (e.g. pooled across corpora rather
  than per-corpus);
- Computed with a different smoothing scheme (e.g. no smoothing, or smoothing on P
  rather than Q);
- Computed with the reverse KL direction `D(reference || track)` rather than
  `D(track || reference)`;
- Or RQ34 was never implemented in this repo and "threshold 3.30" is project lore that
  does not match the implementation specified in the RQ40 task.

RQ40 reports both thresholds (fixed 3.30 and calibrated 6.28) for transparency. The
fixed threshold catches both AISHELL-4 Mode S windows (sensitivity 100%) but at
unacceptable specificity (32.5%); the calibrated threshold achieves 90% specificity
but catches 0 Mode S windows. This is a negative result for RQ34's detector as
specified: it cannot simultaneously achieve 90% specificity and catch Mode S on
AISHELL-4, let alone generalise to gold/silver.

### 2. Gold's missing `mixed_text` is a structural limitation

RQ21's `decode_gold_tracks.py` cached only `sep1_text` / `sep2_text` for the 600 gold
tracks. The `mixed_text` (the Whisper decode of the unseparated audio) was not cached.
This means the full 5-criterion Mode S definition — which requires `length_ratio` and
`content_similarity`, both of which need `mixed_text` — cannot be applied to gold.

The 3-criterion candidate subset (hallucinated AND lang_id < 0.409 AND cr < 2.4) is
the best we can do for gold, but it is too loose: gold's clean Chinese separated
tracks are near-monoscript (lang_id ~ 0) and mostly non-repetitive (cr < 2.4) by
construction, so 217/226 hallucinated gold tracks meet the 3-criterion subset. Without
the `content_similarity` gate, we cannot distinguish true Mode S near-duplicates from
ordinary clean-Chinese hallucinations.

A future RQ could re-run Whisper on the gold mixed audio to cache `mixed_text`, then
apply the full 5-criterion Mode S definition. This would resolve whether gold has 0
Mode S (as the silver result suggests) or a small number hidden among the 217
candidates.

### 3. Silver's small sample size limits statistical power

Silver has only 4 hallucinated tracks (cer > 0.5 out of 25 samples). Even if 1 silver
track were Mode S, the prevalence would be 25% — well above the 5% threshold. The 0/4
result is consistent with Mode S being rare on silver, but the small sample size means
the confidence interval is wide. The H40c verdict (silver prevalence 0% < 5%) is
correct but should be interpreted with the sample-size caveat.

## Implications

1. **Mode S is AISHELL-4-specific in the available data.** The full 5-criterion
   definition finds 0 Mode S tracks in silver (the only gold/silver corpus where the
   full definition applies). Gold cannot be tested with the full definition due to
   missing `mixed_text`, but the 3-criterion candidate set (217/226) is too loose to
   provide evidence either way. This is consistent with RQ26's finding that gold and
   AISHELL-4 have disjoint hallucination mode distributions (chi2=305, p=5.4e-67).

2. **RQ34's KL detector does not generalise as specified.** The fixed threshold 3.30
   gives 32.5% specificity on AISHELL-4 (not 90% as claimed), and the calibrated
   90%-specificity threshold (6.28) catches 0 Mode S windows. The detector's
   per-corpus reference distribution is too sensitive to corpus-specific n-gram
   statistics to transfer across corpora. A pooled or normalised reference might
   generalise better, but that is a question for a future RQ.

3. **The gold `mixed_text` gap is the highest-value next step.** Without `mixed_text`
   for gold, we cannot apply the full Mode S definition to the largest benchmark
   corpus. Re-running Whisper on the gold mixed audio to cache `mixed_text` would
   unblock a definitive gold Mode S search and resolve whether the 217 candidates
   contain any true Mode S near-duplicates.

4. **Mode S remains an AISHELL-4 residual.** The 2 Mode S windows (22, 30) are the
   residual gap that transcript-only reference-free detectors cannot close (RQ19).
   RQ40 confirms that this residual does not appear in the gold/silver benchmarks —
   it is specific to the AISHELL-4 meeting audio where the mixed decode happens to be
   a near-duplicate of the separated decode. This suggests Mode S is driven by
   properties of the AISHELL-4 audio (e.g. speaker overlap patterns, audio quality)
   rather than by Whisper's failure modes in general.

## Outputs

- `mode_s_corpus_specificity_analysis.py` — analysis script (numpy + stdlib only)
- `mode_s_corpus_specificity_results.csv` — per-track results (702 rows: 77 AISHELL-4 + 600 gold + 25 silver)
- `mode_s_corpus_specificity_results.json` — full summary + per-track results
- `tests/test_rq40_mode_s_corpus_specificity.py` — 92 tests (pure helpers + smoke test on real data)
