# LLM Critic Queue Plan

## Goal

Extend the `llm_critic` frontier from a qualitative note into a lightweight review queue that makes the next critic pass order explicit.

## Why This Next

The repository already has critic-style notes, but the next contributor still has to decide which case should be reviewed first. A tiny queue layer broadens the critic frontier without pretending that a real repair loop exists:

- it keeps the artifact scoped to `qualitative/demo`
- it turns qualitative warnings into a more executable triage order
- it reuses existing risk and profile signals rather than inventing a new model

## Proposed Outputs

- `results/tables/llm_critic_review_queue.csv`
- `results/tables/llm_critic_review_queue.json`
- `results/figures/llm_critic_review_queue.md`

## Scope

- derive a simple review priority from risk cues and profile uncertainty
- record queue order, review priority, and why-now reasoning
- recommend which case should receive the first critic review pass
- avoid claiming that any transcript has already been repaired

## Verification

- add unit tests for queue row construction
- add unit tests for markdown rendering
- run `python3 -m src.llm_correct`
- run `python3 -m unittest tests.test_llm_critic_qualitative tests.test_demo_storyboard tests.test_external_validation_candidates tests.test_project_harness tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_compute_aware_cascade -v`
