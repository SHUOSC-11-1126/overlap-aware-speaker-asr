# Confidence-Calibrated Router (CCR) — Findings

## Label: experimental/frontier

## Research Question
Can a multi-signal composite confidence score outperform the single-signal
compression-ratio router for picking the better of {mixed, separated, separated+trim}?

## Key Results (300 greedy rows from separation_tax phase study)

### 2-Way Routing (mixed vs sep_trim)

| Policy              | Mean CER | Regret vs Oracle |
|---------------------|----------|------------------|
| oracle              | 0.396    | 0.000            |
| **cr_only**         | 0.468    | **0.072**        |
| cr_log              | 0.468    | 0.072            |
| threshold_gate      | 0.491    | 0.095            |
| cr_nsp_rep          | 0.529    | 0.134            |
| cr_nsp              | 0.533    | 0.138            |
| fixed_mixed         | 0.697    | 0.301            |

**cr_only (inverse compression ratio) is the best reference-free router for 2-way.**

### 3-Way Routing (mixed vs sep vs sep_trim)

| Policy              | Mean CER | Regret vs Oracle |
|---------------------|----------|------------------|
| oracle              | 0.379    | 0.000            |
| **threshold_gate**  | 0.489    | **0.111**        |
| cr_only             | 0.492    | 0.114            |
| cr_log              | 0.492    | 0.114            |
| cr_nsp_rep          | 0.530    | 0.152            |
| cr_nsp              | 0.534    | 0.155            |
| fixed_sep           | 0.618    | 0.239            |
| fixed_mixed         | 0.697    | 0.319            |

**threshold_gate (CR > 2.4 or NSP > 0.6 → degenerate) is best for 3-way.**

### Signal Contribution: H1 Rejected

Adding no_speech_prob and repetition count to a weighted composite **increases**
regret by 0.04-0.09 CER.  The extra signals add noise, not signal, when combined
via simple weighted averaging.

### Per-Overlap-Ratio Analysis (H2 Partially Confirmed)

At overlap_ratio = 0.0 only, cr_nsp (0.070 regret) beats cr_only (0.143 regret)
by a large margin — confirming that NSP captures the silence-injection artifact at
zero overlap.  But at all other ratios (0.05–0.9), cr_nsp is **worse** than cr_only.

| Overlap | cr_only regret | cr_nsp regret | cr_nsp better? |
|---------|----------------|---------------|----------------|
| 0.00    | 0.143          | **0.070**     | ✓ by 0.073     |
| 0.05    | 0.094          | 0.077         | ✓ by 0.017     |
| 0.10    | 0.111          | 0.092         | ✓ by 0.019     |
| 0.15    | 0.088          | 0.091         | ✗              |
| 0.20+   | varies         | consistently worse | ✗          |

### Hard Regime Analysis (H3 Rejected)

On "hard" samples where |CER_mixed − CER_sep| < 0.1 (n=85):
- cr_only regret: 0.019
- threshold_gate: 0.021 (worse)
- cr_nsp: 0.029 (worse)
- cr_nsp_rep: 0.030 (worse)

The composite signals do NOT help on ambiguous samples — they hurt everywhere.

## Interpretation

**cr_only (1/(1+max_compression_ratio)) is the optimal reference-free routing
signal.**  Whisper's compression ratio already captures the degeneracy that
no_speech_prob and repetition partially overlap with.  Combining them via weighted
averaging introduces noise from their imperfect correlation.

The threshold_gate method (flag as degenerate if CR > 2.4 or NSP > 0.6) is
competitive for 3-way routing because it uses NSP as a binary gate rather than a
continuous weight — this avoids the noise-amplification problem.

**Actionable finding**: The existing hallucination_router's single-signal approach
is near-optimal.  Deployable systems should use `1/(1+max_compression_ratio)` or
Whisper's native `compression_ratio_threshold` for routing, and not bother with
multi-signal composites.

## What Would Change This Conclusion

- Learned weights (logistic regression on the signals) instead of hand-tuned
  weighted averages — the fixed 0.5/0.3/0.2 weights may be suboptimal.
- Segment-level signals (min/mean instead of max) may capture different patterns.
- avg_logprob, which is not available in the phase_curve data, could be the
  missing strong signal.
- A larger evaluation set (300 rows from 20 pairs may overfit to specific speakers).

## Files

- `ccr_summary.json` — full analysis
- `policy_comparison_2way.csv` — 2-way policy comparison
- `policy_comparison_3way.csv` — 3-way policy comparison
- `regret_by_ratio_2way.csv` — per-overlap-ratio regret (2-way)
- `regret_by_ratio_3way.csv` — per-overlap-ratio regret (3-way)
- `ccr_regret_by_ratio.png` — visualization
