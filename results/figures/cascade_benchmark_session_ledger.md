# Cascade Benchmark Session Ledger

This generated ledger connects the ordered execution queue to the evidence that each benchmark session must leave behind.

| queue_rank | plan_step_id | phase | dataset_scope | session_type | priority_bucket | evidence_anchor | todo_field_count | completion_note |
| ---: | --- | --- | --- | --- | --- | --- | ---: | --- |
| 1 | phase1_gold_runtime_foundation | foundation | gold | timing_capture | do_now | hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes | 6 | collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing. |
| 2 | phase2_synthetic_runtime_foundation | foundation | synthetic_split | timing_capture | do_now | hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes | 6 | collect_controlled_runtime -> Synthetic split runtime foundation artifacts are rebuilt from controlled timing. |
| 3 | phase3_gold_surface_refresh | surface | gold | artifact_refresh | next_after_runtime | source_timing_manifest;refresh_command;diff_review_notes | 3 | refresh_timing_backed_artifacts -> Gold surface artifacts are rebuilt from controlled timing-backed inputs. |
| 4 | phase4_synthetic_surface_refresh | surface | synthetic_split | artifact_refresh | next_after_runtime | source_timing_manifest;refresh_command;diff_review_notes | 3 | refresh_timing_backed_artifacts -> Synthetic split surface artifacts are rebuilt from controlled timing-backed inputs. |
| 5 | phase5_cross_dataset_refresh | cross_dataset | cross_dataset | derived_refresh | next_after_runtime | source_timing_manifest;refresh_command;cross_dataset_scope;consistency_notes | 4 | refresh_cross_dataset_stack -> Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs. |
