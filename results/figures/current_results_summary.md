# Current Results Summary

## Core Findings

- Separated speaker-track ASR is the best method on NoOverlap, HeavyOverlap, and OppositeOverlap.
- Mixed ASR remains the best method on LightOverlap and MidOverlap.
- Duplicate suppression improves the separated transcript on LightOverlap and MidOverlap, but does not overtake mixed ASR there.
- The rule-based router does not use CER as an input feature.

## Rule Router Decision Table

| case_id | overlap_level | selected_method | decision_rule |
| --- | ---: | --- | --- |
| HeavyOverlap | 3 | separated_whisper | if overlap_level >= 3, choose separated_whisper |
| LightOverlap | 1 | mixed_whisper | if overlap_level in [1, 2], choose mixed_whisper |
| MidOverlap | 2 | mixed_whisper | if overlap_level in [1, 2], choose mixed_whisper |
| NoOverlap | 0 | separated_whisper | if overlap_level == 0, choose separated_whisper |
| OppositeOverlap | 4 | separated_whisper | if overlap_level >= 3, choose separated_whisper |

## Average CER Comparison

- fixed_mixed_whisper: 0.302093
- fixed_separated_whisper: 0.191846
- fixed_separated_whisper_cleaned: 0.181681
- oracle_best: 0.120042
- rule_router: 0.120042

## Error Type Analysis

- LightOverlap separated output is insertion-heavy and repetition-heavy, which explains why separation hurts in that case.
- MidOverlap shows a similar pattern, with insertion errors and repeated fragments still present after separation.
- Detailed error type summary: results/figures/error_type_summary.md