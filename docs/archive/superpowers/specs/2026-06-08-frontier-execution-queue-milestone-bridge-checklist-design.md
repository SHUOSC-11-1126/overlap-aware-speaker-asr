# Frontier Execution Queue Milestone Bridge Checklist Design

## Goal

Add a bridge checklist for the `frontier_execution_queue` milestone card so future agents can verify the milestone unlock path before reopening the completion dashboard.

## Why This Increment

The execution queue now has a phase checkpoint bridge and a completion dashboard bridge, but the milestone card still connects to the dashboard without its own verification artifact. Adding this bridge makes the local chain explicit:

- phase checkpoint card
- phase checkpoint bridge checklist
- milestone card
- milestone bridge checklist
- completion dashboard

This is a coordination-only extension that keeps the frontier queue easier to reopen without changing any ASR, routing, or benchmark logic.

## Inputs

- `results/tables/frontier_execution_queue_milestone_card.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_milestone_bridge_checklist.csv`
- `results/tables/frontier_execution_queue_milestone_bridge_checklist.json`
- `results/figures/frontier_execution_queue_milestone_bridge_checklist.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`

## Proposed Fields

- `checklist_order`
- `next_milestone`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Use the milestone card to determine the next milestone.
- Set `prerequisite_artifact` to `results/figures/frontier_execution_queue_milestone_card.md`.
- Set `receipt_target` to `results/figures/frontier_execution_queue_completion_dashboard.md`.
- Carry the milestone unlock path forward in the bridge note.
- Refresh the execution queue handoff packet so it includes the new bridge layer.

## Testing

Add unit coverage for:

1. the current milestone state linking to the completion dashboard
2. the empty-milestone fallback state
3. the packet section-count refresh after the new bridge layer is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution or external staging is claimed.
