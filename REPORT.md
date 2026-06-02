# When Should We Separate? Boundary-aware, Compute-aware, and Speaker-aware Adaptive ASR for Overlapping Speech

## 1. Introduction

Multi-speaker audio is hard to transcribe reliably when speakers interrupt each other or talk at the same time. In those cases, a single ASR pass often produces repeated fragments, insertions, missing spans, and speaker attribution errors.

This project asks a focused question:

> When should we separate, and when does separation hurt more than it helps?

The answer is not a single model or a universal separation rule. Instead, the project studies mixed ASR, separated speaker-track ASR, cleaned separated transcripts, adaptive routing, speaker-aware evaluation, and risk-aware selection.

## 2. Background and Motivation

The repository started from an earlier overlapping-speech ASR project and turned it into a benchmark-driven research engineering pipeline. The goal is to understand the conditions under which separation improves accuracy and when it introduces hallucinated repetition or over-deletion.

The motivation is practical:

- meeting and debate audio often contains overlap;
- raw ASR may transcribe the words but still lose who said what;
- separation can help, but it can also amplify repetition and insertion errors;
- a better system should select the safest transcript type for the observed overlap regime.

## 3. Dataset and Benchmark

The gold benchmark contains five manually verified cases:

| case_id | overlap_level | purpose |
| --- | ---: | --- |
| NoOverlap | 0 | clean baseline |
| LightOverlap | 1 | light cross-talk |
| MidOverlap | 2 | moderate overlap |
| HeavyOverlap | 3 | strong overlap |
| OppositeOverlap | 4 | highly competitive overlap |

Each case has:

- mixed audio,
- separated speaker tracks,
- mixed ASR output,
- separated speaker-track ASR output,
- duplicate-suppressed cleaned separated output,
- a verified reference transcript pair for speaker-aware evaluation.

In addition, the repository contains synthetic silver benchmarks and a held-out synthetic split. These are used for robustness validation only and are not gold evaluation.

## 4. Method

### 4.1 Mixed ASR

The mixed baseline uses `whisper-small` directly on the mixed audio. It is the simplest non-separation path and provides the baseline against which all other methods are measured.

### 4.2 Separated Speaker-track ASR

For each case, the already-separated `spk1` and `spk2` waveforms are transcribed independently with `whisper-small`. The resulting segments are merged into a speaker-attributed transcript in start-time order.

This tests the hypothesis that a cleaner signal should help ASR. The benchmark shows that this is true in some overlap regimes, but not all.

### 4.3 Duplicate Suppression

The cleaned transcript is produced by a lightweight duplicate suppression pass over the separated speaker transcript. The goal is to remove repeated hallucinated fragments while preserving speaker order.

The heuristic removes:

- identical neighboring segments,
- short repeated phrases from the same speaker within a local window,
- obvious repetition bursts.

### 4.4 Error Type Analysis

We analyze the edit structure of the CER errors and summarize substitution, deletion, insertion, and repetition-related patterns.

This explains why separation can degrade quality in lighter overlap:

- `LightOverlap` is dominated by insertion and repetition hallucination;
- `MidOverlap` shows a similar pattern;
- `HeavyOverlap` and `OppositeOverlap` benefit more clearly from separation.

### 4.5 Adaptive Router v1 and v2

The router selects one of:

- `mixed_whisper`
- `separated_whisper`
- `separated_whisper_cleaned`

The router does not use ground-truth CER as an input feature. CER is only used after the decision is fixed.

The first router version is overlap-only. The second version adds transcript-instability signals such as:

- length inflation,
- duplicate removal count,
- repetition proxy signals,
- speaker length imbalance,
- method disagreement proxies.

### 4.6 Speaker-aware CER

Normal CER collapses the transcript into one string and can hide speaker attribution problems. Speaker-aware CER evaluates `speaker_1_text` and `speaker_2_text` separately and reports per-speaker CER, macro CER, and speaker gap.

### 4.7 cpCER-lite

cpCER-lite is a lightweight permutation-aware evaluation. It compares direct and swapped speaker mappings and chooses the better one. This helps check whether the main issue is speaker swap or content-level transcription quality.

### 4.8 Synthetic Silver Validation

Synthetic overlap samples are used as supplementary robustness evidence. They are not gold evaluation. Their purpose is to show whether the router behavior remains stable outside the five verified benchmark cases.

### 4.9 Held-out Synthetic Split

A larger synthetic split is divided into dev and test subsets. Dev is useful for inspecting thresholds and behavior, but test is reserved for final evaluation. The held-out split checks whether the router generalizes beyond the original synthetic set.

### 4.10 Risk-aware Final Selector

The risk-aware selector is a reference-free final selection layer. It uses only deployment-visible stability signals and risk proxies to choose a final transcript type. Ground-truth CER is used only after selection, for evaluation.

## 5. Experiments

### 5.1 Global CER

| strategy | average CER |
| --- | ---: |
| fixed_mixed_whisper | 0.302093 |
| fixed_separated_whisper | 0.191846 |
| fixed_separated_whisper_cleaned | 0.181681 |
| router_v2 | 0.120042 |
| oracle_best | 0.120042 |

The gold benchmark shows that:

- separation is useful on average, but not always;
- cleaned separated output is slightly better than raw separated on average;
- router_v2 matches the oracle best average on this benchmark.

### 5.2 Error Type Analysis

The error-type study reveals the main failure mode of separated ASR under light and moderate overlap:

- repeated hallucinations,
- insertion-heavy errors,
- duplicated tail fragments.

This matches the qualitative inspection of the cleaned transcripts and explains why duplicate suppression helps but does not fully solve the problem.

### 5.3 Adaptive Routing

The router chooses the following best method per gold case:

| case_id | selected_method |
| --- | --- |
| NoOverlap | separated_whisper |
| LightOverlap | mixed_whisper |
| MidOverlap | mixed_whisper |
| HeavyOverlap | separated_whisper |
| OppositeOverlap | separated_whisper |

The main result is not that separation always wins. The main result is that the best transcript type depends on the overlap regime.

### 5.4 Synthetic Silver Validation

Original synthetic silver results:

| strategy | average CER |
| --- | ---: |
| v1 | 0.350902 |
| v2 | 0.167553 |
| oracle | 0.082239 |

The synthetic silver benchmark exposed a stability issue in the overlap-only router. It looked strong on the gold benchmark but failed on synthetic NoOverlap. The feature-based router v2 improved robustness by reacting to instability signals.

### 5.5 Held-out Synthetic Split

Held-out synthetic test results:

| strategy | average CER |
| --- | ---: |
| v1 | 0.361350 |
| v2 | 0.335326 |
| oracle | 0.115181 |

The held-out split confirms that v2 is more stable than v1, but there is still a non-trivial gap to oracle performance.

### 5.6 Router Ablation

Router ablation shows that repetition and duplicate-removal features are more useful than length ratio alone. This supports the idea that instability signals matter more than overlap level by itself.

### 5.7 Speaker-aware CER

Speaker-aware CER shows that cleaned separated output can improve some overlap cases, but raw separated output remains better in others.

| case_id | separated_whisper macro CER | separated_whisper_cleaned macro CER |
| --- | ---: | ---: |
| NoOverlap | 0.054312 | 0.089278 |
| LightOverlap | 0.194170 | 0.135164 |
| MidOverlap | 0.175908 | 0.168620 |
| HeavyOverlap | 0.110821 | 0.146535 |
| OppositeOverlap | 0.047479 | 0.083193 |

### 5.8 cpCER-lite

cpCER-lite did not find speaker permutation mismatch in the five gold cases. The direct speaker assignment is always better than the swapped one, which means the main errors are content-level rather than speaker-swap-level.

### 5.9 Risk-aware Selector

| strategy | average CER |
| --- | ---: |
| risk_aware_selector | 0.134587 |
| router_v2 | 0.120042 |
| oracle_best | 0.120042 |

The risk-aware selector is deliberately conservative and explainable. It is not the best-CER result, but it is useful as a deployment-oriented final selector.

## 6. Results and Discussion

The project leads to six main findings:

1. Speech separation is useful, but not universally beneficial.
2. The main degradation in `LightOverlap` and `MidOverlap` is caused by insertion and repetition hallucination.
3. Speaker swap is not the dominant error source in the five gold cases.
4. Router v1 is fragile outside the small gold benchmark, while router v2 is more stable.
5. Synthetic silver validation is valuable for exposing overfitting, but it is not gold evaluation.
6. Speaker-aware and permutation-aware evaluation reveal behaviors that global CER alone does not show.

The strongest practical conclusion is that a system should separate selectively, not blindly. A mixed transcript is safer in some overlap regimes, while separated or cleaned separated output is better in others.

## 7. Limitations

This project is intentionally bounded.

- No new ASR model training was performed.
- The gold benchmark is small.
- Synthetic references are silver, not gold.
- The router is rule-based rather than learned.
- External benchmark validation is not yet complete.
- LLM/RAG remains a future extension rather than the core quantitative result.

## 8. Future Work

Natural next steps include:

- separation phase diagram;
- compute-aware cascade;
- speaker profile / voiceprint exploration;
- MeetEval / cpWER compatibility work;
- external mini validation.

## 9. Conclusion

This project shows that the best transcript strategy depends on the overlap regime. Mixed ASR is safer under light overlap, separated ASR is stronger under heavier overlap, and duplicate suppression can reduce repetition without fully solving separated hallucinations. Router_v2 matches the oracle-best average CER on the gold benchmark, while synthetic validation and risk-aware selection help explain where the system remains fragile.
