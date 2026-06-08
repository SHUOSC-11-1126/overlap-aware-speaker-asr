# Frontier Operator Next-Action Status Bridge Checklist Design

## Goal

Add a top-level bridge checklist for `frontier_operator_next_action_status` so future agents verify the unified operator status rollup before opening the broader operator handoff packet.

## Why This Increment

The top-level operator chain now has a machine-readable status snapshot, but it still lacks the same bridge layer already used elsewhere in the repository:

- status rollup
- bridge checklist
- handoff or next receipt target

Adding that bridge preserves the stable baseline while making the frontier coordination chain more consistent and easier to resume.

## Inputs

- `results/tables/frontier_operator_next_action_status.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_bridge_checklist.md`

## Bridge Shape

The checklist should remain a single-row coordination artifact with:

- `checklist_order`
- `combined_operator_status`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Target Choice

- `prerequisite_artifact`: `results/figures/frontier_operator_next_action_status.md`
- `receipt_target`: `results/figures/frontier_operator_next_action_handoff_packet.md`

This keeps the bridge at the operator layer instead of dropping immediately back to a narrower runbook artifact.

## Status Rules

- Default `combined_operator_status` to `operator_status_unset` when the status file is missing or incomplete.
- The bridge note should echo the combined status and the current primary status target.
- The checklist must explicitly state that it is coordination-only and does not claim frontier execution.

## Testing

Add unit coverage for:

1. a populated mixed-ready status row
2. the empty-input fallback state

## Boundaries

- No gold or verified references are touched.
- No routing or evaluation logic changes.
- No experiment execution is claimed.
