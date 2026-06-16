# Synthetic Split Cascade Validation Design

## Label

experimental/frontier

## Research Question

Does the compute-aware cascade remain useful on the held-out synthetic split benchmark, where routing robustness is already stress-tested outside the five gold cases?

## Hypothesis

A cascade scored on `synthetic_overlap_v2` will keep a meaningful CER advantage over fixed mixed ASR while reducing cost relative to always choosing separated or cleaned separated ASR.

## Scope

This stage extends the existing cascade analysis to a silver held-out validation set. It reuses existing synthetic split manifest, CER tables, and routing decisions. It does not regenerate transcripts, modify gold references, or tune rules with synthetic CER.

## Inputs

- `results/tables/synthetic_split_manifest.csv`
- `results/tables/synthetic_split_cer_results.csv`
- `results/tables/synthetic_split_routing_decisions.csv`
- `results/tables/cascade_performance.csv`
- `src/compute_aware_cascade.py`

## Decision Rules

- Reuse the existing `budget_cascade` overlap/risk heuristic.
- Reuse the existing `v2_full_features` routing decisions as a `router_v2_synthetic_costed` strategy.
- Add a `cleaned_preferred_cascade` strategy for the synthetic split set only:
  - choose `separated_whisper_cleaned` when duplicate removal fired or overlap is heavy
  - otherwise choose `mixed_whisper` for light/mid overlap
  - otherwise choose `separated_whisper`

## Safety Rules

- Synthetic split outputs must be labeled `synthetic/silver`.
- No gold tables may be overwritten except the existing gold cascade outputs when rerun unchanged.
- CER is evaluation-only and must not be used as a decision feature.

## Outputs

- `results/tables/synthetic_split_cascade_performance.csv`
- `results/tables/synthetic_split_cascade_performance.json`
- `results/figures/synthetic_split_cascade_summary.md`
- `results/figures/synthetic_split_cer_runtime_tradeoff.png`

## Metrics

- average CER
- average compute cost
- relative cost versus `fixed_separated_whisper`
- automatic coverage
- sample count
- split and tier breakdown
- selected method mix

## Verification

- `python3 -m unittest tests.test_compute_aware_cascade -v`
- `python3 -m src.compute_aware_cascade --dataset synthetic_split`
- `python3 -m src.project_harness`
