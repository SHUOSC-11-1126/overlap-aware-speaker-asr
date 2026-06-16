# Frontier Operator Next-Action Completion Dashboard Design

## Goal

Add one completion dashboard that summarizes the current top-level operator chain at a glance.

## Why This Increment

The repository now has the detailed top-level coordination chain plus a milestone card, but the overall state is still spread across several artifacts.

What is still missing is the dashboard layer that answers the fast operator question: which frontier leads, what is currently blocked, what milestone is next, and what dominant blocker still controls progress.

## Scope

In scope:

- one new generator under `src/`
- one focused unit test file
- one dashboard artifact in CSV/JSON/Markdown
- small doc updates referencing the dashboard

Out of scope:

- changing ready-lane order
- changing milestone semantics
- executing frontier work
- claiming frontier completion

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_operator_next_action_summary.json`
- `results/tables/frontier_operator_next_action_milestone_card.json`

## Output Shape

One row should include:

- `current_first_frontier`
- `blocked_frontier`
- `next_milestone`
- `remaining_frontier_count`
- `dominant_blocker`
- `dashboard_note`

## Decision Rules

- `current_first_frontier` should come from the operator summary ready frontier.
- `blocked_frontier` should come from the operator summary blocked frontier.
- `next_milestone` and `remaining_frontier_count` should come from the milestone card.
- `dominant_blocker` should name the currently blocked frontier when one exists.
- Keep wording coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that ready frontier, blocked frontier, and milestone fields are merged into one dashboard row
- run the generator locally and inspect the markdown dashboard

## Labeling

Mark the output as experimental/frontier coordination only. The dashboard should summarize state, not claim execution.
