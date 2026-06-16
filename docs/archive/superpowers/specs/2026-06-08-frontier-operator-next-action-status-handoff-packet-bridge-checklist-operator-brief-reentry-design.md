# Frontier Operator Next-Action Status Handoff Packet Bridge Checklist Operator Brief Reentry Design

## Goal

Refresh the top-level `status/handoff` packet bridge checklist so it clearly reopens the `status_handoff_operator_brief` as the preferred plain-language reentry point after packet verification.

## Why This Increment

The packet bridge checklist already points at `status_handoff_operator_brief`, but its structure still exposes a generic `ready_frontier` field rather than using the brief's own naming and evidence framing. This makes the reentry target slightly less explicit than it could be.

Refreshing the checklist keeps the packet and the brief aligned and makes the operator brief the obvious next artifact to open after packet verification.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_operator_brief.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_packet_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_packet_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_packet_bridge_checklist.md`

## Refresh Rules

- Keep the existing single-row checklist shape.
- Replace the generic frontier field with `reentry_frontier`.
- Read `ready_frontier` and `operator_urgency` from the operator brief.
- Keep `results/figures/frontier_operator_next_action_status_handoff_packet.md` as `prerequisite_artifact`.
- Keep `results/figures/frontier_operator_next_action_status_handoff_operator_brief.md` as `receipt_target`.
- Keep the checklist coordination-only and avoid any claim of frontier execution.

## Testing

Update unit coverage so it asserts:

1. the refreshed bridge records `reentry_frontier`
2. the bridge note includes `operator_urgency`
3. the target remains `status_handoff_operator_brief.md`

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
