# MeetEval Readiness Plan

## Goal

Extend the `meeteval_compatibility` frontier from a segment export note into a lightweight readiness card that clarifies what the next cpWER-facing step would be.

## Why This Next

The repository already exports compatible JSONL segments, but the next contributor still has to infer whether the bridge is strong enough to attempt a narrow MeetEval follow-up. A tiny readiness layer keeps this frontier breadth-first:

- it stays scoped to compatibility rather than claiming completed evaluation
- it summarizes fallback usage and next-step readiness in one place
- it turns the bridge from a passive export into a clearer handoff artifact

## Proposed Outputs

- `results/tables/meeteval_readiness.csv`
- `results/tables/meeteval_readiness.json`
- `results/figures/meeteval_readiness.md`

## Scope

- derive a simple readiness view from the existing compatibility rows
- record source mix, fallback dependence, and next action
- make explicit whether the current bridge is ready for a narrow cpWER-style dry run
- avoid claiming that MeetEval or cpWER has already been executed

## Verification

- add unit tests for readiness row construction
- add unit tests for markdown rendering
- run `python3 -m src.export_meeteval_compatibility`
- run `python3 -m unittest tests.test_export_meeteval_compatibility tests.test_llm_critic_qualitative tests.test_demo_storyboard tests.test_external_validation_candidates tests.test_project_harness tests.test_speaker_profile_similarity tests.test_compute_aware_cascade -v`
