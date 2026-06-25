# RQ28: Non-linear mode classifier — random forest to close the 13.5pp gap from RQ23

**Label:** experimental/frontier
**Closes:** #932
**Mode:** B (Focused Extension)

## Executive summary

A random forest (100 CART trees, max_depth=10, Gini impurity, bootstrap aggregation, numpy-only) was trained on the **exact same** 677-track × 5-feature matrix and 4-class mode labels as RQ23's linear classifier, using the same leave-one-out cross-validation protocol with sqrt inverse-frequency class weighting.

**The random forest improved overall LOO accuracy by 1.18pp (95.7% → 96.9%) but could NOT close the AISHELL-4 sensitivity gap (83.8% → 86.5%, still below the 90% target) and could NOT reduce the load-bearing Diverse ↔ Non-hallucinated confusion (17 errors in both classifiers, delta = 0).**

The confusion is **fundamental** (overlapping features in the 5-dimensional transcript-feature space), not an artifact of the linear classifier. A non-linear classifier gains nothing on the Diverse ↔ Non-hallucinated boundary that the linear classifier couldn't already achieve.

| Metric | RQ23 (linear) | RQ28 (random forest) | Delta |
|---|---|---|---|
| LOO accuracy | 95.72% (648/677) | 96.90% (656/677) | +1.18pp |
| Wilson 95% CI | [0.939, 0.970] | [0.953, 0.980] | overlap |
| AISHELL-4 sensitivity (task def) | 83.78% (31/37) | 86.49% (32/37) | +2.70pp |
| AISHELL-4 sensitivity (RQ23 orig) | 81.08% (30/37) | 86.49% (32/37) | +5.41pp |
| Total off-diagonal errors | 29 | 21 | -8 |
| Diverse ↔ Non-hallucinated errors | 17 | 17 | **0** |

## Hypothesis verdicts

| Hypothesis | Criterion | Result | Verdict |
|---|---|---|---|
| **H28a** | RF LOO accuracy > 95.7% | 96.90% | **SUPPORTED** (marginal; CI overlaps RQ23) |
| **H28b** | RF AISHELL-4 sensitivity > 90% | 86.49% | **NOT SUPPORTED** (KILLED) |
| **H28c** | Off-diagonal ≤ 14 (≥ 50% reduction from 29) | 21 | **NOT SUPPORTED** (KILLED) |

H28a is technically supported by the pre-registered criterion, but the 1.18pp improvement is within the Wilson CI overlap (RQ23 upper bound 0.970, RF lower bound 0.953) and thus not statistically significant. The more important finding is H28c's failure: the Diverse ↔ Non-hallucinated confusion is **identical** (17 errors in both classifiers), confirming the confusion is a feature-space limitation, not a model-capacity limitation.

## Method

### Data

Loaded directly from RQ23's `mode_classifier_results.csv` — no feature recomputation. The 677 tracks (600 gold + 77 AISHELL-4) have 5 transcript features:

- `cr` — compression ratio (Whisper-style, zlib)
- `lang_id_entropy` — Shannon entropy over Unicode script categories
- `length_ratio` — track length / separated total
- `content_similarity` — Jaccard overlap between separated texts
- `num_speakers` — speaker count

Mode labels (4 classes, deterministic functions of `cr`, `lang_id_entropy`, and hallucination status):

- **Mode_R** (n=5): hallucinated AND cr > 2.4
- **Mode_S** (n=2): hallucinated AND lang_id_entropy < 0.409 AND cr ≤ 2.4
- **Diverse** (n=35): hallucinated AND lang_id_entropy ≥ 0.409
- **Non-hallucinated** (n=635): not hallucinated

### Classifier

Random forest implemented in numpy (no sklearn):

- **CART decision tree**: recursive binary split on weighted Gini impurity. At each node, all candidate thresholds per feature are evaluated via vectorized cumulative class-weight sums (O(n × n_classes) per feature). Split chosen to maximize Gini gain. Stops at max_depth=10, min_samples_split=5, or purity.
- **Bootstrap aggregation**: 100 trees, each trained on a bootstrap sample of n=676 (LOO training fold size) drawn with replacement.
- **Class weighting**: sqrt inverse-frequency sample weights in the Gini computation, matching RQ23's linear classifier protocol. Weights computed per training fold (no leakage).
- **Prediction**: majority vote across 100 trees.
- **LOO-CV**: for each of 677 held-out samples, train RF on the other 676, predict the held-out.
- **Seed**: 42 (deterministic bootstrap).
- **Runtime**: 320 seconds (5.3 min) on Apple Silicon.

### Sensitivity definitions

Two definitions are reported:

1. **Task definition** (pre-registered for H28b): route to mixed if predicted_mode ∈ {Mode_R, Mode_S, Diverse}. Sensitivity = (truly hallucinated AND predicted hallucinated) / (truly hallucinated).
2. **RQ23 original**: mode_routed_detect — Mode R → CR ≥ 15.818, Diverse → lang_id ≥ 0.409, Mode S / Non-hallucinated → not flagged.

H28b uses the task definition. RQ23's original definition is reported for reference.

## Results

### Confusion matrices

**RQ23 (linear):**
```
                 Mode_R  Mode_S  Diverse  Non-halluc
Mode_R               5       0        0           0
Mode_S               0       0        0           2
Diverse              0       1       30           4
Non-halluc           0       9       13         613
```
Off-diagonal: 29 | Diverse↔Non-halluc: 17 (4+13)

**RQ28 (random forest):**
```
                 Mode_R  Mode_S  Diverse  Non-halluc
Mode_R               5       0        0           0
Mode_S               0       0        0           2
Diverse              0       0       32           3
Non-halluc           1       1       14         619
```
Off-diagonal: 21 | Diverse↔Non-halluc: 17 (3+14)

### Where the RF improved

The RF fixed 8 errors that RQ23's linear classifier made (648 → 656 correct):

- **Mode_S false positives reduced**: RQ23 predicted 9 Non-hallucinated tracks as Mode_S; RF predicted only 1. This is the main source of improvement — the RF's non-linear boundaries better separate the Mode_S region (low lang_id_entropy, moderate cr, high content_similarity) from the Non-hallucinated cluster.
- **Diverse recall improved**: 30/35 → 32/35 (2 fewer Diverse → Non-hallucinated errors).
- **1 new Non-hallucinated → Mode_R error**: the RF misclassified 1 Non-hallucinated track as Mode_R (RQ23 had 0 such errors).

### Where the RF did NOT improve

- **Diverse ↔ Non-hallucinated: unchanged at 17 errors.** The RF made 1 fewer Diverse → Non-hallucinated error (4 → 3) but 1 MORE Non-hallucinated → Diverse error (13 → 14). Net delta: **zero**. This is the load-bearing confusion, and the non-linear classifier gained nothing on it.
- **Mode_S recall: still 0/2.** Both Mode_S tracks (AISHELL-4 windows 22 and 30) are predicted as Non-hallucinated by both classifiers. With only 2 training examples per LOO fold, no classifier can learn this class reliably.
- **AISHELL-4 sensitivity: 86.5% < 90% target.** The RF improved from 83.8% to 86.5% (task definition) by recovering 1 additional hallucinated track, but 5 hallucinated AISHELL-4 tracks are still predicted as Non-hallucinated.

### Feature importances (Gini importance, full-data RF)

| Feature | Importance |
|---|---|
| cr | 0.424 |
| lang_id_entropy | 0.257 |
| length_ratio | 0.128 |
| num_speakers | 0.111 |
| content_similarity | 0.080 |

The feature ranking is consistent with RQ23's findings: `cr` and `lang_id_entropy` dominate (68% combined), which is expected since the mode labels are deterministic functions of these two features. The non-linear classifier uses the same signal as the linear one — there is no "hidden" non-linear interaction that the linear classifier missed.

## Why the confusion is fundamental

The Diverse and Non-hallucinated classes overlap in the 5-dimensional feature space:

- **Diverse** (hallucinated, lang_id_entropy ≥ 0.409): cr median 1.16, lang_id_entropy median 1.24, length_ratio median 0.0
- **Non-hallucinated**: cr median 0.73, lang_id_entropy median 0.0, length_ratio median 0.5

The overlap occurs at the boundary: some Non-hallucinated tracks have high lang_id_entropy (max 0.946, close to the 0.409 Diverse threshold) and some Diverse tracks have low cr (min 0.694, well within the Non-hallucinated range). A random forest can carve out non-linear regions, but if the features genuinely overlap, no partition can separate them.

The key evidence: the RF's Diverse ↔ Non-hallucinated confusion is **identical** to the linear classifier's (17 errors, delta = 0). If the confusion were an artifact of the linear decision boundary, a non-linear classifier would reduce it. It did not. The features themselves are insufficient to distinguish these two classes.

This is consistent with RQ23's documented circularity: the mode labels are derived from `cr` and `lang_id_entropy`, which are also classifier inputs. The Diverse / Non-hallucinated boundary is `lang_id_entropy ≥ 0.409 AND hallucinated`. The classifier sees `lang_id_entropy` but not `hallucinated` directly — it must infer hallucination from the 5 features. When a Non-hallucinated track happens to have high `lang_id_entropy`, no classifier can distinguish it from a Diverse track.

## Limitations

1. **Circularity (inherited from RQ23)**: mode labels are deterministic functions of `cr` and `lang_id_entropy`, which are also classifier inputs. This is a known limitation of RQ23's design, not introduced by RQ28.
2. **Class imbalance**: 635 Non-hallucinated vs 5 Mode_R vs 2 Mode_S vs 35 Diverse. The sqrt class weighting helps but cannot fully compensate for 2-sample Mode_S. With only 2 Mode_S tracks, LOO-CV trains on 1 example — no classifier can learn from this.
3. **No hyperparameter tuning**: n_trees=100, max_depth=10, min_samples_split=5 were chosen per the task spec. A grid search might find better hyperparameters, but given that the Diverse ↔ Non-hallucinated confusion is unchanged, tuning is unlikely to close the 90% sensitivity gap.
4. **Single RF configuration**: only `class_weight="sqrt"` was tested. A standard RF (no class weighting) would likely perform worse on minority classes. Other variants (stratified bootstrap, balanced RF) might help marginally but cannot resolve the fundamental feature overlap.
5. **AISHELL-4 aggregation**: features are computed on concatenated separated text (per RQ23 spec), which may dilute per-speaker signal. This is an RQ23 design choice, not an RQ28 choice.
6. **H28a significance**: the 1.18pp accuracy improvement is within the Wilson CI overlap and is not statistically significant. H28a is technically supported by the pre-registered criterion but should be interpreted as "no worse than linear," not "significantly better."

## Reproducibility

```bash
# Requires /opt/homebrew/bin/python3 with numpy 2.3.2 and scipy 1.18.0
cd /Users/a86198/Desktop/overlap-aware-speaker-asr
/opt/homebrew/bin/python3 results/frontier/nonlinear_mode_classifier/nonlinear_classifier_analysis.py
```

- **Seed**: 42 (deterministic bootstrap sampling)
- **Runtime**: ~5.3 minutes (Apple Silicon)
- **Inputs**: `results/frontier/per_track_mode_classifier/mode_classifier_results.csv` (RQ23's per-track data, unchanged)
- **Outputs**: `nonlinear_classifier_results.json`, `nonlinear_classifier_results.csv`, `nonlinear_classifier_per_track_predictions.csv`

## What this changes for the project

1. **The Diverse ↔ Non-hallucinated confusion is fundamental, not a model artifact.** RQ26 hypothesized the bottleneck was classifier accuracy. RQ28 confirms it is **feature-space overlap**, not model capacity. Switching from linear to non-linear gains 1.18pp accuracy (within noise) and 0 reduction in the load-bearing confusion.

2. **The path to > 90% AISHELL-4 sensitivity is NOT a better classifier on these features.** The 5 transcript features (cr, lang_id_entropy, length_ratio, content_similarity, num_speakers) are insufficient to separate Diverse from Non-hallucinated at the boundary. Future work should either:
   - Add new features (e.g., per-speaker cr, speaker embedding diversity, token-level repetition patterns) that can distinguish diverse-hallucination from legitimate multilingual content.
   - Accept the confusion and route Diverse/Non-hallucinated tracks to the same detector (accepting ~86% sensitivity as the feature-space ceiling).
   - Use a dataset prior (RQ21's approach achieved 94.6% but requires knowing the dataset a priori).

3. **RQ23's linear classifier is sufficient.** The linear classifier already captures all the discriminative signal available in these 5 features. There is no benefit to upgrading to a non-linear classifier for this task.

4. **Mode_S (n=2) is unlearnable.** With only 2 training examples, no classifier (linear or non-linear) can learn this class. Future work should either collect more Mode_S examples or merge Mode_S into another class.

## References

- RQ23: PR #924 — `results/frontier/per_track_mode_classifier/` (linear classifier, 95.7% LOO, 81.1% A4 sensitivity)
- RQ26: PR #930 — confirmed bottleneck is classifier accuracy, not routing
- RQ21: PR #917 — CR + lang-id detector comparison, threshold calibration, 94.6% dataset-aware sensitivity
