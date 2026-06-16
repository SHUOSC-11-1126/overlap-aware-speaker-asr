# Agent Challenge Board

This board is for future agents that want to do more than preserve the baseline.

## Current Frontier Sequence

Use this order when picking a new breadth-first frontier task:

1. MeetEval compatibility
2. External mini validation
3. Speaker profile / voiceprint-assisted risk detection
4. Agentic LLM critic and repair loop
5. Demo and public-facing GitHub excellence

This sequence is coordination guidance only. It does not claim that any frontier item has been completed.

## Current Coordination Focus

The frontier receipt-fill / handoff / coordination-writeback stack that once
lived here was removed in the ceremony purge (it was self-referential
scaffolding that computed nothing — see
`docs/frontier/agentic_research_entropy.md`). Pick the next frontier item from
the sequence above and produce a *computed, falsifiable* result for it; do not
recreate status/handoff/receipt documents as a substitute for work. The
advisory `make quality-predev` entropy guard will warn if a change adds
ceremony files without substance.

## Level 1: Documentation / Presentation

- README beautification
- GitHub hero figure
- contribution table
- final slides
- video script

## Level 2: Engineering Demo

- Streamlit demo
- result dashboard
- audio player
- transcript comparison UI
- router decision explanation UI

## Level 3: Research Extension

- separation phase diagram
- compute-aware cascade
- speaker profile
- MeetEval-compatible export
- external mini validation

## Level 4: Agentic Frontier

- local Ollama ASR critic
- multi-agent transcript debate
- self-repairing transcript pipeline
- uncertainty-aware human review
- active learning sample selector
- benchmark generation agent

## Level 5: High-risk / High-reward

- learned router from synthetic split
- stronger ASR model cascade
- integration with diarization model
- voiceprint-assisted diarization correction
- external dataset mini paper replication

## Task Template

For each challenge, write:

- difficulty
- expected owner
- expected output
- success criteria
- risk
- why it matters

## Board Rule

If a task does not answer a clear research question, it should stay out of the core pipeline and move into a skill card, a demo note, or future work.

This rule now has a meter and an advisory guard. `src/research_entropy_audit.py`
(`make entropy-audit`) measures how much of the `src/` surface is research
substance vs self-referential ceremony, and `scripts/harness/entropy_guard.py`
warns during `make quality-predev` when a change adds ceremony files with no
accompanying substance. See `docs/frontier/agentic_research_entropy.md`. The
current reading — ~89–95% of `src/*.py` is ceremony — is exactly why this rule
exists: prefer adding a computed, falsifiable result over another status doc.
