# Frontier Operator Next-Action Status Handoff Design

## Goal

Add a top-level `experimental/frontier` handoff view driven by `frontier_operator_next_action_status` so future agents can see the immediate ready-lane action and blocked-lane containment action without reopening the full packet first.

## Why This Increment

The top-level operator chain now has:

- a machine-readable status rollup
- a status bridge checklist
- a broader handoff packet

What is still missing is a compact action-dispatch handoff derived directly from the current top-level status. This keeps the frontier stack consistent with other handoff-oriented coordination layers while preserving the stable baseline.

## Inputs

- `results/tables/frontier_operator_next_action_status.json`
- `results/tables/frontier_operator_next_action_card.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff.csv`
- `results/tables/frontier_operator_next_action_status_handoff.json`
- `results/figures/frontier_operator_next_action_status_handoff.md`

## Proposed Fields

- `handoff_order`
- `action_lane`
- `frontier_name`
- `combined_operator_status`
- `recommended_action`
- `expected_inputs`
- `expected_outputs`
- `handoff_note`

## Handoff Rules

- Use the card rows to preserve the existing ready/block frontier names and target artifacts.
- Emit one row per available action lane from the current card.
- Carry `combined_operator_status` from the status rollup into each row.
- For the ready lane, preserve the operator action as the recommended next action.
- For the blocked lane, preserve the blocker action and frame it as containment before broader frontier reopening.
- `expected_inputs` should point to the status note and the status bridge checklist.
- `expected_outputs` should point to the lane-specific `target_artifact` already recorded by the card.

## Testing

Add unit coverage for:

1. a mixed-ready state with both ready and blocked lanes
2. an empty-input fallback with no action rows

## Boundaries

- No gold references or verified results are touched.
- No routing behavior changes.
- No frontier execution is claimed.
- This remains coordination support only.
