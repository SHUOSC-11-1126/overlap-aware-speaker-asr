# Router Ablation Summary - Synthetic Split

This analysis compares feature subsets for the rule-based router on the held-out synthetic split benchmark.
The dev split is available for inspection, but the test split is not used to tune any thresholds.

## ALL

| strategy | average_cer | gap_to_oracle | sample_count | notes |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.465715 | 0.353887 | 100 | Ablation strategy. |
| fixed_separated_whisper | 0.401869 | 0.290041 | 100 | Ablation strategy. |
| fixed_separated_whisper_cleaned | 0.179021 | 0.067193 | 100 | Ablation strategy. |
| oracle_best | 0.111828 | 0.0 | 100 | Oracle upper bound only; not deployable. |
| v1_overlap_only | 0.390725 | 0.278897 | 100 | v1 overlap-only baseline. |
| length_ratio_only | 0.41636 | 0.304532 | 100 | Ablation strategy. |
| repetition_only | 0.249877 | 0.138049 | 100 | Ablation strategy. |
| removed_count_only | 0.249877 | 0.138049 | 100 | Ablation strategy. |
| length_plus_repetition | 0.43621 | 0.324382 | 100 | Ablation strategy. |
| v2_full_features | 0.285187 | 0.173359 | 100 | Full feature router v2. |

## DEV

| strategy | average_cer | gap_to_oracle | sample_count | notes |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.4867 | 0.378224 | 50 | Ablation strategy. |
| fixed_separated_whisper | 0.367072 | 0.258596 | 50 | Ablation strategy. |
| fixed_separated_whisper_cleaned | 0.172804 | 0.064328 | 50 | Ablation strategy. |
| oracle_best | 0.108476 | 0.0 | 50 | Oracle upper bound only; not deployable. |
| v1_overlap_only | 0.4201 | 0.311624 | 50 | v1 overlap-only baseline. |
| length_ratio_only | 0.38799 | 0.279514 | 50 | Ablation strategy. |
| repetition_only | 0.225832 | 0.117356 | 50 | Ablation strategy. |
| removed_count_only | 0.225832 | 0.117356 | 50 | Ablation strategy. |
| length_plus_repetition | 0.408834 | 0.300358 | 50 | Ablation strategy. |
| v2_full_features | 0.235049 | 0.126573 | 50 | Full feature router v2. |

## TEST

| strategy | average_cer | gap_to_oracle | sample_count | notes |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.44473 | 0.329549 | 50 | Ablation strategy. |
| fixed_separated_whisper | 0.436666 | 0.321485 | 50 | Ablation strategy. |
| fixed_separated_whisper_cleaned | 0.185238 | 0.070057 | 50 | Ablation strategy. |
| oracle_best | 0.115181 | 0.0 | 50 | Oracle upper bound only; not deployable. |
| v1_overlap_only | 0.36135 | 0.246169 | 50 | v1 overlap-only baseline. |
| length_ratio_only | 0.44473 | 0.329549 | 50 | Ablation strategy. |
| repetition_only | 0.273921 | 0.15874 | 50 | Ablation strategy. |
| removed_count_only | 0.273921 | 0.15874 | 50 | Ablation strategy. |
| length_plus_repetition | 0.463587 | 0.348406 | 50 | Ablation strategy. |
| v2_full_features | 0.335326 | 0.220145 | 50 | Full feature router v2. |

## SyntheticHeavyOverlap

| strategy | average_cer | gap_to_oracle | sample_count | notes |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.740711 | 0.610813 | 20 | Ablation strategy. |
| fixed_separated_whisper | 0.288975 | 0.159077 | 20 | Ablation strategy. |
| fixed_separated_whisper_cleaned | 0.173261 | 0.043363 | 20 | Ablation strategy. |
| oracle_best | 0.129898 | 0.0 | 20 | Oracle upper bound only; not deployable. |
| v1_overlap_only | 0.288975 | 0.159077 | 20 | v1 overlap-only baseline. |
| length_ratio_only | 0.493937 | 0.364039 | 20 | Ablation strategy. |
| repetition_only | 0.173261 | 0.043363 | 20 | Ablation strategy. |
| removed_count_only | 0.173261 | 0.043363 | 20 | Ablation strategy. |
| length_plus_repetition | 0.498222 | 0.368324 | 20 | Ablation strategy. |
| v2_full_features | 0.288975 | 0.159077 | 20 | Full feature router v2. |

## SyntheticLightOverlap

| strategy | average_cer | gap_to_oracle | sample_count | notes |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.26131 | 0.198201 | 20 | Ablation strategy. |
| fixed_separated_whisper | 0.346618 | 0.283509 | 20 | Ablation strategy. |
| fixed_separated_whisper_cleaned | 0.163761 | 0.100652 | 20 | Ablation strategy. |
| oracle_best | 0.063109 | 0.0 | 20 | Oracle upper bound only; not deployable. |
| v1_overlap_only | 0.26131 | 0.198201 | 20 | v1 overlap-only baseline. |
| length_ratio_only | 0.26131 | 0.198201 | 20 | Ablation strategy. |
| repetition_only | 0.282738 | 0.219629 | 20 | Ablation strategy. |
| removed_count_only | 0.282738 | 0.219629 | 20 | Ablation strategy. |
| length_plus_repetition | 0.282738 | 0.219629 | 20 | Ablation strategy. |
| v2_full_features | 0.26131 | 0.198201 | 20 | Full feature router v2. |

## SyntheticMidOverlap

| strategy | average_cer | gap_to_oracle | sample_count | notes |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.405127 | 0.296724 | 20 | Ablation strategy. |
| fixed_separated_whisper | 0.375541 | 0.267138 | 20 | Ablation strategy. |
| fixed_separated_whisper_cleaned | 0.179826 | 0.071423 | 20 | Ablation strategy. |
| oracle_best | 0.108403 | 0.0 | 20 | Oracle upper bound only; not deployable. |
| v1_overlap_only | 0.405127 | 0.296724 | 20 | v1 overlap-only baseline. |
| length_ratio_only | 0.405127 | 0.296724 | 20 | Ablation strategy. |
| repetition_only | 0.415127 | 0.306724 | 20 | Ablation strategy. |
| removed_count_only | 0.415127 | 0.306724 | 20 | Ablation strategy. |
| length_plus_repetition | 0.415127 | 0.306724 | 20 | Ablation strategy. |
| v2_full_features | 0.405127 | 0.296724 | 20 | Full feature router v2. |

## SyntheticNoOverlap

| strategy | average_cer | gap_to_oracle | sample_count | notes |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.298837 | 0.198948 | 20 | Ablation strategy. |
| fixed_separated_whisper | 0.826526 | 0.726637 | 20 | Ablation strategy. |
| fixed_separated_whisper_cleaned | 0.20657 | 0.106681 | 20 | Ablation strategy. |
| oracle_best | 0.099889 | 0.0 | 20 | Oracle upper bound only; not deployable. |
| v1_overlap_only | 0.826526 | 0.726637 | 20 | v1 overlap-only baseline. |
| length_ratio_only | 0.298837 | 0.198948 | 20 | Ablation strategy. |
| repetition_only | 0.20657 | 0.106681 | 20 | Ablation strategy. |
| removed_count_only | 0.20657 | 0.106681 | 20 | Ablation strategy. |
| length_plus_repetition | 0.362375 | 0.262486 | 20 | Ablation strategy. |
| v2_full_features | 0.298837 | 0.198948 | 20 | Full feature router v2. |

## SyntheticOppositeOverlap

| strategy | average_cer | gap_to_oracle | sample_count | notes |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.622589 | 0.464748 | 20 | Ablation strategy. |
| fixed_separated_whisper | 0.171687 | 0.013846 | 20 | Ablation strategy. |
| fixed_separated_whisper_cleaned | 0.171687 | 0.013846 | 20 | Ablation strategy. |
| oracle_best | 0.157841 | 0.0 | 20 | Oracle upper bound only; not deployable. |
| v1_overlap_only | 0.171687 | 0.013846 | 20 | v1 overlap-only baseline. |
| length_ratio_only | 0.622589 | 0.464748 | 20 | Ablation strategy. |
| repetition_only | 0.171687 | 0.013846 | 20 | Ablation strategy. |
| removed_count_only | 0.171687 | 0.013846 | 20 | Ablation strategy. |
| length_plus_repetition | 0.622589 | 0.464748 | 20 | Ablation strategy. |
| v2_full_features | 0.171687 | 0.013846 | 20 | Full feature router v2. |
