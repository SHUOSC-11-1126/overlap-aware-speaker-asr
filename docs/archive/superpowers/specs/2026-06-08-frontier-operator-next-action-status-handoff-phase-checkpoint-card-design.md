# Frontier Operator Next-Action Status Handoff Phase Checkpoint Card Design

## Goal

Add a phase checkpoint card for the top-level `status/handoff` subchain so future agents can see the exact completion signal for the current ready-lane step without reopening the broader runbook flow.

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
- status handoff runbook card

The natural adjacent next layer, following existing repository patterns, is a phase checkpoint card derived directly from that runbook card.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_runbook_card.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_phase_checkpoint_card.csv`
- `results/tables/frontier_operator_next_action_status_handoff_phase_checkpoint_card.json`
- `results/figures/frontier_operator_next_action_status_handoff_phase_checkpoint_card.md`

## Proposed Fields

- `checkpoint_frontier`
- `checkpoint_action`
- `completion_signal`
- `checkpoint_note`

## Checkpoint Rules

- Use the runbook `recommended_frontier`, `recommended_action`, and `completion_signal`.
- Keep the note coordination-only and frame it as a gate before advancing the `status/handoff` subchain.

## Testing

Add unit coverage for:

1. the current ready-lane state using the runbook completion signal
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No experiment execution is claimed.
