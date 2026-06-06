# Frontier Handoff Packet Plan

## Goal

Extend the project harness from a queue plus focus card into a single frontier handoff packet that points the current queue head directly at its next artifact.

## Why This Next

The repository already has:

- a frontier status table
- a frontier execution queue
- a frontier focus card
- a queue-head-specific `meeteval_dry_run_handoff` artifact

The missing link is a tiny generated note that ties those pieces together in one place. That keeps the breadth-first coordination layer compact while reducing the number of files a future contributor has to inspect before taking action.

## Proposed Outputs

- `results/tables/frontier_handoff_packet.json`
- `results/figures/frontier_handoff_packet.md`

## Scope

- derive one row from the queue head
- point that row at the queue head's most actionable artifact
- capture current frontier, next artifact, execution intent, and evidence target
- keep the wording explicit that the packet is coordination-only and not a claim of completed frontier work

## Verification

- add unit tests for packet row construction
- add unit tests for markdown rendering
- run `python3 -m src.project_harness`
- run `python3 -m unittest tests.test_project_harness tests.test_export_meeteval_compatibility -v`
