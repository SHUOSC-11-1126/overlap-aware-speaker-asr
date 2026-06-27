# RQ52: Chain-of-Thought LLM Critic for Mode S — Findings

**Label:** experimental/frontier + qualitative/demo (LLM outputs)
**Branch:** `research/rq52-llm-cot-critic`
**Source data:** `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (external/sanity-check, read-only — NOT modified)
**Mode S definition:** hallucinated (cpWER>1.0) AND `lang_id_entropy<0.409` AND `length_ratio<2.0` AND `cr<2.4` — the RQ16 corrected-router residual that escapes every surface detector.

---

## Executive Summary

A single `deepseek-r1:7b` call per window with a 5-step chain-of-thought (CoT) prompt — (1) language identification, (2) repetition check, (3) semantic coherence, (4) insertion artifacts, (5) verdict — was run on the max-lang-id-entropy separated speaker track of each of the 77 AISHELL-4 windows at temperature 0.0 (deterministic). The continuous hallucination score (verdict + confidence) was calibrated at 90% specificity on the 40 non-hallucinated tracks and compared against RQ34 (zero-shot direct verdict) and RQ41 (5-call ensemble).

**One of three hypotheses is SUPPORTED.** CoT prompting *did* reduce the false-positive rate from 52.5% (RQ34 zero-shot) to 35.0% — the structured reasoning makes the LLM more conservative about flagging clean transcripts. However, this conservatism comes at a cost: the CoT critic missed **both** Mode S windows (22 and 30) with *high confidence* (0.90 and 0.98 "clean"), whereas RQ34's zero-shot caught window 30. The AUC (0.5520) is near chance and slightly *worse* than RQ34's (0.5632).

The core finding: **chain-of-thought reasoning does not help for Mode S — it makes the Mode S problem worse.** Forcing the LLM to articulate *why* a transcript might be hallucinated causes it to reason itself *out of* flagging the fluent, monolingual, coherent Mode S tracks. The LLM's step-by-step analysis correctly identifies that Mode S text is monolingual Chinese, mostly coherent, and not obviously repetitive — then concludes "clean" with high confidence. This is the same fundamental ceiling identified in RQ36 (the LLM reads Mode S as reliable speech), now reinforced by explicit reasoning.

---

## Method

- **CoT prompt:** 5 explicit reasoning steps before a final `VERDICT: YES/NO` + `CONFIDENCE: x` verdict. The LLM must (1) identify languages, (2) check repetition, (3) check semantic coherence, (4) check insertion artifacts, (5) give a verdict. This differs from RQ34's zero-shot direct-JSON-verdict prompt and RQ41's multi-call majority vote.
- **Text input:** the max-lang-id-entropy separated speaker track (worst-case speaker). For Mode S windows this reduces to the single non-empty speaker, matching RQ34's concatenated-text convention for those specific windows.
- **Single call at T=0.0** (deterministic, unlike RQ41's temperature spread 0.0-0.8).
- **Reference-free:** the LLM sees ONLY the separated transcript (never the reference or mixed decode).
- **Short-circuit:** empty transcripts (13 silence windows, all non-hallucinated) are skipped (no LLM call).
- **Score:** `hallucination_score(verdict, confidence)` in [0, 1] — `confidence` if hallucinated, else `1 - confidence` (RQ34 convention for comparability).
- **Calibration:** one-sided (flag if `score >= threshold`) on the 40 non-hallucinated tracks at 90% specificity. Bootstrap 95% CIs from 10,000 resamples, seed=42, fixed full-sample threshold.
- **AUC:** rank-based Mann-Whitney U over all 77 windows.
- **RQ34 comparison:** RQ34's cached responses are loaded and metrics recomputed with the *same* functions (apples-to-apples). RQ34 used concatenated all-speaker text, so the comparison is approximate.
- **RQ41 comparison:** metrics taken from RQ41's published results JSON.

### LLM call coverage

64 non-empty windows × 1 call = 64 LLM calls (all fresh; no prior cache). The run was interrupted once and resumed from a 25-response partial cache, then completed with 45 additional calls (~1057 s total). The cache now holds 77 entries (64 LLM responses + 13 empty short-circuits).

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
| Total LLM calls | 64 (all fresh) |

### Raw verdict (no calibration — flag if LLM says YES)

| Detector | FP rate | FP / 40 | Sens. Mode S | Sens. all halluc. | AUC |
|---|---|---|---|---|---|
| **CoT (RQ52)** | **35.0%** | 14/40 | 0% (0/2) | 72.9% (27/37) | 0.5520 |
| RQ34 zero-shot | 52.5% | 21/40 | 50% (1/2) | 94.6% (35/37) | 0.5632 |
| RQ41 ensemble (≥3/5) | 62.5% | 25/40 | 50% (1/2) | 97.3% (36/37) | — |

CoT has the **lowest** false-positive rate of the three LLM approaches (35.0% vs 52.5% vs 62.5%), but also the **lowest** Mode S sensitivity (0% vs 50% vs 50%) and the **lowest** AUC (0.5520 vs 0.5632).

### At 90% specificity (calibrated)

| Detector | Threshold | Spec | Sens. Mode S | Sens. all halluc. | FP rate |
|---|---|---|---|---|---|
| **CoT (RQ52)** | 0.90 | 92.5% | 0% (0/2) | 24.3% (9/37) | 7.5% |
| RQ34 zero-shot | +inf | 100.0% | 0% (0/2) | 0.0% (0/37) | 0.0% |
| RQ41 ensemble | +inf | 100.0% | 0% (0/2) | 0.0% (0/37) | 0.0% |

CoT is the *only* LLM approach that achieves a non-trivial operating point at 90% specificity (threshold 0.90 catches 9 of 37 hallucinations at 92.5% specificity). RQ34 and RQ41 both collapse to flag-nothing at 90% specificity. However, none of the three catch any Mode S window at 90% specificity.

### Window-level detail for the 2 Mode S tracks

| Window | Mode S type | CoT verdict | CoT confidence | CoT score | RQ34 zero-shot | RQ41 ensemble |
|---|---|---|---|---|---|---|
| **22** | coherent (near-duplicate of mixed) | **NO** (clean) | 0.90 | 0.100 | not hallucinated | not hallucinated (2/5) |
| **30** | repetitive | **NO** (clean) | 0.98 | 0.020 | **hallucinated** | **hallucinated** (3/5) |

The CoT critic missed **both** Mode S windows with high confidence. Notably, it missed window 30 (the repetitive Mode S track) that both RQ34's zero-shot and RQ41's ensemble caught. The step-by-step reasoning led the LLM to conclude window 30's text is coherent monolingual Chinese with no strong repetition — and thus "clean" with 0.98 confidence.

---

## Hypothesis Verdicts

### H52a — CoT Mode S sensitivity > 50% at 90% specificity — **NOT SUPPORTED**

CoT Mode S sensitivity = **0%** (0/2) at 92.5% specificity. Both Mode S windows (22 and 30) were classified as "clean" with high confidence (0.90 and 0.98). This is *worse* than RQ34's zero-shot, which caught window 30 (50% raw Mode S sensitivity). The pre-registered kill condition (≤ 50% sensitivity) is met.

### H52b — CoT false-positive rate < 50% — **SUPPORTED**

CoT raw FP rate = **35.0%** (14/40), beating zero-shot's 52.5% and the ensemble's 62.5%. The structured 5-step reasoning makes the LLM more conservative: it requires explicit evidence of repetition, incoherence, or insertion artifacts before flagging, which reduces false alarms on clean transcripts. This is the one positive finding.

### H52c — CoT AUC > 0.60 — **NOT SUPPORTED**

CoT AUC = **0.5520**, below the 0.60 threshold and slightly *worse* than RQ34's AUC of 0.5632. The score distributions of hallucinated and non-hallucinated tracks overlap heavily; the CoT critic's (verdict, confidence) mapping does not separate the two classes better than chance. The pre-registered kill condition (AUC ≤ 0.60) is met.

---

## Honest Limitations

1. **Tiny Mode S sample (n=2).** With only 2 Mode S tracks, sensitivity is quantized to 0%/50%/100% and the bootstrap CI is uninformative. The 0% result is real but the positive space is underexplored.
2. **Text-input difference from RQ34/RQ41.** RQ52 uses the max-lang-id-entropy speaker track; RQ34/RQ41 used the concatenated all-speaker text. For Mode S windows this is equivalent (single non-empty speaker), but for the 40 non-hallucinated tracks the texts differ, so the FP-rate comparison is approximate. RQ34's metrics were recomputed from its cached responses with RQ52's functions to minimise methodological drift.
3. **Reference-free judging is intrinsically hard for Mode S.** Mode S tracks are by definition fluent, single-script, normal-length, normal-compression Chinese. A judge that never sees the reference has no anchor to call them hallucinated. CoT reasoning *amplifies* this problem: the LLM's step-by-step analysis correctly identifies that Mode S text lacks the surface artifacts (multilingual mixing, repetition, gibberish) it was asked to look for, then concludes "clean" with high confidence.
4. **CoT makes Mode S worse, not better.** The zero-shot RQ34 prompt catches window 30 because the LLM's fast gut reaction flags the slightly-off phrasing. CoT suppresses this instinct by forcing the LLM to justify a "hallucinated" verdict with specific artifacts — and when it can't find them (Mode S has none by definition), it reverts to "clean." This is a mechanism-level explanation for why CoT underperforms zero-shot on Mode S.
5. **Single prompt design.** Only one CoT prompt structure was tested (5 steps: language, repetition, coherence, insertion, verdict). A different step structure (e.g., "compare to typical meeting speech", "check for near-duplicate loops") might change the verdict, but is out of scope.
6. **T=0.0 only.** A single deterministic call was used (per the RQ52 spec). A CoT ensemble (multiple CoT calls at different temperatures) might reduce variance, but RQ41 showed temperature spreading hurts more than it helps on this corpus.
7. **LLM outputs are qualitative.** Per the project charter, LLM judgments are qualitative/demo-grade evidence; the numeric rates above are descriptive of this specific run, not a deployable metric.

---

## Reproducibility

```bash
# Requires local ollama with deepseek-r1:7b (ollama serve)
cd <repo root>
/opt/homebrew/bin/python3 results/frontier/llm_cot_critic/llm_cot_critic_analysis.py
```

- **Cache:** `results/frontier/llm_cot_critic/llm_cot_cache.json` (77 entries, keyed by `sha1(transcript)[:16]`). Re-running loads from cache and makes no new calls.
- **Outputs:** `llm_cot_critic_results.csv` (per-window) and `llm_cot_critic_results.json` (summary + per-window, including hypothesis verdicts, bootstrap CIs, RQ34/RQ41 comparison).
- **Seed:** bootstrap seed = 42 (10,000 resamples, fixed full-sample threshold).
- **Tests:** `tests/test_llm_cot_critic.py` (58 tests, all pass) covers the module primitives (CoT prompt construction, think-stripping, verdict parsing, hallucination-score mapping, ROC AUC, calibration, evaluation, FP rate, subgroup sensitivity, bootstrap CIs, cache load/save/keying, judge_window_cot with injected fake LLM).
- **Source data:** read-only `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (external/sanity-check) — NOT modified.
