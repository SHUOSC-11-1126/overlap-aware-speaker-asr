# Frontier Parallel Picklist Plan

## Goal

Extend the project harness from a receipt-aware map into a frontier parallel picklist that highlights which current frontiers can be picked up independently without changing the breadth-first queue itself.

## Why This Next

The repository already has:

- a frontier execution queue
- a frontier focus card
- a frontier handoff packet
- a frontier receipt packet
- a frontier receipt map

Those layers make the queue head and receipt paths clear, but they still do not give the next contributor a single parallel-friendly view of which frontiers are immediately safe to pick up side by side. Adding a picklist keeps the work breadth-first because:

- it stays purely in coordination territory
- it preserves queue order instead of redefining priority
- it makes cross-frontier pickup easier without claiming that any frontier step has already been executed

## Proposed Outputs

- `results/tables/frontier_parallel_picklist.json`
- `results/figures/frontier_parallel_picklist.md`

## Scope

- derive one row per current frontier from the execution queue
- record queue order, frontier id, prerequisite artifact, receipt target, and a parallel pickup note
- label the output as coordination-only and breadth-first friendly
- avoid changing queue priority, frontier status logic, or any benchmark claim

## Verification

- add unit tests for picklist row construction
- add unit tests for markdown rendering
- run `python3 -m unittest tests.test_project_harness -v`
- run `python3 -m src.project_harness`
- run `python3 -m unittest tests.test_project_harness tests.test_demo_storyboard tests.test_llm_critic_qualitative tests.test_speaker_profile_similarity tests.test_external_validation_candidates tests.test_export_meeteval_compatibility -v`
