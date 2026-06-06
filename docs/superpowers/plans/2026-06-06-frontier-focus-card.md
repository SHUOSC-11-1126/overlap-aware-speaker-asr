# Frontier Focus Card Plan

## Goal

Extend the project harness coordination layer with a tiny focus card that highlights the current first breadth-first frontier step.

## Why This Next

The harness now has a frontier status table and an execution queue, but the next contributor still has to open the queue to see the single highest-priority item. A tiny focus card keeps the breadth-first layer easy to scan:

- it stays purely at the coordination level
- it reuses the generated frontier queue rather than inventing new priorities
- it turns the queue head into a one-glance starting point

## Proposed Outputs

- `results/tables/frontier_focus_card.json`
- `results/figures/frontier_focus_card.md`

## Scope

- derive the focus card from the frontier execution queue head
- record current frontier, entry artifact, and first action
- avoid claiming that the highlighted work is already complete

## Verification

- add unit tests for focus card row construction
- add unit tests for markdown rendering
- run `python3 -m src.project_harness`
- run `python3 -m unittest tests.test_project_harness tests.test_compute_aware_cascade tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_llm_critic_qualitative tests.test_demo_storyboard tests.test_external_validation_candidates -v`
