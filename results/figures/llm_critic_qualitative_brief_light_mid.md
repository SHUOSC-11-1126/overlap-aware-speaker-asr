# LLM Critic Qualitative Brief — Light/Mid (qualitative/demo)

Label: `qualitative/demo` — heuristic critic-style brief for the harmful overlap band.
No LLM runtime call; does not claim verified transcript repair.

## Summary

| metric | value | label |
| --- | ---: | --- |
| target_case_count | 2 | stable/gold |
| separation_harm_rate | 1.0 | qualitative/demo |
| insertion_driven_harm_count | 2 | qualitative/demo |
| critic_scope | LightOverlap,MidOverlap | qualitative/demo |

## LightOverlap

- Mixed CER: 0.210714 | Separated CER: 0.475
- Dominant errors: mixed=insertion, separated=insertion
- Separation harm: True
- Hypothesis: Separation likely triggers insertion-heavy ASR hallucination (insertions=54, repetitions=38) in the harmful overlap band.
- Candidate repair: Prefer mixed_whisper or apply keep mixed output because separated looks risky; do not treat separated output as authoritative.
- Uncertainty: Qualitative heuristic critic only; no LLM runtime or verified transcript repair was applied.

## MidOverlap

- Mixed CER: 0.178947 | Separated CER: 0.273684
- Dominant errors: mixed=deletion, separated=insertion
- Separation harm: True
- Hypothesis: Separation likely triggers insertion-heavy ASR hallucination (insertions=26, repetitions=59) in the harmful overlap band.
- Candidate repair: Prefer mixed_whisper or apply keep mixed output because separated looks risky; do not treat separated output as authoritative.
- Uncertainty: Qualitative heuristic critic only; no LLM runtime or verified transcript repair was applied.
