# Stage 13A: Synthetic Overlap Benchmark Plan

> Status: Historical document. The current project direction is maintained in docs/technical_implementation_plan_v2.md and docs/project_state.md.

## Goal

The current benchmark has only five verified cases. That is enough to establish the core trend, but it also makes the adaptive router look fragile because it is evaluated on a very small set. This stage adds a synthetic benchmark built from existing short snippets so we can test whether the routing logic remains sensible on more samples.

## Benchmark Construction

We use the existing snippet audio files under `resources/snippets/`:

- `con_001.wav` to `con_011.wav`
- `pro_001.wav` to `pro_015.wav`

From these snippets we generate five synthetic overlap tiers:

- `SyntheticNoOverlap`
- `SyntheticLightOverlap`
- `SyntheticMidOverlap`
- `SyntheticHeavyOverlap`
- `SyntheticOppositeOverlap`

Each tier produces five samples, for a total of 25 synthetic mixtures.

## Output Structure

The generator writes:

- synthetic audio to `resources/synthetic_overlap/audio/`
- synthetic reference placeholders to `resources/synthetic_overlap/references/`
- a manifest to `results/tables/synthetic_manifest.csv`

Each sample stores:

- mixed waveform
- speaker 1 waveform
- speaker 2 waveform
- reference JSON with source filenames and speaker labels

## Why This Stage Matters

The synthetic benchmark is not meant to replace the verified benchmark. It is a stability check.

It helps answer:

- does the routing strategy still make sense when we add more samples?
- do the overlap tiers produce the expected difficulty ordering?
- does the current conclusion only hold because of a small five-case benchmark?

## Current Status

This stage only generates audio and manifest structure.

It does not run ASR.
It does not run LLM correction.
It does not compute CER.

## Silver Reference and Evaluation Scope

The synthetic benchmark uses silver references derived from Whisper transcripts of the source snippets. That means the synthetic result is a stability check, not a gold evaluation.

The five manually verified benchmark cases remain the primary gold benchmark for the project. Synthetic results are supplementary evidence used to test whether the adaptive router still behaves sensibly on a larger and more varied sample set.

That keeps the benchmark-generation step lightweight and reproducible.
