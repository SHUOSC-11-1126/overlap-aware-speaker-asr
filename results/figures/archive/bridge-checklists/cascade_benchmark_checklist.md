# Cascade Benchmark Checklist

This generated checklist records the metadata and acceptance checks required for each benchmark handoff step.

| step_order | plan_step_id | phase | dataset_scope | command | session_type | required_metadata | acceptance_check |
| ---: | --- | --- | --- | --- | --- | --- | --- |
| 1 | phase1_gold_runtime_foundation | foundation | gold | python -m src.compute_aware_cascade | timing_capture | hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes | Gold runtime foundation artifacts are rebuilt from controlled timing. |
| 2 | phase2_synthetic_runtime_foundation | foundation | synthetic_split | python -m src.compute_aware_cascade --dataset synthetic_split | timing_capture | hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes | Synthetic split runtime foundation artifacts are rebuilt from controlled timing. |
| 3 | phase3_gold_surface_refresh | surface | gold | python -m src.compute_aware_cascade | artifact_refresh | source_timing_manifest;refresh_command;diff_review_notes | Gold surface artifacts are rebuilt from controlled timing-backed inputs. |
| 4 | phase4_synthetic_surface_refresh | surface | synthetic_split | python -m src.compute_aware_cascade --dataset synthetic_split | artifact_refresh | source_timing_manifest;refresh_command;diff_review_notes | Synthetic split surface artifacts are rebuilt from controlled timing-backed inputs. |
| 5 | phase5_cross_dataset_refresh | cross_dataset | cross_dataset | python -m src.compute_aware_cascade --dataset synthetic_split | derived_refresh | source_timing_manifest;cross_dataset_scope;refresh_command;consistency_notes | Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs. |
