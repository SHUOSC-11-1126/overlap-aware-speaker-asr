# External Validation Prioritization Plan

## Goal

Extend the `external_validation` frontier from a static candidate list into a lightweight prioritization card that makes the first external sanity-check target explicit.

## Why This Next

The repository now has a candidate table, but the next contributor still has to decide which dataset should be tried first. A tiny prioritization layer keeps this work breadth-first:

- it does not download or run any external dataset yet
- it keeps the label scoped to `external/sanity-check`
- it converts the candidate list into a clearer execution order

## Proposed Outputs

- `results/tables/external_validation_prioritization.csv`
- `results/tables/external_validation_prioritization.json`
- `results/figures/external_validation_prioritization.md`

## Scope

- reuse the four existing candidates: AISHELL-4, AliMeeting, AMI, and LibriCSS
- add a lightweight priority tier, readiness note, and why-now note
- recommend one first dataset for the next narrow sanity-check step
- avoid claiming that any external benchmark has already been run

## Verification

- add unit tests for prioritization row construction
- add unit tests for markdown rendering
- run `python3 -m src.external_validation_candidates`
- run `python3 -m unittest tests.test_external_validation_candidates tests.test_demo_storyboard tests.test_llm_critic_qualitative tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_project_harness tests.test_compute_aware_cascade -v`
