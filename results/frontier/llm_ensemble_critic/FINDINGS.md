# RQ41: Multi-call LLM Ensemble Critic for Mode S — Findings

**Label:** experimental/frontier + qualitative/demo (LLM outputs)
**Reference issue:** #954
**Branch:** `research/rq41-llm-ensemble`
**Source data:** `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (external/sanity-check, read-only — NOT modified)
**Mode S definition:** hallucinated (cpWER>1.0) AND `lang_id_entropy<0.409` AND `length_ratio<2.0` AND `cr<2.4` — the RQ16 corrected-router residual that escapes every surface detector.

---

## Executive Summary

A self-consistency ensemble of N=5 `deepseek-r1:7b` calls (temperatures 0.0, 0.2, 0.4, 0.6, 0.8) with majority vote was run on the separated transcript of each of the 77 AISHELL-4 windows, calibrated at 90% specificity on the 40 non-hallucinated tracks, and compared against (a) the single temperature=0.0 call (a proxy for RQ34's single-call baseline) and (b) the n-gram KL divergence baseline.

**All three hypotheses are NOT SUPPORTED.** Temperature-spread self-consistency does not help for Mode S. The deepseek-r1:7b judge is over-eager on this corpus (it flags the large majority of non-empty separated transcripts as hallucinated), and spreading temperature noise makes it *more* over-eager, not less — the ensemble's raw-majority-vote false-positive rate (62.5%) is *higher* than the single-call's (50.0%), the opposite of the H41a prediction. At 90% specificity the score distributions of the 2 Mode S positives and the 40 non-hallucinated negatives overlap so heavily that every detector (ensemble, single-call, n-gram KL) collapses to flagging nothing. The ensemble and the single-call each catch exactly 1 of the 2 Mode S tracks but catch *different* ones (complementary, not redundant), so neither dominates.

This is a clean negative result: the LLM-as-critic signal is real but too coarse to separate coherent Mode S hallucinations from clean separated speech at usable specificity.

---

## Method

- **Ensemble:** 5 calls per window at temperatures `[0.0, 0.2, 0.4, 0.6, 0.8]`. Majority vote on the `hallucinated` boolean (flag if `yes_count >= 3`, i.e. `yes_vote_fraction >= 0.6`); ensemble score = yes-vote fraction; confidence = mean of per-call confidences.
- **Reference-free:** the LLM never sees the reference or the mixed decode — only the separated transcript.
- **Short-circuit:** empty separated transcripts (13 silence windows, all non-hallucinated) are skipped (no LLM call) to avoid ambiguous empty-text judgments.
- **Single-call baseline:** the temperature=0.0 call's verdict used as a 0/1 score (a proxy for RQ34's single `deepseek-r1:7b` call).
- **n-gram KL baseline:** `KL(sep_trigram || mix_trigram)`; calibrated two-sidedly (both orientations) at 90% specificity, matching RQ19.
- **Calibration:** one-sided (flag if `score >= threshold`) on the 40 non-hallucinated tracks at 90% specificity for the ensemble and single-call; two-sided for n-gram KL. Bootstrap 95% CIs from 10,000 resamples, seed=42, fixed full-sample threshold.
- **Cache:** keyed by `(sha1(transcript)[:16], temperature)`; resumable, saved every 5 calls. 320 total calls (290 cached from a prior run + 30 new calls for 6 windows not previously covered).

### LLM call coverage

The prior agent's cache held 290 entries (58 of the 64 non-empty windows × 5 temperatures). This re-run made 30 fresh calls for the 6 previously-uncached non-empty windows: **69, 70, 72, 73, 74, 76** (all hallucinated, non-Mode-S). Ollama was running with `deepseek-r1:7b` available, so these completed in ~296 s total. The cache now holds 320 entries covering every non-empty window. No Mode S window (22, 30) required a new call — both were already cached.

---

## Results

### Corpus

| Metric | Value |
|---|---|
| Windows | 77 |
| Hallucinated tracks (cpWER > 1.0) | 37 |
| Non-hallucinated tracks | 40 |
| Mode S tracks | 2 (windows **22**, **30**) |
| Empty separated transcripts (short-circuited) | 13 |
| Total LLM calls | 320 (290 cached + 30 new) |

### Raw majority vote (no calibration)

| Detector | FP rate | FP / 40 | Sensitivity Mode S | Sens. all halluc. |
|---|---|---|---|---|
| **Ensemble** (≥3/5 yes) | **62.5%** | 25/40 | 1/2 (50%) | 36/37 (97.3%) |
| Single-call (t=0.0) | 50.0% | 20/40 | 1/2 (50%) | 35/37 (94.6%) |

### At 90% specificity (calibrated)

| Detector | Threshold | Spec | Sens. Mode S | Sens. all halluc. |
|---|---|---|---|---|
| Ensemble | +inf | 100.0% | 0% (0/2) | 0.0% (0/37) |
| Single-call | +inf | 100.0% | 0% (0/2) | 0.0% (0/37) |
| n-gram KL | none | 100.0% | 0% (0/2) | 0.0% (0/37) |

All three detectors collapse to the trivial flag-nothing operating point at 90% specificity. The ceiling analysis confirms that for the ensemble, *no* threshold reaches even 50% Mode S sensitivity at any specificity floor ≥ 0.5 — Mode S scores are entirely interleaved with non-hallucinated scores.

### Window-level detail for the 2 Mode S tracks

| Window | Mode S type | Ensemble (yes/5) | Ensemble majority | Single-call t=0 | n-gram KL |
|---|---|---|---|---|---|
| **22** | coherent (near-duplicate of mixed) | 2/5 | not hallucinated | **hallucinated** | 6.757 |
| **30** | repetitive | 3/5 | **hallucinated** | not hallucinated | 6.568 |

The ensemble and single-call are **complementary on Mode S**: the single-call catches window 22 (the coherent track) but misses window 30 (the repetitive track); the ensemble does the reverse. Neither subsumes the other.

Window 22 per-call verdicts: `[True, False, True, False, False]` — the temperature=0.0 call says hallucinated, but the higher-temperature calls drift to "not hallucinated", flipping the majority. This is the mechanism by which the ensemble *loses* window 22.

---

## Hypothesis Verdicts

### H41a — Ensemble FP rate < 30% at raw majority vote — **NOT SUPPORTED**

Ensemble raw majority-vote FP rate = **62.5%** (25/40) vs single-call **50.0%** (20/40). The target (<30%) is missed by a wide margin, and the ensemble is *worse* than the single call. Adding temperature noise increases the judge's already-high over-eagerness rather than cancelling it out.

### H41b — Ensemble Mode S sensitivity > 50% at 90% specificity — **NOT SUPPORTED**

At ≥90% specificity the only feasible threshold is +inf (flag nothing), giving Mode S sensitivity = **0%** (0/2). Bootstrap 95% CI on Mode S sensitivity = [0.0, 0.0]. No threshold exists that simultaneously achieves 90% specificity and any non-zero Mode S sensitivity, because the 2 Mode S scores (0.4, 0.6) sit squarely inside the bulk of the 40 non-hallucinated scores.

### H41c — Ensemble catches window 22 (the coherent Mode S track) — **NOT SUPPORTED**

Window 22 ensemble majority = **not hallucinated** (2/5 yes votes; per-call `[T, F, T, F, F]`). The single-call temperature=0.0 *does* flag window 22 as hallucinated, so the ensemble strictly loses this catch. Temperature spread pushes the higher-temperature calls toward "not hallucinated" on fluent coherent text.

---

## Honest Limitations

1. **Tiny Mode S sample (n=2).** With only 2 Mode S tracks in the corpus, sensitivity is quantized to 0%/50%/100% and the bootstrap CI is uninformative. Any conclusion about Mode S specifically is necessarily tentative; the negative result is real but the *positive* space is also underexplored.
2. **Reference-free judging is intrinsically hard for Mode S.** Mode S tracks are by definition fluent, single-script, normal-length, normal-compression Chinese — they look like valid speech. A judge that never sees the reference has no anchor to call them hallucinated. This is a fundamental ceiling on this approach, not a tuning issue.
3. **Judge over-eagerness dominates.** `deepseek-r1:7b` flags ~75% of non-empty separated transcripts as hallucinated (48/64 at the single call), so the discriminative question is not "is it hallucinated" but "is it *this kind* of hallucinated", which the prompt does not encode.
4. **Single-call proxy for RQ34.** The temperature=0.0 call is used as a proxy for RQ34's single-call baseline; it is not a re-run of RQ34's exact prompt/model, so the comparison is approximate.
5. **No prompt tuning / few-shot.** The ensemble uses the same zero-shot prompt as the single call; a few-shot prompt with Mode S exemplars might change the verdict, but that is out of scope here.
6. **LLM outputs are qualitative.** Per the project charter, LLM judgments are qualitative/demo-grade evidence; the numeric rates above are descriptive of this specific run, not a deployable metric.
7. **6 windows were freshly called this run** (69, 70, 72, 73, 74, 76) because the prior cache only covered 58 of 64 non-empty windows. These are all non-Mode-S hallucinated tracks, so they do not affect the hypothesis verdicts, but they do mean the cache state differs from the prior agent's snapshot.

---

## Reproducibility

```bash
# Requires local ollama with deepseek-r1:7b (ollama serve, --parallel 4)
cd <repo root>
/opt/homebrew/bin/python3 results/frontier/llm_ensemble_critic/llm_ensemble_critic_analysis.py
```

- **Cache:** `results/frontier/llm_ensemble_critic/llm_ensemble_cache.json` (320 entries, keyed by `(sha1(transcript)[:16], temperature)`). Re-running loads from cache and makes no new calls for the 58 cached windows; the 6 windows above require a running ollama if not yet cached.
- **Outputs:** `llm_ensemble_results.csv` (per-window) and `llm_ensemble_results.json` (summary + per-window, including hypothesis verdicts, bootstrap CIs, and ceiling analysis).
- **Seed:** bootstrap seed = 42 (10,000 resamples, fixed full-sample threshold).
- **Tests:** `tests/test_llm_ensemble_critic.py` (45 tests, all pass) covers the module primitives (cache keying, calibration, bootstrap, ceiling analysis, ensemble aggregation, two-sided KL helpers).
- **Source data:** read-only `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (external/sanity-check) — NOT modified.
