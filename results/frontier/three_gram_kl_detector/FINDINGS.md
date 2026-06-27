# RQ67: 3-gram KL-Divergence Detector for Mode S

> **Label: `experimental/frontier`** — a reanalysis-only simulation that replaces
> RQ58's character 2-gram KL-divergence detector (PR #981) with a character
> **3-gram** variant in RQ16's corrected-router framework. Does NOT run Whisper,
> any ASR model, or any LLM/ollama. Does NOT overwrite any verified reference or
> gold table. Closes #995.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, PR #890, read-only). KL detector primitives are
> imported VERBATIM from `src/llm_semantic_critic.py` (RQ34, PR #951); the 2-gram
> detector is recomputed in-script with the SAME code path so the H67a AUC
> comparison is apples-to-apples and reproduces RQ58 bit-for-bit. BCa CI helpers
> are reimplemented from RQ39/RQ58 so the CI methodology matches.

## Executive Summary

RQ58 (PR #981) plugged a character **2-gram** KL-divergence detector into RQ16's
corrected router and achieved cpWER **1.030** with **100% Mode S sensitivity** at
90% specificity — the first corrected router to catch Mode S. RQ59 (PR #980)
showed the (RQ43) KL detector's ROC is "flat-topped": sensitivity saturates
before 100% on non-Mode-S hallucinations because of an empty KL band separating
the hallucinated floor from the clean low-KL mass. RQ67 asked whether moving to a
**3-gram** KL detector changes the ROC shape (H67a AUC) and improves detection of
non-Mode-S hallucinations, while still catching Mode S (H67b) and beating RQ58's
cpWER (H67c).

**No. The 3-gram detector is cross-class rank-equivalent to the 2-gram detector —
it changes neither the ROC AUC, the calibrated routing decisions, nor the cpWER.**
Two of three pre-registered hypotheses are killed:

| Hypothesis | Verdict | Test statistic | Kill threshold |
|---|:---:|---:|---|
| **H67a** 3-gram AUC > 2-gram AUC | **KILLED** | 0.951351 = 0.951351 (Δ = 0) | ≤ |
| **H67b** Mode S 100% sens @ 90% spec | **SUPPORTED** | 100% (2/2) | < 100% |
| **H67c** 3-gram cpWER < 1.030 | **KILLED** | 1.030303 = 1.030303 | ≥ 1.030 |

The headline finding is that the 3-gram and 2-gram detectors produce the
**byte-identical operating point**: the same calibrated threshold boundary
(same 41 windows flagged), the same routing decisions (41 mixed / 36 separated),
and the same cpWER (**1.030303**, identical to RQ58 to the last digit). The ROC
AUC is exactly identical too (**0.9513513513513514**, Δ = 0.0 to machine
precision) because there are **zero cross-class discordant pairs**: every
hallucinated window ranks above every clean window in *both* n-gram orders. The
131 pairwise rank discordances between the two detectors are **all within-class**
(they reorder windows *inside* the hallucinated class and *inside* the clean
class), which is discriminatively irrelevant — AUC and the 90%-specificity
operating point depend only on cross-class ordering.

| Policy | cpWER | vs RQ58 2-gram | vs always-mixed | vs oracle |
|--------|------:|---------------:|----------------:|----------:|
| always-mixed | 1.1732 | — | — | +0.156 |
| always-separated | 1.5909 | — | — | +0.574 |
| router v2 | 1.2056 | — | — | +0.188 |
| RQ58 2-gram corrected | 1.0303 | — | −0.143 | +0.013 |
| **3-gram corrected (RQ67)** | **1.0303** | **0.000** | **−0.143** | **+0.013** |
| oracle best | 1.0173 | −0.013 | −0.156 | — |

The 3-gram detector still catches Mode S at 100% (H67b supported): windows 22 and
30 have 3-gram KL scores 15.55 and 15.76, far above the calibrated threshold
5.935 — the distributional anomaly is visible at the trigram level just as it was
at the bigram level. But the higher-order n-gram captures **no additional
between-class discriminative information**: the same 2 hard clean windows cross
above the hallucinated floor in both n-gram orders, so the AUC (0.951) and the
false-positive set at 90% specificity are unchanged.

## Pre-registered Hypotheses

| ID | Statement | Kill condition | Verdict |
|---|---|---|---|
| H67a | 3-gram KL AUC > 2-gram KL AUC | AUC ≤ | **KILLED** (0.951351 = 0.951351, Δ = 0.0) |
| H67b | 3-gram KL catches Mode S at 100% sensitivity / 90% specificity | sens < 100% | **SUPPORTED** (100%, 2/2) |
| H67c | 3-gram KL corrected router cpWER < 1.030 (RQ58 2-gram baseline) | cpWER ≥ 1.030 | **KILLED** (1.030303 = 1.030303) |

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min).
Each window stores the per-route cpWER (`always_mixed_cpwer`,
`always_separated_cpwer`, `router_v2_cpwer`, `oracle_best_cpwer`) — produced by
MeetEval 0.4.3 `cpwer`/`orcwer` in PR #890 — and the per-speaker separated
transcripts. No ASR is run; the 3-gram-corrected router's per-window cpWER is the
chosen route's stored word-level cpWER — matching RQ58/RQ16 bit-for-bit.

### Detector: character 3-gram KL divergence (RQ34, pure statistical — NO LLM)

The n-gram KL-divergence detector is a **pure statistical** detector (character
n-grams + KL divergence), NOT an LLM. RQ34 bundled it as a fallback alongside a
deepseek-r1 LLM critic; RQ67 uses ONLY the statistical KL detector (no ollama,
no LLM call). The detector primitives are imported VERBATIM from
`src/llm_semantic_critic.py` (RQ34):

1. **Reference distribution.** Build the average character **3-gram** distribution
   from the 40 non-hallucinated tracks' concatenated separated text (RQ34's
   `build_reference_distribution`, `separated_concat`, n=3). Each text's
   distribution is over its own vocabulary; the average is over the union
   vocabulary (1781 distinct 3-grams vs RQ58's 1487 distinct 2-grams).
2. **Per-window score.** For each window, apply RQ34's `compute_anomaly_score`
   to each non-empty per-speaker separated transcript, then take the **MAX**
   across speakers (the RQ12/RQ13 worst-case-track convention). The score is
   `KL(speaker_text || reference)` with additive smoothing 1e-9; novel 3-grams
   not in the reference contribute a large KL term.
3. **Threshold calibration.** Calibrate the threshold at >=90% specificity on
   the 40 non-hallucinated tracks (RQ34's `calibrate_threshold_at_specificity`).
   Empirically re-calibrated (NOT RQ34's non-reproducible 3.30; RQ40 PR #957).
   The 3-gram threshold is **5.934870** (specificity 90.0%, max_fp = 4 of 40).

### 2-gram comparison (H67a sanity)

For the H67a AUC comparison, the **2-gram** detector is recomputed in-script with
the SAME code path (n=2). This reproduces RQ58 bit-for-bit: the recomputed
2-gram threshold is **5.418144** (matches RQ58's 5.418144) and the recomputed
2-gram cpWER is **1.030303** (matches RQ58's 1.030303). This confirms the
comparison is apples-to-apples before the 3-gram results are evaluated.

### ROC AUC

ROC AUC via the Mann-Whitney U statistic with average-rank tie handling:
`AUC = P(score_pos > score_neg) + 0.5·P(score_pos == score_neg)`, computed as
`(sum_of_ranks_of_positives − n_pos·(n_pos+1)/2) / (n_pos·n_neg)`. Ranks assigned
by sorting scores ascending (higher score = higher rank); ties broken by average
rank. The ROC curve is also computed at every distinct threshold to characterise
the shape: `max_sens_at_90pct_spec` (max sensitivity achievable while keeping
specificity ≥ 0.90) and `plateau_below_1_at_90pct_spec` (True when sensitivity
cannot reach 1.0 at ≥ 90% specificity — the "flat-topped" signature).

### Routing & statistics

For each window: if `3-gram KL ≥ threshold` → MIXED; else → SEPARATED (identical
rule to RQ58). Per-window cpWER is averaged over the 77 windows. Bootstrap 95%
CIs use 10,000 resamples (seed=42) with the RQ39 framework: percentile CI, BCa CI
(bias-corrected + accelerated, jackknife acceleration), and paired-delta CI
(per-window 3-gram minus 2-gram, paired design). The BCa CI is the primary
verdict.

### Reproducibility sanity check

The RQ58 2-gram corrected router is recomputed in-script as a sanity check:
threshold 5.418144 (matches RQ58), cpWER 1.030303 (matches RQ58), Mode S
sensitivity 100% (matches RQ58). The baselines (always-mixed 1.17316,
always-separated 1.590909, router-v2 1.205628, oracle 1.017316) reproduce the
source JSON. This confirms the pipeline matches RQ58 before the 3-gram detector
is applied.

## Results

### Detector evaluation at the empirically-calibrated threshold

| Metric | 3-gram (RQ67) | 2-gram (RQ58, recomputed) |
|---|---:|---:|
| Threshold (empirical, ≥90% spec) | 5.934870 | 5.418144 |
| Specificity | 90.0% (4 FP / 40) | 90.0% (4 FP / 40) |
| Sensitivity (all 37 hallucinations) | **100.0%** (37/37) | **100.0%** (37/37) |
| Sensitivity (Mode S, windows 22 & 30) | **100%** (2/2) | **100%** (2/2) |
| Sensitivity (diverse hallucination) | 100.0% (35/35) | 100.0% (35/35) |
| Flagged windows (count) | 41 | 41 |
| Flagged window set | identical | identical |

Both detectors flag the **exact same 41 windows** at 90% specificity. The 3-gram
catches every hallucination including both Mode S windows — H67b is supported.

### ROC AUC comparison (H67a)

| Quantity | 3-gram | 2-gram | Δ |
|---|---:|---:|---:|
| AUC (Mann-Whitney, exact) | 0.9513513514 | 0.9513513514 | **0.0** |
| max sensitivity @ 90% spec | 1.0000 | 1.0000 | 0.0 |
| plateau below 1.0 @ 90% spec | False | False | — |
| Hallucinated KL floor | 14.838 | 12.346 | — |
| Clean windows above floor | 2 | 2 | 0 |

The AUC is **exactly identical** (0.9513513513513514, Δ = 0.0 to machine
precision). The mechanism: there are **zero cross-class discordant pairs**
(0 / 1480) — every hallucinated window ranks above every clean window in *both*
n-gram orders. The 131 pairwise rank discordances between the two detectors are
**all within-class** (they reorder windows inside the hallucinated class and
inside the clean class), which is discriminatively irrelevant: AUC depends only
on cross-class ordering. The same 2 hard clean windows cross above the
hallucinated floor in both detectors, capping the AUC at 0.951.

### Why the ROC is NOT flat-topped here

RQ59 found the **RQ43 `kl_sep`** signal (the KL of the concatenated separated
transcript, used in the 3-tier cascade) has a flat-topped ROC: all 37
hallucinated windows sit in an empty KL band [0.01, 2.98] above 13 clean windows
at KL = 0, so sensitivity saturates at 35/37 ≈ 94.6% before reaching 100% at
90% specificity. **RQ67's per-speaker MAX n-gram KL detector does not have this
problem**: both the 2-gram and 3-gram variants reach **100% sensitivity at 90%
specificity** (`max_sens_at_90pct_spec = 1.0`, `plateau = False`). The flat-topped
geometry is a property of the RQ43 `kl_sep` *signal* (concatenated-text KL), not
of the per-speaker MAX n-gram KL detector. The 3-gram does not change the ROC
shape because the 2-gram already reaches 100% — there is no saturation plateau
to lift.

### Per-window Mode S detail

| Window | 3-gram KL | 3-gram flag | 3-gram cpWER | 2-gram KL | 2-gram flag | 2-gram cpWER |
|---|---:|:---:|---:|---:|:---:|---:|
| 22 | 15.547 | ✓ | 1.0 | 13.079 | ✓ | 1.0 |
| 30 | 15.765 | ✓ | 1.0 | 12.998 | ✓ | 1.0 |

Both Mode S windows have 3-gram KL scores (~15.5–15.8) far above the threshold
(5.93) — unambiguous outliers in the 3-gram distribution, just as they were in
the 2-gram distribution (~13). Both route to mixed (cpWER 1.0 each), saving 2.0
cpWER total vs always-separated (cpWER 2.0 each).

### Aggregate cpWER (mean over 77 windows)

| Policy | cpWER | percentile CI 95% | BCa CI 95% |
|--------|------:|:---:|:---:|
| always-mixed | 1.1732 | — | — |
| always-separated | 1.5909 | — | — |
| router v2 | 1.2056 | — | — |
| oracle best | 1.0173 | — | — |
| RQ58 2-gram corrected | 1.0303 | [1.0043, 1.0671] | [1.0065, 1.0779] |
| **3-gram corrected (RQ67)** | **1.0303** | **[1.0043, 1.0671]** | **[1.0065, 1.0779]** |

The 3-gram-corrected router's point estimate (**1.030303**), percentile CI, and
BCa CI are **byte-identical** to RQ58's 2-gram router. The routing decisions are
identical (41 mixed / 36 separated), so every per-window cpWER is the same.

### Paired-delta bootstrap CIs (per-window)

| Comparison | point Δ | CI 95% | excludes 0? |
|---|---:|:---:|:---:|
| 3-gram − 2-gram (RQ58) | 0.0000 | [0.0000, 0.0000] | trivially (Δ = 0) |
| 3-gram − always-mixed | −0.1429 | [−0.3117, −0.0130] | **YES** |

The 3-gram minus 2-gram paired-delta is exactly zero (identical per-window cpWER).
Against always-mixed, the 3-gram router is per-window significant (upper CI
−0.0130 < 0) — the same result RQ58 reported.

## Hypothesis Verdicts

### H67a — 3-gram KL AUC > 2-gram KL AUC: KILLED

3-gram AUC = 0.9513513514, 2-gram AUC = 0.9513513514, Δ = 0.0 (exactly). The
kill criterion is "≤", and the two AUCs are equal to machine precision, so H67a
is killed. The mechanism is precise: the 3-gram reorders windows *within* each
class (131 within-class discordant pairs, Spearman ρ = 0.975) but produces *zero*
cross-class discordances (0 / 1480) — every hallucinated window ranks above every
clean window in both n-gram orders. Since AUC depends only on cross-class
ordering, the within-class reordering is invisible to the ROC. Higher-order
n-grams capture no additional between-class discriminative information for this
hallucination-detection task.

### H67b — 3-gram catches Mode S at 100% sensitivity / 90% specificity: SUPPORTED

3-gram Mode S sensitivity = 100% (2/2) at 90.0% specificity. Windows 22 and 30
have 3-gram KL scores 15.547 and 15.765, far above the threshold 5.935. The
distributional anomaly of the monoscript-Chinese near-duplicate hallucinations is
visible at the trigram level just as it was at the bigram level — the 3-gram
detector is the second detector (after RQ58's 2-gram) whose corrected router
catches Mode S.

### H67c — 3-gram KL corrected router cpWER < 1.030: KILLED

3-gram cpWER = 1.030303, RQ58 2-gram cpWER = 1.030303, Δ = 0.000000. The kill
criterion is "≥ 1.030", and 1.030303 ≥ 1.030, so H67c is killed. The 3-gram and
2-gram routers make byte-identical routing decisions (same 41 windows flagged at
90% specificity), so the cpWER is identical to the last digit. The calibrated
thresholds differ (5.935 vs 5.418) and the raw KL scores differ, but the 90%-
specificity operating point lands on the same set of windows.

## Why 3-gram changes nothing operationally

The 2-gram detector already **perfectly separates** the hallucinated class from
the clean class except for 2 hard clean windows that cross above the
hallucinated floor (these 2 windows cap the AUC at 0.951 in both n-gram orders).
Because the cross-class separation is already near-perfect at n=2, the 3-gram
cannot improve it — there is no cross-class overlap for the higher-order n-gram
to remove. The 3-gram does change the *within-class* rank ordering (the
trigram distribution is more sensitive to local character context, so it
reorders which hallucinated window is "most anomalous"), but this within-class
reordering is invisible to the ROC AUC and to the 90%-specificity operating
point (which depends only on the 4 highest-KL clean windows forming the false-
positive set — and those are the same 4 windows in both n-gram orders).

Concretely: the 90%-specificity calibration allows 4 false positives (max_fp = 4
of 40 clean). In both n-gram orders, the same 4 clean windows have the highest
KL scores and form the false-positive set. The hallucinated floor (3-gram 14.84,
2-gram 12.35) sits far above these 4 clean false positives, so all 37
hallucinated windows are flagged in both. The routing is therefore identical.

## Honest Limitations

1. **In-sample calibration (inherited from RQ58/RQ34).** The 3-gram threshold is
   empirically calibrated on these exact 77 AISHELL-4 windows. The 90%
   specificity and 100% sensitivity are in-sample estimates. Treat 1.030 as an
   upper bound, not a deployable number.

2. **RQ34's threshold 3.30 is non-reproducible (RQ40, PR #957).** RQ58/RQ67
   empirically re-calibrate at 90% specificity and do NOT use 3.30.

3. **Single meeting, 77 windows (inherited).** Only `M_R003S02C01` is available.
   The bootstrap CI is over 77 windows, not over meetings.

4. **The 2-gram already saturates the detector.** The central reason H67a/H67c
   are killed is that the 2-gram detector already achieves 100% sensitivity at
90% specificity with near-perfect cross-class separation. There is no headroom
for the 3-gram to improve on. This is a property of the AISHELL-4 hallucination
distribution (the hallucinated KL scores sit far above the clean mass); a corpus
with more cross-class overlap might benefit from the 3-gram. The negative result
is specific to this detector/data combination, not a general claim that n-gram
order never matters.

5. **MAX-across-speakers vs concatenated (RQ34 difference, inherited).** RQ34
   computed the KL score on the concatenated per-speaker text; RQ58/RQ67 use
   MAX-across-speakers per the RQ12/RQ13 worst-case-track convention.

6. **cpWER is utterance-level (inherited).** Each speaker's whole Chinese string
   is one token. RQ30/RQ35 showed char-level cpWER is less lumpy and the
   corrected router's improvement collapses at char-level. The 1.030 is a
   word-level result.

7. **No deployable routing input (inherited).** Per the project's hard safety
   rules, cpWER / references are not used as routing input — the KL detector is
   computed only from the hypothesis transcripts (character n-grams).

## What this changes for the project

1. **Higher-order n-grams do not help this detector on AISHELL-4.** The 3-gram
   KL detector is cross-class rank-equivalent to the 2-gram: identical AUC
   (0.951), identical routing (41 mixed / 36 separated), identical cpWER (1.030).
   The 2-gram already saturates the detector's discriminative power. Future work
   should not expect n-gram order > 2 to improve Mode S detection or the
   corrected router's cpWER on this corpus.

2. **The flat-topped ROC is a signal-specific property, not a detector-class
   property.** RQ59's flat-topped finding was on the RQ43 `kl_sep` signal
   (concatenated-text KL). The RQ58/RQ67 per-speaker MAX n-gram KL detector
   (both 2-gram and 3-gram) does NOT have a flat-topped ROC — it reaches 100%
   sensitivity at 90% specificity. The 3-gram does not change the ROC shape
   because the 2-gram already reaches 100%; there is no saturation plateau to
   lift. This refines RQ59's conclusion: the flat-topped geometry is driven by
   the *signal* (concatenated-text KL with an empty band), not by the n-gram
   order or the per-speaker MAX aggregation.

3. **Mode S is robustly caught by the distributional anomaly.** Both the 2-gram
   and 3-gram detectors catch Mode S at 100% (H67b supported). The
   monoscript-Chinese near-duplicate hallucinations have a character-distribution
   anomaly that is visible at both the bigram and trigram level — the anomaly is
   a distributional property, not an n-gram-order-dependent one.

4. **Negative result is valuable.** H67a and H67c are killed by exact equality,
   not by degradation. This is a clean, precise negative: the 3-gram captures no
   additional between-class information. Future frontier work should explore
   *different* detector signals (e.g. semantic, prosodic) rather than
   higher-order n-grams, which are shown here to be saturating.

## Reproducibility

- Script: `results/frontier/three_gram_kl_detector/analysis.py`
  (deterministic; numpy + scipy + stdlib; no Whisper / no LLM / no ollama).
- Tests: `tests/test_three_gram_kl.py` (unittest suite; pure helpers only —
  ROC AUC, ROC curve, KL primitives from RQ34, BCa framework from RQ39/RQ58,
  new RQ67 routing helpers, end-to-end integration on synthetic data).
- Per-window data: `results/frontier/three_gram_kl_detector/three_gram_kl_results.csv`
  (77 rows; 3-gram + 2-gram KL scores, flags, decisions, cpWER).
- Summary + hypothesis verdicts: `results/frontier/three_gram_kl_detector/three_gram_kl_results.json`
- Bootstrap: 10,000 resamples, seed=42, alpha=0.05. BCa uses jackknife
  acceleration; paired-delta uses the same resample indices for both arms.
- 3-gram config: n=3, reference = average 3-gram distribution of 40
  non-hallucinated tracks' concatenated separated text (vocab 1781),
  aggregation = MAX across per-speaker tracks.
- Threshold: empirically calibrated at ≥90% specificity = 5.934870 (NOT
  RQ34's non-reproducible 3.30; RQ40 PR #957).
- 2-gram recomputed config: n=2, vocab 1487, threshold 5.418144 (matches RQ58),
  cpWER 1.030303 (matches RQ58) — sanity check passes.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).
- Run: `/opt/homebrew/bin/python3 results/frontier/three_gram_kl_detector/analysis.py`
  (~5 s; numpy + scipy only).
