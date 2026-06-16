# Frontier Execution Queue Status Reentry Card Design

## Goal

Add a status reentry card for the `frontier_execution_queue` stack so future agents have a one-page instruction for reopening the execution queue status rollup after the status preflight bridge is verified.

## Why This Increment

The status preflight bridge records the verification gate before reopening the status rollup. A small reentry card makes the next action explicit by combining:

- the current first frontier from the status preflight bridge
- the status rollup target from the same bridge
- the combined execution-chain status from the status JSON

This is coordination-only and keeps the queue refresh path easier to resume without touching benchmark logic.

## Inputs

- `results/tables/frontier_execution_queue_status_preflight_bridge_checklist.json`
- `results/tables/frontier_execution_queue_status.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_status_reentry_card.csv`
- `results/tables/frontier_execution_queue_status_reentry_card.json`
- `results/figures/frontier_execution_queue_status_reentry_card.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`

## Proposed Fields

- `current_first_frontier`
- `status_rollup_target`
- `combined_chain_status`
- `reentry_action`
- `reentry_note`

## Card Rules

- Use the first status preflight bridge row as the source of the current first frontier.
- Use the preflight bridge `receipt_target` as the status rollup target.
- Use the status JSON `combined_chain_status` as the current status context.
- Keep the action text coordination-only and avoid any benchmark execution claim.
- Refresh the execution queue handoff packet so it includes the new reentry card.

## Testing

Add unit coverage for:

1. the status preflight plus status summarization path
2. the empty-input fallback state
3. the packet section-count refresh after the new card is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution or external staging is claimed.
