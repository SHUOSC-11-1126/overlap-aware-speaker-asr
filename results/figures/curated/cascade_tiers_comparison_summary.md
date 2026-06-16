# Three-Tier Cascade — Strategy Comparison

**Label:** experimental/frontier

## CER vs Compute Cost Trade-off

| Strategy | Avg CER | Avg Cost | Auto Coverage | Method Mix |
|----------|---------|----------|---------------|------------|
| fixed_mixed_whisper | 0.3021 | 1.00 | 100.0% | mixed_whisper:5 |
| fixed_separated_whisper | 0.1918 | 2.00 | 100.0% | separated_whisper:5 |
| fixed_separated_whisper_cleaned | 0.1817 | 2.10 | 100.0% | separated_whisper_cleaned:5 |
| router_v2_baseline | 0.1200 | 1.60 | 100.0% | mixed_whisper:2;separated_whisper:3 |
| tiered_cascade_v1 | 0.1811 | 1.92 | 100.0% | mixed_whisper:1;separated_whisper:2;separated_whisper_cleane |

## Interpretation

- **fixed_mixed_whisper**: Cheapest, worst CER. Baseline cost floor.
- **fixed_separated_whisper**: Better CER than mixed, 2× cost.
- **fixed_separated_whisper_cleaned**: Marginally better CER than raw separated.
- **router_v2_baseline**: Single-tier adaptive routing using overlap + instability signals.
- **tiered_cascade_v1** (highlighted in chart): Three-tier cascade —
  escalates only unstable samples to stronger processing.

The goal is not the lowest possible CER but the best accuracy-cost balance.
The tiered cascade should ideally sit near the Pareto frontier —
meaningfully better CER than the cheap baseline without the full cost
of always running the expensive route.

## Notes

- All escalation decisions use ONLY reference-free observable signals.
- `stronger_model` represents a hypothetical larger ASR (e.g., whisper-medium).
- Manual review / LLM critic costs are modeled at 3.5–4.0× the cheap baseline.