# Frontier Operator Next-Action Status Handoff Status Preflight Bridge Checklist Design

## Goal

Add an explicit preflight bridge checklist between the `status/handoff` completion-dashboard bridge layer and the machine-readable status rollup so the final transition before the packet-closing status layer is visible and coordination-only.

## Why This Increment

The current `status/handoff` chain already makes the operator brief, runbook, phase checkpoint, milestone, and completion dashboard transitions explicit. The remaining implicit step is:

- `completion_dashboard_bridge_checklist -> status`

Adding a preflight bridge checklist keeps the chain uniform and avoids jumping straight from a human-facing verification gate into the machine-readable rollup.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_completion_dashboard_bridge_checklist.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_status_preflight_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_status_preflight_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_status_preflight_bridge_checklist.md`
- refreshed `results/tables/frontier_operator_next_action_status_handoff_packet.csv`
- refreshed `results/tables/frontier_operator_next_action_status_handoff_packet.json`
- refreshed `results/figures/frontier_operator_next_action_status_handoff_packet.md`

## Proposed Fields

- `checklist_order`
- `current_first_frontier`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Read the first row from `frontier_operator_next_action_status_handoff_completion_dashboard_bridge_checklist.json`.
- Keep `results/figures/frontier_operator_next_action_status_handoff_completion_dashboard_bridge_checklist.md` as the prerequisite artifact.
- Point `receipt_target` at `results/figures/frontier_operator_next_action_status_handoff_status.md`.
- Carry the prior dashboard-bridge gate wording into the bridge note.
- Refresh the top-level packet so it includes this new preflight layer before the status rollup.

## Testing

Add unit coverage for:

1. the dashboard-bridge-to-status linking path
2. the empty-input fallback
3. the packet section-count refresh after the new preflight layer is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
