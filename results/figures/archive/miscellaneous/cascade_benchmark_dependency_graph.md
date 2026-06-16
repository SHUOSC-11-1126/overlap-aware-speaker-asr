# Cascade Benchmark Dependency Graph

This generated dependency graph shows which benchmark step unlocks which downstream step.

| plan_step_id | step_order | phase | dataset_scope | queue_rank | priority_bucket | depends_on_step | dependency_status | unlocks_step | dependency_note |
| --- | ---: | --- | --- | ---: | --- | --- | --- | --- | --- |
| phase1_gold_runtime_foundation | 1 | foundation | gold | 1 | do_now |  | root | phase2_synthetic_runtime_foundation | phase1_gold_runtime_foundation starts the benchmark chain for the foundation phase. |
| phase2_synthetic_runtime_foundation | 2 | foundation | synthetic_split | 2 | do_now | phase1_gold_runtime_foundation | blocked_by_predecessor | phase3_gold_surface_refresh | Wait for phase1_gold_runtime_foundation before phase2_synthetic_runtime_foundation can produce timing-backed foundation outputs. |
| phase3_gold_surface_refresh | 3 | surface | gold | 3 | next_after_runtime | phase2_synthetic_runtime_foundation | blocked_by_predecessor | phase4_synthetic_surface_refresh | Wait for phase2_synthetic_runtime_foundation before phase3_gold_surface_refresh can produce timing-backed surface outputs. |
| phase4_synthetic_surface_refresh | 4 | surface | synthetic_split | 4 | next_after_runtime | phase3_gold_surface_refresh | blocked_by_predecessor | phase5_cross_dataset_refresh | Wait for phase3_gold_surface_refresh before phase4_synthetic_surface_refresh can produce timing-backed surface outputs. |
| phase5_cross_dataset_refresh | 5 | cross_dataset | cross_dataset | 5 | next_after_runtime | phase4_synthetic_surface_refresh | blocked_by_predecessor |  | Wait for phase4_synthetic_surface_refresh before phase5_cross_dataset_refresh can produce timing-backed cross_dataset outputs. |
