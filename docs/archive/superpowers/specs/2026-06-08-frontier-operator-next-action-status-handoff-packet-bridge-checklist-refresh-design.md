# Frontier Operator Next-Action Status Handoff Packet Bridge Checklist Refresh Design

## Goal

Refresh the top-level `status/handoff` packet bridge checklist so it matches the refreshed packet shape and points future agents at the newer `status_handoff_status` rollup instead of the older completion-summary-only layer.

## Why This Increment

The packet bridge checklist was created before the `status/handoff` subchain gained:

- `status_handoff_status`
- `status_handoff_status_bridge_checklist`

The packet itself has now been refreshed, but the bridge checklist still reopens `status_handoff_completion_summary`, which no longer reflects the newest single-step reentry point. Refreshing the bridge keeps the packet and its next gate aligned.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_status.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_packet_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_packet_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_packet_bridge_checklist.md`

## Refresh Rules

- Keep the existing single-row checklist shape.
- Read `combined_status_handoff_state` and `primary_status_target` from the `status_handoff_status` rollup.
- Keep `results/figures/frontier_operator_next_action_status_handoff_packet.md` as `prerequisite_artifact`.
- Change `receipt_target` to `results/figures/frontier_operator_next_action_status_handoff_status.md`.
- Keep the checklist coordination-only and avoid any claim of frontier execution.

## Testing

Update unit coverage so it asserts:

1. the refreshed bridge points to `status_handoff_status.md`
2. the bridge note includes `combined_status_handoff_state`

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
