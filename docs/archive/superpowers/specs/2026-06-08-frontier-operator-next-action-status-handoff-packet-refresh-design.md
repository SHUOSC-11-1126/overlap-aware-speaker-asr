# Frontier Operator Next-Action Status Handoff Packet Refresh Design

## Goal

Refresh the top-level `status/handoff` packet so it absorbs the newly added `status` rollup and `status` bridge checklist layers, giving future agents a single-entry coordination artifact that matches the current subchain shape.

## Why This Increment

The existing `status/handoff` packet was generated before the subchain gained:

- `status_handoff_status`
- `status_handoff_status_bridge_checklist`

As a result, the packet is now stale: it exposes only the older six-section stack and no longer reflects the current coordination path. Refreshing the packet keeps the stable baseline untouched while making the frontier handoff stack resumable from one accurate packet.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_packet.csv`
- `results/tables/frontier_operator_next_action_status_handoff_packet.json`
- `results/figures/frontier_operator_next_action_status_handoff_packet.md`

## Packet Refresh Rules

- Preserve the original packet ordering for the first six legacy sections.
- Append `status_handoff_status` after the completion summary bridge checklist.
- Append `status_handoff_status_bridge_checklist` after `status_handoff_status`.
- Keep `packet_note` coordination-only and avoid any claim of frontier execution.

## Testing

Update unit coverage so it asserts:

1. the refreshed packet now includes eight sections
2. the last section is `status_handoff_status_bridge_checklist`

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation behavior changes.
- No frontier execution is claimed.
