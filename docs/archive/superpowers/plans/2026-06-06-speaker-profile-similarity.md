# Speaker Profile Similarity Plan

## Goal

Add a minimal `speaker_profile` frontier artifact that turns existing `con/pro` snippet transcripts into a lightweight text-profile similarity signal.

## Why This Next

This direction broadens the project beyond compute-aware routing and MeetEval export while still using assets already present in the repository:

- `resources/snippets/con_*.wav`
- `resources/snippets/pro_*.wav`
- `results/snippet_transcripts/*_whisper.json`
- verified gold references with `speaker_1_text` / `speaker_2_text`
- speaker-attributed hypothesis transcripts

The first step does not need a real voiceprint model. A useful breadth-first scaffold is a profile similarity report that:

- aggregates the snippet transcript text into `con` and `pro` profiles
- compares those profiles against speaker-attributed reference / hypothesis text
- reports direct vs swapped alignment as a lightweight risk signal

## Proposed Outputs

- `results/tables/speaker_profile_similarity.csv`
- `results/tables/speaker_profile_similarity.json`
- `results/figures/speaker_profile_risk_summary.md`

## Scope

- use text-based profile similarity only
- keep it explicitly labeled as a lightweight assistance signal
- compare direct assignment and swapped assignment
- report a confidence gap, not a speaker-ID claim

## Verification

- add unit tests for similarity row construction
- add unit tests for summary rendering
- run `python3 -m src.speaker_profile_similarity`
- run `python3 -m unittest tests.test_speaker_profile_similarity tests.test_project_harness tests.test_compute_aware_cascade -v`
