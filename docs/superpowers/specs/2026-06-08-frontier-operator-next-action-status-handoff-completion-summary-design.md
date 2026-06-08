# Frontier Operator Next-Action Status Handoff Completion Summary Design

## Goal

Add a compact completion summary for `frontier_operator_next_action_status_handoff` so future agents can read one row that says how many top-level lanes are currently actionable, how many remain blocked, and whether the current handoff queue is complete or still in progress.

## Why This Increment

The top-level operator status stack now has:

- a status rollup
- a status bridge checklist
- a lane-specific handoff
- a handoff bridge checklist

The natural next adjacency, following existing repository patterns, is a completion summary that compresses the lane-specific handoff into a single queue-level state.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.csv`
- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.json`
- `results/figures/frontier_operator_next_action_status_handoff_completion_summary.md`

## Proposed Fields

- `scope`
- `ready_lane_count`
- `blocked_lane_count`
- `total_lane_count`
- `queue_status`
- `primary_frontier`
- `observation`

## Summary Rules

- Count ready lanes from `action_lane == ready_lane`
- Count blocked lanes from `action_lane == blocked_lane`
- `queue_status = queue_complete` when at least one ready lane and at least one blocked lane are both visible
- `queue_status = queue_ready_only` when only ready lanes are visible
- `queue_status = queue_blocked_only` when only blocked lanes are visible
- `queue_status = queue_empty` when there are no handoff rows
- `primary_frontier` should use the first handoff row when present

## Testing

Add unit coverage for:

1. the current mixed-ready two-lane state
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
