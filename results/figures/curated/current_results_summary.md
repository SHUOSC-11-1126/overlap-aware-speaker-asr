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

## Speaker-aware Evaluation

- Normal CER can miss speaker attribution problems because it collapses the transcript into one string.
- Speaker-aware CER compares each speaker track separately, so we can see whether a method preserves who said what.
- Separated speaker-track ASR is useful, but cleaned transcripts can trade repetition reduction for content loss.

### Average speaker macro CER

- separated_whisper: 0.116538
- separated_whisper_cleaned: 0.124558

### Largest speaker gap

- MidOverlap / separated_whisper: 0.267901

- Detailed speaker-aware table: results/figures/speaker_cer_summary.md
- Speaker-aware plot: results/figures/speaker_cer_by_case.png

## Feature Router v2

- v1 performs well on the five verified gold cases, but synthetic silver validation exposed a NoOverlap failure mode.
- v2 adds instability features such as length inflation and duplicate removal count to avoid blindly choosing separated transcripts when the output looks pathological.

### Gold Average CER

- fixed_mixed_whisper: 0.302093
- fixed_separated_whisper: 0.191846
- fixed_separated_whisper_cleaned: 0.181681
- oracle_best: 0.120042
- rule_router_v1: 0.120042
- feature_router_v2: 0.120042

### Synthetic Average CER

- fixed_mixed_whisper: 0.311442
- fixed_separated_whisper: 0.380701
- fixed_separated_whisper_cleaned: 0.203778
- oracle_best: 0.082239
- rule_router_v1: 0.350902
- feature_router_v2: 0.167553

## cpCER-lite

- cpCER-lite checks whether a speaker transcript looks better under direct or swapped speaker assignment.
- A large assignment gap means the transcript may have good content but the speakers are mapped incorrectly.

### Average cpCER-lite

- separated_whisper: 0.116538
- separated_whisper_cleaned: 0.124558

### Largest assignment gap

- HeavyOverlap / separated_whisper: 0.0

- Detailed cpCER-lite table: results/figures/cpcer_lite_summary.md
- cpCER-lite plot: results/figures/cpcer_lite_by_case.png

## Post-hoc Risk Detection and Selective Repair

- cpCER-lite did not find a speaker swap problem in the verified gold cases; direct speaker assignment was always best.
- The remaining errors are mostly content-level insertion and repetition issues, not speaker permutation issues.
- The risk-aware selector is reference-free: it only uses transcript stability signals to pick a final output.
- Ground-truth CER is reserved for after-the-fact evaluation and is never used for selection.

- Detailed risk-aware summary: results/figures/risk_aware_selection_summary.md
