# Frontier Operator Next-Action Status Handoff Packet Bridge Checklist Operator Brief Refresh Design

## Goal

Refresh the top-level `status/handoff` packet bridge checklist so it reopens the most useful current reentry artifact: `status_handoff_operator_brief`.

## Why This Increment

After the full packet refresh, the packet now contains the entire current `status/handoff` subchain, including:

- `status_handoff_operator_brief`
- `status_handoff_runbook_card`
- `status_handoff_phase_checkpoint_card`
- `status_handoff_milestone_card`
- `status_handoff_completion_dashboard`
- `status_handoff_completion_dashboard_bridge_checklist`
- `status_handoff_status`
- `status_handoff_status_bridge_checklist`

The existing packet bridge checklist still points to `status_handoff_status`, which is machine-readable but not the most ergonomic reentry point for future agents. The operator brief is now the better reopening target because it provides the same current frontier signal in a plain-language one-page handoff.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_operator_brief.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_packet_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_packet_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_packet_bridge_checklist.md`

## Refresh Rules

- Keep the existing single-row checklist shape.
- Read `ready_frontier` and `operator_urgency` from the operator brief.
- Keep `results/figures/frontier_operator_next_action_status_handoff_packet.md` as `prerequisite_artifact`.
- Change `receipt_target` to `results/figures/frontier_operator_next_action_status_handoff_operator_brief.md`.
- Keep the checklist coordination-only and avoid any claim of frontier execution.

## Testing

Update unit coverage so it asserts:

1. the refreshed bridge points to `status_handoff_operator_brief.md`
2. the bridge note includes `operator_urgency`

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
