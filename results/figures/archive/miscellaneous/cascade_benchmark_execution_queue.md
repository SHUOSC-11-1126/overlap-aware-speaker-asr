# Cascade Benchmark Execution Queue

This generated queue turns the benchmark status stack into an ordered next-run list.

| queue_rank | plan_step_id | phase | dataset_scope | priority_bucket | blocking_category | next_action | pending_field_count | queue_reason |
| ---: | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | phase1_gold_runtime_foundation | foundation | gold | do_now | runtime_capture_missing | collect_controlled_runtime | 6 | runtime_capture_missing with 6 pending fields |
| 2 | phase2_synthetic_runtime_foundation | foundation | synthetic_split | do_now | runtime_capture_missing | collect_controlled_runtime | 6 | runtime_capture_missing with 6 pending fields |
| 3 | phase3_gold_surface_refresh | surface | gold | next_after_runtime | artifact_refresh_missing | refresh_timing_backed_artifacts | 3 | artifact_refresh_missing with 3 pending fields |
| 4 | phase4_synthetic_surface_refresh | surface | synthetic_split | next_after_runtime | artifact_refresh_missing | refresh_timing_backed_artifacts | 3 | artifact_refresh_missing with 3 pending fields |
| 5 | phase5_cross_dataset_refresh | cross_dataset | cross_dataset | next_after_runtime | derived_refresh_missing | refresh_cross_dataset_stack | 4 | derived_refresh_missing with 4 pending fields |
