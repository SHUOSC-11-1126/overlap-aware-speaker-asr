# Compute-aware Cascade Frontier Report

This report consolidates the current compute-aware cascade decision evidence into one generated note.

## Decision Matrix

| profile | gold_recommended_strategy | synthetic_all_recommended_strategy | family_most_common_strategy | family_consensus_ratio | synthetic_all_average_cer | robustness_rank |
| --- | --- | --- | --- | ---: | ---: | ---: |
| accuracy_first | router_v2_costed | fixed_separated_whisper_cleaned | fixed_separated_whisper_cleaned | 0.75 | 0.179021 | 1 |
| balanced | router_v2_costed | router_v2_synthetic_costed | router_v2 | 1.0 | 0.285187 | 3 |
| cost_first | fixed_mixed_whisper | fixed_mixed_whisper | fixed_mixed_whisper | 1.0 | 0.465715 | 2 |

## Stability Highlights

- `accuracy_first`: most common family `fixed_separated_whisper_cleaned`, consensus `0.75`
- `balanced`: most common family `router_v2`, consensus `1.0`
- `cost_first`: most common family `fixed_mixed_whisper`, consensus `1.0`

## Robustness Highlights

- rank 1: `fixed_separated_whisper_cleaned` with `cer_gap_vs_gold -0.00266`
- rank 2: `fixed_mixed_whisper` with `cer_gap_vs_gold 0.163622`
- rank 3: `router_v2` with `cer_gap_vs_gold 0.165145`
