# Frontier Execution Queue Phase Checkpoint Card Design

## Goal

Add a phase checkpoint card for the `frontier_execution_queue` stack so the first execution-queue path now has a narrower completion gate between the runbook/bridge layers and the broader handoff receipt path.

## Why This Increment

The execution queue chain already has:

- packet
- packet bridge checklist
- operator brief
- runbook card
- runbook bridge checklist

The next missing piece is the narrower checkpoint that says exactly what completion signal must be satisfied before contributors consider the current first execution-queue step advanced. This keeps the queue structure moving toward the stronger multi-layer gate shape already used in the other coordination stacks.

## Inputs

- `results/tables/frontier_execution_queue_runbook_card.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_phase_checkpoint_card.csv`
- `results/tables/frontier_execution_queue_phase_checkpoint_card.json`
- `results/figures/frontier_execution_queue_phase_checkpoint_card.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`

## Proposed Fields

- `checkpoint_frontier`
- `checkpoint_action`
- `completion_signal`
- `checkpoint_note`

## Checkpoint Rules

- Read the current execution-queue runbook row from `frontier_execution_queue_runbook_card.json`.
- Carry the runbook action and completion signal through directly.
- Refresh the execution queue handoff packet so it includes the new checkpoint layer.
- Keep the artifact coordination-only and avoid any benchmark or external staging claim.

## Testing

Add unit coverage for:

1. the runbook-to-checkpoint mapping path
2. the empty-input fallback
3. the packet section-count refresh after the new checkpoint card is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution or external staging is claimed.
