# Frontier Operator Next-Action Status Handoff Packet Design

## Goal

Add a single-entry packet for the top-level operator `status -> handoff` subchain so future agents can open the current status snapshot, lane handoff, queue summary, and bridge checkpoints in one place.

## Why This Increment

The top-level operator status subchain now has:

- status
- status bridge checklist
- status handoff
- status handoff bridge checklist
- status handoff completion summary
- status handoff completion summary bridge checklist

The natural next layer is a packet that consolidates these six artifacts into one entrypoint, matching the packet pattern already used elsewhere in this repository.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_packet.csv`
- `results/tables/frontier_operator_next_action_status_handoff_packet.json`
- `results/figures/frontier_operator_next_action_status_handoff_packet.md`

## Proposed Fields

- `packet_order`
- `section_name`
- `artifact_path`
- `section_role`
- `packet_note`

## Packet Sections

1. `status`
2. `status_bridge_checklist`
3. `status_handoff`
4. `status_handoff_bridge_checklist`
5. `status_handoff_completion_summary`
6. `status_handoff_completion_summary_bridge_checklist`

## Summary Rules

- Read `queue_status`, `ready_lane_count`, and `blocked_lane_count` from the completion summary.
- Include those values in each `packet_note`.
- Keep all notes coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. all six sections being present
2. the first section remaining `status`

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No experiment execution is claimed.
