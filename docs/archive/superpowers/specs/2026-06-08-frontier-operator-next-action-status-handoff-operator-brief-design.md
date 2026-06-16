# Frontier Operator Next-Action Status Handoff Operator Brief Design

## Goal

Add a plain-language operator brief for the top-level `status/handoff` subchain so future agents can see, in one short card, the primary ready-lane action, the current blocked-lane target, and the evidence path they should follow next.

## Why This Increment

The top-level operator `status/handoff` subchain now has:

- status
- status bridge checklist
- status handoff
- status handoff bridge checklist
- status handoff completion summary
- status handoff completion summary bridge checklist
- status handoff packet
- status handoff packet bridge checklist

The natural next layer, following existing repository patterns, is a plain-language operator brief that makes the current queue actionable without reopening every underlying artifact.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.json`
- `results/tables/frontier_operator_next_action_status_handoff.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_operator_brief.csv`
- `results/tables/frontier_operator_next_action_status_handoff_operator_brief.json`
- `results/figures/frontier_operator_next_action_status_handoff_operator_brief.md`

## Proposed Fields

- `ready_frontier`
- `ready_action`
- `ready_target`
- `blocked_frontier`
- `blocked_target`
- `operator_evidence`
- `operator_urgency`
- `operator_note`

## Brief Rules

- Use the first `ready_lane` row as the primary action lane.
- Use the first `blocked_lane` row as the visible unblock lane.
- Read `queue_status`, `ready_lane_count`, and `blocked_lane_count` from the completion summary and surface them in `operator_urgency`.
- Point `operator_evidence` at the lane handoff and handoff bridge checklist.
- Keep the note coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. the current mixed-ready state with both ready and blocked lanes
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No experiment execution is claimed.
