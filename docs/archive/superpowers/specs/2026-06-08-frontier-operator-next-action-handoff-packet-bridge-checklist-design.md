# Frontier Operator Next-Action Handoff Packet Bridge Checklist Design

## Goal

Add one checklist that turns the new top-level operator handoff packet into an explicit verification step.

## Why This Increment

The repository now has a single-entry top-level operator handoff packet that consolidates the whole coordination chain.

What is still missing is the final bridge layer that tells the next contributor to verify that packet before reopening the downstream top-level status/entry artifacts.

## Scope

In scope:

- one new generator under `src/`
- one focused unit test file
- one bridge checklist artifact in CSV/JSON/Markdown
- small doc updates referencing the checklist

Out of scope:

- changing packet contents
- changing frontier order
- executing any frontier action
- claiming frontier completion

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_operator_next_action_summary.json`

## Output Shape

Per-row fields should include:

- `checklist_order`
- `coordination_state`
- `operator_sequence`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Decision Rules

- Use the top-level operator handoff packet markdown as the prerequisite artifact.
- Point the receipt target at the top-level operator card markdown.
- Reuse `coordination_state` and `operator_sequence` from the operator summary.
- Keep wording coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that the receipt target points back to the top-level operator card
- unit tests should confirm that the operator sequence is preserved in the bridge note
- run the generator locally and inspect the markdown checklist

## Labeling

Mark the output as experimental/frontier coordination only. The checklist should verify the packet before any downstream top-level artifact is reopened.
