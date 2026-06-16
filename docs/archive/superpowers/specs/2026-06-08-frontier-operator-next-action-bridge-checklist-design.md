# Frontier Operator Next-Action Bridge Checklist Design

## Goal

Add one bridge checklist that turns the top-level frontier operator card into explicit pre-open verification rows.

## Why This Increment

The repository now has a top-level operator card that says:

- which frontier is the highest-priority ready lane
- which frontier is the highest-priority blocked lane
- which artifact each lane should point to next

What is still missing is the final bridge step that tells the next operator to verify the card before opening those targets. This keeps the coordination chain consistent with the existing queue, handoff, and receipt bridge patterns.

## Scope

In scope:

- one new generator under `src/`
- one focused test file
- one bridge checklist artifact in CSV/JSON/Markdown
- small doc updates that reference the new bridge layer

Out of scope:

- changing any frontier ranking
- changing any stable/gold output
- executing any benchmark or writeback path
- claiming that a ready lane has already been completed

## Inputs

Read only existing operator card artifacts:

- `results/tables/frontier_operator_next_action_card.json`

## Output Shape

Per-row fields should include:

- `checklist_order`
- `action_lane`
- `frontier_name`
- `go_no_go_state`
- `prerequisite_artifact`
- `target_artifact`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Decision Rules

- Preserve the ready-lane-first order from the operator card.
- Use the operator card markdown as the `prerequisite_artifact`.
- Reuse each row's `target_artifact` unchanged.
- Make the `checklist_goal` say that the operator card must be verified before opening the target artifact.
- Keep the bridge language coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that the row order is preserved from the operator card
- unit tests should confirm that target artifacts are passed through unchanged
- run the generator locally and inspect the markdown bridge checklist

## Labeling

Mark the output as experimental/frontier coordination only. The bridge checklist should accelerate operator pickup without upgrading any lane into an experiment result.
