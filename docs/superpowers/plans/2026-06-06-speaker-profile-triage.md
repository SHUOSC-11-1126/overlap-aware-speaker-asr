# Speaker Profile Triage Plan

## Goal

Extend the `speaker_profile` frontier from a per-case similarity table into a lightweight triage card that summarizes the current failure pattern.

## Why This Next

The repository already exposes a useful failure mode: the simple text-profile signal prefers swapped alignment across the verified gold cases. A tiny triage layer keeps this frontier breadth-first:

- it stays explicitly in the risk-signal lane rather than claiming voiceprint success
- it turns the case-by-case table into a clearer frontier handoff
- it makes the dominant failure pattern and next action easier to scan

## Proposed Outputs

- `results/tables/speaker_profile_triage.csv`
- `results/tables/speaker_profile_triage.json`
- `results/figures/speaker_profile_triage.md`

## Scope

- derive an aggregate triage row from the existing similarity rows
- summarize swapped/direct counts, average confidence gap, and dominant pattern
- recommend the next profile-method step without claiming speaker identification success

## Verification

- add unit tests for triage row construction
- add unit tests for markdown rendering
- run `python3 -m src.speaker_profile_similarity`
- run `python3 -m unittest tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_llm_critic_qualitative tests.test_demo_storyboard tests.test_external_validation_candidates tests.test_project_harness tests.test_compute_aware_cascade -v`
