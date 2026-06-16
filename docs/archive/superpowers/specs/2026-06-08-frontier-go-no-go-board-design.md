# Frontier Go-No-Go Board Design

## Goal

Add one top-level coordination artifact that compresses the current five frontier tracks into a single go/no-go board.

## Why This Increment

The repository now has frontier-specific decision layers for:

- MeetEval compatibility
- external mini validation
- speaker profile
- LLM critic
- demo excellence

What is still missing is a top-level operator view that answers the coordination question quickly: across all frontier tracks, which ones are ready for a narrow next action, which ones are still blocked, and what is the most relevant boundary for each?

## Scope

In scope:

- a new generator under `src/`
- a focused unit test file
- generated table and markdown board artifacts
- small doc updates referencing the new board

Out of scope:

- changing any stable/gold metrics
- running any frontier execution
- claiming completion of any frontier benchmark or delivery flow

## Inputs

Read only existing repo-local artifacts:

- `results/tables/meeteval_cpwer_execution_receipt_readiness.json`
- `results/tables/meeteval_cpwer_tokenization_adaptation_completion_summary.json`
- `results/tables/external_validation_go_no_go_summary.json`
- `results/tables/speaker_profile_go_no_go_summary.json`
- `results/tables/llm_critic_go_no_go_summary.json`
- `results/tables/demo_go_no_go_summary.json`

## Output Shape

Per-frontier rows should include:

- `frontier_name`
- `current_state`
- `primary_boundary`
- `go_no_go_state`
- `recommended_next_action`
- `evidence_artifact`

Summary row should include:

- `scope`
- `frontier_count`
- `go_count`
- `no_go_count`
- `highest_priority_ready_frontier`
- `highest_priority_blocked_frontier`
- `coordination_state`
- `recommended_operator_focus`

## Decision Rules

- MeetEval counts as `go` when tokenization adaptation is `queue_complete` and receipt readiness is `receipt_ready_to_fill`
- speaker profile counts as `go` when its summary says `narrow_execution_ready`
- LLM critic counts as `go` when its summary says `qualitative_writeback_ready`
- demo counts as `go` when its summary says `presentation_writeback_ready`
- external validation remains `no_go` when its summary says `blocked_by_license_confirmation`
- the highest-priority ready frontier should follow the documented queue order, not alphabetical order

## Verification

- unit tests for frontier classification and summary rollup
- run the generator locally
- verify markdown explicitly keeps blocked and ready frontier states separate

## Labeling

Keep all outputs coordination-only and avoid implying that any frontier has been fully executed merely because it is ready for a narrow next step.
