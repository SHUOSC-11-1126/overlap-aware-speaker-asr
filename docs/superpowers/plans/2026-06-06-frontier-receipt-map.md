# Frontier Receipt Map Plan

## Goal

Extend the project harness from a single queue-head receipt packet into a full frontier receipt map that shows the prerequisite artifact and receipt target for each current frontier.

## Why This Next

The repository already has:

- a frontier execution queue
- a frontier focus card
- a frontier handoff packet
- a frontier receipt packet

Those layers are strong for the queue head, but the next contributor still has to inspect multiple files to understand the receipt path for the other frontiers. Adding a map keeps the work breadth-first because:

- it stays purely in coordination territory
- it preserves the queue while making non-head frontiers easier to pick up in parallel
- it turns several scattered receipt templates into one scan-friendly table

## Proposed Outputs

- `results/tables/frontier_receipt_map.json`
- `results/figures/frontier_receipt_map.md`

## Scope

- derive one row per frontier from the execution queue
- record queue order, frontier id, prerequisite artifact, receipt target, and map note
- keep the wording explicit that this is coordination-only and not a claim of completed frontier work
- avoid changing queue priority or frontier status logic

## Verification

- add unit tests for map row construction
- add unit tests for markdown rendering
- run `python3 -m src.project_harness`
- run `python3 -m unittest tests.test_project_harness tests.test_demo_storyboard tests.test_llm_critic_qualitative tests.test_speaker_profile_similarity tests.test_external_validation_candidates tests.test_export_meeteval_compatibility -v`
