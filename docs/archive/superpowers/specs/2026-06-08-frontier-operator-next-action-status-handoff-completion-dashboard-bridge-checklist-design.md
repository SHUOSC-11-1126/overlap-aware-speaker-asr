# Frontier Operator Next-Action Status Handoff Completion Dashboard Bridge Checklist Design

## Goal

Add a bridge checklist for the top-level `status/handoff` completion dashboard so future agents can verify the dashboard snapshot before reopening the next `status/handoff` target artifact.

## Why This Increment

The `status/handoff` subchain now has:

- status handoff
- status handoff bridge checklist
- status handoff completion summary
- status handoff completion summary bridge checklist
- status handoff packet
- status handoff packet bridge checklist
- status handoff operator brief
- status handoff runbook card
- status handoff phase checkpoint card
- status handoff milestone card
- status handoff completion dashboard

The natural adjacent next layer, following existing repository patterns, is a bridge checklist that turns the new dashboard into a verification step before the next `status/handoff` action artifact is reopened.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_completion_dashboard.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_completion_dashboard_bridge_checklist.csv`
- `results/tables/frontier_operator_next_action_status_handoff_completion_dashboard_bridge_checklist.json`
- `results/figures/frontier_operator_next_action_status_handoff_completion_dashboard_bridge_checklist.md`

## Proposed Fields

- `checklist_order`
- `current_first_frontier`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Checklist Rules

- Use the dashboard row to determine the current first frontier.
- Set `prerequisite_artifact` to the new dashboard Markdown note.
- Set `receipt_target` to `results/figures/frontier_operator_next_action_status_handoff_runbook_card.md`.
- Keep the checklist note coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. the current mixed-ready dashboard state
2. the empty-dashboard fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
