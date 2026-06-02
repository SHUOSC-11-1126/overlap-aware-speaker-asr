# Router Ablation Summary

This analysis compares feature subsets for the rule-based router without using CER as an input feature.

## Gold Benchmark

| strategy | average_cer | gap_to_oracle | notes |
| --- | ---: | ---: | --- |
| fixed_mixed_whisper | 0.302093 | 0.182051 | Fixed baseline that always chooses mixed_whisper. |
| fixed_separated_whisper | 0.191846 | 0.071804 | Fixed baseline that always chooses separated_whisper. |
| fixed_separated_whisper_cleaned | 0.181681 | 0.061639 | Fixed baseline that always chooses separated_whisper_cleaned. |
| oracle_best | 0.120042 | 0.000000 | Upper bound: chooses the lowest CER method per sample/case. |
| v1_overlap_only | 0.120042 | 0.000000 | Uses overlap level only; this is the current rule-based baseline. |
| length_ratio_only | 0.302093 | 0.182051 | Uses length inflation as the only instability signal, then falls back to v1. |
| repetition_only | 0.159942 | 0.039900 | Uses repetition hallucination as the only instability signal, then falls back to v1. |
| removed_count_only | 0.159942 | 0.039900 | Uses cleaned duplicate-removal count as the only instability signal, then falls back to v1. |
| length_plus_repetition | 0.181681 | 0.061639 | Combines length inflation and repetition as instability signals. |
| v2_full_features | 0.120042 | 0.000000 | Current feature router v2 with all observable instability features. |

## Synthetic Silver Benchmark

| strategy | average_cer | gap_to_oracle | notes |
| --- | ---: | ---: | --- |
| fixed_mixed_whisper | 0.311442 | 0.229203 | Fixed baseline that always chooses mixed_whisper. |
| fixed_separated_whisper | 0.380701 | 0.298462 | Fixed baseline that always chooses separated_whisper. |
| fixed_separated_whisper_cleaned | 0.203778 | 0.121539 | Fixed baseline that always chooses separated_whisper_cleaned. |
| oracle_best | 0.082239 | 0.000000 | Upper bound: chooses the lowest CER method per sample/case. |
| v1_overlap_only | 0.350902 | 0.268663 | Uses overlap level only; this is the current rule-based baseline. |
| length_ratio_only | 0.311442 | 0.229203 | Uses length inflation as the only instability signal, then falls back to v1. |
| repetition_only | 0.173979 | 0.091740 | Uses repetition hallucination as the only instability signal, then falls back to v1. |
| removed_count_only | 0.173979 | 0.091740 | Uses cleaned duplicate-removal count as the only instability signal, then falls back to v1. |
| length_plus_repetition | 0.340673 | 0.258434 | Combines length inflation and repetition as instability signals. |
| v2_full_features | 0.167553 | 0.085314 | Current feature router v2 with all observable instability features. |

## Interpretation

- v1_overlap_only is the baseline overlap-only heuristic.
- length_ratio_only captures length inflation but misses repetition hallucinations when length looks normal.
- repetition_only and removed_count_only capture duplication-related failures more directly.
- length_plus_repetition is the strongest low-cost ablation before using the full v2 feature set.
- v2_full_features is the best feature-based strategy overall among the deployable heuristics tested here.

## Gold Best-Improving Features

- length_ratio_only helps when transcript inflation is the dominant failure mode.
- repetition_only and removed_count_only help when duplicated hallucinations dominate.
- length_plus_repetition is the most conservative hybrid heuristic before v2_full_features.

## Synthetic Best-Improving Features

- length_ratio_only helps when transcript inflation is the dominant failure mode.
- repetition_only and removed_count_only help when duplicated hallucinations dominate.
- length_plus_repetition is the most conservative hybrid heuristic before v2_full_features.
