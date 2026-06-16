# LLM Critic Go-No-Go Board Design

## Goal

Add one `qualitative/demo` decision artifact that compresses the current LLM-critic review chain into a go/no-go view for any next narrow repair-style writeback.

## Why This Increment

The repository already has:

- a qualitative critic note
- a review queue and checklist
- five qualitative review passes
- a queue-status rollup
- a completion summary

What is still missing is a single board that answers the practical question quickly: what in the LLM-critic chain is actually ready for a next narrow writeback step, and what still blocks any verified repair claim?

## Scope

In scope:

- a new generator under `src/`
- a focused unit test file
- generated table and markdown board artifacts
- small doc updates referencing the new board

Out of scope:

- running an actual LLM repair loop
- changing stable/gold metrics
- claiming verified transcript correction
- expanding beyond the existing gold qualitative queue evidence

## Inputs

Read only existing repo-local artifacts:

- `results/tables/llm_critic_qualitative_summary.csv`
- `results/tables/llm_critic_review_queue.csv`
- `results/tables/llm_critic_review_pass_status.json`
- `results/tables/llm_critic_review_pass_completion_summary.json`
- `results/tables/llm_critic_review_receipt.json`

## Output Shape

Per-checkpoint rows should include:

- `checkpoint_name`
- `scope`
- `current_status`
- `claim_boundary`
- `go_no_go_state`
- `next_action`
- `evidence_artifact`

Summary row should include:

- `scope`
- `checkpoint_count`
- `go_count`
- `no_go_count`
- `overall_state`
- `primary_boundary`
- `recommended_next_action`

## Decision Rules

- queue-complete qualitative review checkpoints may be `go` for a narrow qualitative writeback
- any checkpoint that only has `template_only` receipt state remains `no_go` for verified repair claims
- overall state should stay conservative: `qualitative_writeback_ready` is allowed, but `verified_repair_claim_blocked` must remain explicit

## Verification

- unit tests for checkpoint classification and summary logic
- run the generator locally
- verify markdown explicitly distinguishes writeback readiness from verified repair success

## Labeling

Keep all outputs in `qualitative/demo` scope and explicitly non-verified.
