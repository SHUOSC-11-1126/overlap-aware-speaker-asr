# Cascade Benchmark Status Board

This generated status board tracks which benchmark handoff phases are still template-only and what evidence is missing next.

| step_order | plan_step_id | phase | dataset_scope | execution_status | readiness_signal | pending_field_count | blocking_category | next_action | missing_fields | acceptance_check |
| ---: | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| 1 | phase1_gold_runtime_foundation | foundation | gold | template_only | pending_execution | 6 | runtime_capture_missing | collect_controlled_runtime | hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes | Gold runtime foundation artifacts are rebuilt from controlled timing. |
| 2 | phase2_synthetic_runtime_foundation | foundation | synthetic_split | template_only | pending_execution | 6 | runtime_capture_missing | collect_controlled_runtime | hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes | Synthetic split runtime foundation artifacts are rebuilt from controlled timing. |
| 3 | phase3_gold_surface_refresh | surface | gold | template_only | pending_execution | 3 | artifact_refresh_missing | refresh_timing_backed_artifacts | source_timing_manifest;refresh_command;diff_review_notes | Gold surface artifacts are rebuilt from controlled timing-backed inputs. |
| 4 | phase4_synthetic_surface_refresh | surface | synthetic_split | template_only | pending_execution | 3 | artifact_refresh_missing | refresh_timing_backed_artifacts | source_timing_manifest;refresh_command;diff_review_notes | Synthetic split surface artifacts are rebuilt from controlled timing-backed inputs. |
| 5 | phase5_cross_dataset_refresh | cross_dataset | cross_dataset | template_only | pending_execution | 4 | derived_refresh_missing | refresh_cross_dataset_stack | source_timing_manifest;refresh_command;cross_dataset_scope;consistency_notes | Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs. |
