# External Validation Slice Handoff Plan

## Goal

Extend the `external_validation` frontier from candidate prioritization into a lightweight slice handoff card that tells the next contributor exactly which tiny external sanity-check slice should be prepared first.

## Why This Next

The repository already has:

- external validation candidate cards
- an ordered prioritization card

What it still lacks is a single artifact that turns the top-ranked dataset into an executable first slice without overstating progress. A tiny slice handoff keeps the work breadth-first because:

- it stays in coordination territory rather than pretending any external benchmark has run
- it narrows the first external step to one tiny slice with explicit gating
- it reduces ambiguity between "AISHELL-4 should go first" and "what should actually be staged next"

## Proposed Outputs

- `results/tables/external_validation_slice_handoff.csv`
- `results/tables/external_validation_slice_handoff.json`
- `results/figures/external_validation_slice_handoff.md`

## Scope

- derive one handoff row from the current prioritization head
- record dataset name, first slice shape, license gate, mapping artifact, and dry-run goal
- keep the artifact explicitly labeled as `external/sanity-check`
- avoid claiming any external validation execution or benchmark result

## Verification

- add unit tests for handoff row construction
- add unit tests for markdown rendering
- run `python3 -m src.external_validation_candidates`
- run `python3 -m unittest tests.test_external_validation_candidates tests.test_project_harness -v`
