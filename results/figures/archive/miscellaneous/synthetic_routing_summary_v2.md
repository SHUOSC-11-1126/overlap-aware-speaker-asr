# Synthetic Routing Stability Summary v2

This silver validation confirms whether the feature router reduces the NoOverlap failure seen in v1.

## Overall Average CER

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.311442 | 25 |
| fixed_separated_whisper | 0.380701 | 25 |
| fixed_separated_whisper_cleaned | 0.203778 | 25 |
| oracle_best | 0.082239 | 25 |
| rule_router_v1 | 0.350902 | 25 |
| feature_router_v2 | 0.167553 | 25 |

## Tier Breakdown

### SyntheticHeavyOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.455293 | 5 |
| fixed_separated_whisper | 0.26253 | 5 |
| fixed_separated_whisper_cleaned | 0.26253 | 5 |
| oracle_best | 0.116376 | 5 |
| rule_router_v1 | 0.26253 | 5 |
| feature_router_v2 | 0.26253 | 5 |

### SyntheticLightOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.118353 | 5 |
| fixed_separated_whisper | 0.214838 | 5 |
| fixed_separated_whisper_cleaned | 0.214838 | 5 |
| oracle_best | 0.060991 | 5 |
| rule_router_v1 | 0.118353 | 5 |
| feature_router_v2 | 0.118353 | 5 |

### SyntheticMidOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.210019 | 5 |
| fixed_separated_whisper | 0.26253 | 5 |
| fixed_separated_whisper_cleaned | 0.26253 | 5 |
| oracle_best | 0.100991 | 5 |
| rule_router_v1 | 0.210019 | 5 |
| feature_router_v2 | 0.210019 | 5 |

### SyntheticNoOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.185019 | 5 |
| fixed_separated_whisper | 1.101761 | 5 |
| fixed_separated_whisper_cleaned | 0.217145 | 5 |
| oracle_best | 0.070991 | 5 |
| rule_router_v1 | 1.101761 | 5 |
| feature_router_v2 | 0.185019 | 5 |

### SyntheticOppositeOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.588526 | 5 |
| fixed_separated_whisper | 0.061846 | 5 |
| fixed_separated_whisper_cleaned | 0.061846 | 5 |
| oracle_best | 0.061846 | 5 |
| rule_router_v1 | 0.061846 | 5 |
| feature_router_v2 | 0.061846 | 5 |
