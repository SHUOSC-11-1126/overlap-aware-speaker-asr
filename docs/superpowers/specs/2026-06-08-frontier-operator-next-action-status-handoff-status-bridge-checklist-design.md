# Frontier Operator Next-Action Status Handoff Status Bridge Checklist Design

## Goal

Add a bridge checklist for the top-level `status/handoff` status rollup so future agents can verify the machine-readable status snapshot before opening the next `status/handoff` coordination packet.

## Why This Increment

The current `status/handoff` subchain now has:

- completion summary
- milestone card
- completion dashboard
- completion dashboard bridge checklist
- status rollup

The natural adjacent next layer, following existing repository patterns, is a bridge checklist that turns the new status rollup into a verification gate before the broader `status/handoff` packet is reopened.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_status.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_status_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_status_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_status_bridge_checklist.md`

## Proposed Fields

- `checklist_order`
- `combined_status_handoff_state`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Preserve `combined_status_handoff_state` from the status rollup.
- Set `prerequisite_artifact` to `results/figures/frontier_operator_next_action_status_handoff_status.md`.
- Set `receipt_target` to `results/figures/frontier_operator_next_action_status_handoff_packet.md`.
- Keep the checklist note coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. the current mixed-ready `status/handoff` state
2. the missing-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
