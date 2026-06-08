# Frontier Operator Next-Action Status Handoff Milestone Bridge Checklist Design

## Goal

Add an explicit bridge checklist between the `status/handoff` milestone card and the completion dashboard so the downstream transition remains visible and coordination-only.

## Why This Increment

The current `status/handoff` chain is already explicit through the runbook, phase checkpoint, and milestone layers, but the handoff from `milestone_card` into `completion_dashboard` is still implicit. Adding a bridge checklist makes the unlock step visible before the dashboard is reopened.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_milestone_card.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_milestone_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_milestone_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_milestone_bridge_checklist.md`
- refreshed `results/tables/frontier_operator_next_action_status_handoff_packet.csv`
- refreshed `results/tables/frontier_operator_next_action_status_handoff_packet.json`
- refreshed `results/figures/frontier_operator_next_action_status_handoff_packet.md`

## Proposed Fields

- `checklist_order`
- `next_milestone`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Read the milestone row from `frontier_operator_next_action_status_handoff_milestone_card.json`.
- Keep `results/figures/frontier_operator_next_action_status_handoff_milestone_card.md` as the prerequisite artifact.
- Point `receipt_target` at `results/figures/frontier_operator_next_action_status_handoff_completion_dashboard.md`.
- Carry the milestone unlock path into the bridge note.
- Refresh the top-level packet so it includes this new bridge layer.

## Testing

Add unit coverage for:

1. the milestone-to-dashboard linking path
2. the empty-input fallback
3. the packet section-count refresh after the new bridge is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
