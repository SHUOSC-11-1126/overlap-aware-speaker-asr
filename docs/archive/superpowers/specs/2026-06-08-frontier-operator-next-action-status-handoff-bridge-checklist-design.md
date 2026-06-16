# Frontier Operator Next-Action Status Handoff Bridge Checklist Design

## Goal

Add a bridge checklist for `frontier_operator_next_action_status_handoff` so future agents verify each top-level lane-specific handoff before opening the lane-specific target artifact.

## Why This Increment

The top-level operator chain now has:

- a status rollup
- a status bridge checklist
- a lane-specific status handoff

The missing adjacent layer is the row-by-row handoff bridge checklist that other handoff-oriented coordination chains already use. Adding it preserves the stable baseline while making the frontier operator chain easier to resume safely.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_bridge_checklist.md`

## Proposed Fields

- `checklist_order`
- `action_lane`
- `frontier_name`
- `combined_operator_status`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Bridge Rules

- Emit one checklist row per handoff row.
- Preserve `action_lane`, `frontier_name`, and `combined_operator_status` from the handoff.
- Use `results/figures/frontier_operator_next_action_status_handoff.md` as `prerequisite_artifact`.
- Use the handoff `expected_outputs` field as `receipt_target`.
- The bridge note should echo the current top-level combined status and lane.
- The checklist must remain coordination-only and must not claim frontier execution.

## Testing

Add unit coverage for:

1. a mixed-ready handoff with both ready and blocked lanes
2. an empty-input fallback

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No experiment execution is claimed.
