# Benchmark Frontier Bridge Plan

## Goal

Extend the compute-aware benchmark handoff stack with a tiny bridge card that connects the benchmark next step to the newer breadth-first frontier queue.

## Why This Next

The repository now has both a deep benchmark execution stack and a cross-frontier queue, but contributors still have to mentally map the benchmark operator brief back to the broader frontier ordering. A tiny bridge layer helps:

- it does not add new benchmark claims
- it links the benchmark stack to the breadth-first coordination layer
- it keeps the next action legible in one short card

## Proposed Outputs

- `results/tables/cascade_benchmark_frontier_bridge.csv`
- `results/figures/cascade_benchmark_frontier_bridge.md`

## Scope

- reuse the benchmark operator brief and the frontier execution queue
- record the current benchmark operator step, its frontier alignment, and why it still matters first
- keep the output explicitly as a coordination artifact rather than a new measurement result

## Verification

- add unit tests for bridge row construction
- add unit tests for markdown rendering
- run `python3 -m src.compute_aware_cascade`
- run `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_llm_critic_qualitative tests.test_demo_storyboard tests.test_external_validation_candidates -v`
