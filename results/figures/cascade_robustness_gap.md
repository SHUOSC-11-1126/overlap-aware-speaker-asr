# Cascade Robustness Gap Audit

This audit compares gold ALL against synthetic split ALL for shared strategy names.

| strategy | gold_average_cer | synthetic_average_cer | cer_gap_vs_gold | gold_average_compute_cost | synthetic_average_compute_cost | cost_gap_vs_gold | gold_average_rtf | synthetic_average_rtf | rtf_gap_vs_gold | robustness_rank |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed_separated_whisper_cleaned | 0.181681 | 0.179021 | -0.00266 | 5.9716 | 1.10836 | -4.86324 | 0.064251 | 0.133284 | 0.069033 | 1 |
| fixed_mixed_whisper | 0.302093 | 0.465715 | 0.163622 | 5.2198 | 0.674 | -4.5458 | 0.109309 | 0.163361 | 0.054052 | 2 |
| router_v2 | 0.120042 | 0.285187 | 0.165145 | 5.5508 | 0.78127 | -4.76953 | 0.080646 | 0.148342 | 0.067696 | 3 |
| fixed_separated_whisper | 0.191846 | 0.401869 | 0.210023 | 5.9716 | 1.10836 | -4.86324 | 0.064251 | 0.133284 | 0.069033 | 4 |
| budget_cascade | 0.134587 | 0.367582 | 0.232995 | 5.5508 | 0.94756 | -4.60324 | 0.080646 | 0.148228 | 0.067582 | 5 |
