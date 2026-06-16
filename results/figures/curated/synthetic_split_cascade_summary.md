# Synthetic Split Compute-aware Cascade Summary

## Label

- synthetic/silver
- experimental/frontier

## Interpretation

- This is a held-out synthetic split cascade validation using silver references.
- Route selection uses overlap, duplicate-removal signals, or existing reference-free router v2 decisions.
- CER is used only after each strategy has fixed its selected method.
- Runtime values come from existing synthetic routing tables and are repository-local cost signals only.

## ALL

| strategy | average_cer | average_compute_cost | relative_cost_vs_fixed_separated | method_mix |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.465715 | 0.674 | 0.608106 | mixed_whisper:100 |
| fixed_separated_whisper | 0.401869 | 1.10836 | 1.0 | separated_whisper:100 |
| fixed_separated_whisper_cleaned | 0.179021 | 1.10836 | 1.0 | separated_whisper_cleaned:100 |
| router_v2_synthetic_costed | 0.285187 | 0.78127 | 0.704888 | mixed_whisper:60;separated_whisper:40 |
| budget_cascade | 0.367582 | 0.94756 | 0.854921 | mixed_whisper:40;separated_whisper:20;separated_whisper_cleaned:40 |
| cleaned_preferred_cascade | 0.249877 | 1.04816 | 0.945686 | mixed_whisper:38;separated_whisper:17;separated_whisper_cleaned:45 |

## DEV

| strategy | average_cer | average_compute_cost | relative_cost_vs_fixed_separated | method_mix |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.4867 | 0.74366 | 0.735016 | mixed_whisper:50 |
| fixed_separated_whisper | 0.367072 | 1.01176 | 1.0 | separated_whisper:50 |
| fixed_separated_whisper_cleaned | 0.172804 | 1.01176 | 1.0 | separated_whisper_cleaned:50 |
| router_v2_synthetic_costed | 0.235049 | 0.76668 | 0.757769 | mixed_whisper:30;separated_whisper:20 |
| budget_cascade | 0.4201 | 0.97074 | 0.959457 | mixed_whisper:20;separated_whisper:10;separated_whisper_cleaned:20 |
| cleaned_preferred_cascade | 0.225832 | 0.97074 | 0.959457 | mixed_whisper:20;separated_whisper:8;separated_whisper_cleaned:22 |

## TEST

| strategy | average_cer | average_compute_cost | relative_cost_vs_fixed_separated | method_mix |
| --- | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.44473 | 0.60434 | 0.501544 | mixed_whisper:50 |
| fixed_separated_whisper | 0.436666 | 1.20496 | 1.0 | separated_whisper:50 |
| fixed_separated_whisper_cleaned | 0.185238 | 1.20496 | 1.0 | separated_whisper_cleaned:50 |
| router_v2_synthetic_costed | 0.335326 | 0.79586 | 0.660487 | mixed_whisper:30;separated_whisper:20 |
| budget_cascade | 0.315064 | 0.92438 | 0.767146 | mixed_whisper:20;separated_whisper:10;separated_whisper_cleaned:20 |
| cleaned_preferred_cascade | 0.273921 | 1.12558 | 0.934122 | mixed_whisper:18;separated_whisper:9;separated_whisper_cleaned:23 |

## Tier Breakdown

### SyntheticHeavyOverlap

| strategy | average_cer | average_compute_cost | sample_count |
| --- | ---: | ---: | ---: |
| fixed_mixed_whisper | 0.740711 | 0.7447 | 20 |
| fixed_separated_whisper | 0.288975 | 0.96445 | 20 |
| fixed_separated_whisper_cleaned | 0.173261 | 0.96445 | 20 |
| router_v2_synthetic_costed | 0.288975 | 0.96445 | 20 |
| budget_cascade | 0.173261 | 0.96445 | 20 |
| cleaned_preferred_cascade | 0.173261 | 0.96445 | 20 |

### SyntheticLightOverlap

| strategy | average_cer | average_compute_cost | sample_count |
| --- | ---: | ---: | ---: |
| fixed_mixed_whisper | 0.26131 | 0.77015 | 20 |
| fixed_separated_whisper | 0.346618 | 1.1859 | 20 |
| fixed_separated_whisper_cleaned | 0.163761 | 1.1859 | 20 |
| router_v2_synthetic_costed | 0.26131 | 0.77015 | 20 |
| budget_cascade | 0.26131 | 0.77015 | 20 |
| cleaned_preferred_cascade | 0.282738 | 1.03665 | 20 |

### SyntheticMidOverlap

| strategy | average_cer | average_compute_cost | sample_count |
| --- | ---: | ---: | ---: |
| fixed_mixed_whisper | 0.405127 | 0.63515 | 20 |
| fixed_separated_whisper | 0.375541 | 1.0234 | 20 |
| fixed_separated_whisper_cleaned | 0.179826 | 1.0234 | 20 |
| router_v2_synthetic_costed | 0.405127 | 0.63515 | 20 |
| budget_cascade | 0.405127 | 0.63515 | 20 |
| cleaned_preferred_cascade | 0.415127 | 0.87165 | 20 |

### SyntheticNoOverlap

| strategy | average_cer | average_compute_cost | sample_count |
| --- | ---: | ---: | ---: |
| fixed_mixed_whisper | 0.298837 | 0.7494 | 20 |
| fixed_separated_whisper | 0.826526 | 1.58085 | 20 |
| fixed_separated_whisper_cleaned | 0.20657 | 1.58085 | 20 |
| router_v2_synthetic_costed | 0.298837 | 0.7494 | 20 |
| budget_cascade | 0.826526 | 1.58085 | 20 |
| cleaned_preferred_cascade | 0.20657 | 1.58085 | 20 |

### SyntheticOppositeOverlap

| strategy | average_cer | average_compute_cost | sample_count |
| --- | ---: | ---: | ---: |
| fixed_mixed_whisper | 0.622588 | 0.4706 | 20 |
| fixed_separated_whisper | 0.171687 | 0.7872 | 20 |
| fixed_separated_whisper_cleaned | 0.171687 | 0.7872 | 20 |
| router_v2_synthetic_costed | 0.171687 | 0.7872 | 20 |
| budget_cascade | 0.171687 | 0.7872 | 20 |
| cleaned_preferred_cascade | 0.171687 | 0.7872 | 20 |

## Outputs

- Table: `results/tables/synthetic_split_cascade_performance.csv`
- Figure: `results/figures/synthetic_split_cer_runtime_tradeoff.png`

## Caution

These results are silver validation evidence and must not be promoted to gold benchmark claims.
