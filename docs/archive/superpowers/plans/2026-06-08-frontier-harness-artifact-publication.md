# Frontier Harness Artifact Publication Plan

## Goal

Publish the generated frontier harness coordination artifacts that are already produced by `src.project_harness` and already referenced by the project docs.

## Why This Next

The latest code can generate several breadth-first coordination views:

- status and queue checklists
- focus, handoff, receipt, map, picklist, board, matrix, and writeback views
- matching CSV / JSON / Markdown result artifacts

Some of those files are still ignored by the broad `results/tables/*` and `results/figures/*` rules. Publishing them keeps the repository self-contained for the next agent: docs that point at a coordination artifact should resolve to a tracked file.

## Scope

- update the result artifact whitelist for the current frontier harness outputs
- regenerate `src.project_harness` outputs
- commit only coordination artifacts, not new experimental claims
- keep stable/gold and synthetic result tables untouched

## Verification

- run `python3 -m src.project_harness`
- run `python3 -m unittest tests.test_project_harness -v`
- verify `git status --short --ignored` no longer shows the published frontier harness artifacts as ignored-only
