# Frontier Execution Queue Receipt Open Card Design

## Goal

Add a receipt open card for the `frontier_execution_queue` stack so future agents can see the first receipt target to open after the handoff bridge checklist is verified.

## Why This Increment

The execution queue handoff bridge checklist already maps each frontier to its receipt target. A one-row receipt open card gives the next contributor a compact action view for the first frontier without rereading the full handoff bridge table.

This remains coordination-only. It does not fill any receipt, run any benchmark, stage external audio, or alter stable/gold outputs.

## Inputs

- `results/tables/frontier_execution_queue_handoff_bridge_checklist.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_receipt_open_card.csv`
- `results/tables/frontier_execution_queue_receipt_open_card.json`
- `results/figures/frontier_execution_queue_receipt_open_card.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`

## Proposed Fields

- `frontier_name`
- `chain_status`
- `receipt_target`
- `open_action`
- `open_note`

## Card Rules

- Use the first handoff bridge checklist row as the current receipt-open target.
- Carry forward `frontier_name`, `chain_status`, and `receipt_target`.
- Keep the open action explicitly coordination-only.
- Refresh the execution queue handoff packet so it includes the new receipt open card.

## Testing

Add unit coverage for:

1. the handoff bridge to receipt open card summarization path
2. the empty-input fallback state
3. the packet section-count refresh after the new card is added

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution, receipt filling, or external staging is claimed.
