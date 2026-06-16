# Frontier Operator Next-Action Status Handoff Runbook Bridge Checklist Design

## Goal

Add a checklist that links the `status/handoff` runbook card to the phase checkpoint card so future agents can verify the runbook before opening the narrower completion checkpoint.

## Why This Increment

The `status/handoff` path now has an explicit reopening chain up through:

- packet bridge checklist -> operator brief
- operator brief bridge
- operator brief bridge checklist
- runbook card

What is still missing is the verification step between the runbook card and the phase checkpoint card. Adding it keeps the path explicit and consistent with similar bridge -> checklist patterns elsewhere in the repo.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_runbook_card.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_runbook_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_runbook_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_runbook_bridge_checklist.md`

## Proposed Fields

- `checklist_order`
- `recommended_frontier`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Read the runbook row from `frontier_operator_next_action_status_handoff_runbook_card.json`.
- Preserve `recommended_frontier`.
- Use `results/figures/frontier_operator_next_action_status_handoff_runbook_card.md` as `prerequisite_artifact`.
- Use `results/figures/frontier_operator_next_action_status_handoff_phase_checkpoint_card.md` as `receipt_target`.
- Keep the checklist coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. the current ready frontier state
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
