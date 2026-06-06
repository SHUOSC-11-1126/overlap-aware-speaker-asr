# Frontier Harness Breadth Plan

## Goal

Extend `src/project_harness.py` so it reports a lightweight breadth-first frontier status view instead of only checking the stable baseline files.

## Why This Next

The repository already has several frontier directions documented:

- speaker profile / voiceprint
- MeetEval / cpWER compatibility
- agentic LLM critic
- external mini validation
- demo / visualization polish

What is missing is a small machine-generated status view that tells future agents whether each direction already has:

- a documented challenge card
- an expected output path
- a clearly stated next step

That pushes the project in a breadth-first way without forcing one narrow frontier to dominate the work queue.

## Proposed Change

Add a `frontier_status` section to the harness report with one row per direction:

- `frontier_id`
- `status`
- `evidence_path`
- `expected_output`
- `next_step`

## Initial Frontier Scope

- `speaker_profile`
- `meeteval_compatibility`
- `llm_critic`
- `external_validation`
- `demo_excellence`

## Verification

- add a unit test for frontier status presence in `build_report()`
- run `python3 -m src.project_harness`
- run `python3 -m unittest tests.test_project_harness tests.test_compute_aware_cascade -v`

## Result

This keeps the stable baseline untouched while making the frontier workload easier to spread across multiple directions.
