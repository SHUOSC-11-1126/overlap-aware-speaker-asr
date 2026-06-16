# MeetEval Dry Run Receipt Plan

## Goal

Extend the `meeteval_compatibility` coordination line with a lightweight dry-run receipt template so the next contributor has a concrete evidence writeback target before any real MeetEval / cpWER execution claim exists.

## Why This Next

The repository already has:

- a readiness card
- a dry-run handoff packet
- a frontier handoff packet that points at that dry-run handoff

Those layers now all reference `results/tables/meeteval_dry_run_receipt.json`, but that evidence target does not yet exist. Adding a receipt template keeps the work breadth-first because:

- it closes a coordination gap without pretending evaluation has happened
- it makes the expected writeback schema explicit before anyone runs a dry run
- it reduces ambiguity around what evidence must be captured for the first narrow diagnostic step

## Proposed Outputs

- `results/tables/meeteval_dry_run_receipt.json`
- `results/figures/meeteval_dry_run_receipt.md`

## Scope

- derive one receipt template row from the current dry-run handoff row
- record run scope, execution status, expected inputs, expected outputs, and writeback note
- keep the receipt explicitly marked as template-only / not-yet-executed
- avoid claiming any actual MeetEval or cpWER result

## Verification

- add unit tests for receipt row construction
- add unit tests for markdown rendering
- run `python3 -m src.export_meeteval_compatibility`
- run `python3 -m unittest tests.test_export_meeteval_compatibility tests.test_project_harness -v`
