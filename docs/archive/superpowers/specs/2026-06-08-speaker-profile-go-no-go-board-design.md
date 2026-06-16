# Speaker Profile Go-No-Go Board Design

## Goal

Add one `experimental/frontier` decision artifact that compresses the current speaker-profile stronger-method chain into a go/no-go view for the first embedding baseline attempt.

## Why This Increment

The repository already has:

- text-proxy and audio-proxy diagnostics
- a multi-signal summary
- embedding scaffold and scaffold completion
- execution preflight readiness
- execution-chain status
- receipt readiness

What is still missing is a single board that answers the practical frontier question quickly: what part of the speaker-profile chain is actually ready to execute, and what parts are still blocked from any stronger attribution claim?

## Scope

In scope:

- a new generator under `src/`
- a focused unit test file
- generated table and markdown board artifacts
- small doc updates referencing the new board

Out of scope:

- running a real voiceprint or embedding model
- changing stable/gold metrics
- claiming speaker identification success
- widening scope beyond the existing narrow `NoOverlap` embedding-preflight path

## Inputs

Read only existing repo-local artifacts:

- `results/tables/speaker_profile_multisignal_summary.json`
- `results/tables/speaker_profile_embedding_trial_execution_preflight_readiness.json`
- `results/tables/speaker_profile_embedding_trial_execution_status.json`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_readiness.json`

## Output Shape

Per-checkpoint rows should include:

- `checkpoint_name`
- `case_scope`
- `current_status`
- `claim_boundary`
- `go_no_go_state`
- `next_action`
- `evidence_artifact`

Summary row should include:

- `scope`
- `case_scope`
- `checkpoint_count`
- `go_count`
- `no_go_count`
- `overall_state`
- `primary_boundary`
- `recommended_next_action`

## Decision Rules

- `preflight_ready`, `execution_chain_ready`, and `receipt_ready_to_fill` should map to `go`
- `advance_to_narrow_embedding_baseline` is a limited `go` only for a narrow baseline attempt, not for broader attribution claims
- any status that still reflects weak support, missing evidence, or not-ready execution should stay `no_go`
- overall state should stay conservative: `narrow_execution_ready` only when execution-specific checkpoints are ready, while the boundary text still blocks attribution claims

## Verification

- unit tests for checkpoint classification and summary logic
- run the generator locally
- verify markdown explicitly distinguishes narrow execution readiness from attribution-proof readiness

## Labeling

Keep all outputs in `experimental/frontier` scope and explicitly diagnostic rather than attribution-claiming.
