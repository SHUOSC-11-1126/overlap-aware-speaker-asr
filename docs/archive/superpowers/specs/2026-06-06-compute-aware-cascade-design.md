# Compute-aware Cascaded Recognition Design

## Label

experimental/frontier

## Research Question

When should this ASR system spend more compute instead of always running the same recognition path?

## Hypothesis

A costed cascade can preserve most of the router v2 or risk-aware selector accuracy while reducing the average compute proxy relative to always using separated speaker-track ASR.

## Scope

This stage is an offline evaluation layer. It reuses existing gold benchmark outputs, router decisions, risk-aware decisions, CER tables, and recorded runtime fields. It does not rerun ASR, overwrite verified references, or tune routing rules with ground-truth CER.

## Inputs

- `results/tables/cer_results.csv`
- `results/tables/mixed_asr_benchmark.csv`
- `results/tables/separated_asr_benchmark.csv`
- `results/tables/routing_decisions_v2.csv`
- `results/tables/risk_aware_selection.csv`
- `configs/config.yaml`

## Cascade Strategies

- `fixed_mixed_whisper`: always choose the mixed transcript.
- `fixed_separated_whisper`: always choose the separated transcript.
- `fixed_separated_whisper_cleaned`: always choose the cleaned separated transcript.
- `router_v2_costed`: use the existing feature router v2 decision and score its cost.
- `risk_aware_costed`: use the existing risk-aware selector decision and score its cost.
- `budget_cascade`: start with mixed ASR and escalate only for low-overlap or high-overlap regimes where the existing reference-free project findings say separated ASR is usually useful.

## Cost Model

The preferred cost signal is measured runtime already stored in project result tables. If a runtime is missing, the script falls back to a deterministic proxy:

- `mixed_whisper`: 1.0
- `separated_whisper`: 2.0
- `separated_whisper_cleaned`: 2.1
- `manual_review`: 3.0

This is compute-aware analysis, not a hardware benchmark. The summary must state that runtime is an observed-or-proxy cost and should not be treated as a universal deployment number.

## Decision Safety

The cascade rules may use case metadata, overlap level, router decisions, risk levels, and observable transcript stability outputs. They must not use CER, reference transcripts, or oracle best methods when selecting a route. CER is used only after decisions are fixed to evaluate the trade-off.

## Outputs

- `src/compute_aware_cascade.py`
- `tests/test_compute_aware_cascade.py`
- `results/tables/cascade_performance.csv`
- `results/tables/cascade_performance.json`
- `results/figures/cer_runtime_tradeoff.png`
- `results/figures/compute_aware_cascade_summary.md`

## Metrics

- average CER
- average compute cost
- relative cost versus `fixed_separated_whisper`
- automatic coverage
- manual review count
- selected method mix

## Error Handling

Missing required input tables should raise `FileNotFoundError` with a repository-relative path. Missing optional runtime values should fall back to the proxy cost model. Unknown selected methods should be represented but excluded from CER aggregation unless they are `manual_review`, which counts as a manual-review decision without adding automatic CER.

## Testing

Unit tests cover the pure cascade helpers before production implementation:

- cost uses observed runtime when available and proxy cost when missing
- strategy aggregation does not inspect CER until after a selected method is fixed
- `budget_cascade` escalates only from overlap/risk signals
- manual review contributes to coverage and cost but not automatic CER

Integration verification runs:

- `python3 -m unittest tests.test_compute_aware_cascade -v`
- `python3 -m src.compute_aware_cascade`
- `python3 -m src.project_harness`

## Documentation Updates

Update `README.md`, `docs/project_state.md`, `docs/roadmap.md`, and `docs/README.md` so future agents can find the cascade output and understand that it is experimental/frontier, not a new stable gold claim.

