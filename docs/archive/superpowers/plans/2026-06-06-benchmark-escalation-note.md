# Benchmark Escalation Note Plan

## Goal

Add a generated `benchmark escalation note` artifact to the compute-aware cascade benchmark handoff stack so the next contributor can tell what to do when the current benchmark run cannot yet be closed out cleanly.

## Why This Next

The current stack now covers:

- what to run next
- which evidence to collect
- what must be written back after the run

The missing operator-facing layer is what happens if the run stalls or cannot yet satisfy the expected completion signal. A compact escalation note should answer:

- which blocker is still active
- which artifact should be consulted next
- which follow-up action should be recorded before handing off

That keeps the work on the same `compute-aware cascade -> benchmark handoff` frontier while extending the operator loop from start and closeout into exception handling.

## Proposed Outputs

- `results/tables/cascade_benchmark_escalation_note.csv`
- `results/tables/cascade_benchmark_escalation_note.json`
- `results/figures/cascade_benchmark_escalation_note.md`

## Data Shape

One row is sufficient for the current operator-facing layer:

- `escalation_step`
- `escalation_blocker`
- `escalation_trigger`
- `escalation_artifact`
- `escalation_followup`
- `escalation_note`

## Input Sources

- completion dashboard rows
- operator brief rows
- evidence receipt rows
- blocker matrix rows

## Handoff Integration

- add the new artifact to the artifact index
- add an `## Escalation Note` section to the benchmark handoff packet
- wire the new output through `main()`

## Verification

- add unit tests for row building
- add unit tests for markdown rendering
- extend the packet test to assert the new section appears
- run `python3 -m src.compute_aware_cascade --dataset synthetic_split`
- run `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
