# MeetEval Dry Run Handoff Plan

## Goal

Extend the `meeteval_compatibility` frontier from a readiness card into a lightweight dry-run handoff packet that tells the next contributor exactly what narrow diagnostic step should run first.

## Why This Next

The repository already has:

- a compatibility export note
- JSONL segment exports
- a readiness card

What it still lacks is a single handoff artifact that turns that readiness state into an executable next move without overstating progress. A tiny handoff layer keeps the work breadth-first because:

- it stays strictly in planning / coordination territory
- it clarifies the first slice, blocker, and evidence target for a future dry run
- it improves continuity between the queue head in `project_harness` and the `meeteval_compatibility` frontier itself

## Proposed Outputs

- `results/tables/meeteval_dry_run_handoff.csv`
- `results/tables/meeteval_dry_run_handoff.json`
- `results/figures/meeteval_dry_run_handoff.md`

## Scope

- derive one dry-run handoff row from the existing compatibility and readiness summaries
- record the current bridge status, dominant source mix, recommended first slice, dry-run goal, blocker, and expected evidence writeback
- keep all wording explicit that no MeetEval / cpWER execution has happened yet
- avoid changing any gold outputs or benchmark claims

## Verification

- add unit tests for handoff row construction
- add unit tests for markdown rendering
- run `python3 -m src.export_meeteval_compatibility`
- run `python3 -m unittest tests.test_export_meeteval_compatibility tests.test_project_harness -v`
