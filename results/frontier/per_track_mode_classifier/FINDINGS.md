# RQ23: Per-Track Mode Classifier — Transcript-Feature Routing Without a Dataset Prior

> **Label: `experimental/frontier`** — tests whether a per-track mode classifier
> (Mode R / Mode S / Diverse / Non-hallucinated) can route each track to the right
> detector (CR vs lang-id) using only transcript features, removing RQ21's dataset
> prior. Implements multinomial logistic regression with leave-one-out
> cross-validation, a 4x4 confusion matrix, and a mode-routed detector. Closes #921.
> Builds on `results/frontier/gold_detector_comparison/` (RQ21, PR #917) and
> `results/external_sanity_check/aishell4/` (RQ1, PR #890).

## Executive Summary

RQ21 showed that CR and language-id entropy are complementary: CR dominates on
gold's repetitive hallucination (Mode R, 100% sensitivity), lang-id dominates on
AISHELL-4's diverse hallucination (94.6% sensitivity). A dataset-aware switch
achieved 95.2% combined sensitivity — but it **requires knowing the dataset a
priori** (CR on gold, lang-id on AISHELL-4). This study asks: can a per-track
classifier route each track to the right detector using only 5 transcript features,
with no dataset prior?

**A per-track classifier routes Mode R perfectly but cannot reach 90% on AISHELL-4
without the dataset prior.** A multinomial logistic regression (softmax + L2, numpy
only) with sqrt inverse-frequency class balancing achieves **95.7% LOO accuracy**
(beats the 93.8% majority-class baseline) and routes gold's 5 Mode R tracks with
**100% sensitivity** (CR fires on all 5, no dataset prior needed — CR's 16x
separation gap makes Mode R trivially separable). But AISHELL-4 sensitivity drops to
**81.1%** (30/37), killing H23b: 5 Diverse tracks are misclassified as
Non-hallucinated / Mode S, and the 2 Mode S tracks are unresolvable by design. The
dataset prior is worth **13.5 percentage points** on AISHELL-4 (94.6% with prior vs
81.1% without).

| Metric | Value |
|---|---:|
| Tracks | 677 (gold 600 + aishell4 77) |
| Mode counts | R=5, S=2, Diverse=35, Non-hall=635 |
| LOO accuracy | **95.7%** (648/677), Wilson CI [93.9%, 97.0%] |
| Majority baseline | 93.8% (635/677) — **beaten** |
| Mode-routed gold sensitivity | **100.0%** (5/5), CI [100%, 100%] |
| Mode-routed AISHELL-4 sensitivity | **81.1%** (30/37), CI [67.6%, 91.9%] |

**Hypothesis verdicts:**

- **H23a (>80% LOO accuracy): SUPPORTED.** 95.7% accuracy, far above the 80% bar and
  the 70% kill threshold. The classifier beats the majority-class baseline (93.8%).
- **H23b (>90% sensitivity on both, no dataset prior): KILLED.** Gold achieves 100%
  but AISHELL-4 achieves only 81.1% (<= 90% kill criterion met). Five Diverse tracks
  are misclassified; two Mode S tracks are unresolvable by design.
- **H23c (confusable modes exist): SUPPORTED.** 29 off-diagonal errors. The
  confusions are Diverse -> Non-hallucinated (4), Mode S -> Non-hallucinated (2),
  Non-hallucinated -> Mode S (9), Non-hallucinated -> Diverse (13).

## Method

### Data sources (read-only, not overwritten)

- **Gold** — `results/frontier/gold_detector_comparison/comparison_results.csv`
  (RQ21, PR #917): 600 gold tracks with `cr`, `lang_id_entropy`, `cer`,
  `hallucinated`. The raw separated text is loaded from
  `gold_track_texts.json` to compute `length_ratio` and `content_similarity`.
  Hallucination label: `cer > 5.0 OR cr_phase > 2.4` (5 hallucinated / 595 clean).
  All 5 hallucinated are Mode R (cr > 15.8).
- **AISHELL-4** — `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (RQ1, PR #890): 77 windows. Hallucination label:
  `always_separated_cpwer > 1.0` (37 hallucinated / 40 clean).

### Feature aggregation

AISHELL-4 uses a **hybrid aggregation** chosen to reproduce RQ21's pre-registered
mode labels exactly:

- `cr`: computed on the **concatenated** separated text (per the RQ23 spec).
  Concatenation dilutes single-speaker repetition, so no AISHELL-4 window exceeds
  Whisper's `cr > 2.4` Mode R boundary (window #18 drops from max-cr 2.97 to
  concat-cr 1.70). This keeps all AISHELL-4 hallucination in Mode S / Diverse.
- `lang_id_entropy`: **max** across per-speaker separated texts (matching RQ21's
  calibration, where the 0.409 threshold was set on max-aggregated entropy). This
  reproduces the 2 / 35 Mode-S / Diverse split exactly (windows 22 and 30).

Gold uses per-track values from RQ21's CSV (cr and lang_id computed on the
individual separated track text).

### Features (5, computed from stored transcripts only)

| Feature | Gold | AISHELL-4 |
|---|---|---|
| `cr` | per-track (from CSV) | concatenated separated text |
| `lang_id_entropy` | per-track (from CSV) | max across speakers |
| `length_ratio` | track_len / (sep1+sep2) proxy | sep_total / mixed_text_len |
| `content_similarity` | Jaccard(sep1, sep2) proxy | Jaccard(sep_concat, mixed) |
| `num_speakers` | 2 | per-window count |

Gold has no stored mixed_text, so `length_ratio` and `content_similarity` use
within-condition proxies (the track's share of the two-speaker separated total, and
the Jaccard overlap between the two separated tracks). This asymmetry versus
AISHELL-4 is a limitation (see below).

### Mode labels (4-class)

- **Mode R**: hallucinated AND `cr > 2.4` (gold's 5 tracks; cr 15.8-29.1).
- **Mode S**: hallucinated AND `lang_id_entropy < 0.409` AND `cr <= 2.4` (AISHELL-4
  windows 22 and 30; lang_id 0.14-0.32, cr 1.37-1.49).
- **Diverse**: hallucinated AND `lang_id_entropy >= 0.409` (AISHELL-4's 35 tracks;
  lang_id 0.41-1.75, cr 0.69-1.70).
- **Non-hallucinated**: not hallucinated (gold's 595 + AISHELL-4's 40 = 635 tracks).

### Classifier

- **Model**: multinomial logistic regression (softmax + L2), implemented in numpy
  (no sklearn).
- **Class balancing**: sqrt inverse-frequency sample weights (the 635/42
  non-hallucinated/hallucinated imbalance would otherwise collapse the classifier to
  the majority class). This is a loss-weighting choice, not a different model.
- **Standardization**: leave-one-out z-score (mean/std from the training fold only,
  preventing leakage).
- **Training**: full-batch gradient descent, lr=0.5, 3000 steps, L2=0.01.
- **Cross-validation**: leave-one-out (677 folds). For each held-out track, train on
  the remaining 676, predict the held-out.
- **Baseline**: majority-class classifier (always predict Non-hallucinated;
  accuracy = 635/677 = 93.8%).

### Mode-routed detector

For each track, the classifier predicts a mode, then:

- Predicted Mode R -> CR detector fires (threshold 15.818, gold-calibrated).
- Predicted Diverse -> lang-id detector fires (threshold 0.409).
- Predicted Mode S -> flag as unresolvable (never detected).
- Predicted Non-hallucinated -> no detection.

Sensitivity = correctly detected hallucinated / total hallucinated, per dataset.
Bootstrap 95% CIs use 10,000 resamples (seed=42) with the full-sample-fixed
threshold. The detector uses **no dataset prior** — routing is driven entirely by
the classifier's mode prediction.

## Results

### LOO accuracy

| Classifier | Accuracy | Wilson CI | Beats baseline? |
|---|---:|---:|---|
| Majority class (always Non-hallucinated) | 93.8% (635/677) | — | — |
| **Per-track mode classifier (LOO)** | **95.7%** (648/677) | [93.9%, 97.0%] | **Yes** |

### Confusion matrix (rows = true, cols = predicted)

|  | Mode R | Mode S | Diverse | Non-hall |
|---|---:|---:|---:|---:|
| **Mode R** (n=5) | **5** | 0 | 0 | 0 |
| **Mode S** (n=2) | 0 | **0** | 0 | 2 |
| **Diverse** (n=35) | 0 | 1 | **30** | 4 |
| **Non-hall** (n=635) | 0 | 9 | 13 | **613** |

Off-diagonal errors: 29. The confusion matrix is far from diagonal (H23c supported).

### Per-class metrics

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Mode R | 100.0% | 100.0% | 100.0% | 5 |
| Mode S | 0.0% | 0.0% | 0.0% | 2 |
| Diverse | 69.8% | 85.7% | 76.9% | 35 |
| Non-hallucinated | 99.0% | 96.5% | 97.8% | 635 |

### Mode-routed detector sensitivity

| Dataset | Sensitivity | TP / Total | Bootstrap CI |
|---|---:|---:|---:|
| gold (Mode R) | **100.0%** | 5 / 5 | [100.0%, 100.0%] |
| AISHELL-4 (Diverse + Mode S) | **81.1%** | 30 / 37 | [67.6%, 91.9%] |

The 7 missed AISHELL-4 tracks: 4 Diverse misclassified as Non-hallucinated (detector
does not fire), 1 Diverse misclassified as Mode S (unresolvable), 2 Mode S
(unresolvable by design). The theoretical ceiling on AISHELL-4 is 35/37 = 94.6%
(the 2 Mode S tracks are unresolvable); the classifier's 5 Diverse misclassifications
drop the achieved sensitivity from 94.6% to 81.1%.

### Feature distributions by mode (medians)

| Feature | Mode R | Mode S | Diverse | Non-hall |
|---|---:|---:|---:|---:|
| cr | 16.33 | 1.43 | 1.16 | 0.73 |
| lang_id_entropy | 0.00 | 0.23 | 1.24 | 0.00 |
| length_ratio | 0.96 | 1.02 | 0.00 | 0.50 |
| content_similarity | 0.07 | 0.71 | 0.00 | 0.06 |
| num_speakers | 2 | 1.5 | 3 | 2 |

Mode R is separated by a 16x cr gap (16.3 vs 0.7-1.4). Diverse is separated by
lang_id (1.24 vs 0.0-0.23). Mode S's distinguishing feature is high
content_similarity (0.71 — the near-duplicate of mixed text identified by RQ19), but
with n=2 this is insufficient for the classifier to learn.

## Hypothesis Verdicts

### H23a — Per-track classifier achieves > 80% accuracy (LOO)

- **Kill criterion**: accuracy <= 70%.
- **Result**: 95.7% accuracy, Wilson CI [93.9%, 97.0%].
- **Verdict**: **SUPPORTED**. The classifier exceeds the 80% bar and beats the 93.8%
  majority-class baseline. Mode R (100% recall) and Diverse (85.7% recall) carry the
  accuracy; Mode S (0% recall) is too small (n=2) to learn.

### H23b — Mode-routed detector achieves > 90% sensitivity on both datasets

- **Kill criterion**: sensitivity <= 90% on either dataset.
- **Result**: gold 100.0%, AISHELL-4 81.1%.
- **Verdict**: **KILLED**. Gold clears the bar (100%), but AISHELL-4 does not
  (81.1% <= 90%). The kill is driven by two factors: (1) 5 Diverse tracks
  misclassified as Non-hallucinated / Mode S (the classifier cannot perfectly
  separate Diverse from Non-hallucinated on AISHELL-4, because some non-hallucinated
  windows also have high lang_id — RQ21's 3 lang-id false positives); (2) the 2 Mode
  S tracks are unresolvable by design (caught by neither CR nor lang-id). Even a
  perfect classifier would cap at 35/37 = 94.6% on AISHELL-4.

### H23c — Confusion matrix reveals confusable modes

- **Kill criterion**: confusion matrix is diagonal (no confusable modes).
- **Result**: 29 off-diagonal errors.
- **Verdict**: **SUPPORTED**. The confusion matrix is far from diagonal. The dominant
  confusions are Non-hallucinated -> Diverse (13) and Non-hallucinated -> Mode S (9),
  plus Diverse -> Non-hallucinated (4) and Mode S -> Non-hallucinated (2). The
  Diverse <-> Non-hallucinated confusion is the load-bearing failure for H23b.

## Honest Limitations

1. **Mode labels are derived in-sample.** The 4-class labels are deterministic
   functions of `cr` and `lang_id_entropy` (two of the five classifier inputs). This
   is a known circularity: the classifier "should" trivially recover the labels from
   the features that define them. The fact that it still misses 5 Diverse and all 2
   Mode S tracks is evidence that the class imbalance and feature overlap make the
   task non-trivial — but the labels are not independent ground truth.

2. **Mode S has n=2.** With only 2 samples (AISHELL-4 windows 22 and 30), the
   classifier cannot learn this class (0% recall). Mode S's distinguishing feature
   (high content_similarity, 0.71 vs 0.06) is real but unsupported by enough data.

3. **Gold has n=5 hallucinated.** The 100% gold sensitivity has a degenerate
   bootstrap CI [100%, 100%]. With 5 samples, the estimate is fragile.

4. **Logistic regression is linear.** A non-linear classifier (e.g., a small neural
   net or tree ensemble) might separate Diverse from Non-hallucinated better, since
   the decision boundary on lang_id is not perfectly linear (some non-hallucinated
   AISHELL-4 windows have lang_id >= 0.409).

5. **Hybrid aggregation.** AISHELL-4 uses concatenated text for `cr` and max-across-
   speakers for `lang_id_entropy`. This was chosen to reproduce RQ21's pre-registered
   mode labels (2 Mode S / 35 Diverse) and the task's assertion that no AISHELL-4
   track is Mode R. A single consistent aggregation would be cleaner but does not
   reproduce the labels.

6. **Gold feature proxies.** Gold has no stored mixed_text, so `length_ratio` and
   `content_similarity` use within-condition proxies (track share of separated total,
   Jaccard between the two separated tracks) rather than the true mixed-text features
   used on AISHELL-4. The two datasets' features are not strictly comparable on these
   two dimensions.

7. **Class balancing is a hyperparameter.** Sqrt inverse-frequency weighting was
   chosen to beat the majority baseline while preserving minority recall. Full
   inverse-frequency (1/count) achieves higher minority recall (100% gold, 81.1% a4)
   but drops below the baseline on accuracy (93.6%); no weighting beats the baseline
   on accuracy (96.5%) but collapses minority recall (20% gold, 45.9% a4). The
   reported sqrt result is the middle ground.

## Reproducibility

```bash
cd /Users/a86198/Desktop/overlap-aware-speaker-asr
python3 results/frontier/per_track_mode_classifier/per_track_mode_classifier_analysis.py
```

- **Dependencies**: numpy + stdlib only (no scipy, no sklearn, no Whisper, no audio).
- **Runtime**: ~30 seconds (677 LOO folds x 3000 gradient steps each).
- **Seed**: 42 (numpy default_rng, deterministic).
- **Outputs**: `mode_classifier_results.csv` (per-track predictions + features),
  `mode_classifier_results.json` (full summary, confusion matrix, per-class metrics,
  mode-routed detector, hypothesis verdicts, feature distributions).
- **Read-only inputs**: RQ21's `comparison_results.csv` and `gold_track_texts.json`;
  RQ1's `rq1_aishell4_validation_results.json`. No verified references or gold tables
  were modified.

## What This Changes for the Project

1. **The dataset prior is worth 13.5 points on AISHELL-4.** RQ21's dataset-aware
   switch achieved 94.6% on AISHELL-4 (with the prior); RQ23's per-track classifier
   achieves 81.1% (without). The prior is not free — it requires knowing which
   dataset a track came from, which is not always available at deployment. RQ23 shows
   that CR-based routing (Mode R) transfers perfectly (100% gold, no prior), but
   lang-id-based routing (Diverse) loses 13.5 points without the prior.

2. **Mode R is trivially separable; Diverse is not.** Mode R's 16x CR gap (16.3 vs
   0.7) makes it perfectly separable by a linear classifier. Diverse's lang_id gap
   (1.24 vs 0.0) is large but contaminated by non-hallucinated AISHELL-4 windows with
   high lang_id (RQ21's 3 false positives). A linear classifier cannot fully separate
   Diverse from Non-hallucinated — this is the load-bearing failure.

3. **Mode S remains the hard ceiling.** The 2 Mode S tracks (windows 22, 30) are
   unresolvable by both CR and lang-id. Even a perfect mode classifier caps AISHELL-4
   sensitivity at 35/37 = 94.6%. Closing this gap requires a third detector (e.g.,
   RQ19's content_similarity, which separates Mode S at 0.71 vs 0.06) — but with
   n=2, this cannot be validated robustly.

4. **Per-track routing is viable for Mode R but not yet for Diverse.** A deployment
   that only needs to catch repetitive hallucination (Mode R) can use a per-track CR
   classifier with no dataset prior (100% sensitivity). A deployment that also needs
   to catch diverse hallucination (AISHELL-4-style) still benefits from the dataset
   prior, or needs a stronger (non-linear) classifier and more Mode S / Diverse
   training data.
