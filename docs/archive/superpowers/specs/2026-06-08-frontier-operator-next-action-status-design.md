# Frontier Operator Next-Action Status Design

## Goal

Add a single-row `experimental/frontier` coordination status artifact for the top-level operator chain so future agents can read one machine-friendly snapshot instead of stitching together the summary, milestone card, completion dashboard, and bridge checklist by hand.

## Why This Increment

The current top-level operator chain already exposes:

- ordered ready/blocked lanes
- a phase checkpoint
- a milestone boundary
- a completion dashboard
- a completion dashboard bridge checklist

What is still missing is a status-style rollup that compresses those artifacts into one coordination state row. This keeps the stable baseline untouched while making the frontier queue easier to resume and automate.

## Inputs

- `results/tables/frontier_operator_next_action_summary.json`
- `results/tables/frontier_operator_next_action_milestone_card.json`
- `results/tables/frontier_operator_next_action_completion_dashboard.json`
- `results/tables/frontier_operator_next_action_completion_dashboard_bridge_checklist.json`

All inputs remain coordination-only and must not be interpreted as completed benchmark execution.

## Output Artifacts

- `results/tables/frontier_operator_next_action_status.csv`
- `results/tables/frontier_operator_next_action_status.json`
- `results/figures/frontier_operator_next_action_status.md`

## Proposed Fields

- `scope`
- `coordination_state`
- `ready_lane_status`
- `blocked_lane_status`
- `milestone_status`
- `dashboard_bridge_status`
- `combined_operator_status`
- `primary_status_target`
- `status_note`

## Status Rules

- `ready_lane_status = ready_lane_active` when a ready frontier exists, otherwise `ready_lane_empty`
- `blocked_lane_status = blocked_lane_waiting` when a blocked frontier exists, otherwise `blocked_lane_clear`
- `milestone_status = milestone_active` when a next milestone exists, otherwise `milestone_missing`
- `dashboard_bridge_status = dashboard_bridge_ready` when the completion dashboard has a current frontier and the bridge checklist has at least one row, otherwise `dashboard_bridge_missing`
- `combined_operator_status = operator_status_mixed_ready` when ready lane, blocked lane, milestone, and dashboard bridge are all present together
- `combined_operator_status = operator_status_ready_lane_only` when only the ready lane and milestone are present
- `combined_operator_status = operator_status_blocked_lane_only` when only a blocked lane is present without a ready lane
- `combined_operator_status = operator_status_unset` otherwise

## Testing

Add unit coverage for:

1. the current mixed-ready top-level state
2. the empty/missing-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No frontier execution is claimed.
- No routing behavior changes.
- This is coordination support only.
