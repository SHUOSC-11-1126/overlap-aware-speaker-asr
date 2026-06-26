# RQ47: Tied-cpWER Window Characterisation on AISHELL-4

> **Label: `experimental/frontier`** — a reanalysis-only characterisation of the
> "tied" cpWER windows on AISHELL-4. Reads the existing external-validation JSON
> (label `external/sanity-check`, PR #890) read-only. No Whisper / no ASR / no
> MeetEval / no scipy / no sklearn; Mann-Whitney U and the logistic regression
> are implemented from scratch (numpy + stdlib only). Closes the RQ47 issue.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (77 windows of 30 s from meeting `M_R003S02C01`).

## Executive Summary

RQ39 (PR #960) showed the corrected router's word-level BCa CI [1.0130, 1.0974]
*includes* the oracle (1.0173) — the corrected router reaches the oracle within
statistical noise (H39b NOT SUPPORTED). RQ47 asks what properties the **tied**
windows share — windows where `always_mixed_cpwer == always_separated_cpwer`
(within 1e-6), so the corrected router (constrained to {mixed, separated})
cannot improve over always-mixed no matter which route it picks — and whether
they form a separable class that could be excluded from routing decisions.

Under the stated operational definition, **35 of 77 windows are tied** (34 tie
at exactly cpWER 1.0; one ties at 1.333). The tied windows are a real, separable
class, but they are *not* a failure mode to exclude — they are exactly the
no-op windows the corrected router already correctly leaves alone.

**Headline results:**

| Hypothesis | Verdict | Statistic | Kill condition |
|---|:---:|---:|---|
| **H47a** tied windows have fewer active speakers | **SUPPORTED** | p = 6.0e-06, r = -0.578 | p ≥ 0.05 |
| **H47b** tied windows have lower overlap ratio | **NOT SUPPORTED (killed)** | p = 0.074, r = -0.229 | p ≥ 0.05 |
| **H47c** metadata-only LOO-CV AUC > 0.70 | **SUPPORTED** | AUC = 0.873 | AUC ≤ 0.70 |

The single strongest discriminator is **language-id entropy** (RQ13, max across
per-speaker separated tracks): tied windows have median entropy 0.000 bits vs
1.139 bits for non-tied (Mann-Whitney p = 1.5e-09, rank-biserial r = -0.773).
This is the same detector the corrected router already uses (RQ16, threshold
0.409 bits) — so the router is *implicitly* already flagging the actionable
(non-tied) windows and leaving the tied no-op windows alone.

## A note on the tie count (brief vs data)

The task brief's narrative mentions "5 tied windows", but the stated operational
definition — `abs(always_mixed_cpwer - always_separated_cpwer) < 1e-6` — yields
**35** tied windows on the 77-window AISHELL-4 file (34 of which tie at exactly
1.0). We checked every natural alternative definition; none yields 5:

| Definition | Count |
|---|---:|
| `always_mixed == always_separated` within 1e-6 (stated) | **35** |
| `always_mixed == always_separated == 1.0` | 34 |
| `router_v2 == mixed == separated` | 35 |
| `mixed == separated` AND `mixed != 1.0` | 1 |
| `mixed == separated` AND router chose separated | 12 |
| corrected router misses oracle (`router_v2 > oracle`) | 11 |
| corrected router hurts vs mixed (`router_v2 > mixed`) | 9 |

We implement the precise operational definition (35 tied windows). Asserting 5
would make the smoke test fail on the real data; with only 5 positives the
pre-registered Mann-Whitney tests and a logistic-regression AUC would also be
near-uninformative. The 35/42 split is the analytically meaningful one and
matches the pre-registered hypotheses. The discrepancy is surfaced here, in the
analysis-module docstring, and in the PR body.

## Method

### Tie definition

A window is **tied** iff `abs(always_mixed_cpwer - always_separated_cpwer) < 1e-6`.
On a tie the corrected router — which can only choose `mixed` or `separated` —
gets the same cpWER either way, so no routing decision can improve over
always-mixed on that window. This is the precise definition of "the corrected
router cannot improve over mixed" in the RQ39 narrative.

### Features (all metadata, no cpWER leakage)

For each window we extract:

| Feature | Definition | Source |
|---|---|---|
| `speaker_count` | `num_speakers` | diarisation |
| `active_speaker_count` | speakers with non-empty separated hypothesis | separator output |
| `active_speaker_count_ref` | speakers with non-empty reference (cross-check only) | reference |
| `overlap_ratio` | `overlap_ratio` | diarisation/alignment |
| `mixed_text_length` | `mixed_text_length` | mixed ASR |
| `separated_text_length` | `separated_total_length` | separated ASR |
| `total_separated_chars` | Σ `len(separated_text_per_speaker[s])` | separated ASR |
| `runtime_ratio` | `runtime_ratio` | both ASR passes |
| `avg_speaker_length_sep` | `separated_total_length / active_speaker_count` | separated ASR |
| `lang_id_entropy` | Shannon entropy over Unicode script categories, max across per-speaker separated tracks (RQ13 verbatim) | separated ASR |
| `compression_ratio` | `separated_total_length / max(1, mixed_text_length)` (RQ16 `length_ratio`) | both ASR passes |

All features are available *before* the cpWER that defines the label is
computed — there is no label leakage from the cpWER values themselves.

### Statistical tests

- **Mann-Whitney U** (two-sided) implemented from scratch in numpy: normal
  approximation with tie correction and continuity correction. Effect size is
  the rank-biserial correlation `r = 2U/(n1·n2) - 1` (positive when the tied
  group tends larger). Run for every feature.
- **Logistic regression** (L2-regularised, gradient descent, numpy only,
  seed=42, lr=0.1, 3000 iterations, L2=0.01) with **leave-one-out CV**. AUC is
  computed from the out-of-fold scores via the rank (Mann-Whitney) formula with
  mid-rank ties. Features are standardised inside each fold.

## Results

### Mann-Whitney U (tied vs non-tied), all features

| Feature | p (two-sided) | r (biserial) | tied median | non-tied median |
|---|---:|---:|---:|---:|
| `lang_id_entropy` | **1.5e-09** | **-0.773** | 0.000 | 1.139 |
| `active_speaker_count` | **6.0e-06** | -0.578 | 1 | 2 |
| `total_separated_chars` | 8.9e-05 | -0.520 | 57 | 104 |
| `separated_text_length` | 8.9e-05 | -0.520 | 57 | 104 |
| `compression_ratio` | 7.1e-05 | -0.528 | 0.985 | 2.835 |
| `runtime_ratio` | 7.0e-04 | -0.452 | 1.530 | 5.774 |
| `speaker_count` | 0.017 | -0.301 | 2 | 2 |
| `active_speaker_count_ref` | 0.017 | -0.301 | 2 | 2 |
| `avg_speaker_length_sep` | 0.054 | -0.256 | 35.0 | 50.5 |
| `overlap_ratio` | 0.074 | -0.229 | 0.021 | 0.068 |
| `mixed_text_length` | 0.868 | +0.022 | 58 | 42 |

Tied windows have **fewer active speakers, shorter separated transcripts, lower
runtime ratio, lower compression ratio, and dramatically lower language-id
entropy**. The mixed transcript length is essentially identical between groups
(p = 0.87) — the discriminator is what the *separator* does, not what the mixed
pass produces.

### Logistic regression (LOO-CV, metadata-only)

- **AUC = 0.8728** (H47c SUPPORTED, well above the 0.70 kill threshold).
- 9 features, 77 windows (35 tied / 42 non-tied), seed=42.

Standardised coefficients (last = bias):

| Feature | Coefficient (std) |
|---|---:|
| `speaker_count` | +1.023 |
| `active_speaker_count` | -0.890 |
| `overlap_ratio` | +0.092 |
| `mixed_text_length` | -0.499 |
| `separated_text_length` | +0.476 |
| `runtime_ratio` | -0.929 |
| `avg_speaker_length_sep` | -0.145 |
| `lang_id_entropy` | **-1.688** |
| `compression_ratio` | -0.589 |
| bias | -0.469 |

The dominant negative weight on `lang_id_entropy` (-1.688) confirms the
univariate finding: low language-id entropy is the single strongest predictor of
a tied window. Note the multivariate `speaker_count` coefficient is positive
while `active_speaker_count` is negative — the model captures the *interaction*
"more total speakers but fewer active speakers → tied" (i.e. inactive-speaker
windows), which the univariate tests cannot see. This is a real signal, not
instability: the two features are correlated and the model assigns the
discriminative load to the active/total contrast.

## Qualitative characterisation

The 35 tied windows fall into two clear groups:

1. **Silence windows (10).** Both the mixed and the separated ASR produced an
   empty transcript (`mixed_text_length == 0` AND `separated_total_length == 0`).
   With an empty hypothesis every reference word is a deletion, so both routes
   score cpWER = 1.0 — a trivial tie. All 10 silence windows are tied, and
   *zero* silence windows appear in the non-tied set. These are genuine
   low-activity / low-confidence-silence regions of the meeting where Whisper
   emitted nothing on both passes.

2. **Single-speaker / low-overlap no-op windows (25).** The remaining tied
   windows are dominated by single-speaker, no-overlap windows where the mixed
   and separated passes produce coincidentally equal cpWER — usually 1.0 (both
   routes hallucinate equally badly against a non-empty reference) or, for one
   window, 1.333. 12 of the 22 single-speaker windows in the corpus are tied.
   These are windows where separation *cannot* help because there is only one
   speaker to separate, and the two ASR passes happen to make the same errors.

| Property | tied | non-tied |
|---|---:|---:|
| silence (empty mixed & empty sep) | 10 | 0 |
| empty mixed transcript | 16 | 19 |
| single-speaker windows | 12 | 10 |

The tied windows are therefore **not silence-heavy in the mixed pass** (empty
mixed is 16 vs 19 — comparable) — the silence signal is specifically about the
*separated* pass being empty, which pulls `separated_text_length`,
`compression_ratio`, `runtime_ratio`, and `lang_id_entropy` down together. This
is why those four features move as a block in the Mann-Whitney table.

## What this changes for the project

1. **The tied windows are a separable class (H47c SUPPORTED, AUC 0.873), but
   they are not a class worth excluding.** They are exactly the no-op windows on
   which routing cannot help by construction (both routes give the same cpWER).
   The corrected router already handles them correctly: on a tied window the
   router's choice is irrelevant, so any decision is "right". The RQ39 finding
   that the corrected router reaches the oracle within statistical noise is
   *not* undermined by the ties — the ties are the windows where the oracle and
   the router trivially agree.

2. **The lang-id entropy detector already flags the actionable windows.** The
   strongest tied/non-tied discriminator is `lang_id_entropy` (p = 1.5e-09) —
   the same signal the corrected router uses (RQ16, threshold 0.409). Tied
   windows have near-zero entropy (clean / empty / monoscript output); non-tied
   windows have high entropy (multilingual hallucination, where separation
   actually helps or hurts). The router is therefore implicitly already
   concentrating its decisions on the non-tied windows. There is no separate
   "tie detector" to bolt on — the existing detector is the tie detector.

3. **H47b (overlap ratio) is killed.** Tied windows do *not* have significantly
   lower overlap ratio (p = 0.074, r = -0.229). The tie is driven by speaker
   activity and ASR output properties (active speakers, separated length,
   entropy, runtime), not by the diarisation overlap ratio. A routing policy
   that skipped low-overlap windows hoping to avoid ties would not work —
   overlap ratio is not a reliable tie predictor.

4. **Implication for the RQ39 "reaches oracle" verdict.** The 35 tied windows
   are windows where mixed, separated, the corrected router, and the oracle all
   agree (the oracle is `min(mixed, separated)`, which on a tie equals both).
   The corrected router's CI including the oracle is therefore partly structural
   (≈45% of windows are no-ops) and partly because the router makes the right
   call on the remaining action windows. Removing the tied windows from the
   evaluation would *tighten* the comparison but would not change the H39b
   verdict — it would just restate it on the 42 windows where routing matters.

## Honest Limitations

1. **Single meeting, 77 windows (inherited from RQ16/RQ39).** The 35/42 tied /
   non-tied split and the AUC characterise within-meeting structure only. The
   logistic-regression AUC is in-sample LOO over these 77 windows, not
   cross-meeting generalisation; the lang-id threshold (0.409) was calibrated on
   this same meeting (RQ13), so the "the existing detector is the tie detector"
   claim is conditional on that calibration.

2. **Normal-approximation Mann-Whitney.** With n1=35, n2=42 the normal
   approximation with tie correction is accurate, but for very small strata the
   exact distribution would be preferable. We did not implement the exact test
   (numpy-only constraint). The H47a / H47b verdicts are not close to the 0.05
   boundary except H47b (p = 0.074), where the verdict is "killed" regardless of
   the approximation.

3. **Logistic-regression AUC is optimistic on lumpy data.** The cpWER label is
   discrete and several features are zero-inflated (10 silence windows have
   `lang_id_entropy = 0`, `separated_text_length = 0`, etc.), which gives the
   classifier easy wins. The AUC 0.873 is a real upper bound on separability
   but should not be read as a deployable routing accuracy — it says "ties are
   detectable from metadata", not "this classifier should gate routing".

4. **Feature definitions are ASR-output-dependent.** `active_speaker_count`,
   `separated_text_length`, `lang_id_entropy`, and `compression_ratio` all
   depend on the separator + ASR output, not on audio metadata alone. They are
   legitimate pre-cpWER metadata (the cpWER is computed from these same texts,
   so they exist before the label is derivable), but a truly *audio-only* tie
   detector would need diarisation-only features; the lang-id entropy signal in
   particular requires running the separated ASR pass first.

5. **The "5 tied windows" in the brief is inconsistent with the data.** See the
   dedicated section above. We implemented the stated operational definition
   (35) and surfaced the discrepancy rather than fabricating a definition that
   yields 5.

## Reproducibility

- Script: `results/frontier/tied_cpwer_characterisation/tied_cpwer_analysis.py`
  (deterministic; numpy + stdlib only — no scipy, no sklearn, no MeetEval, no
  Whisper, no audio).
- Tests: `tests/test_tied_cpwer.py` (56 tests; pure-helper pins for
  `identify_tied_windows`, `extract_window_features`, `mann_whitney_u`,
  `logistic_regression_loo_auc` plus the lang-id / ranking / AUC helpers; two
  smoke tests load the real AISHELL-4 JSON to pin the verified tie count of 35).
- Per-window data: `results/frontier/tied_cpwer_characterisation/tied_cpwer_results.csv`
  (77 rows; per-window features + `tied` label).
- Summary + hypothesis verdicts: `results/frontier/tied_cpwer_characterisation/tied_cpwer_results.json`.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (read-only — not modified).
- Run: `/opt/homebrew/bin/python3 results/frontier/tied_cpwer_characterisation/tied_cpwer_analysis.py`
- Tests: `/opt/homebrew/bin/python3 -m unittest tests.test_tied_cpwer -v`
- Seed: 42 (logistic-regression weight init and LOO fits).
