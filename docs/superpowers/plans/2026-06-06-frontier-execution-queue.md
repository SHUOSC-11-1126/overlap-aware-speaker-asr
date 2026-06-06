# Frontier Execution Queue Plan

## Goal

Extend the project harness from a static frontier status table into a lightweight execution queue that orders the next breadth-first steps.

## Why This Next

The repository now has multiple frontier-specific handoff cards, but the next contributor still has to decide which breadth-first move should happen first. A tiny queue layer makes the harness more actionable:

- it stays at the coordination layer rather than deepening one frontier
- it summarizes breadth-first order in one generated artifact
- it reuses existing next-step language instead of inventing new experimental claims

## Proposed Outputs

- `results/tables/frontier_execution_queue.csv`
- `results/tables/frontier_execution_queue.json`
- `results/figures/frontier_execution_queue.md`

## Scope

- derive a simple queue from the current frontier status rows
- record queue order, frontier id, reason to act now, and entry artifact
- recommend a first breadth-first step without claiming that the queued work is already complete

## Verification

- add unit tests for frontier queue row construction
- add unit tests for markdown rendering
- run `python3 -m src.project_harness`
- run `python3 -m unittest tests.test_project_harness tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_llm_critic_qualitative tests.test_demo_storyboard tests.test_external_validation_candidates tests.test_compute_aware_cascade -v`
