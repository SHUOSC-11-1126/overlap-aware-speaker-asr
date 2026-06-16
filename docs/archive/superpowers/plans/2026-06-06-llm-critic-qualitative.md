# LLM Critic Qualitative Plan

## Goal

Add a minimal `llm_critic` frontier artifact that produces a qualitative transcript critique without pretending the critic is the ground truth.

## Why This Next

This direction broadens the project again without requiring external APIs or a real LLM runtime. The repository already has structured evidence that can feed a first critic-style output:

- `results/tables/risk_aware_selection.csv`
- `results/tables/speaker_profile_similarity.csv`
- verified references and speaker-attributed transcripts

That is enough to build a first qualitative critic note that:

- explains which failure mode looks risky
- suggests a candidate repair path
- states what remains uncertain

## Proposed Outputs

- `results/tables/llm_critic_qualitative_summary.csv`
- `results/tables/llm_critic_qualitative_summary.json`
- `results/figures/llm_critic_qualitative_note.md`

## Scope

- no real LLM call yet
- use structured heuristics to produce critic-style explanations
- clearly label the result as qualitative
- compare risk cues and suggest whether repair seems worthwhile

## Verification

- add unit tests for critique row construction
- add unit tests for summary rendering
- run `python3 -m src.llm_correct`
- run `python3 -m unittest tests.test_llm_critic_qualitative tests.test_speaker_profile_similarity tests.test_export_meeteval_compatibility tests.test_project_harness tests.test_compute_aware_cascade -v`
