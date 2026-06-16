# Frontier Execution Queue Milestone Card Design

## Goal

Add a milestone card for the `frontier_execution_queue` stack so the chain explicitly records what the current first checkpoint unlocks next after the present execution-queue step closes.

## Why This Increment

The execution queue chain now has:

- packet
- packet bridge checklist
- operator brief
- runbook card
- runbook bridge checklist
- phase checkpoint card

The next missing layer is the milestone boundary that says what the current first checkpoint unlocks and how many visible execution fronts remain afterward. This keeps the chain aligned with the more mature coordination stacks in the repo.

## Inputs

- `results/tables/frontier_execution_queue_completion_summary.json`
- `results/tables/frontier_execution_queue_handoff.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_milestone_card.csv`
- `results/tables/frontier_execution_queue_milestone_card.json`
- `results/figures/frontier_execution_queue_milestone_card.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`

## Proposed Fields

- `next_milestone`
- `unlocks`
- `remaining_frontier_count`
- `milestone_note`

## Milestone Rules

- Use the second handoff row, when present, as the next unlocked frontier.
- Derive the remaining frontier count from the execution queue completion summary.
- Refresh the execution queue handoff packet so it includes the new milestone layer.
- Keep the artifact coordination-only and avoid any benchmark or external staging claim.

## Testing

Add unit coverage for:

1. the second-frontier unlock path
2. the empty-input fallback
3. the packet section-count refresh after the new milestone card is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution or external staging is claimed.
