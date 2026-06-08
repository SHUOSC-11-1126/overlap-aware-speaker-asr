# Frontier Operator Next-Action Status Handoff Operator Brief Bridge Checklist Design

## Goal

Add a checklist for the `status/handoff` operator brief bridge so future agents can verify the bridge before reopening the current runbook card target.

## Why This Increment

The `status/handoff` subchain now has:

- packet bridge checklist -> operator brief
- operator brief
- operator brief bridge -> runbook card
- runbook card

What is still missing is the verification checklist for that new bridge. Adding it makes the reopening path explicit all the way from packet to runbook and matches the repository's usual bridge -> bridge checklist pairing.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_operator_brief_bridge.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_operator_brief_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_operator_brief_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_operator_brief_bridge_checklist.md`

## Proposed Fields

- `checklist_order`
- `reentry_frontier`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Read the bridge row from `frontier_operator_next_action_status_handoff_operator_brief_bridge.json`.
- Preserve `reentry_frontier`, `prerequisite_artifact`, and `receipt_target`.
- Keep the checklist coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. the current ready frontier state
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
