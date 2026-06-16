# Frontier Operator Next-Action Operator Brief Design

## Goal

Add one plain-language operator brief that summarizes the current top-level frontier operator lanes.

## Why This Increment

The repository now has:

- a top-level frontier operator card
- a bridge checklist that verifies each lane before opening its target

What is still missing is the concise operator-facing summary that says, in one place, what the current contributor should do first, which blocked lane should be tracked in parallel, and which artifacts define the evidence path.

## Scope

In scope:

- one new generator under `src/`
- one focused unit test file
- one operator brief artifact in CSV/JSON/Markdown
- small doc updates referencing the brief

Out of scope:

- changing lane order
- changing the top-level go/no-go decision
- executing any frontier work
- claiming frontier completion

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_operator_next_action_card.json`
- `results/tables/frontier_operator_next_action_summary.json`

## Output Shape

One row should include:

- `ready_frontier`
- `ready_action`
- `ready_target`
- `blocked_frontier`
- `blocked_target`
- `operator_evidence`
- `operator_urgency`
- `operator_note`

## Decision Rules

- The ready lane should be taken from the first `ready_lane` row in the operator card.
- The blocked lane should be taken from the first `blocked_lane` row in the operator card.
- `operator_evidence` should point to the operator card plus the operator bridge checklist.
- `operator_urgency` should be derived from the coordination summary so the brief says how many lanes are active and what the current coordination state is.
- Keep all wording coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that the ready and blocked lanes are mapped into one operator brief row
- unit tests should confirm that the ready target and blocked target are preserved
- run the generator locally and inspect the markdown brief

## Labeling

Mark the output as experimental/frontier coordination only. The brief should accelerate operator pickup without turning a ready lane into a completed experiment.
