# Demo Walkthrough Receipt Plan

## Goal

Extend the `demo_excellence` coordination line with a template-only walkthrough receipt so the next contributor has an explicit evidence writeback target before any live demo or recorded walkthrough is claimed complete.

## Why This Next

The repository already has:

- a demo storyboard
- a demo walkthrough sequence

Those layers now describe what the demo should say, but they do not yet provide the concrete evidence slot that a future live demo or recording pass should fill. Adding a receipt template keeps the work breadth-first because:

- it closes a coordination gap without pretending any polished demo has already been delivered
- it defines the minimal writeback schema before a walkthrough is actually run
- it reduces ambiguity around what the first demo pass should record

## Proposed Outputs

- `results/tables/demo_walkthrough_receipt.json`
- `results/figures/demo_walkthrough_receipt.md`

## Scope

- derive one receipt template row from the current walkthrough head
- record execution status, walkthrough scope, expected inputs, expected outputs, and writeback note
- keep the artifact explicitly marked as template-only / not-yet-executed
- avoid claiming any real demo delivery success

## Verification

- add unit tests for receipt row construction
- add unit tests for markdown rendering
- run `python3 -m src.demo_storyboard`
- run `python3 -m unittest tests.test_demo_storyboard tests.test_project_harness -v`
