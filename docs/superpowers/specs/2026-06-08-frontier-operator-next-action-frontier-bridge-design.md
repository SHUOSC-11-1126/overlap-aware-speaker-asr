# Frontier Operator Next-Action Frontier Bridge Design

## Goal

Add one bridge artifact that connects the new top-level operator runbook card back to the broader frontier coordination board.

## Why This Increment

The repository now has a top-level operator chain:

- operator card
- bridge checklist
- operator brief
- runbook card

What is still missing is the explicit bridge showing that the first ready-lane action chosen by this chain still aligns with the broader frontier queue head and the top-level go/no-go focus.

## Scope

In scope:

- one new generator under `src/`
- one focused test file
- one bridge artifact in CSV/JSON/Markdown
- small doc updates referencing the bridge

Out of scope:

- changing queue order
- changing frontier readiness
- executing any benchmark or writeback step
- claiming frontier completion

## Inputs

Read only existing coordination artifacts:

- `results/tables/frontier_operator_next_action_runbook_card.json`
- `results/tables/frontier_go_no_go_summary.json`

## Output Shape

One row should include:

- `runbook_frontier`
- `frontier_queue_head`
- `bridge_reason`
- `bridge_note`

## Decision Rules

- `runbook_frontier` should come from the runbook card.
- `frontier_queue_head` should come from `highest_priority_ready_frontier` in the top-level go/no-go summary.
- The bridge should explicitly say whether those two values align.
- Keep the output coordination-only and avoid implying that alignment means execution has happened.

## Verification

- unit tests should confirm that the runbook frontier and queue head are copied into one bridge row
- unit tests should confirm that alignment text is preserved when both values match
- run the generator locally and inspect the markdown bridge

## Labeling

Mark the output as experimental/frontier coordination only. The bridge should prove queue alignment, not frontier completion.
