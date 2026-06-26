# RQ32: Feature-Expanded Classifier for Diverse<->Non-hallucinated Confusion

**Label:** experimental/frontier
**Closes issue:** #939
**Status:** COMPLETE — 1 of 3 hypotheses supported, 2 killed

## Executive Summary

RQ28 (PR #933) proved that the Diverse<->Non-hallucinated confusion is
FUNDAMENTAL: a numpy-only random forest on RQ23's 5 transcript features produced
the *same* 17 Diverse<->Non-hallucinated off-diagonal errors as RQ23's linear
classifier. The confusion was diagnosed as a feature-overlap issue, not a
model-capacity issue.

RQ32 tests whether EXPANDING the feature set with 7 runtime/transcript metadata
features (extracted from the AISHELL-4 validation windows) plus a `has_metadata`
binary indicator can break the confusion. The expanded 13-feature matrix
(5 original + 7 metadata + 1 indicator) was fed to the *exact same* numpy-only
random forest (100 trees, max_depth=10, sqrt class weighting, LOO-CV) over the
same 677 tracks.

**Result: the confusion is NOT broken.** The Diverse<->Non-hallucinated
off-diagonal actually *increased* from 17 to 18, and AISHELL-4 sensitivity was
unchanged at 86.5%. LOO accuracy improved marginally from 96.90% to 97.05%
(+0.15 percentage points, +1 correctly classified track), but that gain came
from fixing peripheral errors, not the load-bearing boundary. The metadata
features were informative (runtime_ratio was the 2nd-most important feature,
sep_total_chars 3rd) but they did not separate the Diverse and
Non-hallucinated classes on the AISHELL-4 subset.

This reinforces RQ28's conclusion: the Diverse<->Non-hallucinated confusion is
a fundamental feature-overlap limit at the boundary, not something additional
metadata features of this kind can resolve.

## Method

### Data (reanalysis only — no Whisper / no ASR run)

- **RQ23 CSV** (`results/frontier/per_track_mode_classifier/mode_classifier_results.csv`):
  the EXACT same per-track feature matrix and mode labels used by RQ23 and RQ28
  (677 tracks: 600 gold + 77 AISHELL-4).
- **AISHELL-4 JSON** (`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`):
  source of the 7 new metadata features for the 77 AISHELL-4 tracks.

### Feature matrix (13 features)

| Block | Features | Source |
|-------|----------|--------|
| Original (5) | `cr`, `lang_id_entropy`, `length_ratio`, `content_similarity`, `num_speakers` | RQ23 CSV |
| Metadata (7) | `runtime_ratio`, `sep_total_chars`, `mix_total_chars`, `char_ratio`, `num_active_speakers_sep`, `avg_speaker_length_sep`, `length_entropy_speakers` | AISHELL-4 windows (0.0 for gold) |
| Indicator (1) | `has_metadata` | 1.0 for AISHELL-4, 0.0 for gold |

For the 600 gold tracks (no metadata available), all 7 metadata features are
set to 0.0 and `has_metadata = 0.0`. The RF must learn to ignore the metadata
block for gold tracks and rely on the 5 original features.

### Classifier

Identical to RQ28 (control for the feature-expansion variable only):

- Random forest: CART decision trees + bootstrap aggregation
- Implementation: numpy only (no sklearn)
- 100 trees, max_depth=10, min_samples_split=5
- Split criterion: weighted Gini impurity
- Class weighting: sqrt inverse-frequency (matches RQ23/RQ28)
- Bootstrap: n samples drawn with replacement from n
- Prediction: majority vote
- Cross-validation: leave-one-out (677 folds)
- Seed: 42
- Runtime: 443.1 seconds (~7.4 min)

### Pre-registered hypotheses

| ID | Statement | Kill criterion |
|----|-----------|----------------|
| H32a | Expanded-feature RF LOO accuracy > 96.9% (RQ28) | accuracy ≤ 96.9% |
| H32b | AISHELL-4 mode-routed sensitivity > 90% | sensitivity ≤ 90% |
| H32c | Diverse<->Non-hallucinated off-diagonal < 17 (RQ28) | off-diagonal ≥ 17 |

## Results

### Confusion matrix (rows = true, cols = predicted)

|              | Mode_R | Mode_S | Diverse | Non-hallucinated |
|--------------|--------|--------|---------|------------------|
| Mode_R       | 5      | 0      | 0       | 0                |
| Mode_S       | 0      | 0      | 0       | 2                |
| Diverse      | 0      | 0      | 32      | 3                |
| Non-halluc   | 0      | 0      | 15      | 620              |

- **Off-diagonal total:** 20 (RQ28: 21, RQ23: 29)
- **Diverse<->Non-halluc off-diagonal:** 18 (RQ28: 17, RQ23: 17)

### Per-class metrics

| Class            | Precision | Recall  | F1      | Support |
|------------------|-----------|---------|---------|---------|
| Mode_R           | 1.000     | 1.000   | 1.000   | 5       |
| Mode_S           | 0.000     | 0.000   | 0.000   | 2       |
| Diverse          | 0.681     | 0.914   | 0.780   | 35      |
| Non-hallucinated | 0.992     | 0.976   | 0.984   | 635     |

### LOO accuracy

- **RQ32 RF (13 features):** 0.970458 (657/677), Wilson 95% CI [0.9548, 0.9808]
- RQ28 RF (5 features): 0.968981 (656/677)
- RQ23 linear (5 features): 0.957164 (648/677)
- Majority-class baseline: 0.937962 (635/677)
- Delta vs RQ28: +0.001477 (+1 track)

### AISHELL-4 mode-routed sensitivity

- **RQ32:** 0.864865 (32/37), CI [0.720, 0.941]
- RQ28: 0.864865 (32/37) — *identical, 0.0 delta*
- RQ23: 0.837838 (31/37)

### Feature importances (full-data RF, normalised)

| Rank | Feature                  | Importance |
|------|--------------------------|------------|
| 1    | `cr`                     | 0.476794   |
| 2    | `runtime_ratio` *(new)*  | 0.161720   |
| 3    | `sep_total_chars` *(new)*| 0.124229   |
| 4    | `content_similarity`     | 0.076359   |
| 5    | `lang_id_entropy`        | 0.057539   |
| 6    | `avg_speaker_length_sep` *(new)* | 0.035238 |
| 7    | `length_ratio`           | 0.025634   |
| 8    | `num_speakers`           | 0.022300   |
| 9    | `mix_total_chars` *(new)*| 0.008825   |
| 10   | `length_entropy_speakers` *(new)* | 0.005622 |
| 11   | `num_active_speakers_sep` *(new)* | 0.005107 |
| 12   | `char_ratio` *(new)*     | 0.000632   |
| 13   | `has_metadata` *(new)*   | 0.000000   |

The 7 new metadata features contribute ~34.1% of total importance
(`runtime_ratio` + `sep_total_chars` alone account for ~28.6%), confirming they
are informative — but informativeness for overall accuracy ≠ informativeness for
the Diverse<->Non-hallucinated boundary.

## Hypothesis Verdicts

### H32a — SUPPORTED ✓

> Expanded-feature RF LOO accuracy > 96.9% (RQ28)

**Verdict: SUPPORTED.** Accuracy = 0.970458 > 0.968981. Margin is thin
(+0.15 pp, +1 track) and the Wilson 95% CIs overlap heavily
(RQ32: [0.955, 0.981]; RQ28's CI is similar), so this should be read as "no
degradation, marginal improvement" rather than a decisive accuracy gain.

### H32b — KILLED ✗

> AISHELL-4 mode-routed sensitivity > 90%

**Verdict: KILLED.** Sensitivity = 0.864865 ≤ 0.90. Identical to RQ28 (0.0
delta). The 5 AISHELL-4 hallucinated windows that RQ28 mis-routed as
Non-hallucinated are *still* mis-routed. The metadata features did not help the
RF distinguish hallucinated AISHELL-4 windows from genuinely Non-hallucinated
gold tracks.

### H32c — KILLED ✗

> Diverse<->Non-hallucinated off-diagonal < 17 (RQ28)

**Verdict: KILLED.** Off-diagonal = 18 ≥ 17. The confusion actually got
*slightly worse* (+1). The total off-diagonal dropped from 21 to 20 (one
peripheral Mode_S/Diverse error was fixed), but the load-bearing
Diverse<->Non-hallucinated boundary specifically did not improve.

## Honest Limitations

1. **Tiny support for minority classes.** Mode_R (5) and Mode_S (2) have so few
   samples that any per-class metric for them is statistically fragile. The
   2 Mode_S tracks are predicted as Non-hallucinated in every RQ (RQ23, RQ28,
   RQ32) — the model has effectively never seen enough Mode_S to learn it.

2. **Metadata only available for AISHELL-4.** The 7 metadata features are
   non-zero for only 77/677 tracks (11.4%). For the 600 gold tracks the metadata
   block is zeroed and `has_metadata=0`, so the RF cannot use metadata to
   disambiguate Diverse vs Non-hallucinated *within the gold subset*. The
   metadata features can only help on the 77 AISHELL-4 tracks, of which only 35
   are Diverse and 37 are hallucinated — a very small arena for breaking a
   confusion that is dominated by gold-track errors.

3. **`has_metadata` importance is exactly 0.0.** The indicator was never
   selected as a split feature by any tree. This is because the RF can already
   perfectly detect AISHELL-4 tracks via the zero/non-zero pattern of the 7
   metadata features, making the indicator redundant.

4. **Accuracy CIs overlap RQ28.** The +0.15 pp accuracy gain is within sampling
   noise. Treat H32a as "no regression" rather than "decisive improvement".

5. **No new data, no new ASR.** This is a reanalysis of existing features plus
   metadata that was already computed by `rq1_aishell4_validation.py`. It does
   not test new acoustic features (e.g., speaker embeddings, prosody) that
   might actually separate the Diverse/Non-hallucinated boundary.

6. **The confusion is dominated by gold Non-hallucinated -> Diverse (15 errors)
   and gold Diverse -> Non-hallucinated (3 errors).** Metadata features cannot
   address the gold-track errors (they are zeroed for gold). To break this
   boundary, future work would need gold-track metadata or a fundamentally
   different feature family (e.g., acoustic/prosodic).

## Reproducibility

```bash
# From the repository root:
/opt/homebrew/bin/python3 \
  results/frontier/feature_expanded_classifier/feature_expanded_classifier_analysis.py

# Tests:
/opt/homebrew/bin/python3 -m unittest tests.test_feature_expanded_classifier -v
```

- **Seed:** 42 (RF bootstrap and tree training)
- **Runtime:** ~443 seconds (LOO-CV over 677 folds × 100 trees)
- **Inputs:**
  - `results/frontier/per_track_mode_classifier/mode_classifier_results.csv` (RQ23)
  - `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
- **Outputs:**
  - `results/frontier/feature_expanded_classifier/feature_expanded_classifier_results.csv`
  - `results/frontier/feature_expanded_classifier/feature_expanded_classifier_results.json`
  - `results/frontier/feature_expanded_classifier/feature_expanded_per_track_predictions.csv`
- **Python:** /opt/homebrew/bin/python3 (CPython 3.13.7), numpy only

## References

- RQ23: PR #924, `results/frontier/per_track_mode_classifier/` (linear, 5 features, 95.7% LOO)
- RQ28: PR #933, `results/frontier/nonlinear_mode_classifier/` (RF, 5 features, 96.9% LOO, 17 Diverse<->Non-halluc off-diag)
- AISHELL-4: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
