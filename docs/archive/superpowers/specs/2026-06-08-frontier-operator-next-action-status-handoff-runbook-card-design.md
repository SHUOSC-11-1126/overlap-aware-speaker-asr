# Frontier Operator Next-Action Status Handoff Runbook Card Design

## Goal

Add a one-page runbook card for the top-level `status/handoff` subchain so future agents can see the current ready-lane action, evidence path, and completion signal without reopening the broader packet.

## Why This Increment

The top-level operator `status/handoff` subchain now has:

- status
- status bridge checklist
- status handoff
- status handoff bridge checklist
- status handoff completion summary
- status handoff completion summary bridge checklist
- status handoff packet
- status handoff packet bridge checklist
- status handoff operator brief

The natural adjacent next layer, following existing repository patterns, is a runbook card derived from that operator brief.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_operator_brief.json`
- `results/tables/frontier_operator_next_action_status_handoff.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_runbook_card.csv`
- `results/tables/frontier_operator_next_action_status_handoff_runbook_card.json`
- `results/figures/frontier_operator_next_action_status_handoff_runbook_card.md`

## Proposed Fields

- `recommended_frontier`
- `recommended_action`
- `required_evidence`
- `completion_signal`
- `urgency`
- `runbook_note`

## Runbook Rules

- Use the operator brief `ready_frontier`, `ready_action`, and `operator_evidence`.
- Use the first `ready_lane` handoff row to surface the ready target artifact in `completion_signal`.
- Keep the urgency copied from the operator brief.
- Keep the note coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. the current ready-lane state with a ready target artifact
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No experiment execution is claimed.
