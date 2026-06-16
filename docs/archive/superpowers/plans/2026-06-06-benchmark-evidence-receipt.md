# Benchmark Evidence Receipt Plan

## Goal

Add a generated `benchmark evidence receipt` artifact to the compute-aware cascade benchmark handoff stack so the next contributor can see what must be written back after running the current benchmark step.

## Why This Next

The current stack now tells the operator:

- which benchmark step should run next
- which evidence fields must be collected
- how urgent the current blocker is

What is still missing is a compact receipt-style artifact that answers the second half of the operator loop:

- which completion signal closes the current step
- which evidence fields should be treated as the minimum write-back payload
- which downstream phase or action becomes valid after that write-back lands

That keeps the work on the same `compute-aware cascade -> benchmark handoff` frontier while extending the stack from “start here” into “close the loop like this”.

## Proposed Outputs

- `results/tables/cascade_benchmark_evidence_receipt.csv`
- `results/tables/cascade_benchmark_evidence_receipt.json`
- `results/figures/cascade_benchmark_evidence_receipt.md`

## Data Shape

One generated row is enough for the current operator-facing layer:

- `receipt_step`
- `receipt_action`
- `receipt_evidence`
- `receipt_completion_signal`
- `receipt_followup`
- `receipt_note`

## Input Sources

- completion dashboard rows
- operator brief rows
- session ledger rows
- phase checkpoint card rows

## Handoff Integration

- add the new artifact to the artifact index
- add a `## Evidence Receipt` section to the benchmark handoff packet
- wire the new output through `main()`

## Verification

- add unit tests for row building
- add unit tests for markdown rendering
- extend the packet test to assert the new section appears
- run `python3 -m src.compute_aware_cascade --dataset synthetic_split`
- run `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
