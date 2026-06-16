# Frontier Operator Next-Action Status Handoff Milestone Card Design

## Goal

Add a milestone card for the top-level `status/handoff` subchain so future agents can see what the current ready-lane checkpoint unlocks next and how many top-level lanes remain after that checkpoint closes.

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
- status handoff phase checkpoint card

The natural adjacent next layer, following existing repository patterns, is a milestone card that defines the immediate unlock boundary after the current ready-lane checkpoint closes.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.json`
- `results/tables/frontier_operator_next_action_status_handoff.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_milestone_card.csv`
- `results/tables/frontier_operator_next_action_status_handoff_milestone_card.json`
- `results/figures/frontier_operator_next_action_status_handoff_milestone_card.md`

## Proposed Fields

- `next_milestone`
- `unlocks`
- `remaining_frontier_count`
- `milestone_note`

## Milestone Rules

- Use the second handoff row, when present, as the explicit next unlocked target.
- `next_milestone = ready_lane_checkpoint_complete`
- `remaining_frontier_count = max(total_lane_count - 1, 0)`
- Keep the note coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. the current mixed-ready two-lane state
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No experiment execution is claimed.
