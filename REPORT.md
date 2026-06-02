# Overlap-Aware Speaker-Attributed ASR with Adaptive Routing

## 1. Introduction

Multi-speaker audio is difficult to transcribe reliably when speakers interrupt each other or speak at the same time. In these cases, a single ASR pass often produces repeated fragments, insertions, missing spans, and speaker attribution errors. This project studies how to improve speaker-attributed ASR for overlapping conversation by comparing mixed transcription, separated speaker-track transcription, duplicate suppression, and a rule-based adaptive router.

The central question is not simply whether speech separation improves ASR, but when it helps and when it hurts. On this benchmark, separation is beneficial under stronger overlap, but it can also introduce hallucinated repetitions and insertions under lighter overlap. The final system therefore emphasizes selective routing rather than one-size-fits-all separation.

## 2. Background and Motivation

The repository is based on XuTong's multi-speaker conversation management work and uses that project as the starting point for a more systematic evaluation of overlap-aware transcription. The benchmark contains five overlap conditions ranging from clean audio to heavy cross-talk. These cases make it possible to isolate failure modes and measure whether speaker-specific content is preserved.

The motivation for the project is practical:

- meeting and debate audio often contains overlap;
- raw ASR can transcribe words correctly but still lose who said what;
- separation can help, but may also amplify hallucinated fragments;
- a better system should route audio to the most suitable transcript type.

## 3. Dataset and Benchmark

We evaluate five benchmark cases:

| case_id | overlap_level | purpose |
| --- | ---: | --- |
| NoOverlap | 0 | clean baseline |
| LightOverlap | 1 | light cross-talk |
| MidOverlap | 2 | moderate overlap |
| HeavyOverlap | 3 | strong overlap |
| OppositeOverlap | 4 | highly competitive overlap |

Each case has:

- the mixed audio waveform,
- two separated speaker tracks,
- mixed ASR transcripts,
- separated speaker-track ASR transcripts,
- cleaned separated transcripts after duplicate suppression,
- a verified reference transcript pair for speaker-aware evaluation.

The verified references were assembled from LLM-assisted drafts and manually checked by the team. The reference file contains `full_text` plus `speaker_1_text` and `speaker_2_text` so that both transcript-level and speaker-aware metrics can be computed.

## 4. Method

### 4.1 Mixed Whisper Baseline

The mixed baseline uses `whisper-small` on the mixed audio. This is the simplest reference point and the default non-separation path. It measures what can be achieved without trying to disentangle speakers.

### 4.2 Separated Speaker-track ASR

For each case, the already separated `spk1` and `spk2` waveforms are transcribed independently with `whisper-small`. The resulting segments are merged into a speaker-attributed transcript by ordering segments by start time and attaching the speaker label from the source track.

This method tests the intuition that a cleaner signal should help ASR. The experiments show that this is true in some overlap regimes, but not all.

### 4.3 Duplicate Suppression

The cleaned transcript is produced by a lightweight heuristic duplicate suppression pass over the separated speaker transcript. The goal is to reduce repeated hallucinated fragments that appear near the end of some separated outputs.

The cleanup rules remove:

- identical neighboring segments,
- short repeated phrases from the same speaker within a local window,
- obvious repeated hallucination bursts.

The cleaned transcript is not a rewrite. It is a conservative post-processing step designed to reduce repetition while keeping speaker order intact.

### 4.4 Error Type Analysis

To explain why separation sometimes degrades transcription quality, we analyze the edit structure of the CER errors and summarize substitution, deletion, insertion, and repetition-related patterns.

This analysis shows that the problematic separated cases are not dominated by random mistakes. Instead, `LightOverlap` and `MidOverlap` are strongly affected by insertion and repeated fragments, which is consistent with separation-triggered hallucination.

### 4.5 Rule-based Adaptive Router

We implement a simple router that selects a transcript type without using ground-truth CER as an input feature. The initial rule is:

- if `overlap_level == 0`, choose `separated_whisper`;
- if `overlap_level in [1, 2]`, choose `mixed_whisper`;
- if `overlap_level >= 3`, choose `separated_whisper`;
- otherwise choose `mixed_whisper`.

This router uses only observable metadata such as overlap level, runtime, segment counts, text lengths, and duplicate counts. CER is only used after the decision is made, for evaluation.

### 4.6 Speaker-aware CER Evaluation

Normal CER collapses the transcript into one string and can hide speaker attribution problems. Speaker-aware CER evaluates `speaker_1_text` and `speaker_2_text` separately, then reports per-speaker CER, macro CER, and speaker gap.

This metric is important because a transcript can look acceptable at the global text level while still mixing speaker content unevenly.

## 5. Experiments

### 5.1 Global CER

The global CER results are summarized below:

| strategy | average CER |
| --- | ---: |
| fixed_mixed_whisper | 0.302093 |
| fixed_separated_whisper | 0.191846 |
| fixed_separated_whisper_cleaned | 0.181681 |
| oracle_best | 0.120042 |
| rule_router | 0.120042 |

Key observations:

- raw separation is already better than mixed ASR on average;
- duplicate suppression provides a small additional gain;
- the rule-based router matches the oracle best on this benchmark;
- the benchmark is small, so this should be treated as a strong empirical result, not a universal guarantee.

### 5.2 Adaptive Routing

The router chooses the following best method per case:

| case_id | selected_method |
| --- | --- |
| NoOverlap | separated_whisper |
| LightOverlap | mixed_whisper |
| MidOverlap | mixed_whisper |
| HeavyOverlap | separated_whisper |
| OppositeOverlap | separated_whisper |

The adaptive router performs well because it captures the main pattern of this benchmark: clean and strongly overlapping cases benefit from separation, while lighter overlap is often safer with the mixed baseline.

### 5.3 Error Type Analysis

The error-type study explains the failure mode of separated ASR under light and moderate overlap:

- `LightOverlap` separated output is dominated by insertions and repeated fragments.
- `MidOverlap` shows a similar pattern, with many insertions and repetitions remaining after separation.
- `HeavyOverlap` and `OppositeOverlap` do not show the same failure profile and benefit more clearly from separation.

This supports the main thesis of the project: speech separation is useful, but not universally beneficial.

### 5.4 Speaker-aware Evaluation

Speaker-aware CER results:

| case_id | separated_whisper macro CER | separated_whisper_cleaned macro CER | note |
| --- | ---: | ---: | --- |
| NoOverlap | 0.054312 | 0.089278 | raw separated is better |
| LightOverlap | 0.194170 | 0.135164 | cleaned improves speaker-level quality |
| MidOverlap | 0.175908 | 0.168620 | cleaned slightly improves macro CER |
| HeavyOverlap | 0.110821 | 0.146535 | raw separated is better |
| OppositeOverlap | 0.047479 | 0.083193 | raw separated is better |

This shows that cleaning helps the light and moderate overlap cases, but it can also remove useful content. In the clean and strongly overlapping cases, the raw separated transcript still preserves speaker-specific content better.

## 6. Results and Discussion

The project leads to four main findings:

1. Speech separation is useful, but not universally beneficial.
2. The main degradation in `LightOverlap` and `MidOverlap` is caused by insertion and repetition hallucination.
3. A simple rule-based router can match the oracle best average CER on this benchmark.
4. Speaker-aware CER reveals differences that global CER alone cannot show.

The speaker-aware evaluation is especially important because it shows that a transcript can improve at the global CER level while still being uneven across speakers. This is why the cleaned transcript is worth keeping as a candidate, but not as the only answer.

## 7. Limitations

This project is intentionally small and benchmark-driven.

- The benchmark has only five cases.
- The router is rule-based, not learned.
- The duplicate suppression heuristic is lightweight and may remove useful content in some cases.
- Speaker-aware evaluation depends on manually verified references.
- The project does not yet include an end-to-end learned diarization or routing model.

## 8. Future Work

Several extensions would be natural next steps:

- learn a router from overlap and transcript features rather than using fixed rules;
- add a better hallucination detector for repeated fragments;
- expand the benchmark with more realistic meeting audio;
- integrate lexical constraints or domain terminology retrieval;
- add a learned speaker-attributed correction step.

LLM/RAG is a plausible extension, but it is not required for the current core result.

## 9. Conclusion

This project shows that the best transcript strategy depends on the overlap regime. Mixed ASR is safer under light overlap, separated ASR is stronger under heavier overlap, and duplicate suppression can reduce repetition without fully solving separated hallucinations. A simple rule-based router reaches the oracle-best average CER on the current benchmark, and speaker-aware CER confirms that raw and cleaned separated transcripts trade off content preservation in different ways.
