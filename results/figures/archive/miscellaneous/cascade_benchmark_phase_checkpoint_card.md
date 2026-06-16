# Cascade Benchmark Phase Checkpoint Card

This generated card summarizes each benchmark phase's current blocker and completion signal.

## foundation

- readiness: `pending_execution`
- blocker: `runtime_capture_missing`
- action: `collect_controlled_runtime`
- completion: Gold runtime foundation artifacts are rebuilt from controlled timing.

## surface

- readiness: `pending_execution`
- blocker: `artifact_refresh_missing`
- action: `refresh_timing_backed_artifacts`
- completion: Gold surface artifacts are rebuilt from controlled timing-backed inputs.

## cross_dataset

- readiness: `pending_execution`
- blocker: `derived_refresh_missing`
- action: `refresh_cross_dataset_stack`
- completion: Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.

