# Frontier Execution Queue Status Reentry Bridge Checklist Design

## Goal

Add a bridge checklist for the `frontier_execution_queue` status reentry card so future agents can verify the reentry instruction before opening the execution queue handoff bridge.

## Why This Increment

The execution queue now has a status reentry card that explains how to reopen the queue status rollup after status preflight. The next adjacent coordination layer is a bridge checklist that confirms that reentry card before moving into the handoff bridge. This keeps the tail of the packet explicit:

- status preflight bridge checklist
- status reentry card
- status reentry bridge checklist
- handoff bridge checklist

This is a coordination-only extension and does not change any ASR, routing, or evaluation behavior.

## Inputs

- `results/tables/frontier_execution_queue_status_reentry_card.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_status_reentry_bridge_checklist.csv`
- `results/tables/frontier_execution_queue_status_reentry_bridge_checklist.json`
- `results/figures/frontier_execution_queue_status_reentry_bridge_checklist.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`

## Proposed Fields

- `checklist_order`
- `current_first_frontier`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Use the status reentry card to determine the current first frontier.
- Set `prerequisite_artifact` to `results/figures/frontier_execution_queue_status_reentry_card.md`.
- Set `receipt_target` to `results/figures/frontier_execution_queue_handoff_bridge_checklist.md`.
- Carry the reentry action forward in the bridge note.
- Refresh the execution queue handoff packet so it includes the new bridge layer.

## Testing

Add unit coverage for:

1. the current reentry card linking to the handoff bridge
2. the empty-reentry fallback state
3. the packet section-count refresh after the new bridge layer is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution or external staging is claimed.
