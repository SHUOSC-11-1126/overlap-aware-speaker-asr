# Frontier Operator Next-Action Card Design

## Goal

Add one operator-facing coordination artifact that turns the unified frontier go/no-go board into explicit next actions.

## Why This Increment

The repository now has:

- a unified frontier go/no-go board
- a unified frontier go/no-go summary

What is still missing is the final translation layer from state to action. A contributor can now see which frontier is the highest-priority ready track and which one is the highest-priority blocked track, but they still need to manually infer what to do next.

## Scope

In scope:

- one new generator under `src/`
- one focused test file
- one operator card artifact plus one summary artifact
- small doc updates that reference the new operator layer

Out of scope:

- any real frontier execution
- any overwrite of verified references
- any change to stable/gold outputs
- any claim that a ready frontier is complete

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_go_no_go_board.json`
- `results/tables/frontier_go_no_go_summary.json`

## Output Shape

Operator rows should include:

- `action_lane`
- `frontier_name`
- `go_no_go_state`
- `current_state`
- `operator_action`
- `prerequisite_artifact`
- `target_artifact`
- `action_boundary`

Summary row should include:

- `scope`
- `coordination_state`
- `ready_frontier`
- `blocked_frontier`
- `ready_action_lane`
- `blocked_action_lane`
- `operator_sequence`
- `observation`

## Decision Rules

- Emit one `ready_lane` row when `highest_priority_ready_frontier` is present.
- Emit one `blocked_lane` row when `highest_priority_blocked_frontier` is present.
- Pull `current_state`, `recommended_next_action`, and `evidence_artifact` from the unified board row for that frontier.
- Map each frontier to one concrete `target_artifact` that represents the next writeback or bridge artifact instead of a vague suggestion.
- Keep the output coordination-only and explicitly preserve all claim boundaries.

## Verification

- unit tests should confirm that the highest-priority ready and blocked frontiers are converted into two ordered action lanes
- unit tests should confirm the ready lane appears before the blocked lane
- run the generator locally and inspect the markdown card

## Labeling

Mark the output as experimental/frontier coordination only. The card should help the next operator move faster without upgrading readiness into a result claim.
