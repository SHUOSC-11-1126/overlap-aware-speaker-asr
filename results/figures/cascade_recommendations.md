# Cascade Recommendation Card

This card recommends strategies for different deployment preferences using the current cascade audits.

## gold / ALL

| profile | recommended_strategy | average_cer | average_compute_cost | average_rtf | reason |
| --- | --- | ---: | ---: | ---: | --- |
| accuracy_first | router_v2_costed | 0.120042 | 5.5508 | 0.080646 | Lowest average CER; ties break toward lower compute cost. |
| cost_first | fixed_mixed_whisper | 0.302093 | 5.2198 | 0.109309 | Lowest average compute cost; ties break toward lower CER. |
| balanced | router_v2_costed | 0.120042 | 5.5508 | 0.080646 | Chosen from the Pareto frontier by the smallest normalized CER+compute distance to the ideal point. |

