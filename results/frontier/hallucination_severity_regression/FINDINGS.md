# RQ29: Hallucination Severity Regression — Predict cpWER Contribution

> **Label: `experimental/frontier`** — a reanalysis-only regression that predicts
> per-window separated and mixed cpWER from reference-free transcript features
> (numpy-only random forest, LOO CV). Does NOT run Whisper or overwrite any
> verified reference / gold table. Closes #933.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, PR #890). Detector primitives
> (`compression_ratio`, `script_category`, `language_id_entropy`, `bigram_jaccard`)
> are lifted verbatim from RQ13/RQ16/RQ19 so the features are directly comparable.

## Executive Summary

All prior detector studies (RQ13, RQ16, RQ17, RQ19-RQ27) framed hallucination
detection as **binary classification** (hallucinated vs not). This has two
limitations the present module addresses: (i) it treats Mode S (cpWER ~2.0) and
Mode D (cpWER ~1.5) hallucinations as equivalent, and (ii) it optimises detection
accuracy rather than the downstream routing objective (cpWER). A **regression**
subsumes detection: predict the continuous cpWER of each route, then route to
mixed if predicted `separated_cpwer` > predicted `mixed_cpwer`.

We fit a numpy-only random-forest regressor (CART + bootstrap aggregation, 100
trees, max_depth=8, min_samples_split=5, seed=42) on 10 reference-free transcript
features (compression ratio, language-id entropy, length ratio, content
similarity, runtime ratio, etc.) computed from the stored per-speaker separated
transcripts and mixed transcript of the 77 AISHELL-4 windows. We evaluate with
**leave-one-out CV** (77 folds; per-fold RF fit on 76 samples).

**Headline numbers:**

| Metric | Value |
|--------|------:|
| LOO R² (separated_cpwer) | **0.5952** |
| LOO MAE (separated_cpwer) | 0.3191 |
| LOO Spearman ρ (separated_cpwer) | 0.8079 |
| LOO R² (mixed_cpwer) | −0.1322 |
| Regression-router cpWER | **1.0433** (95% CI [1.0087, 1.0887]) |

| Policy | cpWER | vs always-mixed | vs RQ16 corrected | vs oracle |
|--------|------:|----------------:|------------------:|----------:|
| always-mixed | 1.173 | — | — | — |
| always-separated | 1.591 | +0.418 | — | — |
| router v2 | 1.206 | +0.033 | — | — |
| **RQ16 corrected router** | **1.043** | −0.130 | — | +0.026 |
| **RQ29 regression router** | **1.043** | **−0.130** | **+0.0003** | **+0.026** |
| oracle best | 1.017 | −0.156 | −0.026 | — |

**Hypothesis verdicts:**

- **H29a (SUPPORTED)**: LOO R² = 0.5952 > 0.5. The regression predicts
  per-window separated_cpwer from transcript features with moderate skill.
- **H29b (NOT SUPPORTED)**: Top-3 highest-predicted-cpWER windows are [68, 63,
  42], not the Mode S windows [22, 30]. Mode S windows are predicted at ranks 63
  and 50 (out of 77). The hypothesis' premise is empirically wrong: Mode S
  windows have actual separated_cpwer = 2.0, which ranks 17 and 19 — far below
  the top of the distribution (windows 73=4.333, 26=3.5, 45=3.25, 11=3.0 all
  exceed them). Even a perfect predictor would not place Mode S in the top-3.
- **H29c (SUPPORTED)**: Regression-router cpWER = 1.0433 < 1.10, below
  always-mixed (1.173), below router v2 (1.206), and statistically tied with
  RQ16's corrected router (1.043, Δ = +0.0003, well inside the bootstrap CI).

**The headline finding is convergence, not improvement.** The regression router
achieves the same cpWER as RQ16's hand-built three-guard corrected router
(1.0433 vs 1.0430) via a continuous regression approach — confirming that the
corrected router's cpWER is not an artefact of its specific guard composition but
reflects the ceiling imposed by the available reference-free features. **The
regression inherits RQ16's Mode S blind spot exactly**: Mode S windows 22 and 30
are predicted at ~1.0 cpWER (vs actual 2.0) because their monoscript-Chinese
features look clean to every surface signal, so the regression routes them to
separated and loses 1.0 cpWER on each. Mode S accounts for **100% of the
regression router's gap to oracle** (0.026 / 0.026). The continuous regression
frame does not by itself expose what binary detection missed.

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min).
Each window already stores, per route, the cpWER that would result
(`always_mixed_cpwer`, `always_separated_cpwer`, `router_v2_cpwer`,
`oracle_best_cpwer`) plus the per-speaker separated transcripts and the mixed
transcript. No ASR is run; the regression router's per-window cpWER is the chosen
route's stored cpWER. Aggregate cpWER is the per-window mean (same metric as
RQ1/RQ16; matches the published always-mixed 1.173, always-separated 1.591,
router v2 1.206, corrected 1.043, oracle 1.017).

### Features (10, all reference-free)

The separated-text features are computed on the per-speaker separated transcripts
*concatenated* (no separator), as specified by RQ29. Mixed-text features use the
stored `mixed_text` directly.

| Feature | Description |
|---------|-------------|
| `cr` | Whisper-style compression ratio of concatenated separated text (len(utf8)/len(zlib)) |
| `lang_id_entropy` | Shannon entropy (bits) over Unicode script categories of concatenated separated text |
| `length_ratio` | separated_total_length / max(1, mixed_text_length) |
| `content_similarity` | character-bigram Jaccard(concatenated_separated, mixed_text) |
| `num_speakers` | stored num_speakers |
| `runtime_ratio` | stored separated_runtime_sec / mixed_runtime_sec |
| `separated_total_length` | stored |
| `mixed_text_length` | stored |
| `cr_mixed` | compression ratio of mixed_text |
| `lang_id_entropy_mixed` | Shannon entropy of mixed_text |

### Targets

- `separated_cpwer` = `cpwer_separated.error_rate`
- `mixed_cpwer` = `orcwer_mixed.error_rate`
- `cpwer_contribution` = `separated_cpwer − mixed_cpwer` (analysis-only)

### Model

Random-forest regressor implemented from scratch in numpy (no sklearn):

- **CART regression tree**: recursive binary split minimising weighted child SSE
  (equivalent to max variance reduction); candidate thresholds at midpoints
  between consecutive sorted unique values per feature; O(n log n) per feature
  via prefix-sum cumsum. `max_depth=8`, `min_samples_split=5`. Leaf value = mean
  of y in the leaf. Stops early on depth limit, too-few-samples, or pure node.
- **Bootstrap aggregation**: 100 trees per forest, each fit on a size-n bootstrap
  sample (with replacement). No random feature subsampling (`max_features = d`).
- **Prediction**: average across trees.
- **LOO CV**: for each of 77 held-out samples, fit a fresh RF on the other 76
  (seed = 42 + fold_index, so each fold is reproducible but distinct) and predict
  the held-out sample's `separated_cpwer` and `mixed_cpwer`. Total: 154 RF fits.

### Decision rule (regression router)

For each window, route to **MIXED** if `predicted_separated_cpwer` >
`predicted_mixed_cpwer`, else **SEPARATED**. Per-window cpWER = chosen route's
stored cpWER. This is the regression analogue of RQ16's "route to mixed if any
guard fires" — the regression replaces the discrete guard OR with a continuous
comparison of predicted cpWERs.

### Metrics

- LOO R² = 1 − SS_res/SS_tot for `separated_cpwer` (and secondarily for
  `mixed_cpwer`).
- LOO MAE = mean |actual − predicted|.
- Spearman ρ between predicted and actual `separated_cpwer` (rank correlation;
  numpy-only, ties averaged).
- Top-3 / top-5 / top-10 windows by predicted `separated_cpwer`; rank of Mode S
  windows 22 and 30 by predicted and by actual cpWER.
- Regression-router cpWER (per-window mean) with 10,000-resample bootstrap 95% CI
  (seed=42), plus paired CIs vs always-mixed, router v2, and oracle.

## Results

### LOO prediction quality (H29a)

| Target | R² | MAE | Spearman ρ |
|--------|---:|----:|-----------:|
| `separated_cpwer` | **0.5952** | 0.3191 | 0.8079 |
| `mixed_cpwer` | −0.1322 | 0.2590 | 0.4816 |

`separated_cpwer` is predicted with moderate skill (R² = 0.60, ρ = 0.81): the
regression explains ~60% of the leave-one-out variance and ranks windows
correctly ~80% of the time. `mixed_cpwer` is predicted poorly (R² < 0): the
mixed route has very low variance (most windows have orcwer_mixed = 1.0, the
insertion-free baseline), so the regression defaults to predicting the mean and
fails to distinguish the rare windows where mixed cpWER > 1.0. The router still
works because `mixed_cpwer` is rarely the deciding factor — the regression
router's decision is dominated by `predicted_separated_cpwer`.

### Top-3 predicted cpWER windows (H29b)

| Rank | window_id | predicted_sep | actual_sep |
|-----:|----------:|--------------:|-----------:|
| 1 | 68 | 2.506 | 3.000 |
| 2 | 63 | 2.399 | 3.000 |
| 3 | 42 | 2.273 | 3.000 |
| 4 | 65 | 2.247 | 2.667 |
| 5 | 73 | 2.219 | 4.333 |
| ... | ... | ... | ... |
| 50 | 30 | 1.057 | 2.000 |
| 63 | 22 | 1.000 | 2.000 |

Top-3 = [68, 63, 42]. Mode S windows 22 and 30 are predicted at ranks 63 and 50
(out of 77) — far outside the top-5 kill condition. Two compounding causes:

1. **Empirical premise failure**: Mode S windows have actual `separated_cpwer` =
   2.0, which ranks 17 and 19 (windows 73=4.333, 26=3.5, 45=3.25, 11=3.0, 23=3.0,
   42=3.0, 53=3.0, 63=3.0, 68=3.0, 76=3.0, 33=2.667, 65=2.667, 31=2.5, 0=2.333,
   5=2.0, 17=2.0, 22=2.0 all exceed or tie them). **Even a perfect predictor
   would not place Mode S in the top-3.** H29b's pre-registered premise that
   Mode S tracks are the highest-cpWER is not supported by the AISHELL-4 data.
2. **Surface-feature blind spot**: Mode S windows are by definition
   monoscript-Chinese hallucinations that escape every RQ16 surface detector
   (lang_id_entropy < 0.409, length_ratio < 2.0, cr < 2.4 — RQ19's Mode S
   definition). The regression uses the same surface features, so it predicts
   ~1.0 cpWER for Mode S (vs actual 2.0). The regression inherits RQ16's blind
   spot exactly.

### Regression router cpWER (H29c)

Regression-router cpWER = **1.0433** (95% CI [1.0087, 1.0887]). Below always-mixed
(1.173), below router v2 (1.206), and statistically tied with RQ16's corrected
router (1.043, Δ = +0.0003, well inside the bootstrap CI). Decision mix: 47
mixed, 30 separated (vs RQ16's 47 mixed, 30 separated — nearly identical).

**Mode S accounts for 100% of the regression router's gap to oracle.** Both Mode
S windows (22, 30) are routed to separated (predicted_sep ≈ 1.0 < predicted_mix ≈
1.0–1.34) but the oracle routes them to mixed (always_mixed=1.0 <
always_separated=2.0), costing 1.0 cpWER each. Summed over 77 windows, Mode S
adds 0.026 cpWER — exactly the gap to oracle (0.026). Every other window is
routed correctly (or ties). The regression router and RQ16's corrected router
fail on the same 2 windows for the same mechanistic reason: Mode S is invisible
to surface transcript features.

## Hypothesis Verdicts

| ID | Statement | Verdict | Key number |
|----|-----------|---------|-----------:|
| H29a | LOO R² > 0.5 for separated_cpwer prediction | **SUPPORTED** | R² = 0.5952 |
| H29b | Top-3 highest-predicted-cpWER windows include both Mode S tracks (22, 30) | **NOT SUPPORTED** | top-3 = [68, 63, 42]; Mode S ranks 63, 50 |
| H29c | Regression-router cpWER < 1.10 | **SUPPORTED** | cpWER = 1.0433 (95% CI [1.0087, 1.0887]) |

H29b is killed by both kill conditions: (i) the hypothesis is killed if either
Mode S track is outside the top-5 (both are outside — ranks 50 and 63); (ii) the
supporting condition (both in top-3) is also unmet. The kill is not a model
failure but a pre-registration error: the hypothesis' premise (Mode S = highest
cpWER) is empirically false on AISHELL-4.

## Limitations

1. **In-sample calibration, like RQ16.** The features, hyperparameters
   (max_depth=8, min_samples_split=5, n_trees=100), and the regression-router
   decision rule were all chosen with knowledge of the AISHELL-4 distribution.
   LOO CV gives an honest estimate of *prediction* quality on held-out windows of
   the same meeting, but does not test transfer to other meetings, languages, or
   ASR models. The regression-router cpWER 1.0433 is therefore an in-meeting
   ceiling, not a deployable estimate.
2. **No audio features.** The features are transcript-only because the AISHELL-4
   audio is not available in this repo. RQ8's silence-gap gate (the strongest
   single detector in the RQ16 ablation, redundant only because lang-id entropy
   subsumes it on AISHELL-4) is proxied by `length_ratio`. A real deployment
   would have acoustic silence-gap and SNR features that would likely expose
   Mode S.
3. **Mode S blind spot is structural.** The regression inherits RQ16's Mode S
   residual exactly (windows 22 and 30) because it uses the same surface
   features. The continuous-regression frame does not by itself expose what
   binary detection missed — both fail on monoscript-Chinese hallucinations
   whose transcript features look clean. Closing this gap requires either audio
   features (silence gaps), a second-hypothesis comparison (RQ19's
   content-similarity, which is non-deployable at 90% specificity), or a
   different ASR model whose failure modes don't include Mode S.
4. **`mixed_cpwer` prediction is poor** (R² = −0.13). The mixed route has very
   low variance on AISHELL-4 (most windows have orcwer_mixed = 1.0), so the
   regression defaults to the mean. The router still works because the decision
   is dominated by `predicted_separated_cpwer`, but a deployment where mixed
   cpWER varies more would need a better-mixed predictor.
5. **Aggregate metric is per-window mean**, matching RQ1/RQ16. An
   errors-over-length aggregate (sum of errors / sum of lengths) would give
   different absolute numbers (always-mixed 1.296, always-separated 1.880 on
   this file) but the same ranking and the same conclusion.
6. **Comparison to RQ16 is at the cpWER point estimate only.** RQ16's corrected
   router has its own bootstrap CI; we report the regression router's CI
   ([1.0087, 1.0887]) and the Δ = +0.0003 vs RQ16's 1.043 point estimate. A
   formal equivalence test would need both CIs, which is out of scope here.

## Reproducibility

- **Script**: `results/frontier/hallucination_severity_regression/severity_regression_analysis.py`
- **Run**: `/opt/homebrew/bin/python3 results/frontier/hallucination_severity_regression/severity_regression_analysis.py`
  (numpy 2.3.2; scipy not required; sklearn not required; no Whisper / no ASR).
- **Runtime**: ~30 s on Apple Silicon (77 LOO folds × 2 targets × 100 trees).
- **Seed**: 42 (RF bootstrap); 42 + fold_index (per-fold RF seed); 42 (bootstrap
  CI).
- **Inputs**: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (label `external/sanity-check`, PR #890).
- **Outputs**:
  - `severity_regression_results.csv` — per-window table (77 rows; actual and
    predicted cpWERs, decisions, all 10 features).
  - `severity_regression_results.json` — full results (metrics, hypotheses,
    comparison, per-window, references).
  - `FINDINGS.md` — this file.

## What this changes for the project

1. **The cpWER 1.043 ceiling on AISHELL-4 is robust to the modelling frame.**
   RQ16's hand-built three-guard corrected router and RQ29's continuous
   regression router converge to the same cpWER (1.0430 vs 1.0433, Δ = +0.0003).
   This confirms that the corrected router's cpWER is not an artefact of its
   specific guard composition — it reflects the ceiling imposed by the available
   reference-free transcript features. Future detector work should not expect to
   beat 1.043 with more clever combinations of the same surface features.
2. **The Mode S residual is the single remaining gap to oracle.** Both routers
   lose 0.026 cpWER on windows 22 and 30, accounting for 100% of the gap to
   oracle. Closing this gap requires either (a) audio features (silence gaps —
   RQ8's actual gate, not the text proxy), (b) a second ASR hypothesis (RQ19's
   content-similarity, non-deployable at 90% specificity), or (c) a different ASR
   model whose failure modes don't include monoscript-Chinese hallucination.
3. **Regression subsumes detection but does not by itself improve routing.** The
   regression predicts separated_cpwer with R² = 0.60 — moderate skill, enough
   for the router to match the corrected router — but the continuous frame does
   not expose Mode S, which is invisible to every surface feature. The
   regression's value is (i) a single continuous decision variable that
   subsumes the three discrete guards, and (ii) an honest R²/MAE/ρ evaluation
   that the binary-detection frame lacks. It is not a path to lower cpWER on
   AISHELL-4 without new feature sources.
4. **H29b's pre-registration was wrong.** Mode S windows are not the
   highest-cpWER tracks on AISHELL-4 (they tie at 2.0 with 5 other windows and
   are exceeded by 12 windows with cpWER ≥ 2.33). Future Mode S work should
   frame Mode S as "the residual that escapes surface detectors" (RQ19's
   definition) rather than "the most severe hallucinations" (the H29b premise).
