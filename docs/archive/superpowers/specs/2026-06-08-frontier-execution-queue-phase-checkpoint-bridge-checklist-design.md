# Frontier Execution Queue Phase Checkpoint Bridge Checklist Design

## Goal

Add a bridge checklist for the `frontier_execution_queue` phase checkpoint card so future agents can verify the current checkpoint completion signal before reopening the milestone card.

## Why This Increment

The `frontier_execution_queue` stack already has:

- runbook card
- runbook bridge checklist
- phase checkpoint card
- milestone card
- completion dashboard
- completion dashboard bridge checklist

What is still missing inside this narrower subchain is an explicit bridge between the phase checkpoint card and the milestone card. Adding that bridge makes the local progression more consistent with the existing status/handoff coordination pattern and removes an avoidable gap in the execution queue handoff packet.

## Inputs

- `results/tables/frontier_execution_queue_phase_checkpoint_card.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_phase_checkpoint_bridge_checklist.csv`
- `results/tables/frontier_execution_queue_phase_checkpoint_bridge_checklist.json`
- `results/figures/frontier_execution_queue_phase_checkpoint_bridge_checklist.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`

## Proposed Fields

- `checklist_order`
- `checkpoint_frontier`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Use the phase checkpoint card to determine the current checkpoint frontier.
- Set `prerequisite_artifact` to `results/figures/frontier_execution_queue_phase_checkpoint_card.md`.
- Set `receipt_target` to `results/figures/frontier_execution_queue_milestone_card.md`.
- Carry the checkpoint completion signal forward in the bridge note.
- Refresh the execution queue handoff packet so it includes the new bridge layer.

## Testing

Add unit coverage for:

1. the current checkpoint state linking to the milestone card
2. the empty-checkpoint fallback state
3. the packet section-count refresh after the new bridge layer is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution or external staging is claimed.
