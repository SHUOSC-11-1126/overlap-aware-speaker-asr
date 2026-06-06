# External Validation Slice Receipt Plan

## Goal

Extend the `external_validation` coordination line with a template-only slice receipt so the next contributor has an explicit evidence writeback target before any real external sanity-check run is claimed.

## Why This Next

The repository already has:

- an external validation prioritization card
- an external validation slice handoff packet

Those layers now describe what the first external slice should look like, but they do not yet provide the concrete evidence slot that a future dry run should fill. Adding a receipt template keeps the work breadth-first because:

- it closes a coordination gap without pretending any external benchmark has happened
- it defines the minimal writeback schema before any slice is staged
- it reduces ambiguity around what the first external sanity-check should record

## Proposed Outputs

- `results/tables/external_validation_slice_receipt.json`
- `results/figures/external_validation_slice_receipt.md`

## Scope

- derive one receipt template row from the current slice handoff row
- record execution status, slice scope, expected inputs, expected outputs, and writeback note
- keep the artifact explicitly marked as template-only / not-yet-executed
- avoid claiming any external benchmark result

## Verification

- add unit tests for receipt row construction
- add unit tests for markdown rendering
- run `python3 -m src.external_validation_candidates`
- run `python3 -m unittest tests.test_external_validation_candidates tests.test_project_harness -v`
