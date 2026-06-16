# Speaker Profile Method Handoff Plan

## Goal

Extend the `speaker_profile` frontier from an aggregate triage card into a lightweight method handoff packet that tells the next contributor what stronger profile direction should be tried first.

## Why This Next

The repository already has:

- a per-case speaker profile similarity table
- an aggregate triage card

What it still lacks is a single artifact that translates the current `swapped_bias` finding into an explicit next method handoff. A tiny handoff layer keeps the work breadth-first because:

- it stays in diagnostic coordination territory rather than claiming voiceprint success
- it clarifies the first stronger-method direction without forcing a full implementation
- it reduces ambiguity between "current signal is weak" and "what should be attempted next"

## Proposed Outputs

- `results/tables/speaker_profile_method_handoff.csv`
- `results/tables/speaker_profile_method_handoff.json`
- `results/figures/speaker_profile_method_handoff.md`

## Scope

- derive one method handoff row from the current triage summary
- record dominant pattern, first stronger-method direction, expected evidence, and handoff note
- keep the artifact explicitly diagnostic rather than a speaker-ID claim
- avoid claiming any actual profile-method improvement has already been achieved

## Verification

- add unit tests for handoff row construction
- add unit tests for markdown rendering
- run `python3 -m src.speaker_profile_similarity`
- run `python3 -m unittest tests.test_speaker_profile_similarity tests.test_project_harness -v`
