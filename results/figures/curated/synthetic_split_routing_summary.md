# Synthetic Routing Stability Summary

This is a stability check based on silver references built from snippet Whisper transcriptions.
The test split is held out from any router tuning.

## Average CER by Scope

### ALL

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.465715 | 100 |
| fixed_separated_whisper | 0.401869 | 100 |
| fixed_separated_whisper_cleaned | 0.179021 | 100 |
| oracle_best | 0.111828 | 100 |
| v1_overlap_only | 0.390725 | 100 |
| v2_full_features | 0.285187 | 100 |

### DEV

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.4867 | 50 |
| fixed_separated_whisper | 0.367072 | 50 |
| fixed_separated_whisper_cleaned | 0.172804 | 50 |
| oracle_best | 0.108476 | 50 |
| v1_overlap_only | 0.4201 | 50 |
| v2_full_features | 0.235049 | 50 |

### TEST

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.44473 | 50 |
| fixed_separated_whisper | 0.436666 | 50 |
| fixed_separated_whisper_cleaned | 0.185238 | 50 |
| oracle_best | 0.115181 | 50 |
| v1_overlap_only | 0.36135 | 50 |
| v2_full_features | 0.335326 | 50 |

## Tier Breakdown

### SyntheticHeavyOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.740711 | 20 |
| fixed_separated_whisper | 0.288975 | 20 |
| fixed_separated_whisper_cleaned | 0.173261 | 20 |
| oracle_best | 0.129898 | 20 |
| v1_overlap_only | 0.288975 | 20 |
| v2_full_features | 0.288975 | 20 |

### SyntheticLightOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.26131 | 20 |
| fixed_separated_whisper | 0.346618 | 20 |
| fixed_separated_whisper_cleaned | 0.163761 | 20 |
| oracle_best | 0.063109 | 20 |
| v1_overlap_only | 0.26131 | 20 |
| v2_full_features | 0.26131 | 20 |

### SyntheticMidOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.405127 | 20 |
| fixed_separated_whisper | 0.375541 | 20 |
| fixed_separated_whisper_cleaned | 0.179826 | 20 |
| oracle_best | 0.108403 | 20 |
| v1_overlap_only | 0.405127 | 20 |
| v2_full_features | 0.405127 | 20 |

### SyntheticNoOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.298837 | 20 |
| fixed_separated_whisper | 0.826526 | 20 |
| fixed_separated_whisper_cleaned | 0.20657 | 20 |
| oracle_best | 0.099889 | 20 |
| v1_overlap_only | 0.826526 | 20 |
| v2_full_features | 0.298837 | 20 |

### SyntheticOppositeOverlap

| strategy | average_cer | sample_count |
| --- | ---: | ---: |
| fixed_mixed_whisper | 0.622589 | 20 |
| fixed_separated_whisper | 0.171687 | 20 |
| fixed_separated_whisper_cleaned | 0.171687 | 20 |
| oracle_best | 0.157841 | 20 |
| v1_overlap_only | 0.171687 | 20 |
| v2_full_features | 0.171687 | 20 |
