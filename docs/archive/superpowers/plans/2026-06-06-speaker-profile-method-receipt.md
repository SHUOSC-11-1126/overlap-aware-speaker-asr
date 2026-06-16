# Speaker Profile Method Receipt Plan

## Goal

Extend the `speaker_profile` coordination line with a template-only method receipt so the next contributor has an explicit evidence writeback target before any stronger profile method is claimed to work.

## Why This Next

The repository already has:

- a speaker profile triage card
- a speaker profile method handoff packet

Those layers now describe what stronger method direction should be tried first, but they do not yet provide the concrete evidence slot that a future method trial should fill. Adding a receipt template keeps the work breadth-first because:

- it closes a coordination gap without pretending any profile improvement has happened
- it defines the minimal writeback schema before a stronger baseline is attempted
- it reduces ambiguity around what the first stronger-method experiment should record

## Proposed Outputs

- `results/tables/speaker_profile_method_receipt.json`
- `results/figures/speaker_profile_method_receipt.md`

## Scope

- derive one receipt template row from the current method handoff row
- record execution status, method scope, expected inputs, expected outputs, and writeback note
- keep the artifact explicitly marked as template-only / not-yet-executed
- avoid claiming any actual speaker attribution improvement

## Verification

- add unit tests for receipt row construction
- add unit tests for markdown rendering
- run `python3 -m src.speaker_profile_similarity`
- run `python3 -m unittest tests.test_speaker_profile_similarity tests.test_project_harness -v`
