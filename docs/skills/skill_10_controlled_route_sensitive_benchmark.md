# Controlled Route-Sensitive Benchmark for Overlap-Aware ASR Routing

## Research question

Can a hybrid AudioDepth router prove its usefulness on a benchmark where mixed, separated, and cleaned routes genuinely differ?

## Why this is needed

Stage 25 showed that weak synthetic references and tiny route gaps make real-ASR validation inconclusive. A stronger benchmark must expose cases where routing decisions matter.

## Benchmark design

- exact or manually verified references when available
- controlled overlap ratio
- controlled speaker dominance
- controlled duration
- controlled interruption style
- known source tracks when possible

## Success criteria

- route-gap distribution has enough meaningful cases
- oracle has clear improvement over fixed baselines
- hybrid router improves over router_v2 or clearly explains where it fails
- real Whisper CER is computed, not proxy-only

## Caution

If the benchmark uses candidate Whisper snippet transcripts, label it `silver_plus_unverified`, not gold. If verified transcript fields are manually filled later, rerun verified mode and label those samples `verified_micro_gold`.

## Stage 27 follow-up

Stage 27 adds a balanced v2 benchmark because the first controlled run was separation-dominant. The v2 follow-up keeps the same caution: references remain `silver_plus_unverified`, and the result is frontier evidence. The key new finding is that mixed and separated wins both occur under real Whisper, but cleaned wins still do not.
