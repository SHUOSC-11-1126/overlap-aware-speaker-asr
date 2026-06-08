# Frontier Operator Next-Action Status Handoff Operator Brief Bridge Design

## Goal

Add a bridge artifact between the top-level `status/handoff` operator brief and the current runbook card so future agents can see the exact reentry hop after reopening the packet and brief.

## Why This Increment

The `status/handoff` subchain already has:

- packet bridge checklist -> operator brief
- operator brief
- runbook card

What is still missing is the explicit bridge between the brief and the runbook card. Adding it keeps the reopening path legible end to end and matches the repository's broader pattern of making each handoff step explicit.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_operator_brief.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_operator_brief_bridge.csv`
- `results/tables/frontier_operator_next_action_status_handoff_operator_brief_bridge.json`
- `results/figures/frontier_operator_next_action_status_handoff_operator_brief_bridge.md`

## Proposed Fields

- `reentry_frontier`
- `prerequisite_artifact`
- `receipt_target`
- `bridge_note`

## Bridge Rules

- Read `ready_frontier` and `operator_urgency` from the operator brief.
- Use `results/figures/frontier_operator_next_action_status_handoff_operator_brief.md` as `prerequisite_artifact`.
- Use `results/figures/frontier_operator_next_action_status_handoff_runbook_card.md` as `receipt_target`.
- Keep the bridge coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. the current ready frontier state
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
