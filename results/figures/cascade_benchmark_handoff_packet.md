# Cascade Benchmark Handoff Packet

This generated packet consolidates the benchmark readiness scaffold, staged plan, execution checklist, and session manifest template.

## Readiness Snapshot

| artifact_id | benchmark_priority | benchmark_status | next_evidence_step |
| --- | --- | --- | --- |
| gold_cascade_performance | high | repo_local_runtime_only | Rebuild this artifact after controlled route timing is collected. |
| gold_runtime_audit | high | repo_local_runtime_only | Run a controlled same-hardware timing sweep for the selected routes. |
| gold_runtime_normalization | high | repo_local_runtime_only | Run a controlled same-hardware timing sweep for the selected routes. |
| gold_tradeoff_figure | high | repo_local_runtime_only | Rebuild this artifact after controlled route timing is collected. |
| synthetic_split_cascade_performance | high | repo_local_runtime_only | Rebuild this artifact after controlled route timing is collected. |

## Phase Order

- step 1: `phase1_gold_runtime_foundation` / `foundation` / `gold` / `python -m src.compute_aware_cascade`
- step 2: `phase2_synthetic_runtime_foundation` / `foundation` / `synthetic_split` / `python -m src.compute_aware_cascade --dataset synthetic_split`
- step 3: `phase3_gold_surface_refresh` / `surface` / `gold` / `python -m src.compute_aware_cascade`
- step 4: `phase4_synthetic_surface_refresh` / `surface` / `synthetic_split` / `python -m src.compute_aware_cascade --dataset synthetic_split`
- step 5: `phase5_cross_dataset_refresh` / `cross_dataset` / `cross_dataset` / `python -m src.compute_aware_cascade --dataset synthetic_split`

## Metadata Capture

- `phase1_gold_runtime_foundation`: session `timing_capture`, metadata `hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes`, acceptance `Gold runtime foundation artifacts are rebuilt from controlled timing.`
- `phase2_synthetic_runtime_foundation`: session `timing_capture`, metadata `hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes`, acceptance `Synthetic split runtime foundation artifacts are rebuilt from controlled timing.`
- `phase3_gold_surface_refresh`: session `artifact_refresh`, metadata `source_timing_manifest;refresh_command;diff_review_notes`, acceptance `Gold surface artifacts are rebuilt from controlled timing-backed inputs.`
- `phase4_synthetic_surface_refresh`: session `artifact_refresh`, metadata `source_timing_manifest;refresh_command;diff_review_notes`, acceptance `Synthetic split surface artifacts are rebuilt from controlled timing-backed inputs.`
- `phase5_cross_dataset_refresh`: session `derived_refresh`, metadata `source_timing_manifest;cross_dataset_scope;refresh_command;consistency_notes`, acceptance `Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.`

## Manifest Template

Manifest template fields: hardware_label, device, repeat_count, warmup_count, batch_shape, timing_notes
