# Frontier Operator Next-Action Status Handoff Completion Dashboard Design

## Goal

Add a completion dashboard for the top-level `status/handoff` subchain so future agents can see the current ready frontier, current blocked frontier, next milestone, remaining visible lanes, and dominant blocker in one glance.

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

The natural next layer, following existing repository patterns, is a completion dashboard that compresses the current `status/handoff` subchain into a single operator-facing snapshot.

## Inputs

- `results/tables/frontier_operator_next_action_status_handoff_operator_brief.json`
- `results/tables/frontier_operator_next_action_status_handoff_milestone_card.json`

## Output Artifacts

- `results/tables/frontier_operator_next_action_status_handoff_completion_dashboard.csv`
- `results/tables/frontier_operator_next_action_status_handoff_completion_dashboard.json`
- `results/figures/frontier_operator_next_action_status_handoff_completion_dashboard.md`

## Proposed Fields

- `current_first_frontier`
- `blocked_frontier`
- `next_milestone`
- `remaining_frontier_count`
- `dominant_blocker`
- `dashboard_note`

## Dashboard Rules

- Use the operator brief to determine the current ready frontier and current blocked frontier.
- Use the milestone card to determine `next_milestone` and `remaining_frontier_count`.
- Set `dominant_blocker` to the blocked frontier when present, otherwise `none`.
- Keep the note coordination-only and avoid any claim of frontier execution.

## Testing

Add unit coverage for:

1. the current mixed-ready two-lane state
2. the empty-input fallback state

## Boundaries

- No gold references or verified results are touched.
- No routing or evaluation logic changes.
- No frontier execution is claimed.
