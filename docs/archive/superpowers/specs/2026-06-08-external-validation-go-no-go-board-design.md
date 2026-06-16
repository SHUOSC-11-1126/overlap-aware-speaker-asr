# External Validation Go-No-Go Board Design

## Goal

Add one `external/sanity-check` decision artifact that compresses the current external mini-validation chain into a simple go/no-go view for the first AISHELL-4 slice.

## Why This Increment

The repo already has:

- candidate and prioritization cards
- license gate and confirmation scaffold
- slice manifest
- staging readiness
- staging execution-chain status

What is still missing is a single board that answers the operational question quickly: can we stage the first external slice yet, and if not, what exact blocker still prevents that move?

## Scope

In scope:

- a new generator under `src/`
- a focused unit test file
- generated table and markdown board artifacts
- small doc updates referencing the new board

Out of scope:

- downloading external audio
- making any license claim that is not already in repo state
- changing stable/gold benchmark outputs
- claiming external validation has run

## Inputs

Read only existing repo-local artifacts:

- `results/tables/external_validation_license_gate.json`
- `results/tables/external_validation_license_confirmation_scaffold.json`
- `results/tables/external_validation_slice_manifest.json`
- `results/tables/external_validation_slice_staging_readiness.json`
- `results/tables/external_validation_slice_staging_execution_status.json`

## Output Shape

Per-checkpoint rows should include:

- `checkpoint_name`
- `current_status`
- `blocker`
- `go_no_go_state`
- `next_action`
- `evidence_artifact`

Summary row should include:

- `scope`
- `dataset_name`
- `checkpoint_count`
- `go_count`
- `no_go_count`
- `overall_state`
- `primary_blocker`
- `recommended_next_action`

## Decision Rules

- checkpoints with any `pending`, `blocked`, `not_ready`, or `template_only` status remain `no_go`
- if license confirmation is still pending anywhere in the chain, overall state should be `blocked_by_license_confirmation`
- recommended next action should explicitly point to recording the license confirmation decision before any staging attempt

## Verification

- unit tests for checkpoint classification and summary rollup
- run the generator locally
- verify markdown summary states that no external download or benchmark execution is claimed

## Labeling

Keep all outputs in `external/sanity-check` scope and explicitly coordination-only.
