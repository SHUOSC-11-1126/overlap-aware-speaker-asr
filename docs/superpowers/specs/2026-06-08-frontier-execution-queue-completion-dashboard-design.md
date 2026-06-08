# Frontier Execution Queue Completion Dashboard Design

## Goal

Add a completion dashboard for the `frontier_execution_queue` stack so the chain now has a one-glance operator-facing state summary after the phase checkpoint and milestone layers.

## Why This Increment

The execution queue chain already has:

- packet
- packet bridge checklist
- operator brief
- runbook card
- runbook bridge checklist
- phase checkpoint card
- milestone card

What is still missing is the dashboard layer that compresses the current first frontier, next milestone, remaining frontiers, and dominant blocker into a single quick-read artifact. This is the natural next layer before any further bridge/status rollup refinement.

## Inputs

- `results/tables/frontier_execution_queue_operator_brief.json`
- `results/tables/frontier_execution_queue_milestone_card.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_completion_dashboard.csv`
- `results/tables/frontier_execution_queue_completion_dashboard.json`
- `results/figures/frontier_execution_queue_completion_dashboard.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`

## Proposed Fields

- `current_first_frontier`
- `next_milestone`
- `remaining_frontier_count`
- `dominant_blocker`
- `dashboard_note`

## Dashboard Rules

- Read the current first frontier from the execution queue operator brief.
- Read the next milestone and remaining frontier count from the milestone card.
- Use a stable coordination-only blocker label rather than implying benchmark execution.
- Refresh the execution queue handoff packet so it includes the new completion dashboard layer.

## Testing

Add unit coverage for:

1. the operator-brief plus milestone summarization path
2. the empty-input fallback
3. the packet section-count refresh after the new dashboard is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution or external staging is claimed.
