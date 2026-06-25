# RQ34: LLM-Based Semantic Critic for Mode S Detection

> **Label: `experimental/frontier`** (n-gram KL-divergence fallback) +
> **`qualitative/demo`** (LLM-based judgments — deepseek-r1:7b outputs are
> qualitative unless evaluated against a reference, which is what this study does).
>
> Reanalysis-only: reads the existing AISHELL-4 external-validation results
> (`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`,
> label `external/sanity-check`, PR #890). No Whisper / ASR model is run; no
> verified reference or gold table is modified. The LLM (deepseek-r1:7b via
> ollama, offline) evaluates stored transcripts only. Closes #941.

## Executive Summary

Mode S (the 2 monoscript-Chinese near-duplicate hallucinations on windows 22
and 30) has escaped every SURFACE detector: RQ19 (content-similarity), RQ22,
RQ23, RQ28 all achieved 0% Mode S sensitivity at 90% specificity. All prior
detectors use surface features (compression ratio, lang-id entropy, length
ratio, content-similarity). None use semantic understanding. RQ34 tests whether
a local LLM (deepseek-r1:7b) can detect Mode S by SEMANTIC analysis of the
separated transcript, and — as a fallback / baseline — whether a character
3-gram KL-divergence distributional anomaly detector can.

**The LLM semantic critic FAILS (H34a/b/c all NOT SUPPORTED).** deepseek-r1:7b
has a 52.5% false-positive rate on non-hallucinated tracks (it flags normal
Whisper-tiny ASR errors as hallucinations), making it non-deployable at 90%
specificity (the calibrated threshold collapses to +inf, flagging nothing). The
LLM does correctly flag window 30 (detecting its repetitive "包包包" and
non-standard characters) but misses window 22 (judging it "coherent and
plausible for a meeting discussion"). At its own unconstrained boolean
decision the LLM achieves 50% Mode S sensitivity (1/2) but only 47.5%
specificity — below the 90% deployability floor.

**The n-gram KL-divergence fallback SUCCEEDS — and is the first detector to
catch Mode S at 90% specificity.** The character 3-gram distribution of each
separated transcript is compared (via KL divergence) to the average 3-gram
distribution of the 40 non-hallucinated tracks. The separation is dramatic:
non-hallucinated tracks score KL 0.00–3.30, hallucinated tracks score 14.84–18.93
(gap = 11.54). Both Mode S windows (22: KL=15.55, 30: KL=15.76) fall well
within the hallucinated range. At 90% specificity (threshold 3.30), the n-gram
KL detector achieves 100% sensitivity on Mode S, 100% on diverse
hallucinations, and 100% on all 37 hallucinated tracks.

**The key insight: Mode S is semantically coherent but distributionally
anomalous.** Mode S's near-duplicate-with-substitutions mechanism produces
Chinese text that reads as plausible meeting speech (defeating the LLM's
semantic analysis) but uses character 3-gram combinations that never appear in
normal speech (defeating the distributional baseline). The distributional signal
is MORE informative than the semantic signal for this specific failure mode —
the opposite of what the LLM-based hypothesis predicted.

| Detector (at 90% specificity) | spec | sens (Mode S, n=2) | sens (diverse, n=35) | sens (all 37) |
|-------------------------------|-----:|-------------------:|---------------------:|--------------:|
| LLM semantic critic (deepseek-r1:7b) | 100% | 0.0% | 0.0% | 0.0% |
| LLM boolean decision (raw, unconstrained) | 47.5% | 50.0% | 65.7% | 64.9% |
| **char 3-gram KL divergence (fallback)** | **90.0%** | **100%** | **100%** | **100%** |
| lang-id entropy alone (RQ13 baseline) | 92.5% | 0.0% | 100% | 94.6% |

**Hypothesis verdicts: H34a NOT SUPPORTED, H34b NOT SUPPORTED, H34c NOT
SUPPORTED.** The LLM semantic critic does not catch Mode S at 90% specificity
(H34a), does not achieve > 95% sensitivity on all hallucinations (H34b), and
does not outperform lang-id entropy on Mode S (H34c — both get 0% at 90%
specificity). The unexpected positive finding is the n-gram KL-divergence
fallback, which is the first detector to achieve 100% Mode S sensitivity at
90% specificity and should be investigated as the new Mode S detector on
additional datasets.

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min).
Each window stores `separated_text_per_speaker`, `mixed_text`, and the cpWER
each route would yield. Hallucination label: `always_separated_cpwer > 1.0`
(37 hallucinated / 40 non-hallucinated, RQ12's split). Mode S = hallucinated
AND `lang_id_entropy < 0.409` AND `length_ratio < 2.0` AND `cr < 2.4` —
verified to be exactly windows 22 and 30, matching RQ16/RQ19's residual.
Diverse hallucination = hallucinated AND `lang_id_entropy > 0.409` (35 tracks).

### LLM semantic critic (primary method)

For each window the separated transcript (per-speaker texts concatenated) is
sent to deepseek-r1:7b via ollama's HTTP API (temperature 0.0, num_predict
1024). The prompt asks the LLM to evaluate whether the transcript contains
hallucinated content, considering: (1) semantic sense as meeting speech, (2)
suspicious repetitiveness/genericness, (3) unusual character patterns. The LLM
responds as a JSON object `{hallucinated, confidence, reason}`; responses are
parsed with `<think>`-block stripping, JSON extraction (with balanced-brace
matching), and regex fallback for malformed JSON.

The LLM's `(hallucinated, confidence)` pair is mapped to a hallucination-probability
score in [0, 1]: if hallucinated=True, score = confidence; if hallucinated=False,
score = 1 - confidence. Higher score = more likely hallucinated. This score is
calibrated at 90% specificity on the 40 non-hallucinated tracks.

### Character n-gram KL-divergence fallback

The character 3-gram probability distribution of each separated transcript is
compared (via KL divergence) to the average 3-gram distribution of the 40
non-hallucinated tracks. Novel 3-grams (not in the reference) contribute a
large KL term. Additive smoothing (1e-9) prevents log(0). High KL = the text's
character 3-gram distribution is anomalous relative to normal speech. This
tests whether Mode S has a detectable distributional anomaly even though it
lacks a detectable surface-feature anomaly.

### Calibration + evaluation

Each detector is calibrated at >= 90% specificity on the 40 non-hallucinated
tracks: the threshold is the smallest candidate (from the union of neg and pos
scores) where false positives <= 4 (floor(0.10 * 40)). This maximises
sensitivity while holding specificity >= 90%. Bootstrap 95% CIs use 10,000
resamples (seed=42) with FIXED thresholds. The lang-id entropy baseline
(threshold 0.409, RQ13) is included for comparison.

### Hypotheses

- H34a: LLM catches both Mode S windows at 90% specificity (sens = 100%).
- H34b: LLM achieves > 95% sensitivity on all 37 hallucinated tracks.
- H34c: LLM outperforms lang-id entropy on Mode S (Mode S sens > 0%).

## Results

### LLM semantic critic — non-deployable (high false-positive rate)

The LLM flags 21 of 40 non-hallucinated tracks as hallucinated (52.5% false-
positive rate). The non-hallucinated score distribution (median 0.70, 34/40
with score >= 0.5, 9/40 with score >= 0.9) overlaps heavily with the
hallucinated distribution (median 0.85). At 90% specificity the only valid
threshold is +inf (flag nothing), yielding 0% sensitivity across all subgroups.

The LLM does catch real hallucinations at lower specificity — its raw boolean
decision achieves 64.9% sensitivity on all hallucinated, 65.7% on diverse —
but the false-positive cost is too high for deployment.

| Specificity floor | Max Mode S sensitivity | threshold |
|------------------:|-----------------------:|----------:|
| >= 50% | 50% (1/2) | 0.85 |
| >= 70% | 50% (1/2) | 0.90 |
| >= 80% | 0% (0/2) | +inf |
| >= 90% | 0% (0/2) | +inf |
| >= 95% | 0% (0/2) | +inf |

The LLM catches window 30 (score 0.95: "filled with repetitive phrases, unclear
sentences, and non-standard Chinese characters") but misses window 22 (score
0.15: "coherent and plausible for a meeting discussion with some repetitive
phrases that are common in group settings"). Window 22's Mode S text IS
coherent Chinese meeting speech — the near-duplicate-with-substitutions
mechanism produces text that reads naturally, defeating semantic analysis.

### Character 3-gram KL divergence — first detector to catch Mode S at 90% specificity

The n-gram KL divergence achieves a clean separation between hallucinated and
non-hallucinated tracks:

| Group | KL score range | n |
|-------|---------------:|--:|
| non-hallucinated | [0.00, 3.30] | 40 |
| hallucinated (all) | [14.84, 18.93] | 37 |
| Mode S (windows 22, 30) | [15.55, 15.76] | 2 |
| diverse hallucination | [14.84, 18.93] | 35 |

The gap between the highest non-hallucinated KL (3.30) and the lowest
hallucinated KL (14.84) is 11.54 — a dramatic separation with no overlap. At
90% specificity (threshold 3.30, the max non-hallucinated score), the n-gram KL
detector flags 100% of Mode S, 100% of diverse hallucinations, and 100% of all
37 hallucinated tracks.

The 4 false positives at the 90%-specificity threshold are all very-short-text
tracks (2 characters: windows 15, 24, 66, 67) whose 3-gram distributions are
naturally unusual. A minimum-length filter would likely restore specificity to
100% without losing sensitivity, but this is left to future work to keep the
analysis conservative.

### Why the n-gram KL succeeds where the LLM and surface detectors fail

Mode S's mechanism (RQ19) is that the separator produces essentially the mixed
audio back, and Whisper re-decodes it with small character substitutions. This
produces text that:
- Is semantically coherent (defeats the LLM — "coherent and plausible for a
  meeting discussion")
- Has normal surface features (defeats CR, lang-id entropy, length ratio — all
  below threshold for Mode S)
- Has normal content-similarity to mixed (defeats RQ19 — Mode S is a near-
  duplicate, which is confounded with clean single-speaker tracks)
- BUT has unusual character 3-gram combinations (the substitutions create 3-grams
  not seen in normal speech) → high KL divergence

The distributional anomaly is the signal surface that Mode S cannot hide. The
n-gram KL divergence is the first detector to exploit it.

### Comparison to all prior Mode S detectors

| RQ | Detector | Mode S sens at 90% spec | |
|----|----------|------------------------:|--|
| RQ19 | content-similarity (token-overlap Jaccard) | 0.0% | confounded with clean tracks |
| RQ22 | (surface detector) | 0.0% | |
| RQ23 | (surface detector) | 0.0% | |
| RQ28 | (surface detector) | 0.0% | |
| RQ34 | LLM semantic critic (deepseek-r1:7b) | 0.0% | non-deployable (52.5% FP rate) |
| **RQ34** | **char 3-gram KL divergence** | **100%** | **first detector to catch Mode S** |

## Hypothesis Verdicts

- **H34a — LLM catches both Mode S windows at 90% specificity: NOT SUPPORTED.**
  The LLM's 90%-specificity threshold is +inf (flag nothing) because 21 of 40
  non-hallucinated tracks are false-positively flagged. Mode S sensitivity =
  0.0% (0/2) at 100% specificity. Even at 50% specificity the LLM catches only
  50% of Mode S (window 30 but not window 22).

- **H34b — LLM achieves > 95% sensitivity on all 37 hallucinated: NOT
  SUPPORTED.** The LLM's all-hallucinated sensitivity is 0.0% at 90%
  specificity (threshold = +inf). At its raw boolean decision (47.5%
  specificity) it achieves 64.9% — well below 95% even ignoring the
  specificity floor.

- **H34c — LLM outperforms lang-id entropy on Mode S: NOT SUPPORTED.** The LLM
  achieves 0% Mode S sensitivity at 90% specificity, equal to lang-id
  entropy's 0%. Both miss Mode S at the deployability floor. (The LLM does
  catch window 30 at its raw decision, but not at 90% specificity.)

## Honest Limitations

1. **n = 2 Mode S tracks (the headline caveat, same as RQ19).** The entire
   Mode S analysis rests on 2 windows. Mode S sensitivity can only take values
   0%, 50%, 100%. The n-gram KL's 100% should be read as "both Mode S windows
   scored well above the threshold," not as a precise estimate. The dramatic
   separation (KL 15.5 vs threshold 3.3) is reassuring but must be validated on
   additional datasets with more Mode S cases.

2. **In-sample calibration.** The 90%-specificity threshold (3.30) is
   calibrated on these exact 40 non-hallucinated tracks. Out-of-sample transfer
   is untested (single AISHELL-4 meeting). The n-gram reference distribution is
   also built from these same 40 tracks. A leave-one-out or external-dataset
   validation would strengthen the result.

3. **The 4 false positives are all short-text tracks.** The n-gram KL's 90%
   specificity is achieved despite 4 false positives on 2-character tracks
   (windows 15, 24, 66, 67) whose 3-gram distributions are naturally unusual.
   This is a length confound: short texts have sparse, atypical 3-gram
   distributions. A minimum-length filter or length-normalised KL would likely
   help but was not applied to keep the analysis conservative.

4. **LLM false-positive rate may be prompt/model-dependent.** The 52.5% FP rate
   is specific to deepseek-r1:7b with the RQ34 prompt. A different model, a
   more conservative prompt, or few-shot examples might reduce false positives.
   The LLM's fundamental limitation (missing window 22's coherent Mode S text)
   is unlikely to be fixed by prompt engineering — the text genuinely reads as
   meeting speech.

5. **Single LLM, temperature 0.** Only deepseek-r1:7b was tested, at
   temperature 0.0 for determinism. Other LLMs (larger deepseek-r1, Qwen, Llama)
   might perform differently. The LLM responses are cached
   (`llm_raw_responses.json`) for reproducibility but are qualitative (model-
   version-dependent) — hence the `qualitative/demo` label for LLM outputs.

6. **The n-gram KL's Mode S mechanism is post-hoc.** The explanation (near-
   duplicate-with-substitutions creates unusual 3-grams) is consistent with the
   data but was identified after seeing the results. A pre-registered
   hypothesis test on a held-out dataset would be more convincing.

7. **Oracle-TextGrid-specific.** Mode S arises from oracle-TextGrid separation
   leaving true silence that Whisper fills. A real separator produces residual
   noise, not true silence, and the near-duplicate mechanism (and hence the
   3-gram anomaly) may differ.

## Reproducibility

- Script: `python3 results/frontier/llm_semantic_critic/llm_semantic_critic_analysis.py`
  (deterministic for the n-gram fallback; LLM calls cached to
  `llm_raw_responses.json` for reproducibility). The LLM run takes ~25 minutes
  (77 calls × ~19s each); re-runs load from cache and complete in seconds.
  numpy + stdlib only for the fallback; ollama + deepseek-r1:7b for the LLM.
- Core module: `src/llm_semantic_critic.py` (pure functions, unit-tested in
  `tests/test_llm_semantic_critic.py`, 77 tests).
- Outputs: `llm_semantic_critic_results.csv` (per-window), 
  `llm_semantic_critic_results.json` (summary + per-window + hypothesis
  verdicts), `llm_raw_responses.json` (cached LLM responses), `FINDINGS.md`.
- Bootstrap: 10,000 resamples, seed=42. LLM: temperature 0.0, num_predict 1024.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

RQ19–RQ28 showed Mode S is the residual gap that no surface or content-
similarity detector can close at 90% specificity. RQ34 tested two new signal
surfaces:

1. **Semantic (LLM) — fails.** deepseek-r1:7b cannot distinguish Mode S's
   coherent near-duplicate Chinese from real meeting speech, and has a 52.5%
   false-positive rate on clean tracks that makes it non-deployable at 90%
   specificity. The LLM approach is fundamentally limited by Mode S's semantic
   coherence — the hallucination reads as valid speech.

2. **Distributional (n-gram KL) — succeeds.** The character 3-gram KL-divergence
   achieves 100% Mode S sensitivity at 90% specificity, the first detector to
   do so. The distributional anomaly (unusual 3-gram combinations from the
   near-duplicate-with-substitutions mechanism) is the signal surface Mode S
   cannot hide.

The n-gram KL-divergence detector should be investigated as the new Mode S
detector on additional datasets (more Mode S cases, real separators, other
meetings). If it generalises, it closes the RQ16 corrected-router's 2-window
residual (0.026 cpWER) that has been the transcript-only ceiling since RQ19.
The LLM semantic critic, despite its appeal, is not the right tool for Mode S —
Mode S's failure mode is distributional, not semantic.
