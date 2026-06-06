# Skill 05: Agentic LLM Transcript Critic

## What question does this skill explore?

Can an LLM or local agent critique transcripts, explain risk, and suggest repairs without being treated as the ground truth?

## Why is it relevant to the current project?

The baseline already shows content-level hallucination and boundary-dependent failure modes. A critic agent could help classify those errors, but only if its outputs remain clearly labeled.

## Current queue position

Fourth in the current frontier queue. Use this after the MeetEval bridge, external validation, and speaker profile cards are already clearer, so the critic stays framed as a diagnostic layer rather than a truth source.

## Challenge level

Level 4: Agentic Frontier

## Minimum viable attempt

- Input: transcript + risk report + glossary
- Output: a short critique and a list of candidate corrections
- Mark the result as qualitative unless it is evaluated

## Stretch goal

- Build a repair loop with a second pass
- Compare the critic output against verified references only after the fact
- Produce a structured uncertainty report

## Failure is useful if...

- The critic makes useful error explanations even when it does not improve the transcript
- The experiment reveals which errors are too subtle for the critic to fix reliably
- The system is good at diagnosis but not at correction, which is still useful information

## Inputs

- Transcript text
- Risk report
- Speaker-aware features
- Glossary or terminology hints

## Outputs

- Risk explanation
- Correction candidates
- Summary of likely failure mode

## What not to do

- Do not let the LLM silently become the gold truth.
- Do not mix qualitative repair suggestions with measured benchmark claims.
- Do not hide uncertainty.
- Do not call an unverified repair step a final evaluation result.

## Success criteria

- The critic explains at least one failure mode clearly.
- Its outputs are labeled as qualitative or evaluated.
- It helps a future agent decide whether repair is worthwhile.

## Suggested agent prompt

Act as a transcript critic. Explain what looks risky, what might be repaired, and what remains uncertain. Do not assume you are the truth source.

## Owner suggestion

LLM / agentic systems owner.
