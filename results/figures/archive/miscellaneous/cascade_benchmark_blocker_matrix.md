# Cascade Benchmark Blocker Matrix

This generated blocker matrix consolidates blocker type, queue priority, dependency state, and pending-field scale.

| plan_step_id | phase | dataset_scope | queue_rank | priority_bucket | blocking_category | dependency_status | pending_field_count | severity_band | matrix_note |
| --- | --- | --- | ---: | --- | --- | --- | ---: | --- | --- |
| phase1_gold_runtime_foundation | foundation | gold | 1 | do_now | runtime_capture_missing | root | 6 | high | do_now / root / 6 pending fields |
| phase2_synthetic_runtime_foundation | foundation | synthetic_split | 2 | do_now | runtime_capture_missing | blocked_by_predecessor | 6 | high | do_now / blocked_by_predecessor / 6 pending fields |
| phase3_gold_surface_refresh | surface | gold | 3 | next_after_runtime | artifact_refresh_missing | blocked_by_predecessor | 3 | medium | next_after_runtime / blocked_by_predecessor / 3 pending fields |
| phase4_synthetic_surface_refresh | surface | synthetic_split | 4 | next_after_runtime | artifact_refresh_missing | blocked_by_predecessor | 3 | medium | next_after_runtime / blocked_by_predecessor / 3 pending fields |
| phase5_cross_dataset_refresh | cross_dataset | cross_dataset | 5 | next_after_runtime | derived_refresh_missing | blocked_by_predecessor | 4 | high | next_after_runtime / blocked_by_predecessor / 4 pending fields |
