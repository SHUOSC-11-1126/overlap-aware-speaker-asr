# Compute-aware Cascade Summary

## Label

- experimental/frontier

## Interpretation

- This is an offline costed analysis of existing gold benchmark outputs.
- Route selection uses overlap, risk, and existing reference-free router decisions.
- CER is used only after each strategy has fixed its selected method.
- Compute cost uses observed runtime fields when available and deterministic proxy costs otherwise.

## Performance

| strategy | average_cer | average_compute_cost | relative_cost_vs_fixed_separated | coverage | method_mix |
| --- | ---: | ---: | ---: | ---: | --- |
| fixed_mixed_whisper | 0.302093 | 5.2198 | 0.874104 | 1.0 | mixed_whisper:5 |
| fixed_separated_whisper | 0.191846 | 5.9716 | 1.0 | 1.0 | separated_whisper:5 |
| fixed_separated_whisper_cleaned | 0.181681 | 5.9716 | 1.0 | 1.0 | separated_whisper_cleaned:5 |
| router_v2_costed | 0.120042 | 5.5508 | 0.929533 | 1.0 | mixed_whisper:2;separated_whisper:3 |
| risk_aware_costed | 0.134587 | 5.5508 | 0.929533 | 1.0 | mixed_whisper:2;separated_whisper:1;separated_whisper_cleaned:2 |
| budget_cascade | 0.134587 | 5.5508 | 0.929533 | 1.0 | mixed_whisper:2;separated_whisper:1;separated_whisper_cleaned:2 |

## Outputs

- Table: `results/tables/cascade_performance.csv`
- Figure: `results/figures/cer_runtime_tradeoff.png`

## Caution

The runtime values are useful for comparing routes inside this repository, but they are not a universal hardware benchmark.
