# RQ36: LLM Emotion Reading from Hallucinated Transcripts

> **Label: `experimental/frontier`** (statistics) + **`qualitative/demo`** (LLM readings)
>
> Tests whether a local LLM (deepseek-r1:7b via ollama) reading emotion from
> hallucinated ASR transcripts produces a usable safety signal for emotion-gated
> routing. The LLM is asked to read emotion and report confidence + reliability
> for each transcript. If hallucinated transcripts produce lower confidence or
> lower reliability than clean transcripts, the LLM's own meta-cognition could
> serve as a reference-free hallucination detector. Closes #943.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (label `external/sanity-check`, read-only). Gold tracks from
> `results/frontier/gold_detector_comparison/gold_track_texts.json` (RQ21)
> joined with `results/frontier/separation_tax/phase_curve.csv` for CER labels.

## Executive Summary

The LLM emotion reading does NOT produce a usable hallucination safety signal.
All three hypotheses fail on AISHELL-4:

- **H36a NOT SUPPORTED**: The LLM's confidence variance on hallucinated tracks
  (0.036) is slightly *lower* than on clean tracks (0.046), F=0.78, p=0.50.
  The LLM is not more uncertain on hallucinated transcripts — if anything, it
  is slightly more confident.
- **H36b NOT SUPPORTED**: The LLM's `reliable` field achieves AUC=0.502
  (random chance) as a hallucination classifier. 15 of 40 clean tracks are
  false-positively flagged as unreliable (37.5% FP rate), while both Mode S
  hallucination tracks are flagged as *reliable*.
- **H36c SUPPORTED**: Mode S mean confidence (0.70) is within 1 SD of the
  clean mean (0.75 ± 0.21). The LLM reads Mode S hallucinations as clean,
  reliable meeting speech — confirming RQ34's finding that Mode S is
  semantically coherent.

Cross-dataset validation on the gold benchmark (13 catastrophic + 40 clean)
confirms the negative: H36a F=0.97 (p=0.88), H36b AUC=0.668 (below 0.80
threshold). The LLM emotion reading does not generalize as a hallucination
detector.

The critical failure pattern: the LLM is overcautious on clean tracks
(37.5% FP rate) while being confident on Mode S hallucinations (both flagged
reliable). This is the worst possible error pattern for a safety signal —
it would block clean transcripts while letting hallucinations through.

## Method

### Data

- AISHELL-4: 77 windows from meeting `M_R003S02C01` (37 hallucinated = 2
  Mode S + 35 diverse, 40 clean). Hallucination label:
  `always_separated_cpwer > 1.0`. Transcript = concatenated
  `separated_text_per_speaker` (mixed_text fallback for empty).
- Gold: 53 tracks (13 catastrophic `cer_sep2 > 1.0`, 40 clean control).
  Transcript = `sep2_text` from `gold_track_texts.json` (RQ21 decoded cache)
  joined with `phase_curve.csv` for CER labels. The task brief named
  `causal_hallucination_probe/probe_rows.csv` as the gold source, but that
  file stores only reduced metrics, not decoded text. The substitution is
  faithful and documented here.

### LLM emotion reading

Each transcript is sent to deepseek-r1:7b via ollama's HTTP API
(temperature 0.0, num_predict 1024, timeout 120s). The prompt asks the LLM
to read the emotional state of the speaker(s), report a confidence level
(0-1), and judge whether the transcript is reliable enough to base an
emotion reading on. The LLM responds as a JSON object
`{emotion, confidence, reliable, reason}`; responses are parsed with
`<think>`-block stripping, JSON extraction (balanced-brace matching), and
regex fallback for malformed JSON.

Transcript-hash caching (every 5 calls) makes the analysis resumable.
All 120 calls completed (120 parsed OK, 0 errors).

### Hypotheses

- H36a: LLM confidence variance on hallucinated > clean (F > 2.0).
  Kill: F ≤ 2.0.
- H36b: LLM `reliable` field classifies hallucinated vs clean (AUC > 0.80).
  Kill: AUC ≤ 0.80.
- H36c: Mode S confidence within 1 SD of clean mean (indistinguishable).
  Success: within 1 SD.

## Results

### H36a — Confidence variance (AISHELL-4)

| Group | n | Variance | Mean |
|------- |--:|---------:|-----:|
| Hallucinated | 36 | 0.0362 | 0.736 |
| Clean | 30 | 0.0462 | 0.753 |

F = 0.783, p = 0.504. The hallucinated variance is *lower* than clean, not
higher. The LLM is not more uncertain on hallucinated transcripts.

### H36b — Reliable field as classifier (AISHELL-4)

| Metric | Value |
|--------|------:|
| AUC(reliable) | 0.502 |
| AUC(1 - confidence) | 0.465 |
| Clean flagged unreliable (FP) | 15/40 (37.5%) |
| Hallucinated flagged reliable (FN) | varies by subgroup |

The `reliable` field is at random-chance level (AUC 0.502). The LLM flags
37.5% of clean tracks as unreliable while flagging both Mode S tracks as
reliable.

### H36c — Mode S indistinguishable (AISHELL-4)

| Window | Emotion | Confidence | Reliable |
|--------|---------|-----------:|:---------|
| 22 (Mode S) | neutral | 0.60 | True |
| 30 (Mode S) | neutral | 0.80 | True |
| Clean mean | — | 0.753 | — |
| Clean SD | — | 0.215 | — |

Mode S mean confidence = 0.70, within 1 SD of clean mean (0.753 ± 0.215).
Max deviation = 0.71 SD. The LLM reads both Mode S hallucinations as clean,
reliable meeting speech. This confirms RQ34's finding that Mode S's
near-duplicate-with-substitutions mechanism produces semantically coherent
text.

### Cross-dataset validation (gold benchmark)

| Hypothesis | F / AUC | Supported? |
|------------|--------:|:-----------|
| H36a (F-test) | F=0.971, p=0.880 | NOT SUPPORTED |
| H36b (AUC) | AUC=0.668 | NOT SUPPORTED |

The gold benchmark's AUC (0.668) is higher than AISHELL-4's (0.502) but
still well below the 0.80 threshold. The LLM has *some* signal on gold's
catastrophic hallucinations (which are repetitive and clearly broken) but
none on AISHELL-4's diverse/Mode S hallucinations (which are semantically
coherent).

## Honest Limitations

1. **Single LLM, temperature 0.** Only deepseek-r1:7b was tested, at
   temperature 0.0 for determinism. A larger model (deepseek-r1:14b is
   available locally) might detect Mode S. RQ41 tests a multi-call ensemble
   at varying temperatures.

2. **Emotion prompt, not detection prompt.** The LLM was asked to read
   emotion, not to detect hallucination. A detection-oriented prompt might
   produce different `reliable` judgments. RQ34 tested a detection prompt
   and found 52.5% FP rate — the emotion prompt's 37.5% FP rate is better
   but still non-deployable.

3. **n = 2 Mode S tracks.** H36c rests on 2 windows (22, 30). The "within
   1 SD" finding is consistent with RQ34's semantic-critic result (window
   22 scored 0.15 on hallucination probability) but must be validated on
   more Mode S cases (RQ40 checks gold/silver).

4. **Gold benchmark substitution.** The task brief named
   `causal_hallucination_probe/probe_rows.csv` as the gold source, but that
   file lacks decoded text. The substitution to `gold_track_texts.json`
   (RQ21) is faithful and documented. The gold CER threshold (1.0) matches
   the project's catastrophic threshold.

5. **LLM readings are qualitative.** The emotion labels and confidence
   values are model-version-dependent. The cache
   (`llm_responses_cache.json`) ensures reproducibility but the readings
   themselves are `qualitative/demo`.

## Reproducibility

- Module: `src/llm_emotion_hallucination.py` (pure functions, unit-tested
  in `tests/test_llm_emotion_hallucination.py`, 36 tests).
- Driver: `results/frontier/llm_emotion_hallucination/llm_emotion_hallucination_analysis.py`
- Run: `python3 results/frontier/llm_emotion_hallucination/llm_emotion_hallucination_analysis.py`
  (loads from cache in seconds; first run takes ~45 min for 120 ollama calls).
- Outputs: `llm_emotion_hallucination_results.json` (summary + per-track +
  verdicts), `llm_responses_cache.json` (120 cached responses).
- LLM: deepseek-r1:7b, temperature 0.0, num_predict 1024, timeout 120s.
- Source data: AISHELL-4 (external/sanity-check) + gold (experimental/frontier),
  both read-only.

## What this changes for the project

RQ34 showed the LLM semantic critic fails at Mode S detection (52.5% FP
rate, 0% sensitivity at 90% specificity). RQ36 tests a different angle:
the LLM's *own meta-cognition* (confidence + reliability) as an implicit
hallucination signal. The result is the same — the LLM cannot distinguish
hallucinated transcripts from clean ones.

The critical finding is the error pattern: the LLM is overcautious on
clean tracks (37.5% FP rate) while being confident on Mode S hallucinations
(both flagged reliable). This means the LLM's meta-cognition is not just
uninformative — it is *anti-informative* for Mode S. Using `reliable=False`
as a routing gate would block 37.5% of clean transcripts while letting
both Mode S hallucinations through.

This closes the emotion-reading-as-safety-signal thread. The LLM's emotion
reading is useful for the emotion-routing direction (RQ6, where the LLM
reads emotion from clean transcripts) but not for hallucination detection.
The two directions are decoupled: emotion reading works on clean audio,
hallucination detection requires reference-free transcript analysis (RQ34's
n-gram KL divergence), and the LLM's meta-cognition is not a substitute for
either.
