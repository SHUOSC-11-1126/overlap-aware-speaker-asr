# Project State

This document is for future Codex / AI coding agents so they can resume work without losing project context.

## Current Project Title

**When Should We Separate? Boundary-aware, Compute-aware, Speaker-aware, and Agent-augmented ASR for Overlapping Speech**

## Teacher Feedback and Direction Shift

- The core technical baseline is complete.
- Future agents are encouraged to explore the frontier, not just maintain the baseline.
- The project direction has therefore shifted from a maintenance-only mindset to a stable baseline + ambitious frontier exploration mindset.
- The stable baseline remains preserved.
- Future agents may explore phase diagrams, compute-aware cascades, voiceprint ideas, LLM critic loops, external mini validation, and demo excellence.

## Completed Stages

- Stage 1 project skeleton
- mixed Whisper baseline
- separated speaker-track ASR
- duplicate suppression
- 5 verified gold references
- global CER
- error type analysis
- adaptive router v1
- adaptive router v2
- router ablation
- synthetic silver benchmark
- synthetic silver evaluation
- held-out synthetic split validation
- speaker-aware CER
- cpCER-lite
- risk-aware selector
- project context docs
- docs index
- markdown audit
- skills cards
- roadmap
- maintenance harness
- contribution records
- handoff notes
- backup plan
- ambitious research agenda
- challenge board
- experiment proposal template
- experimental compute-aware cascade analysis

## Current Core Findings

1. Speech separation is useful but not universally beneficial.
2. `NoOverlap`, `HeavyOverlap`, and `OppositeOverlap` benefit strongly from separated speaker-track ASR.
3. `LightOverlap` and `MidOverlap` degradation is mainly caused by insertion and repetition hallucination.
4. Speaker swap is not the dominant error source in the five gold cases.
5. Overlap-only router v1 performs perfectly on gold but fails on synthetic silver validation.
6. Feature-based router v2 improves robustness using repetition and duplicate-removal signals.
7. Risk-aware selector is a deployability and explainability layer, not the best-CER result.
8. Synthetic benchmarks are silver robustness validation, not gold evaluation.
9. LLM/RAG is optional future extension, not the current core quantitative contribution.
10. The compute-aware cascade is an experimental/frontier cost analysis layer; it evaluates route cost after reference-free decisions are fixed and does not use CER as a routing input.

## Gold Benchmark Final CER Table

### NoOverlap

- `mixed_whisper: 0.215827`
- `separated_whisper: 0.053957`
- `separated_whisper_cleaned: 0.089928`
- `best: separated_whisper`

### LightOverlap

- `mixed_whisper: 0.210714`
- `separated_whisper: 0.475000`
- `separated_whisper_cleaned: 0.382143`
- `best: mixed_whisper`

### MidOverlap

- `mixed_whisper: 0.178947`
- `separated_whisper: 0.273684`
- `separated_whisper_cleaned: 0.207018`
- `best: mixed_whisper`

### HeavyOverlap

- `mixed_whisper: 0.386861`
- `separated_whisper: 0.109489`
- `separated_whisper_cleaned: 0.145985`
- `best: separated_whisper`

### OppositeOverlap

- `mixed_whisper: 0.518116`
- `separated_whisper: 0.047101`
- `separated_whisper_cleaned: 0.083333`
- `best: separated_whisper`

### Averages

- `fixed mixed: 0.302093`
- `fixed separated: 0.191846`
- `fixed cleaned: 0.181681`
- `router_v2: 0.120042`
- `oracle best: 0.120042`

## Synthetic Findings

### Original 25 synthetic silver

- `v1: 0.350902`
- `v2: 0.167553`
- `oracle: 0.082239`

### Held-out synthetic test

- `v1: 0.361350`
- `v2: 0.335326`
- `oracle: 0.115181`

### Interpretation

- `v2` improves stability but still has a gap to oracle.
- Improvement mainly comes from `SyntheticNoOverlap`.
- Synthetic results are silver robustness evidence, not gold evaluation.

## Speaker-Aware Findings

### speaker_macro_cer

- `NoOverlap separated: 0.054312, cleaned: 0.089278`
- `LightOverlap separated: 0.194170, cleaned: 0.135164`
- `MidOverlap separated: 0.175908, cleaned: 0.168620`
- `HeavyOverlap separated: 0.110821, cleaned: 0.146535`
- `OppositeOverlap separated: 0.047479, cleaned: 0.083193`

## cpCER-lite Findings

- No obvious speaker permutation mismatch.
- `speaker_assignment_gap = 0.0` for all five gold cases.
- Main errors are content-level, not speaker-swap-level.

## Risk-Aware Selector Findings

- `NoOverlap -> separated_whisper`
- `LightOverlap -> mixed_whisper`
- `MidOverlap -> mixed_whisper`
- `HeavyOverlap -> separated_whisper_cleaned`
- `OppositeOverlap -> separated_whisper_cleaned`

### Averages

- `risk_aware_selector: 0.134587`
- `router_v2: 0.120042`
- `oracle_best: 0.120042`

## Experimental Compute-Aware Cascade Findings

Label: `experimental/frontier`

- `router_v2_costed: average_cer 0.120042, relative_cost_vs_fixed_separated 0.929533`
- `risk_aware_costed: average_cer 0.134587, relative_cost_vs_fixed_separated 0.929533`
- `budget_cascade: average_cer 0.134587, relative_cost_vs_fixed_separated 0.929533`

Outputs:

- `results/tables/cascade_performance.csv`
- `results/figures/compute_aware_cascade_summary.md`
- `results/figures/cer_runtime_tradeoff.png`

Interpretation:

- This is an offline costed analysis of the five gold cases.
- It uses observed runtime fields when available and deterministic proxy costs otherwise.
- CER is reserved for post-decision evaluation only.

Runtime provenance audit:

- `results/tables/cascade_runtime_audit.csv`
- `results/figures/cascade_runtime_audit.md`
- Current committed gold cascade outputs use observed runtime for all `5/5` selections in every reported strategy.
- The proxy cost model remains a guardrail for missing-runtime edge cases rather than an active source in the current gold result tables.

Runtime normalization audit:

- `results/tables/cascade_runtime_normalization.csv`
- `results/figures/cascade_runtime_normalization.md`
- Gold `router_v2_costed`, `risk_aware_costed`, and `budget_cascade` all show `average_rtf 0.080646` when normalized by selected-route processed audio duration.
- This RTF is not a wall-clock latency claim; separated routes divide by two-stream processed duration.

## Synthetic Split Cascade Validation

Label: `synthetic/silver` and `experimental/frontier`

- `router_v2_synthetic_costed: average_cer 0.285187, relative_cost_vs_fixed_separated 0.704888`
- `budget_cascade: average_cer 0.367582, relative_cost_vs_fixed_separated 0.854921`
- `cleaned_preferred_cascade: average_cer 0.249877, relative_cost_vs_fixed_separated 0.945686`

Outputs:

- `results/tables/synthetic_split_cascade_performance.csv`
- `results/figures/synthetic_split_cascade_summary.md`
- `results/figures/synthetic_split_cer_runtime_tradeoff.png`

Interpretation:

- This is a held-out silver validation layer on top of the existing synthetic split benchmark.
- `cleaned_preferred_cascade` improves CER over `router_v2_synthetic_costed`, but spends more compute.
- `budget_cascade` is cheaper than always separated, but loses too much CER on the synthetic split benchmark.
- Silver validation remains separate from gold benchmark claims.

Runtime provenance audit:

- `results/tables/synthetic_split_cascade_runtime_audit.csv`
- `results/figures/synthetic_split_cascade_runtime_audit.md`
- Current committed synthetic split cascade outputs use observed runtime for all `100/100` `ALL` selections and all `50/50` selections in both `DEV` and `TEST`.
- The proxy cost model remains available for missing-runtime future experiments, but it is not active in the current synthetic split tables.

Runtime normalization audit:

- `results/tables/synthetic_split_cascade_runtime_normalization.csv`
- `results/figures/synthetic_split_cascade_runtime_normalization.md`
- `router_v2_synthetic_costed: average_rtf 0.148342`
- `budget_cascade: average_rtf 0.148228`
- `cleaned_preferred_cascade: average_rtf 0.156245`
- These values are normalized by selected-route processed audio duration, not by a single mixed-stream wall-clock target.

## What Should Happen Next

The next stage is not another maintenance loop. It should focus on:

- final REPORT.md polish
- README polish
- Streamlit demo
- presentation / video script
- contribution / maintenance clarity
- ambitious exploration docs
- experimental frontier work

## How to Resume Work

Common commands:

```powershell
python -m src.adaptive_router_v2
python -m src.evaluate_error_types --case all
python -m src.evaluate_speaker_cer --case all
python -m src.evaluate_cpcer_lite --case all
python -m src.risk_aware_selector --case all
python -m src.compute_aware_cascade
python -m src.compute_aware_cascade --dataset synthetic_split
python -m src.router_ablation
python -m src.router_ablation_split
python -m src.project_harness
```

## Notes for Future Agents

- Do not use ground-truth CER or reference transcripts as routing input.
- References and CER are for evaluation only.
- Keep gold and synthetic evaluation clearly separated.
- Prefer adding new outputs over overwriting existing benchmark files.
- If a new stage changes the main conclusion, update README and REPORT together.
