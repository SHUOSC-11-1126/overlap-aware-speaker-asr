# Roadmap

## Current Status

The core technical work is complete. The repository now has a stable baseline and a clear path toward more ambitious agentic exploration.

## Phase 0: Stable Baseline Completed

- Gold benchmark and references
- ASR baselines
- Post-processing
- Evaluation
- Adaptive routing
- Synthetic validation
- Risk-aware selection
- Documentation and maintenance structure

## Phase 1: Final Packaging

- Final REPORT.md
- Final README.md
- Contribution records
- Handoff notes
- Backup plan

## Phase 2: Boundary Exploration

- Separation phase diagram
- error boundary analysis
- overlap regime exploration

## Phase 3: Compute-aware Cascade

- cheap route vs stronger route
- runtime-aware selection
- risk-triggered repair tiers

Status: an initial `experimental/frontier` offline cascade analysis now exists.

- Script: `python -m src.compute_aware_cascade`
- Table: `results/tables/cascade_performance.csv`
- Summary: `results/figures/compute_aware_cascade_summary.md`
- Figure: `results/figures/cer_runtime_tradeoff.png`

Update: synthetic split cascade validation now exists as `synthetic/silver` frontier evidence.

- Script: `python -m src.compute_aware_cascade --dataset synthetic_split`
- Table: `results/tables/synthetic_split_cascade_performance.csv`
- Summary: `results/figures/synthetic_split_cascade_summary.md`
- Figure: `results/figures/synthetic_split_cer_runtime_tradeoff.png`

Update: runtime provenance audit now makes the cost source explicit.

- Gold audit: `results/tables/cascade_runtime_audit.csv`
- Synthetic split audit: `results/tables/synthetic_split_cascade_runtime_audit.csv`
- Current committed cascade outputs are fully backed by observed runtime fields; proxy cost remains a fallback for future incomplete-runtime experiments.

Update: runtime normalization audit now makes route-specific RTF explicit.

- Gold normalization: `results/tables/cascade_runtime_normalization.csv`
- Synthetic split normalization: `results/tables/synthetic_split_cascade_runtime_normalization.csv`
- The current audit uses selected-route processed audio duration, which is a stronger compute-normalized signal than raw runtime alone but still not a hardware-controlled benchmark.

Update: Pareto frontier audit now makes dominated strategies explicit.

- Gold Pareto audit: `results/tables/cascade_pareto.csv`
- Synthetic split Pareto audit: `results/tables/synthetic_split_cascade_pareto.csv`
- Current evidence suggests `router_v2_costed` dominates the other adaptive gold cascades, while synthetic split still leaves multiple meaningful frontier options.

Update: recommendation cards now turn the audits into deployment-facing choices.

- Gold recommendation card: `results/tables/cascade_recommendations.csv`
- Synthetic split recommendation card: `results/tables/synthetic_split_cascade_recommendations.csv`
- Current evidence recommends `router_v2_costed` as the gold balanced choice and `router_v2_synthetic_costed` as the synthetic split balanced choice.

Update: robustness gap audit now compares gold and held-out synthetic split directly.

- Cross-dataset gap audit: `results/tables/cascade_robustness_gap.csv`
- Current evidence suggests `router_v2` is the strongest shared adaptive route, while `budget_cascade` is less robust on held-out synthetic split.

Remaining stretch work:

- replace proxy costs with a controlled hardware/runtime benchmark
- evaluate a true stronger-model fallback when compute budget allows

## Phase 4: Speaker Profile / Voiceprint

- known-speaker enrollment
- speaker attribution risk detection
- contaminated track detection

## Phase 5: Agentic LLM Critic and Repair

- transcript critique
- repair suggestion loops
- uncertainty-aware review

## Phase 6: External Mini Validation

- small sanity check on an external dataset
- license/source documented
- gold/silver separation preserved

## Phase 7: Demo and Public-facing GitHub Excellence

- Streamlit demo
- presentation / video polish
- architecture diagrams
- onboarding clarity

## Healthy Project Principles

- New experiments should be isolated.
- Stable results should not be overwritten.
- Gold / silver / experimental / demo labels must be clear.
- Every ambitious module needs an owner and output path.
