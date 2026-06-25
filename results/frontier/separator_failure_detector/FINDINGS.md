# RQ22 — Separator-failure detector: per-speaker transcript structure for Mode S residual

Label: experimental/frontier
Closes: #920
Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (label `external/sanity-check`, PR #890)

## Executive summary

RQ22 tested whether per-speaker transcript structure can catch the 2 Mode S monoscript-Chinese hallucinations (windows 22, 30) that escape every surface detector (RQ13 lang-id entropy, RQ14 length/CR) and every content-similarity detector (RQ19). Seven per-speaker-structure features were computed (per-speaker length entropy, per-speaker length Gini, sep-to-mix length ratio, sep-to-mix runtime ratio, speaker-attribution consistency, per-speaker overlap fraction, effective speaker count), each calibrated two-sidedly at >= 90% specificity on the 40 non-hallucinated tracks, with a permutation test (10,000 perms, seed=42) for a distinct Mode S profile.

All three hypotheses were KILLED. The best per-speaker-structure detector (per_speaker_length_entropy, lowest permutation p=0.4508) catches 0% of Mode S at 90% specificity, and the ceiling analysis shows 0% sensitivity even if specificity is relaxed to 50%. The combined detector (best OR lang-id) achieves 94.6% sensitivity on the 37 hallucinated — exactly equal to lang-id alone — so per-speaker-structure adds 0 Mode S tracks. Zero of seven features have a distinct Mode S profile (all permutation p >= 0.05).

The negative result has a single mechanistic cause: Mode S's per-speaker profile (one speaker carries the whole near-duplicate of mixed, the other channels empty) is the SAME profile as the majority of clean single-speaker non-hallucinated tracks. 32 of 40 non-hallucinated tracks have per-speaker length entropy = 0, 19 of 40 have effective speaker count = 1, and 34 of 40 have per-speaker overlap fraction = 0 — all identical to Mode S. Per-speaker structure does not break the RQ19 confound; it reproduces it. Mode S is structurally indistinguishable from a clean single-speaker track at the transcript level because the separator failure produces exactly the per-speaker distribution a genuine single-speaker track would produce.

## Method

### Data
77 windows of 30 s from AISHELL-4 meeting M_R003S02C01. Hallucination label: `always_separated_cpwer > 1.0` (37 hallucinated / 40 non-hallucinated). Mode S label: hallucinated AND `lang_id_entropy < 0.409` AND `length_ratio < 2.0` AND `cr < 2.4` — exactly windows 22 and 30 (RQ16/RQ19).

### Mode S mechanism (per window)
- Window 22 (`num_speakers=2`): only speaker 005-F carries text (98 chars, near-duplicate of the 96-char mixed transcript with small substitutions e.g. 那种→那些, 南方户→男生后); speaker 006-F is empty. Sep-to-mix length ratio 1.021; runtime ratio 7.052.
- Window 30 (`num_speakers=1`): speaker 005-F carries 154 chars (near-duplicate of the 150-char mixed with substitutions e.g. 說說大好→那個都給包包包). Sep-to-mix length ratio 1.027; runtime ratio 0.991.

### Seven per-speaker-structure features
1. `per_speaker_length_entropy` — Shannon entropy (bits) over normalised per-speaker separated text lengths. Low = one speaker dominates.
2. `per_speaker_length_gini` — Gini coefficient of per-speaker separated text lengths (including empty channels as zeros). High = unequal split.
3. `sep_to_mix_length_ratio` — `separated_total_length / mixed_text_length` (Mode S hypothesis: approx 1.02).
4. `sep_to_mix_runtime_ratio` — `separated_runtime_sec / mixed_runtime_sec`.
5. `speaker_attribution_consistency` — fraction of non-empty per-speaker separated texts that appear as an exact contiguous substring of the mixed text (whitespace stripped on both sides).
6. `per_speaker_overlap_fraction` — fraction of non-empty speaker pairs whose separated texts share at least one non-whitespace character.
7. `effective_speaker_count` — number of distinct non-empty per-speaker separated texts.

### Calibration and statistics
Each feature calibrated two-sidedly at >= 90% specificity on the 40 non-hallucinated tracks (both orientations tried; Mode S sensitivity maximised; tiebreak all-hallucinated sensitivity, then specificity). Best detector = lowest permutation p-value; tiebreak highest Mode S sensitivity at 90% spec. Permutation test: 10,000 perms, seed=42, two-sided, +1 smoothing, test statistic = mean(feature | Mode S) − mean(feature | others). Bootstrap 95% CIs: 10,000 resamples, seed=42, fixed full-sample thresholds. Combined detector = best per-speaker-structure (at its 90%-specificity operating point) OR lang-id entropy (threshold 0.409 bits). numpy + stdlib only.

## Results

### Per-detector table (at 90% specificity operating point)

| Detector | Dir | Threshold | Spec | Sens_MS | Sens_AH | Perm p | Sens_MS CI 95% |
|---|---|---|---|---|---|---|---|
| per_speaker_length_entropy | high | 0.6500 | 92.5% | 0.0% | 70.3% | 0.4508 | [0.000, 0.000] |
| per_speaker_length_gini | high | 1.1224 | 90.0% | 0.0% | 43.2% | 0.7870 | [0.000, 0.000] |
| sep_to_mix_length_ratio | high | 2.3590 | 90.0% | 0.0% | 62.2% | 0.5199 | [0.000, 0.000] |
| sep_to_mix_runtime_ratio | high | 5.8397 | 90.0% | 50.0% | 56.8% | 0.7355 | [0.000, 1.000] |
| speaker_attribution_consistency | high | 1.0000 | 97.5% | 0.0% | 0.0% | 1.0000 | [0.000, 0.000] |
| per_speaker_overlap_fraction | none | inf | 100.0% | 0.0% | 0.0% | 0.4911 | [0.000, 0.000] |
| effective_speaker_count | high | 3.0000 | 97.5% | 0.0% | 37.8% | 0.5615 | [0.000, 0.000] |

`Sens_MS` = sensitivity on Mode S (n=2). `Sens_AH` = sensitivity on all 37 hallucinated. Dir = flagging direction at the calibrated operating point.

The best per-speaker-structure detector by selection rule (lowest permutation p-value) is `per_speaker_length_entropy` (p=0.4508), which catches 0% of Mode S at 92.5% specificity.

### Ceiling analysis (best detector)

| Specificity floor | Max Sens_MS | Direction | Achieved spec |
|---|---|---|---|
| >= 0.50 | 0.0% | none | 100.0% |
| >= 0.70 | 0.0% | none | 100.0% |
| >= 0.80 | 0.0% | none | 100.0% |
| >= 0.90 | 0.0% | none | 100.0% |
| >= 0.95 | 0.0% | none | 100.0% |

Relaxing specificity all the way to 50% does not help: `per_speaker_length_entropy` cannot catch a single Mode S track at any specificity floor because Mode S's entropy (0) is the modal value among non-hallucinated tracks.

### Combined detector (best OR lang-id entropy)

- Rule: `(per_speaker_length_entropy >= 0.65) OR (lang_id_entropy > 0.409)`
- Specificity: 87.5% (CI 95% [0.761, 0.971]) — below 90% because OR-ing adds the best detector's false positives without adding any Mode S true positives.
- Sensitivity on all 37 hallucinated: 94.6% (35/37, CI 95% [0.862, 1.000]) — identical to lang-id alone.
- Sensitivity on Mode S: 0.0% (0/2) — identical to lang-id alone.

Lang-id entropy alone reference: specificity 92.5%, sensitivity 94.6% (35/37), sensitivity on Mode S 0.0% (0/2). Per-speaker-structure adds 0 hallucinated tracks and 0 Mode S tracks over lang-id alone.

### Permutation test (H22c)

| Feature | Mode S mean | Others mean | Test stat | Perm p (two-sided) |
|---|---|---|---|---|
| per_speaker_length_entropy | 0.0000 | 0.4610 | -0.4610 | 0.4508 |
| per_speaker_length_gini | 0.5000 | 0.6872 | -0.1872 | 0.7870 |
| sep_to_mix_length_ratio | 1.0237 | 31.0993 | -30.0756 | 0.5199 |
| sep_to_mix_runtime_ratio | 4.0216 | 5.6916 | -1.6700 | 0.7355 |
| speaker_attribution_consistency | 0.0000 | 0.0200 | -0.0200 | 1.0000 |
| per_speaker_overlap_fraction | 0.0000 | 0.3809 | -0.3809 | 0.4911 |
| effective_speaker_count | 1.0000 | 1.5600 | -0.5600 | 0.5615 |

Zero of seven features have permutation p < 0.05. Mode S is not in the extreme tail of any per-speaker-structure feature. Note `sep_to_mix_length_ratio` has a large negative test statistic (-30.08) because the "others" mean (31.1) is inflated by hallucinated tracks with very large separated lengths; the non-hallucinated tracks near Mode S's ratio of ~1.02 are numerous enough to keep the permutation p high (0.52).

### The structural confound (why per-speaker structure fails)

Among the 40 non-hallucinated tracks:
- 32 (80%) have `per_speaker_length_entropy == 0.0` — same as both Mode S windows.
- 19 (48%) have `effective_speaker_count == 1.0` — same as both Mode S windows.
- 34 (85%) have `per_speaker_overlap_fraction == 0.0` — same as both Mode S windows.
- 4 (10%) have `sep_to_mix_length_ratio` in [1.00, 1.05] — same as both Mode S windows.
- 11 (28%) have `sep_to_mix_length_ratio` in [0.95, 1.10] — same as both Mode S windows.

Mode S's per-speaker profile is the profile of a clean single-speaker track. A separator that fails by re-decoding the mixed audio into one channel produces exactly the per-speaker distribution a genuine single-speaker track would produce, so per-speaker structure cannot tell them apart.

### Partial signal: sep_to_mix_runtime_ratio

`sep_to_mix_runtime_ratio` is the only feature that catches any Mode S track at 90% specificity: it flags window 22 (runtime ratio 7.052, threshold 5.840) but misses window 30 (runtime ratio 0.991). The ceiling never exceeds 50% (1 of 2) at any specificity floor, and the bootstrap CI for Mode S sensitivity is [0.000, 1.000] (consistent with 0% or 100% given n=2). This signal is a fragile artifact of window 22's unusually slow separated decoding (4.612 s vs 0.654 s mixed), not a structural separator-failure signature — window 30, which is the same Mode S mechanism, has a runtime ratio near 1.0 and is invisible to this feature.

## Hypothesis verdicts

### H22a — per-speaker-structure detector achieves > 50% sensitivity on Mode S (n=2) at > 90% specificity on non-hallucinated (n=40)
- Kill criterion: sensitivity <= 0% at 90% specificity.
- Best detector: `per_speaker_length_entropy` (lowest permutation p=0.4508).
- Sensitivity on Mode S at 90% spec: 0.0% (0/2). Specificity: 92.5%.
- Ceiling: 0.0% sensitivity even at specificity >= 50%.
- Verdict: NOT SUPPORTED. KILLED (kill criterion met: 0.0% <= 0% at 90% spec).

### H22b — combining best per-speaker-structure detector with lang-id entropy achieves > 95% sensitivity on all 37 hallucinated
- Kill criterion: combined sensitivity <= 94.6% (lang-id alone).
- Combined sensitivity on all hallucinated: 94.6% (35/37) — identical to lang-id alone (94.6%, 35/37).
- Per-speaker-structure adds 0 hallucinated tracks and 0 Mode S tracks over lang-id alone.
- Verdict: NOT SUPPORTED. KILLED (kill criterion met: 94.6% <= 94.6%).

### H22c — Mode S tracks have a distinct per-speaker-structure profile (permutation p < 0.05 on >= 1 feature)
- Kill criterion: all features p >= 0.05.
- Best feature permutation p: 0.4508 (`per_speaker_length_entropy`).
- Features with p < 0.05: 0 of 7.
- Verdict: NOT SUPPORTED. KILLED (kill criterion met: all 7 features p >= 0.05).

## Honest limitations

1. **n=2 Mode S.** Both Mode S windows come from a single AISHELL-4 meeting (M_R003S02C01) transcribed by whisper-tiny with oracle TextGrid separation. The Mode S mechanism (separator returns one near-duplicate of mixed in a single channel) is documented on exactly 2 windows; the permutation test resolution is bounded by C(77,2)=2926 distinct labelings, and bootstrap CIs on Mode S sensitivity are wide (often [0, 1]). The negative verdict is robust within this sample but the positive case for per-speaker structure on a larger Mode S corpus is untested.

2. **In-sample calibration.** All thresholds are calibrated on the same 77 tracks they are evaluated on. With n=2 Mode S this is unavoidable (no held-out Mode S exists), but it means the ceiling analysis is optimistic — even the optimistic ceiling is 0%, which strengthens the negative verdict.

3. **Oracle-TextGrid-specific.** Separation used oracle TextGrid boundaries, so the separator-failure mechanism here is "Whisper re-decoded the mixed audio after the separator returned the mixed audio in one channel." Real separation pipelines (e.g. speech separation models) may fail differently, and per-speaker structure may have different discriminative power there. The finding generalises to oracle-separated AISHELL-4, not to all separator failures.

4. **speaker_attribution_consistency uses strict exact-substring match.** Whisper produces slightly different text on each decode, so the near-duplicate Mode S text is NOT an exact substring of mixed (small character substitutions break the match). This feature is 0 for 98% of all tracks (Mode S and others) and is therefore non-informative as implemented. A fuzzy / LCS-based contiguous-attribution measure might be more informative, but it would also be confounded with clean single-speaker tracks for the same reason content-similarity was in RQ19.

5. **Per-speaker structure cannot, in principle, separate "one speaker spoke a contiguous span" from "the separator dumped the mixed audio into one channel."** Both produce one non-empty channel whose text is a near-duplicate of mixed. This is the fundamental identifiability limit, and it is the reason RQ19's content-similarity confound reproduces here at the per-speaker level.

## Reproducibility

```bash
python3 results/frontier/separator_failure_detector/separator_failure_detector_analysis.py
```

- Inputs (read-only, not modified): `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
- Outputs: `separator_failure_results.csv` (per-window: window_id, hallucinated, mode_s, all 7 features, lang_id_entropy, cr, best_detector_flag), `separator_failure_results.json` (summary, per-detector calibration + permutation tests + ceiling analysis, combined detector, hypothesis verdicts), `FINDINGS.md`.
- Dependencies: numpy + stdlib only (no scipy, sklearn, Whisper). Deterministic (seed=42 for permutation and bootstrap).
- Surface-detector primitives (`compression_ratio`, `script_category`, `language_id_entropy`) lifted verbatim from RQ13/RQ16/RQ19 so the Mode S definition is directly comparable.

## What this changes for the project

RQ19 found content-similarity is confounded with clean single-speaker tracks and speculated (limitation #5) that per-speaker structure might break the confound. RQ22 closes that speculation with a negative answer: per-speaker structure reproduces the confound because Mode S's per-speaker profile IS the clean single-speaker profile. The Mode S residual is therefore not identifiable from transcript text alone at any specificity — not from aggregate content (RQ19), not from per-speaker structure (RQ22).

This narrows the solution space for Mode S. The remaining avenues are signals OUTSIDE the transcript text:
- Acoustic / waveform features (e.g. does the separated channel's audio actually differ from mixed, or did the separator return a copy?).
- Separation-model internals (e.g. separator confidence, mask energy, embedding distance between channels).
- Metadata consistency (e.g. does the separated runtime diverge from what the speaker count would predict — `sep_to_mix_runtime_ratio` caught 1 of 2 Mode S here, suggesting runtime metadata has weak but non-zero signal worth a dedicated RQ).

Mode S remains a 2-window residual on AISHELL-4 (cpWER gap 0.026 above oracle). The corrected router (RQ16, cpWER 1.043) and lang-id entropy (RQ13, 94.6% sensitivity) are unchanged. RQ22 adds no deployable detector but does add a principled negative result: transcript-structure-based detection of Mode S is impossible because the failure mode is structurally identical to the clean case.
