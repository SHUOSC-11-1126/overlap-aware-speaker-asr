# Frontier Operator Next-Action Status Handoff Phase Checkpoint Bridge Checklist Design

## Goal

Add an explicit bridge checklist between the `status/handoff` phase checkpoint card and the milestone card so the downstream transition stays visible and coordination-only.

## Why This Increment

The current `status/handoff` reopening path is explicit through the runbook and checkpoint layers, but the transition from `phase_checkpoint_card` into `milestone_card` is still implicit. Adding a bridge checklist keeps the chain symmetrical and makes the checkpoint completion signal the visible gate before the next milestone is reopened.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_phase_checkpoint_card.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_phase_checkpoint_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_phase_checkpoint_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_phase_checkpoint_bridge_checklist.md`
- refreshed `results/tables/frontier_operator_next_action_status_handoff_packet.csv`
- refreshed `results/tables/frontier_operator_next_action_status_handoff_packet.json`
- refreshed `results/figures/frontier_operator_next_action_status_handoff_packet.md`

## Proposed Fields

- `checklist_order`
- `checkpoint_frontier`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Read the checkpoint row from `frontier_operator_next_action_status_handoff_phase_checkpoint_card.json`.
- Keep `results/figures/frontier_operator_next_action_status_handoff_phase_checkpoint_card.md` as the prerequisite artifact.
- Point `receipt_target` at `results/figures/frontier_operator_next_action_status_handoff_milestone_card.md`.
- Carry the checkpoint completion signal into the bridge note.
- Refresh the top-level packet so it includes this new bridge layer.

## Testing

Add unit coverage for:

1. the checkpoint-to-milestone linking path
2. the empty-input fallback
3. the packet section-count refresh after the new bridge is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
