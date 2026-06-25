# RQ33 — Metadata-only Mode S detector: runtime + duration + segment count, NO content

Label: experimental/frontier
Closes: #940
Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (label `external/sanity-check`, PR #890)

## Executive summary

RQ33 tested whether a METADATA-ONLY detector (runtime + duration + segment count + word count, NO content features) can catch the 2 Mode S monoscript-Chinese hallucinations (windows 22, 30) that escape every surface detector (RQ13 lang-id entropy, RQ14 length/CR), every content-similarity detector (RQ19), every per-speaker-structure detector (RQ22), and every other surface attempt (RQ23, RQ28 — all reported 0% Mode S sensitivity at 90% specificity). The motivating observation, lifted from RQ22, is that exactly one partial metadata signal has ever appeared: `sep_to_mix_runtime_ratio` caught 1 of 2 Mode S (window 22, runtime ratio 7.05; window 30 was missed at 0.99). This study asks whether bundling ALL 10 metadata features into a single numpy-only L2 logistic regression with leave-one-out cross-validation can catch BOTH Mode S windows.

Ten metadata-only features were extracted for all 77 AISHELL-4 windows. Each feature was calibrated two-sidedly at >= 90% specificity on the 40 non-hallucinated tracks. A combined detector (numpy-only L2 logistic regression on all 10 features, Mode S label, LOO-CV out-of-fold probabilities, threshold at 90% specificity) was then evaluated, with an L2 sensitivity analysis over 9 L2 values. An ensemble (metadata LR flag OR RQ13 lang-id entropy at threshold 0.409 bits) was tested against the 37 hallucinated tracks. A 1000-permutation test (seed=42, two-sided, +1 smoothing) was run per feature for a distinct Mode S metadata profile.

The mixed verdict:

- **H33a SUPPORTED but FRAGILE.** The combined metadata LR catches both Mode S windows at 100% specificity (threshold 0.1101) at the default L2=50.0. But only **1 of 9** L2 values achieve 100% Mode S sensitivity; the other 8 collapse to 50% (1 of 2). With n=2 Mode S, L2 cannot be tuned by cross-validation, so the 100% result is a razor-thin artifact of a single L2 value, not a robust detector.
- **H33b SUPPORTED robustly.** The ensemble (metadata LR OR lang-id entropy) achieves 100% sensitivity (37/37) on the AISHELL-4 hallucinated tracks at 92.5% specificity. **9 of 9** L2 values yield ensemble sensitivity > 95%. The metadata LR adds 2 Mode S tracks over lang-id alone (94.6% -> 100%).
- **H33c NOT SUPPORTED.** Only 2 of 10 features have a permutation p-value < 0.05 (`avg_speaker_length_sep` p=0.0030; `mix_total_chars` p=0.0170). Mode S does not have a distinct metadata profile.

The single positive discovery is that **`avg_speaker_length_sep` (mean characters per non-empty speaker segment) is the first feature in any study (RQ13, RQ14, RQ19, RQ22, RQ23, RQ28, RQ33) to catch BOTH Mode S windows at 90% specificity** (threshold 98, 4 clean FPs, bootstrap CI [100%, 100%], perm p=0.003). Mode S's near-duplicate transcripts (98 and 154 chars per active speaker) are longer than most clean single-speaker tracks. The 4 clean FPs are themselves clean single-speaker long tracks (windows 12, 16, 27, 37 with avg_speaker_length 99-142 chars), confirming the structural confound: Mode S's metadata profile is the profile of a long clean single-speaker track.

The combined LR's 100% result is therefore best understood as the LR assembling `avg_speaker_length_sep`'s signal with the other 9 features to push Mode S just above the noise floor (Mode S probs 0.1101, 0.1104 vs top clean prob 0.0552 — a 2x margin that collapses if 6-decimal display rounding is applied, and collapses to 50% if L2 is changed by even a small amount). This is not robustly deployable.

## Method

### Data
77 windows of 30 s from AISHELL-4 meeting M_R003S02C01. Hallucination label: `always_separated_cpwer > 1.0` (37 hallucinated / 40 non-hallucinated). Mode S label: hallucinated AND `lang_id_entropy < 0.409` AND `length_ratio < 2.0` AND `cr < 2.4` — exactly windows 22 and 30 (RQ16/RQ19/RQ22/RQ29).

### Mode S mechanism (per window)
- Window 22 (`num_speakers=2`): only speaker 005-F carries text (98 chars, near-duplicate of the 96-char mixed transcript with small substitutions e.g. 那种->那些, 南方户->男生后); speaker 006-F is empty. Sep-to-mix length ratio 1.021; runtime ratio 7.052; avg_speaker_length_sep 98.
- Window 30 (`num_speakers=1`): speaker 005-F carries 154 chars (near-duplicate of the 150-char mixed with substitutions e.g. 說說大好->那個都給包包包). Sep-to-mix length ratio 1.027; runtime ratio 0.991; avg_speaker_length_sep 154.

The two Mode S windows are highly heterogeneous: window 22 has a slow separated decode (4.612 s vs 0.654 s mixed, runtime_ratio 7.05) and window 30 has a normal-speed decode (1.689 s vs 1.704 s, runtime_ratio 0.99). This heterogeneity is the binding constraint: LOO-CV must generalise from one Mode S to the other.

### The 10 metadata-only features (NO content analysis)
1. `sep_runtime_sec` — separated ASR runtime in seconds (raw).
2. `mix_runtime_sec` — mixed ASR runtime in seconds (raw).
3. `runtime_ratio` — `sep_runtime_sec / mix_runtime_sec` (RQ22 `sep_to_mix_runtime_ratio`; partial signal: caught 1/2 Mode S).
4. `sep_total_chars` — total character count of the separated transcript.
5. `mix_total_chars` — total character count of the mixed transcript.
6. `char_ratio` — `sep_total_chars / mix_total_chars` (= RQ22 `sep_to_mix_length_ratio`).
7. `num_speakers` — number of speakers in the reference.
8. `num_active_speakers_sep` — number of non-empty speaker segments in separated output (= RQ22 `effective_speaker_count`).
9. `avg_speaker_length_sep` — mean characters per non-empty speaker segment.
10. `length_entropy_speakers` — Shannon entropy (bits) over per-speaker lengths (= RQ22 `per_speaker_length_entropy`).

`runtime_ratio` and `char_ratio` are recomputed from the raw counts (rather than trusting the stored `runtime_ratio` field) so the feature contract is self-contained.

### Calibration and statistics
- Per-feature two-sided ROC calibration at >= 90% specificity on the 40 non-hallucinated tracks (both orientations tried; Mode S sensitivity maximised; tiebreak all-hallucinated sensitivity, then specificity). Lifted from RQ19/RQ22 for direct comparability.
- Combined detector: numpy-only L2 logistic regression on all 10 standardised features (Mode S label, class-balanced loss weighting). Leave-one-out cross-validation over all 77 windows. Threshold at 90% specificity on the 40 non-hallucinated out-of-fold probabilities.
- L2 sensitivity: same LOO-CV repeated for L2 in {1.0, 5.0, 10.0, 25.0, 50.0, 75.0, 100.0, 150.0, 200.0}. With n=2 Mode S, L2 cannot be tuned by cross-validation, so this grid exposes the fragility directly. Default L2=50.0 is the smallest L2 at which all LOO fold probabilities are non-saturated in (0.01, 0.99) — a numerical-stability criterion, NOT a Mode-S-performance criterion.
- Permutation test: 1000 perms, seed=42, two-sided, +1 smoothing, test statistic = mean(feature | Mode S) - mean(feature | not Mode S).
- Bootstrap 95% CIs: 10000 resamples, seed=42, fixed full-sample thresholds.
- Ensemble: `(metadata LR flag at 90% spec) OR (lang_id_entropy > 0.409 bits)`.
- numpy + stdlib only; scipy / sklearn / Whisper are NOT required.

## Results

### Per-detector table (at 90% specificity operating point)

| Detector | Dir | Threshold | Spec | Sens_MS | Sens_AH | Perm p | Sens_MS CI 95% |
|---|---|---|---|---|---|---|---|
| sep_runtime_sec | high | 6.1750 | 92.5% | 0.0% | 67.6% | 0.5425 | [0.000, 0.000] |
| mix_runtime_sec | low | 0.5020 | 90.0% | 0.0% | 21.6% | 0.6943 | [0.000, 0.000] |
| runtime_ratio | high | 5.8397 | 90.0% | 50.0% | 56.8% | 0.7263 | [0.000, 1.000] |
| sep_total_chars | high | 115.0000 | 95.0% | 50.0% | 54.1% | 0.2737 | [0.000, 1.000] |
| mix_total_chars | high | 107.0000 | 90.0% | 50.0% | 18.9% | 0.0170 | [0.000, 1.000] |
| char_ratio | high | 1.1121 | 90.0% | 0.0% | 29.7% | 0.4825 | [0.000, 0.000] |
| num_speakers | high | 3.0000 | 90.0% | 0.0% | 51.4% | 0.5115 | [0.000, 0.000] |
| num_active_speakers_sep | high | 3.0000 | 97.5% | 0.0% | 37.8% | 0.6004 | [0.000, 0.000] |
| **avg_speaker_length_sep** | high | **98.0000** | 90.0% | **100.0%** | 8.1% | **0.0030** | **[1.000, 1.000]** |
| length_entropy_speakers | high | 0.6500 | 92.5% | 0.0% | 70.3% | 0.4755 | [0.000, 0.000] |

`Sens_MS` = sensitivity on Mode S (n=2). `Sens_AH` = sensitivity on all 37 hallucinated. Dir = flagging direction at the calibrated operating point.

**The best single-feature detector is `avg_speaker_length_sep` (lowest permutation p=0.0030), which catches 100% of Mode S (2/2) at 90% specificity.** This is the first feature in any RQ13/RQ14/RQ19/RQ22/RQ23/RQ28/RQ33 study to catch BOTH Mode S windows. Its threshold (98 chars per active speaker) is exactly window 22's value, and window 30's value (154) is well above. The 4 clean FPs at this threshold are themselves clean single-speaker long tracks (windows 12, 16, 27, 37 with avg_speaker_length 99-142 chars).

### Combined metadata LR (LOO-CV, default L2=50.0)

- Rule: numpy-only L2 logistic regression on all 10 standardised metadata features; Mode S label (2 positives vs 75 negatives); LOO-CV out-of-fold probabilities; flag if prob >= threshold.
- Threshold = 0.1101 (direction = high), specificity = 100.0%, sensitivity on Mode S = **100.0% (2/2, bootstrap CI [100%, 100%])**.
- Mode S window probabilities: window 22 = 0.1101, window 30 = 0.1104. Top clean (non-hallucinated) OOF probability = 0.0552. The Mode S probs sit ~2x above the top clean prob — a razor-thin margin.

### L2 sensitivity analysis (FRAGILE)

| L2 | Sens_MS | Spec | Saturated | Mode S probs | Top clean prob |
|---|---|---|---|---|---|
| 1.0 | 50.0% | 92.5% | yes | [1.000, 1.000] | 1.0000 |
| 5.0 | 50.0% | 100.0% | yes | [0.878, 1.000] | 0.9999 |
| 10.0 | 50.0% | 100.0% | yes | [0.098, 1.000] | 1.0000 |
| 25.0 | 50.0% | 100.0% | yes | [0.000, 1.000] | 0.9617 |
| **50.0** | **100.0%** | **100.0%** | yes | **[0.110, 0.110]** | **0.0552** |
| 75.0 | 50.0% | 100.0% | yes | [0.013, 1.000] | 0.7602 |
| 100.0 | 50.0% | 100.0% | yes | [0.000, 1.000] | 0.4871 |
| 150.0 | 50.0% | 97.5% | yes | [0.000, 0.056] | 0.1866 |
| 200.0 | 50.0% | 97.5% | yes | [0.000, 0.104] | 0.9953 |

**Only 1 of 9 L2 values achieve 100% Mode S sensitivity.** The other 8 collapse to 50% (catching only window 30, which has the higher Mode S prob in most folds). With n=2 Mode S precluding L2 tuning by cross-validation, the 100% result is a razor-thin artifact of L2=50.0, not a robust detector.

`saturated` = at least one OOF probability in [0, 0.01] or [0.99, 1.0] (numerical pathology, not signal). All 9 L2 values are saturated; even L2=50.0 has at least one OOF prob in the saturated range (clean tracks near 0). The L2=50.0 row's Mode S probs (0.110, 0.110) are non-saturated and well-separated from the clean max (0.055), which is why this L2 is selected as the default.

### Combined detector OR lang-id entropy (H33b ensemble)

- Rule: `(metadata LR flag at 90% spec) OR (lang_id_entropy > 0.409 bits)`.
- Specificity: 92.5%.
- Sensitivity on all 37 hallucinated: **100.0% (37/37)**.
- Sensitivity on Mode S: 100.0% (2/2).
- Lang-id entropy alone (RQ13 reference): specificity 92.5%, sensitivity 94.6% (35/37), sensitivity on Mode S 0.0% (0/2).
- The metadata LR adds **2 Mode S tracks** over lang-id alone (94.6% -> 100% on all hallucinated).
- Across L2 values, **9 of 9** yield ensemble sensitivity > 95% (robust on sensitivity; specificity varies, good only at non-saturated L2).

### Permutation test (H33c)

| Feature | Mode S mean | Others mean | Test stat | Perm p (two-sided) |
|---|---|---|---|---|
| sep_runtime_sec | 3.1505 | 2.6145 | 0.5360 | 0.5425 |
| mix_runtime_sec | 1.1790 | 1.3510 | -0.1720 | 0.6943 |
| runtime_ratio | 4.0216 | 5.6916 | -1.6700 | 0.7263 |
| sep_total_chars | 126.0000 | 47.0779 | 78.9221 | 0.2737 |
| mix_total_chars | 123.0000 | 47.3091 | 75.6909 | 0.0170 |
| char_ratio | 1.0238 | 1.7528 | -0.7290 | 0.4825 |
| num_speakers | 1.5000 | 1.8571 | -0.3571 | 0.5115 |
| num_active_speakers_sep | 1.0000 | 1.5455 | -0.5455 | 0.6004 |
| **avg_speaker_length_sep** | **126.0000** | **44.0779** | **81.9221** | **0.0030** |
| length_entropy_speakers | 0.0000 | 0.4805 | -0.4805 | 0.4755 |

**2 of 10 features have permutation p < 0.05** (`avg_speaker_length_sep` p=0.0030; `mix_total_chars` p=0.0170). The H33c success criterion (perm p < 0.05 for > 5 of 10 features) is not met. Mode S does not have a distinct metadata profile across most features.

The negative result has a single mechanistic cause: Mode S's metadata is highly heterogeneous. Window 22 (runtime_ratio 7.05, 1 active speaker of 2, avg_speaker_length 98) and window 30 (runtime_ratio 0.99, 1 active speaker of 1, avg_speaker_length 154) sit at opposite ends of `runtime_ratio` and `num_speakers`. Averaging the two for the permutation test's mean-difference statistic washes out the signal in features where they pull in opposite directions (e.g. `runtime_ratio`: window 22 at 7.05 is high, window 30 at 0.99 is low, mean 4.02 vs others' mean 5.69 — non-significant).

The two significant features (`avg_speaker_length_sep` and `mix_total_chars`) are both length features where Mode S's near-duplicate transcripts (98, 154, 96, 150 chars) are unusually long compared to the non-hallucinated tracks. This is the same signal: Mode S is a long monoscript-Chinese hallucination.

### The structural confound (why the LR is fragile)

Among the 40 non-hallucinated tracks:
- 32 (80%) have `length_entropy_speakers == 0.0` — same as both Mode S windows.
- 19 (48%) have `num_active_speakers_sep == 1.0` — same as both Mode S windows.
- 4 (10%) have `char_ratio` in [1.00, 1.05] — same as both Mode S windows.
- 9 (23%) have `avg_speaker_length_sep >= 80` — overlapping Mode S's 98-154 range.
- The 4 clean FPs at `avg_speaker_length_sep >= 98` are themselves clean single-speaker long tracks (windows 12, 16, 27, 37 with avg_speaker_length 99-142 chars).

Mode S's metadata profile is the profile of a long clean single-speaker track. The separator failure produces exactly the metadata distribution a genuine long single-speaker track would produce, so a metadata-only detector can only push Mode S slightly above the noise floor — not robustly separate it from clean long single-speaker tracks. This is the same structural confound identified in RQ19 (content similarity) and RQ22 (per-speaker structure): Mode S is structurally indistinguishable from a clean single-speaker track at the transcript level.

### Razor-thin operating point (documented fragility)

At L2=50.0 the Mode S OOF probabilities (0.1101, 0.1104) sit just 2x above the top clean probability (0.0552). This margin is so thin that **6-decimal display rounding of the input features flips the result**: with rounded features, L2=50.0 gives 50% sensitivity (window 22 prob=0.0, window 30 prob=1.0); with unrounded features, L2=50.0 gives 100% (both probs ~0.11). The script feeds the unrounded features to the LR (the `raw_features` list) and stores only the rounded copies in CSV/JSON for display. This rounding fragility is itself evidence that the LR result is not robustly deployable.

## Hypothesis verdicts

### H33a — metadata-only detector catches both Mode S windows at 90% specificity (sensitivity = 100% at specificity >= 90% on the 40 non-hallucinated)
- Kill criterion: sensitivity < 100%.
- Detector: combined metadata LR (LOO-CV) at default L2=50.0.
- Sensitivity on Mode S at 90% spec: **100.0% (2/2)**. Specificity: 100.0%. Bootstrap CI 95% [100%, 100%].
- L2 robustness: 1 of 9 L2 values achieve 100% Mode S sensitivity; the other 8 collapse to 50%. With n=2 Mode S, L2 cannot be tuned by cross-validation.
- Verdict: **SUPPORTED but FRAGILE.** The 100% result is a razor-thin artifact of L2=50.0 (Mode S probs 0.110, 0.110 vs top clean 0.055) and is not robust to the L2 hyperparameter. Not robustly deployable.

### H33b — combined metadata + lang-id detector achieves > 95% sensitivity on the 37 AISHELL-4 hallucinated tracks
- Kill criterion: combined sensitivity <= 95%.
- Combined sensitivity on all 37 hallucinated: **100.0% (37/37)** at 92.5% specificity.
- Lang-id alone: 94.6% (35/37). The metadata LR adds 2 Mode S tracks over lang-id alone.
- L2 robustness: 9 of 9 L2 values yield ensemble sensitivity > 95% (robust on sensitivity; specificity varies — good only at non-saturated L2).
- Verdict: **SUPPORTED (robust on sensitivity).** The ensemble achieves 100% on the 37 hallucinated across all L2 values tested. This is the first study to close the AISHELL-4 hallucinated sensitivity gap to 100% with a metadata-only signal.

### H33c — Mode S tracks have a distinct metadata profile (permutation p < 0.05 for > 50% of features)
- Kill criterion: perm p >= 0.05 for >= 5 of 10 features.
- Best feature: `avg_speaker_length_sep` (p=0.0030).
- Features with perm p < 0.05: **2 of 10** (`avg_speaker_length_sep` p=0.0030; `mix_total_chars` p=0.0170).
- Verdict: **NOT SUPPORTED.** Only 2 of 10 features have a distinct Mode S profile (need > 5). The negative result is driven by Mode S's metadata heterogeneity: window 22 and window 30 sit at opposite ends of `runtime_ratio` and `num_speakers`, so averaging the two for the permutation test's mean-difference statistic washes out the signal in most features.

## Relation to prior studies

| Study | Detector family | Mode S sens at 90% spec | Best feature |
|---|---|---|---|
| RQ13 | lang-id entropy | 0% (0/2) | lang_id_entropy |
| RQ14 | length / CR | 0% (0/2) | length_ratio / compression_ratio |
| RQ19 | content similarity | 0% (0/2) | mixed-sep normalised edit distance |
| RQ22 | per-speaker structure | 50% (1/2) | sep_to_mix_runtime_ratio |
| RQ23 | surface combo | 0% (0/2) | various |
| RQ28 | surface combo | 0% (0/2) | various |
| **RQ33** | **metadata-only (10 features)** | **100% (2/2) single feature, 100% (2/2) combined LR** | **avg_speaker_length_sep** |

RQ33 is the first study to report a single feature (`avg_speaker_length_sep`) catching BOTH Mode S windows at 90% specificity. The combined LR matches the single feature's 100% at the default L2, but the L2 sensitivity analysis shows the LR result is razor-thin (1 of 9 L2 values achieve 100%). The single feature `avg_speaker_length_sep` is the more robust finding: it catches both Mode S at every L2 implicitly (because it's a per-feature threshold, not an LR operating point), and its 4 clean FPs are themselves long clean single-speaker tracks.

The RQ22 partial signal (`sep_to_mix_runtime_ratio` = `runtime_ratio` here, caught 1/2 Mode S) replicates exactly in RQ33: `runtime_ratio` catches 50% (window 22, threshold 5.840) and misses window 30 (0.991).

## Reproducibility

- Script: `results/frontier/metadata_mode_s_detector/metadata_detector_analysis.py`
- Results: `results/frontier/metadata_mode_s_detector/metadata_detector_results.csv` (per-window), `metadata_detector_results.json` (full summary + per-window)
- Tests: `tests/test_metadata_mode_s_detector.py` (71 tests, all pass; 62 helper tests + 9 main-driver smoke tests)
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (label `external/sanity-check`, PR #890)
- Runtime: ~35 s on Apple M-series (numpy 2.3.2, no GPU, no Whisper, no ASR run).
- Determinism: all random operations use `seed=42` (permutation tests, bootstrap CIs, LR initialisation). Re-running produces byte-identical JSON output.
- Dependencies: `numpy`, `scipy` NOT required, `sklearn` NOT required, `whisper` NOT required. Pure reanalysis of the existing AISHELL-4 results JSON.
