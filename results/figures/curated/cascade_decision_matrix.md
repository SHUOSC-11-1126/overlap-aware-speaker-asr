# Cascade Decision Matrix

This matrix consolidates recommendation, family-level stability, and shared robustness into one deployment-facing table.

| profile | gold_recommended_strategy | synthetic_all_recommended_strategy | family_most_common_strategy | family_consensus_ratio | synthetic_all_average_cer | synthetic_all_average_compute_cost | synthetic_all_average_rtf | robustness_rank | shared_cer_gap_vs_gold |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| accuracy_first | router_v2_costed | fixed_separated_whisper_cleaned | fixed_separated_whisper_cleaned | 0.75 | 0.179021 | 1.10836 | 0.133284 | 1 | -0.00266 |
| balanced | router_v2_costed | router_v2_synthetic_costed | router_v2 | 1.0 | 0.285187 | 0.78127 | 0.148342 | 3 | 0.165145 |
| cost_first | fixed_mixed_whisper | fixed_mixed_whisper | fixed_mixed_whisper | 1.0 | 0.465715 | 0.674 | 0.163361 | 2 | 0.163622 |
