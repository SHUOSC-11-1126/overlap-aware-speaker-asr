# Frontier Operator Next-Action Milestone Card Design

## Goal

Add one milestone card that shows what the current top-level ready-lane checkpoint unlocks next.

## Why This Increment

The repository now has a top-level phase checkpoint card that isolates the current ready-lane completion signal.

What is still missing is the immediate milestone view: once that checkpoint is satisfied, what is the next unlocked frontier action and how many frontier states remain in this top-level coordination layer.

## Scope

In scope:

- one new generator under `src/`
- one focused unit test file
- one milestone card artifact in CSV/JSON/Markdown
- small doc updates referencing the milestone card

Out of scope:

- changing the top-level frontier order
- changing checkpoint semantics
- executing any frontier action
- claiming frontier completion

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_operator_next_action_summary.json`

## Output Shape

One row should include:

- `next_milestone`
- `unlocks`
- `remaining_frontier_count`
- `milestone_note`

## Decision Rules

- Use the current operator summary as the source of current ready and blocked frontiers.
- The immediate milestone should be the completion of the current ready-lane checkpoint.
- The unlock should point to the blocked frontier becoming the next visible coordination target.
- `remaining_frontier_count` should reflect how many top-level frontier states remain after the current ready-lane checkpoint closes.
- Keep wording coordination-only and boundary-preserving.

## Verification

- unit tests should confirm that the blocked frontier is named in `unlocks`
- unit tests should confirm that the milestone name and remaining count are preserved
- run the generator locally and inspect the markdown card

## Labeling

Mark the output as experimental/frontier coordination only. The card should express the next unlock boundary, not claim execution.
