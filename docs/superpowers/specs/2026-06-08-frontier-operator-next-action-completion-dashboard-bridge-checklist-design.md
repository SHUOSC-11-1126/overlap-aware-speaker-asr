# Frontier Operator Next-Action Completion Dashboard Bridge Checklist Design

## Goal

Add one checklist that turns the new top-level completion dashboard into an explicit verification step.

## Why This Increment

The repository now has a top-level completion dashboard that summarizes the current ready frontier, blocked frontier, milestone, and dominant blocker.

What is still missing is the bridge layer that says what must be verified before that dashboard hands off back into the actionable top-level operator artifacts.

## Scope

In scope:

- one new generator under `src/`
- one focused unit test file
- one bridge checklist artifact in CSV/JSON/Markdown
- small doc updates referencing the checklist

Out of scope:

- changing the dashboard summary
- changing frontier ordering
- executing frontier work
- claiming frontier completion

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_operator_next_action_completion_dashboard.json`

## Output Shape

Per-row fields should include:

- `checklist_order`
- `current_first_frontier`
- `prerequisite_artifact`
- `receipt_target`
- `checklist_goal`
- `bridge_note`
- `next_gate`

## Decision Rules

- Use the completion dashboard markdown as the prerequisite artifact.
- Point the receipt target at the top-level runbook card markdown.
- Reuse the dashboard note as the bridge note.
- Keep wording coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that the receipt target points to the top-level runbook card
- unit tests should confirm that the bridge note is preserved
- run the generator locally and inspect the markdown checklist

## Labeling

Mark the output as experimental/frontier coordination only. The checklist should verify the dashboard before reopening the next actionable top-level artifact.
