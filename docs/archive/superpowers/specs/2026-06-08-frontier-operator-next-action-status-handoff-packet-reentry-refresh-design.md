# Frontier Operator Next-Action Status Handoff Packet Reentry Refresh Design

## Goal

Refresh the top-level `status/handoff` packet so it explicitly lists the newer reentry layers that now sit between the operator brief and the phase checkpoint card.

## Why This Increment

The `status/handoff` packet is intended to be the single-entry artifact for future contributors, but it currently stops short of the newest bridge layers. The current reentry path now includes:

- packet bridge checklist -> operator brief
- operator brief bridge
- operator brief bridge checklist
- runbook card
- runbook bridge checklist
- phase checkpoint card

If the packet omits those middle layers, its summary is no longer a faithful map of the current coordination chain.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.json`
- existing packet section definitions

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_packet.csv`
- `results/tables/frontier_operator_next_action_status_handoff_packet.json`
- `results/figures/frontier_operator_next_action_status_handoff_packet.md`

## Proposed Change

- Extend the packet section list to include:
  - `status_handoff_operator_brief_bridge`
  - `status_handoff_operator_brief_bridge_checklist`
  - `status_handoff_runbook_bridge_checklist`
- Preserve the existing coordination-only note style.
- Keep the packet bridge checklist reentry target on the plain-language operator brief for now.

## Testing

Add or update unit coverage so the packet row builder asserts:

1. the full section count after the refresh
2. the ordered presence of the new bridge layers
3. the existing final status bridge checklist remains the packet tail

## Boundaries

- No gold references or benchmark results are changed.
- No routing or evaluation logic changes.
- No packet field schema changes beyond the additional section rows.
