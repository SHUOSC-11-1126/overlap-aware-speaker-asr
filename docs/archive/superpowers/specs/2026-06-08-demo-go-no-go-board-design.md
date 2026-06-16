# Demo Go-No-Go Board Design

## Goal

Add one `qualitative/demo` decision artifact that compresses the current demo-excellence chain into a go/no-go view for any next narrow presentation writeback.

## Why This Increment

The repository already has:

- a storyboard
- a walkthrough
- review passes for storyboard and walkthrough
- status rollups and completion summaries
- receipt scaffolds and bridge checklists

What is still missing is a single board that answers the practical question quickly: what in the demo chain is actually ready for a next narrow presentation-style writeback, and what still blocks any claim of live delivery?

## Scope

In scope:

- a new generator under `src/`
- a focused unit test file
- generated table and markdown board artifacts
- small doc updates referencing the new board

Out of scope:

- running a real live demo or recording
- changing stable/gold metrics
- claiming delivered video, recording, or public demo success

## Inputs

Read only existing repo-local artifacts:

- `results/tables/demo_storyboard_receipt.json`
- `results/tables/demo_storyboard_review_pass_status.json`
- `results/tables/demo_storyboard_review_pass_completion_summary.json`
- `results/tables/demo_walkthrough_receipt.json`
- `results/tables/demo_walkthrough_review_pass_status.json`
- `results/tables/demo_walkthrough_review_pass_completion_summary.json`

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

- queue-complete storyboard and walkthrough review checkpoints may be `go` for a narrow presentation writeback
- any receipt that is still template-only remains `no_go` for live-delivery claims
- overall state should stay conservative: `presentation_writeback_ready` is allowed, but `live_demo_claims_still_blocked` must remain explicit

## Verification

- unit tests for checkpoint classification and summary logic
- run the generator locally
- verify markdown explicitly distinguishes presentation readiness from live-delivery success

## Labeling

Keep all outputs in `qualitative/demo` scope and explicitly non-delivery.
