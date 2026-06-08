# Frontier Operator Next-Action Runbook Card Design

## Goal

Add one one-page runbook card that condenses the current top-level frontier operator brief into a first-action execution card.

## Why This Increment

The repository now has:

- a top-level operator card
- a bridge checklist
- a plain-language operator brief

What is still missing is the one-page runbook layer that gives the next contributor one compact execution entrypoint: what to do first, what evidence path to follow, and what would count as completion of that narrow coordination step.

## Scope

In scope:

- one new generator under `src/`
- one focused unit test file
- one runbook card artifact in CSV/JSON/Markdown
- small doc updates referencing the runbook card

Out of scope:

- changing lane order
- changing frontier readiness
- executing any benchmark or writeback
- claiming completion beyond coordination guidance

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_operator_next_action_operator_brief.json`
- `results/tables/frontier_operator_next_action_bridge_checklist.json`

## Output Shape

One row should include:

- `recommended_frontier`
- `recommended_action`
- `required_evidence`
- `completion_signal`
- `urgency`
- `runbook_note`

## Decision Rules

- The `recommended_frontier` and `recommended_action` should come from the ready lane in the operator brief.
- `required_evidence` should point at the operator brief plus the operator bridge checklist.
- `completion_signal` should describe the narrow coordination event that would close the ready lane handoff, not claim experiment completion.
- `urgency` should summarize the active-lane state already captured in the operator brief.
- Keep all wording coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that the ready frontier is promoted into the runbook card
- unit tests should confirm that the urgency and evidence path are preserved
- run the generator locally and inspect the markdown card

## Labeling

Mark the output as experimental/frontier coordination only. The card should accelerate the first next step without implying that the frontier work itself is already done.
