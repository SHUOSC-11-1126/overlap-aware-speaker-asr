# Stage 10 Adaptive Router Plan

> Status: Historical document. The current project direction is maintained in docs/technical_implementation_plan_v2.md and docs/project_state.md.

## Stage 10 Goal

Implement a real adaptive router that selects one of:

- `mixed_whisper`
- `separated_whisper`
- `separated_whisper_cleaned`

The router must not use ground-truth CER as input features. CER is allowed only for final evaluation.

## Allowed Routing Features

- `overlap_level`
- `mixed_segments_count`
- `separated_segments_count`
- `mixed_text_length`
- `separated_text_length`
- `text_length_ratio`
- `mixed_runtime_sec`
- `separated_runtime_sec`
- `runtime_ratio`
- `duplicate_removed_count`
- `repeated_phrase_count` if available

## Expected Outputs

- `results/tables/routing_decisions.csv`
- `results/tables/routing_decisions.json`
- `results/tables/routing_performance.csv`
- `results/tables/routing_performance.json`
- `results/figures/routing_performance.md`

## Performance Comparison

The final comparison should include:

- mixed average CER
- separated average CER
- cleaned average CER
- oracle best average CER
- rule router average CER

## Proposed Routing Logic

The first version of the router should be rule-based and transparent. A simple initial policy is enough for Stage 10:

1. Prefer separated outputs when overlap is high.
2. Prefer mixed outputs when overlap is low or when separated output shows obvious repetition.
3. Prefer cleaned separated output when it improves over raw separated output without introducing extra instability.

This policy should remain deterministic and interpretable.

## Evaluation Protocol

The router will be evaluated on the five verified benchmark cases.

For each case, record:

- selected method
- selected CER
- oracle best method
- oracle best CER
- whether the router matched the oracle choice

The average performance of the router should be compared with:

- fixed mixed pipeline
- fixed separated pipeline
- fixed cleaned separated pipeline
- oracle best pipeline

## Acceptance Criteria

- The router can run without any ground-truth transcript input.
- The router outputs a clear decision for each case.
- The router performance table is generated and reproducible.
- The results support a discussion of when separation should be used.

## Notes

- This stage is meant to be lightweight and interpretable.
- It should not introduce a new ASR model.
- It should not depend on LLM or RAG.
- It should build directly on the currently available benchmark outputs.
