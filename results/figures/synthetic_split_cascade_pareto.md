# Cascade Pareto Frontier Audit

This audit marks which strategies are on the CER/compute Pareto frontier and which are dominated.

## synthetic_split / ALL

| strategy | average_cer | average_compute_cost | average_rtf | pareto_status | dominated_by |
| --- | ---: | ---: | ---: | --- | --- |
| fixed_mixed_whisper | 0.465715 | 0.674 | 0.163361 | frontier |  |
| fixed_separated_whisper | 0.401869 | 1.10836 | 0.133284 | dominated | fixed_separated_whisper_cleaned |
| fixed_separated_whisper_cleaned | 0.179021 | 1.10836 | 0.133284 | frontier |  |
| router_v2_synthetic_costed | 0.285187 | 0.78127 | 0.148342 | frontier |  |
| budget_cascade | 0.367582 | 0.94756 | 0.148228 | dominated | router_v2_synthetic_costed |
| cleaned_preferred_cascade | 0.249877 | 1.04816 | 0.156245 | frontier |  |

## synthetic_split / DEV

| strategy | average_cer | average_compute_cost | average_rtf | pareto_status | dominated_by |
| --- | ---: | ---: | ---: | --- | --- |
| fixed_mixed_whisper | 0.4867 | 0.74366 | 0.17536 | frontier |  |
| fixed_separated_whisper | 0.367072 | 1.01176 | 0.122603 | dominated | fixed_separated_whisper_cleaned |
| fixed_separated_whisper_cleaned | 0.172804 | 1.01176 | 0.122603 | frontier |  |
| router_v2_synthetic_costed | 0.235049 | 0.76668 | 0.148484 | frontier |  |
| budget_cascade | 0.4201 | 0.97074 | 0.151484 | dominated | router_v2_synthetic_costed |
| cleaned_preferred_cascade | 0.225832 | 0.97074 | 0.151484 | frontier |  |

## synthetic_split / TEST

| strategy | average_cer | average_compute_cost | average_rtf | pareto_status | dominated_by |
| --- | ---: | ---: | ---: | --- | --- |
| fixed_mixed_whisper | 0.44473 | 0.60434 | 0.151362 | frontier |  |
| fixed_separated_whisper | 0.436666 | 1.20496 | 0.143966 | dominated | fixed_separated_whisper_cleaned |
| fixed_separated_whisper_cleaned | 0.185238 | 1.20496 | 0.143966 | frontier |  |
| router_v2_synthetic_costed | 0.335326 | 0.79586 | 0.148201 | frontier |  |
| budget_cascade | 0.315064 | 0.92438 | 0.144971 | frontier |  |
| cleaned_preferred_cascade | 0.273921 | 1.12558 | 0.161006 | frontier |  |

