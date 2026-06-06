# Cascade Pareto Frontier Audit

This audit marks which strategies are on the CER/compute Pareto frontier and which are dominated.

## gold / ALL

| strategy | average_cer | average_compute_cost | average_rtf | pareto_status | dominated_by |
| --- | ---: | ---: | ---: | --- | --- |
| fixed_mixed_whisper | 0.302093 | 5.2198 | 0.109309 | frontier |  |
| fixed_separated_whisper | 0.191846 | 5.9716 | 0.064251 | dominated | fixed_separated_whisper_cleaned |
| fixed_separated_whisper_cleaned | 0.181681 | 5.9716 | 0.064251 | dominated | router_v2_costed |
| router_v2_costed | 0.120042 | 5.5508 | 0.080646 | frontier |  |
| risk_aware_costed | 0.134587 | 5.5508 | 0.080646 | dominated | router_v2_costed |
| budget_cascade | 0.134587 | 5.5508 | 0.080646 | dominated | router_v2_costed |

