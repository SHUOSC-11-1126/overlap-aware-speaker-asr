# Frontier Execution Queue Runbook Card Design

## Goal

Add a runbook card for the `frontier_execution_queue` stack so the new operator-facing path narrows from a plain-language brief into one explicit first-action execution card.

## Why This Increment

The execution queue now has:

- status
- status bridge checklist
- completion summary
- completion summary bridge checklist
- handoff
- handoff bridge checklist
- handoff packet
- handoff packet bridge checklist
- operator brief

What is still missing is the first-action execution card that turns the operator brief into a narrower completion gate. This is the next structural step toward giving the execution queue a reentry path closer to the stronger `status/handoff` and receipt-fill stacks.

## Inputs

- `results/tables/frontier_execution_queue_operator_brief.json`
- `results/tables/frontier_execution_queue_handoff.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_runbook_card.csv`
- `results/tables/frontier_execution_queue_runbook_card.json`
- `results/figures/frontier_execution_queue_runbook_card.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`

## Proposed Fields

- `recommended_frontier`
- `recommended_action`
- `required_evidence`
- `completion_signal`
- `urgency`
- `runbook_note`

## Runbook Rules

- Use the operator brief frontier as the current runbook target.
- Resolve the matching execution queue handoff row so the completion signal can name the exact receipt artifact.
- Carry `operator_evidence` and `operator_urgency` forward.
- Refresh the handoff packet so it includes the new runbook card section.

## Testing

Add unit coverage for:

1. the first-frontier targeting path
2. the empty-input fallback
3. the packet section-count refresh after the new runbook card is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution or external staging is claimed.
