# Benchmark Receipt Bridge Plan

## Goal

Extend the compute-aware benchmark coordination stack with a lightweight receipt bridge that points the current benchmark handoff packet directly at the current evidence receipt target.

## Why This Next

The repository already has:

- a benchmark handoff packet
- a benchmark runbook card
- a benchmark evidence receipt

What it still lacks is a short bridge that turns those larger coordination artifacts into one explicit handoff path from "open this packet" to "write back here". Adding this layer keeps the work breadth-first because:

- it stays in coordination territory rather than claiming execution
- it reduces the final ambiguity between benchmark operator guidance and benchmark writeback target
- it mirrors the newer receipt-aware harness layer without changing benchmark priorities

## Proposed Outputs

- `results/tables/cascade_benchmark_receipt_bridge.csv`
- `results/tables/cascade_benchmark_receipt_bridge.json`
- `results/figures/cascade_benchmark_receipt_bridge.md`

## Scope

- derive one bridge row from the current runbook and evidence receipt cards
- record the current start step, prerequisite artifact, receipt target, and bridge note
- keep the wording explicit that this is coordination-only and not a claim of completed benchmark execution
- avoid changing the existing benchmark queue or readiness logic

## Verification

- add unit tests for bridge row construction
- add unit tests for markdown rendering
- run `python3 -m src.compute_aware_cascade --dataset synthetic_split`
- run `python3 -m unittest tests.test_compute_aware_cascade tests.test_project_harness -v`
