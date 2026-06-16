# Demo Walkthrough Plan

## Goal

Extend the `demo_excellence` frontier from a static storyboard into a lightweight walkthrough card set that suggests a short demo flow.

## Why This Next

The repository already has a one-page storyboard, but a new contributor still has to decide how to present it live or in a short recording. A tiny walkthrough layer broadens the demo frontier without building a full app:

- it keeps the work qualitative and presentation-facing
- it reuses existing baseline and frontier findings
- it turns the demo artifact into a clearer sequence of talking points

## Proposed Outputs

- `results/tables/demo_walkthrough_steps.json`
- `results/figures/demo_walkthrough.md`

## Scope

- define a short ordered walkthrough across problem, evidence, routing, frontier, and next-step framing
- keep the artifact demo-facing rather than quantitative evaluation
- mention the newest breadth-first frontier additions without claiming unsupported results

## Verification

- add unit tests for walkthrough step construction
- add unit tests for markdown rendering
- run `python3 -m src.demo_storyboard`
- run `python3 -m unittest tests.test_demo_storyboard tests.test_external_validation_candidates tests.test_project_harness tests.test_llm_critic_qualitative tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_compute_aware_cascade -v`
