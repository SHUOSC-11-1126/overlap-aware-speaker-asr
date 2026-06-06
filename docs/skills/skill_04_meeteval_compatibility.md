# Skill 04: MeetEval / cpWER Compatibility Plan

## What question does this skill explore?

How can the current evaluation stack be aligned with meeting-transcription conventions such as cpWER or ORC-WER?

## Why is it relevant to the current project?

The project already has speaker-aware CER and cpCER-lite. This skill defines a path toward compatibility with more standard multi-speaker meeting benchmarks.

## Current queue position

Queue head. If you are picking up a frontier task now, start here and use the readiness handoff before moving to any other frontier card.

## Challenge level

Level 3: Research Extension

## Minimum viable attempt

- Export current transcripts into a MeetEval-compatible format
- Compare the current metrics with cpWER-style expectations
- Write a short compatibility note

## Stretch goal

- Run a small external sanity check using a compatible export
- Compare speaker-aware CER, cpCER-lite, and standard meeting metrics side by side

## Failure is useful if...

- The export is tricky, but the format mismatch is clearly documented
- The current benchmark is enough for a local comparison even if the external integration is partial
- The exercise clarifies what would be needed for a real meeting benchmark bridge

## Inputs

- Speaker-aware transcripts
- cpCER-lite outputs
- Gold references

## Outputs

- MeetEval-compatible export
- cpWER / ORC-WER discussion note

## What not to do

- Do not force a large benchmark integration if the project does not need it.
- Do not present this as a core quantitative result unless it is actually evaluated.
- Do not blur the line between current metrics and future work.
- Do not pretend compatibility is the same as evaluation.

## Success criteria

- A clear export path exists.
- The report explains how the current metrics relate to standard meeting evaluation.
- The work is framed as a compatibility bridge, not a new benchmark obsession.

## Suggested agent prompt

Bridge the current evaluation pipeline toward MeetEval / cpWER compatibility without confusing export support with a new benchmark claim.

## Owner suggestion

Metrics / benchmarking owner.
