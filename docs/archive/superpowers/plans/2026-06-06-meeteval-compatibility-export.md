# MeetEval Compatibility Export Plan

## Goal

Add a minimal `meeteval_compatibility` export scaffold so the repository produces a concrete compatibility bridge instead of only a challenge card.

## Why This Next

This direction broadens the project beyond the compute-aware frontier without needing new external data or heavyweight dependencies. The repository already has:

- verified gold references with speaker-attributed segments
- separated speaker-track hypotheses with speaker labels and timestamps

That is enough to produce a first segment-level export candidate and a note explaining what is compatible today versus what still requires real MeetEval / cpWER evaluation.

## Proposed Outputs

- `results/tables/meeteval_compatibility_summary.csv`
- `results/tables/meeteval_compatibility_summary.json`
- `results/tables/meeteval_reference_segments.jsonl`
- `results/tables/meeteval_hypothesis_segments.jsonl`
- `results/figures/meeteval_compatibility_note.md`

## Scope

- Export verified gold reference segments for each gold case
- Export `separated_whisper` speaker transcript segments for each gold case
- Summarize counts, speakers, and source paths
- Clearly label the work as a compatibility bridge, not a completed external benchmark

## Verification

- add unit tests for summary rows
- add unit tests for JSONL line generation
- run `python3 -m src.export_meeteval_compatibility`
- run `python3 -m unittest tests.test_export_meeteval_compatibility tests.test_project_harness tests.test_compute_aware_cascade -v`
