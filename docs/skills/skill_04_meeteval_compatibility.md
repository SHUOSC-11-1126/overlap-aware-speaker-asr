# Skill 04: MeetEval / cpWER Compatibility Plan

## What question does this skill explore?

Can the project's overlap-aware ASR outputs be exported and evaluated with MeetEval-compatible cpWER tooling without breaking the stable baseline?

## Why is it relevant to the current project?

The repository already has speaker-aware CER and cpCER-lite on the gold benchmark. MeetEval compatibility is the frontier path toward community-standard meeting transcription metrics while keeping the stable evaluation layer intact.

## Current queue position

First in the current frontier queue. Use it before external validation or speaker-profile work so compatibility scaffolding stays separate from sanity-check and risk-signal experiments.

## Challenge level

Level 3: Research Extension

## Minimum viable attempt

- Export one verified gold case into MeetEval-compatible segment format
- Run a dry-run alignment check without claiming official cpWER scores
- Document the export path and any speaker-label mapping assumptions

## Stretch goal

- Compare cpWER-lite and official cpWER on one narrow case
- Document alignment drift and segment-granularity issues
- Turn the export path into a repeatable compatibility scaffold

## Failure is useful if...

- The export format is correct but cpWER reveals alignment drift the project had not surfaced
- The work clarifies which cases are safe for official MeetEval evaluation first
- The scaffold shows that compatibility work must stay separate from gold CER tables

## Inputs

- Verified gold references
- Speaker-track and mixed transcript outputs
- MeetEval export conventions

## Outputs

- MeetEval-compatible export artifacts
- cpWER execution scaffold and preflight notes
- Explicit experimental/frontier labels on all compatibility outputs

## What not to do

- Do not overwrite stable gold CER tables with cpWER results.
- Do not claim official MeetEval evaluation before the execution receipt is filled.
- Do not use reference transcripts as routing input.
- Do not blur oracle/analysis-only alignment work with deployable metrics.

## Success criteria

- One verified case has a documented MeetEval export and preflight path.
- All outputs are labeled `experimental/frontier`.
- A future agent can see whether official cpWER evaluation is worth running next.

## Suggested agent prompt

"Pick up Skill 04. Advance the MeetEval cpWER execution chain for one verified gold case. Keep all outputs in experimental/frontier scope and do not claim official benchmark completion."

## Owner suggestion

Mode B focused extension agent with evaluation discipline.
