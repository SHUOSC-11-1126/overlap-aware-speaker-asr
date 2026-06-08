# Frontier Operator Next-Action Frontier Bridge Checklist Design

## Goal

Add one checklist that turns the new top-level frontier bridge into an explicit pre-open verification step.

## Why This Increment

The repository now has a top-level operator chain ending in a frontier bridge that confirms the runbook-ready frontier still matches the broader frontier queue head.

What is still missing is the final verification layer that tells the next contributor to confirm that alignment before reopening the runbook card.

## Scope

In scope:

- one new generator under `src/`
- one focused unit test file
- one bridge checklist artifact in CSV/JSON/Markdown
- small doc updates referencing the checklist

Out of scope:

- changing queue order
- changing bridge conclusions
- executing any frontier action
- claiming frontier completion

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_operator_next_action_frontier_bridge.json`

## Output Shape

Per-row fields should include:

- `checklist_order`
- `runbook_frontier`
- `frontier_queue_head`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Decision Rules

- Preserve the single bridge row as checklist order `1`.
- Use the top-level frontier bridge markdown as the prerequisite artifact.
- Point the receipt target at the top-level runbook card markdown.
- Keep the wording coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that the receipt target points to the top-level runbook card
- unit tests should confirm that the bridge note is passed through unchanged
- run the generator locally and inspect the markdown checklist

## Labeling

Mark the output as experimental/frontier coordination only. The checklist should verify queue alignment before the runbook card is reopened.
