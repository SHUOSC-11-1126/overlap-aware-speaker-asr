# Frontier Operator Next-Action Phase Checkpoint Card Design

## Goal

Add one phase checkpoint card that isolates the current top-level ready-lane completion signal.

## Why This Increment

The repository now has:

- a top-level operator handoff packet
- a handoff packet bridge checklist

What is still missing is the narrow checkpoint card that says: for the current ready frontier, what exact action and completion signal must be satisfied before the chain should advance.

## Scope

In scope:

- one new generator under `src/`
- one focused unit test file
- one phase checkpoint card artifact in CSV/JSON/Markdown
- small doc updates referencing the checkpoint card

Out of scope:

- changing ready-lane priority
- changing the runbook wording
- executing frontier work
- claiming frontier completion

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_operator_next_action_runbook_card.json`

## Output Shape

One row should include:

- `checkpoint_frontier`
- `checkpoint_action`
- `completion_signal`
- `checkpoint_note`

## Decision Rules

- `checkpoint_frontier` should come from the runbook card.
- `checkpoint_action` should come from the runbook card.
- `completion_signal` should be copied directly from the runbook card.
- Keep wording coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that the frontier and completion signal are preserved from the runbook card
- run the generator locally and inspect the markdown card

## Labeling

Mark the output as experimental/frontier coordination only. The card should isolate the current checkpoint without implying frontier execution has happened.
