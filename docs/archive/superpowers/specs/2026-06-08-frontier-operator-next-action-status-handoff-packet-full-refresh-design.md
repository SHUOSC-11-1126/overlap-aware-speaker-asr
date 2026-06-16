# Frontier Operator Next-Action Status Handoff Packet Full Refresh Design

## Goal

Refresh the top-level `status/handoff` packet again so it reflects the full current subchain, including the later-added operator brief, runbook, checkpoint, milestone, completion dashboard, completion dashboard bridge, status rollup, and status bridge.

## Why This Increment

The packet was recently refreshed to absorb:

- `status_handoff_status`
- `status_handoff_status_bridge_checklist`

But the packet still omits other already-generated `status/handoff` artifacts that sit between the legacy summary stack and the newer status rollup:

- `status_handoff_operator_brief`
- `status_handoff_runbook_card`
- `status_handoff_phase_checkpoint_card`
- `status_handoff_milestone_card`
- `status_handoff_completion_dashboard`
- `status_handoff_completion_dashboard_bridge_checklist`

That leaves the packet only partially up to date. Refreshing it again makes the packet a true single-entry artifact for the current subchain shape.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_packet.csv`
- `results/tables/frontier_operator_next_action_status_handoff_packet.json`
- `results/figures/frontier_operator_next_action_status_handoff_packet.md`

## Refresh Rules

- Preserve the original ordering of the legacy packet sections.
- Insert the newer `operator_brief`, `runbook_card`, `phase_checkpoint_card`, `milestone_card`, `completion_dashboard`, and `completion_dashboard_bridge_checklist` layers before the `status_handoff_status` rollup.
- Keep `status_handoff_status` and `status_handoff_status_bridge_checklist` as the final two sections.
- Keep `packet_note` coordination-only and avoid any claim of frontier execution.

## Testing

Update unit coverage so it asserts:

1. the refreshed packet now includes fourteen sections
2. the new intermediate sections are present
3. the last section remains `status_handoff_status_bridge_checklist`

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation behavior changes.
- No frontier execution is claimed.
