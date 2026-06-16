# Frontier Execution Queue Operator Brief Design

## Goal

Add a plain-language operator brief for the `frontier_execution_queue` stack so contributors can reopen the queue through a concise “what should I do first” artifact instead of reading only machine-friendly status and handoff tables.

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

What is still missing is the operator-facing summary layer that turns the first handoff row into one explicit next-step card. This mirrors the higher-quality operator experience already present in the newer `status/handoff` and receipt-fill stacks.

## Inputs

- `results/tables/frontier_execution_queue_completion_summary.json`
- `results/tables/frontier_execution_queue_handoff.json`

## Output Artifacts

- `results/tables/frontier_execution_queue_operator_brief.csv`
- `results/tables/frontier_execution_queue_operator_brief.json`
- `results/figures/frontier_execution_queue_operator_brief.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.csv`
- refreshed `results/tables/frontier_execution_queue_handoff_packet.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet.md`
- refreshed `results/tables/frontier_execution_queue_handoff_packet_bridge_checklist.json`
- refreshed `results/figures/frontier_execution_queue_handoff_packet_bridge_checklist.md`

## Proposed Fields

- `operator_frontier`
- `operator_action`
- `operator_receipt`
- `operator_evidence`
- `operator_urgency`
- `operator_note`

## Brief Rules

- Use the first handoff row as the current operator target.
- Carry `queue_status`, `ready_chain_count`, and `pending_chain_count` into `operator_urgency`.
- Point `operator_evidence` at the execution queue handoff and its bridge checklist.
- Refresh the handoff packet so it includes the new operator brief.
- Refresh the packet bridge checklist so it reopens the operator brief instead of jumping directly back to status.

## Testing

Add unit coverage for:

1. the first-handoff targeting path
2. the empty-input fallback
3. the packet section-count refresh
4. the packet-bridge target shift to operator brief

## Boundaries

- No gold references or benchmark outputs are changed.
- No routing or evaluation logic changes.
- No benchmark execution or external staging is claimed.
