# Cascade Benchmark Handoff Packet

This generated packet consolidates the benchmark readiness scaffold, staged plan, execution checklist, session manifest template, and execution-status board.

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

## Execution Summary

- `foundation`: `pending_execution` with `2/2` template-only steps, `12` pending fields, blocker `runtime_capture_missing`, next `collect_controlled_runtime`, datasets `gold;synthetic_split`
- `surface`: `pending_execution` with `2/2` template-only steps, `6` pending fields, blocker `artifact_refresh_missing`, next `refresh_timing_backed_artifacts`, datasets `gold;synthetic_split`
- `cross_dataset`: `pending_execution` with `1/1` template-only steps, `4` pending fields, blocker `derived_refresh_missing`, next `refresh_cross_dataset_stack`, datasets `cross_dataset`

## Execution Queue

- rank 1: `phase1_gold_runtime_foundation` / `do_now` / blocker `runtime_capture_missing` / next `collect_controlled_runtime` / reason `runtime_capture_missing with 6 pending fields`
- rank 2: `phase2_synthetic_runtime_foundation` / `do_now` / blocker `runtime_capture_missing` / next `collect_controlled_runtime` / reason `runtime_capture_missing with 6 pending fields`
- rank 3: `phase3_gold_surface_refresh` / `next_after_runtime` / blocker `artifact_refresh_missing` / next `refresh_timing_backed_artifacts` / reason `artifact_refresh_missing with 3 pending fields`
- rank 4: `phase4_synthetic_surface_refresh` / `next_after_runtime` / blocker `artifact_refresh_missing` / next `refresh_timing_backed_artifacts` / reason `artifact_refresh_missing with 3 pending fields`
- rank 5: `phase5_cross_dataset_refresh` / `next_after_runtime` / blocker `derived_refresh_missing` / next `refresh_cross_dataset_stack` / reason `derived_refresh_missing with 4 pending fields`

## Session Ledger

- rank 1: `phase1_gold_runtime_foundation` / session `timing_capture` / evidence `hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes` / completion `collect_controlled_runtime -> Gold runtime foundation artifacts are rebuilt from controlled timing.`
- rank 2: `phase2_synthetic_runtime_foundation` / session `timing_capture` / evidence `hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes` / completion `collect_controlled_runtime -> Synthetic split runtime foundation artifacts are rebuilt from controlled timing.`
- rank 3: `phase3_gold_surface_refresh` / session `artifact_refresh` / evidence `source_timing_manifest;refresh_command;diff_review_notes` / completion `refresh_timing_backed_artifacts -> Gold surface artifacts are rebuilt from controlled timing-backed inputs.`
- rank 4: `phase4_synthetic_surface_refresh` / session `artifact_refresh` / evidence `source_timing_manifest;refresh_command;diff_review_notes` / completion `refresh_timing_backed_artifacts -> Synthetic split surface artifacts are rebuilt from controlled timing-backed inputs.`
- rank 5: `phase5_cross_dataset_refresh` / session `derived_refresh` / evidence `source_timing_manifest;refresh_command;cross_dataset_scope;consistency_notes` / completion `refresh_cross_dataset_stack -> Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.`

## Dependency Graph

- `phase1_gold_runtime_foundation` depends on `` / status `root` / unlocks `phase2_synthetic_runtime_foundation` / note `phase1_gold_runtime_foundation starts the benchmark chain for the foundation phase.`
- `phase2_synthetic_runtime_foundation` depends on `phase1_gold_runtime_foundation` / status `blocked_by_predecessor` / unlocks `phase3_gold_surface_refresh` / note `Wait for phase1_gold_runtime_foundation before phase2_synthetic_runtime_foundation can produce timing-backed foundation outputs.`
- `phase3_gold_surface_refresh` depends on `phase2_synthetic_runtime_foundation` / status `blocked_by_predecessor` / unlocks `phase4_synthetic_surface_refresh` / note `Wait for phase2_synthetic_runtime_foundation before phase3_gold_surface_refresh can produce timing-backed surface outputs.`
- `phase4_synthetic_surface_refresh` depends on `phase3_gold_surface_refresh` / status `blocked_by_predecessor` / unlocks `phase5_cross_dataset_refresh` / note `Wait for phase3_gold_surface_refresh before phase4_synthetic_surface_refresh can produce timing-backed surface outputs.`
- `phase5_cross_dataset_refresh` depends on `phase4_synthetic_surface_refresh` / status `blocked_by_predecessor` / unlocks `` / note `Wait for phase4_synthetic_surface_refresh before phase5_cross_dataset_refresh can produce timing-backed cross_dataset outputs.`

## Blocker Matrix

- `phase1_gold_runtime_foundation` / blocker `runtime_capture_missing` / priority `do_now` / dependency `root` / severity `high` / note `do_now / root / 6 pending fields`
- `phase2_synthetic_runtime_foundation` / blocker `runtime_capture_missing` / priority `do_now` / dependency `blocked_by_predecessor` / severity `high` / note `do_now / blocked_by_predecessor / 6 pending fields`
- `phase3_gold_surface_refresh` / blocker `artifact_refresh_missing` / priority `next_after_runtime` / dependency `blocked_by_predecessor` / severity `medium` / note `next_after_runtime / blocked_by_predecessor / 3 pending fields`
- `phase4_synthetic_surface_refresh` / blocker `artifact_refresh_missing` / priority `next_after_runtime` / dependency `blocked_by_predecessor` / severity `medium` / note `next_after_runtime / blocked_by_predecessor / 3 pending fields`
- `phase5_cross_dataset_refresh` / blocker `derived_refresh_missing` / priority `next_after_runtime` / dependency `blocked_by_predecessor` / severity `high` / note `next_after_runtime / blocked_by_predecessor / 4 pending fields`

## Runbook Card

- start `phase1_gold_runtime_foundation` / action `collect_controlled_runtime` / session `timing_capture` / evidence `hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes` / urgency `high` / note `Start with phase1_gold_runtime_foundation because it is do_now and root.`

## Milestone Card

- current `phase1_gold_runtime_foundation` / next milestone `phase2_synthetic_runtime_foundation` / remaining phases `3` / urgency `high` / note `phase1_gold_runtime_foundation unlocks phase2_synthetic_runtime_foundation and leaves 3 pending phases.`

## Phase Checkpoint Card

- phase `foundation` / readiness `pending_execution` / blocker `runtime_capture_missing` / action `collect_controlled_runtime` / completion `Gold runtime foundation artifacts are rebuilt from controlled timing.`
- phase `surface` / readiness `pending_execution` / blocker `artifact_refresh_missing` / action `refresh_timing_backed_artifacts` / completion `Gold surface artifacts are rebuilt from controlled timing-backed inputs.`
- phase `cross_dataset` / readiness `pending_execution` / blocker `derived_refresh_missing` / action `refresh_cross_dataset_stack` / completion `Cross-dataset decision-support artifacts are rebuilt from controlled timing-backed inputs.`

## Completion Dashboard

- start `phase1_gold_runtime_foundation` / pending phases `3` / dominant blocker `runtime_capture_missing` / urgency `high` / note `phase1_gold_runtime_foundation leads a 3-phase pending stack with dominant blocker runtime_capture_missing.`

## Execution Status

- step 1: `phase1_gold_runtime_foundation` is `template_only` / `pending_execution` with missing `hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes`
- step 2: `phase2_synthetic_runtime_foundation` is `template_only` / `pending_execution` with missing `hardware_label;device;repeat_count;warmup_count;batch_shape;timing_notes`
- step 3: `phase3_gold_surface_refresh` is `template_only` / `pending_execution` with missing `source_timing_manifest;refresh_command;diff_review_notes`
- step 4: `phase4_synthetic_surface_refresh` is `template_only` / `pending_execution` with missing `source_timing_manifest;refresh_command;diff_review_notes`
- step 5: `phase5_cross_dataset_refresh` is `template_only` / `pending_execution` with missing `source_timing_manifest;refresh_command;cross_dataset_scope;consistency_notes`

## Manifest Template

Manifest template fields: hardware_label, device, repeat_count, warmup_count, batch_shape, timing_notes
