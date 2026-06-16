# Frontier Receipt Packet Plan

## Goal

Extend the project harness from a frontier handoff packet into a receipt-aware packet that points the current queue head directly at its evidence writeback target.

## Why This Next

The repository already has:

- a frontier execution queue
- a frontier focus card
- a frontier handoff packet
- receipt templates across several frontier lines

The remaining coordination gap is tiny but real: the current harness points to the next artifact and expected evidence, but not to a single receipt-first packet. Adding this layer keeps the work breadth-first because:

- it stays in coordination territory
- it reduces the last bit of ambiguity between "what should I open next?" and "where should I eventually write back?"
- it connects the harness more directly to the receipt templates that now exist across multiple frontiers

## Proposed Outputs

- `results/tables/frontier_receipt_packet.json`
- `results/figures/frontier_receipt_packet.md`

## Scope

- derive one row from the queue head
- point that row at the current receipt target and prerequisite artifact
- capture current frontier, prerequisite artifact, receipt target, and execution note
- keep the wording explicit that this is coordination-only and not a claim of completed frontier work

## Verification

- add unit tests for packet row construction
- add unit tests for markdown rendering
- run `python3 -m src.project_harness`
- run `python3 -m unittest tests.test_project_harness tests.test_demo_storyboard tests.test_llm_critic_qualitative tests.test_speaker_profile_similarity tests.test_external_validation_candidates tests.test_export_meeteval_compatibility -v`
