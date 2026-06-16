# Frontier Operator Next-Action Status Handoff Completion Summary Bridge Checklist Design

## Goal

Add a bridge checklist for `frontier_operator_next_action_status_handoff_completion_summary` so future agents verify the queue-level top-level operator handoff summary before reopening the lane-level handoff target.

## Why This Increment

The top-level operator status stack now has:

- a status rollup
- a status bridge checklist
- a lane-specific handoff
- a handoff bridge checklist
- a handoff completion summary

The natural adjacent next layer is the completion summary bridge checklist, which already exists throughout other handoff-oriented coordination chains in this repository.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_completion_summary_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_completion_summary_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_completion_summary_bridge_checklist.md`

## Proposed Fields

- `checklist_order`
- `queue_status`
- `ready_lane_count`
- `blocked_lane_count`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Bridge Rules

- Emit a single-row bridge checklist.
- Read `queue_status`, `ready_lane_count`, and `blocked_lane_count` from the completion summary.
- Use `results/figures/frontier_operator_next_action_status_handoff_completion_summary.md` as `prerequisite_artifact`.
- Use `results/figures/frontier_operator_next_action_status_handoff.md` as `receipt_target`.
- The bridge note should echo the current queue status and both lane counts.
- The checklist must remain coordination-only and must not claim frontier execution.

## Testing

Add unit coverage for:

1. the current mixed-ready queue-complete state
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No experiment execution is claimed.
