# Roadmap

## Current Status

The core technical work is complete. The repository now has a stable baseline and a clear path toward more ambitious agentic exploration.

## Phase 0: Stable Baseline Completed

- Gold benchmark and references
- ASR baselines
- Post-processing
- Evaluation
- Adaptive routing
- Synthetic validation
- Risk-aware selection
- Documentation and maintenance structure

## Phase 1: Final Packaging

- Final REPORT.md
- Final README.md
- Contribution records
- Handoff notes
- Backup plan

## Phase 2: Boundary Exploration

- Separation phase diagram
- error boundary analysis
- overlap regime exploration

## Phase 3: Compute-aware Cascade

- cheap route vs stronger route
- runtime-aware selection
- risk-triggered repair tiers

Status: an initial `experimental/frontier` offline cascade analysis now exists.

- Script: `python -m src.compute_aware_cascade`
- Table: `results/tables/cascade_performance.csv`
- Summary: `results/figures/compute_aware_cascade_summary.md`
- Figure: `results/figures/cer_runtime_tradeoff.png`

Update: synthetic split cascade validation now exists as `synthetic/silver` frontier evidence.

- Script: `python -m src.compute_aware_cascade --dataset synthetic_split`
- Table: `results/tables/synthetic_split_cascade_performance.csv`
- Summary: `results/figures/synthetic_split_cascade_summary.md`
- Figure: `results/figures/synthetic_split_cer_runtime_tradeoff.png`

Update: runtime provenance audit now makes the cost source explicit.

- Gold audit: `results/tables/cascade_runtime_audit.csv`
- Synthetic split audit: `results/tables/synthetic_split_cascade_runtime_audit.csv`
- Current committed cascade outputs are fully backed by observed runtime fields; proxy cost remains a fallback for future incomplete-runtime experiments.

Update: runtime normalization audit now makes route-specific RTF explicit.

- Gold normalization: `results/tables/cascade_runtime_normalization.csv`
- Synthetic split normalization: `results/tables/synthetic_split_cascade_runtime_normalization.csv`
- The current audit uses selected-route processed audio duration, which is a stronger compute-normalized signal than raw runtime alone but still not a hardware-controlled benchmark.

Update: Pareto frontier audit now makes dominated strategies explicit.

- Gold Pareto audit: `results/tables/cascade_pareto.csv`
- Synthetic split Pareto audit: `results/tables/synthetic_split_cascade_pareto.csv`
- Current evidence suggests `router_v2_costed` dominates the other adaptive gold cascades, while synthetic split still leaves multiple meaningful frontier options.

Update: recommendation cards now turn the audits into deployment-facing choices.

- Gold recommendation card: `results/tables/cascade_recommendations.csv`
- Synthetic split recommendation card: `results/tables/synthetic_split_cascade_recommendations.csv`
- Current evidence recommends `router_v2_costed` as the gold balanced choice and `router_v2_synthetic_costed` as the synthetic split balanced choice.

Update: robustness gap audit now compares gold and held-out synthetic split directly.

- Cross-dataset gap audit: `results/tables/cascade_robustness_gap.csv`
- Current evidence suggests `router_v2` is the strongest shared adaptive route, while `budget_cascade` is less robust on held-out synthetic split.

Update: recommendation stability audit now checks whether deployment guidance is consistent across scopes.

- Stability audit: `results/tables/cascade_recommendation_stability.csv`
- Current evidence shows `cost_first` is the most stable profile, while `balanced` and `accuracy_first` vary between gold and synthetic settings.

Update: family-level stability audit separates naming drift from true recommendation drift.

- Family stability audit: `results/tables/cascade_recommendation_family_stability.csv`
- Current evidence shows `balanced` is actually stable at the strategy-family level; the remaining cross-scope disagreement is concentrated in `accuracy_first`.

Update: decision matrix now consolidates the cascade recommendation evidence into one deployment-facing table.

- Decision matrix: `results/tables/cascade_decision_matrix.csv`
- Current evidence suggests `balanced` is the cleanest default operating point, while `accuracy_first` is the strongest robustness-first alternative.

Update: a generated frontier report now consolidates the full cascade audit stack.

- Frontier report: `results/figures/cascade_frontier_report.md`
- This gives future contributors one entrypoint before diving into the more granular audit tables.

Update: a generated artifact index now turns the cascade outputs into an explicit registry.

- Artifact index: `results/tables/cascade_artifact_index.csv`
- Summary view: `results/figures/cascade_artifact_index.md`
- This gives future contributors a label-aware lookup table for which cascade artifact is gold-facing, synthetic-facing, or cross-dataset decision support.

Update: a generated benchmark-readiness scaffold now turns the hardware benchmark next step into a concrete handoff.

- Benchmark readiness: `results/tables/cascade_benchmark_readiness.csv`
- Summary view: `results/figures/cascade_benchmark_readiness.md`
- This prioritizes the runtime-facing artifacts that should be refreshed first once controlled same-hardware timing evidence is available.

Update: a generated benchmark plan now turns the readiness scaffold into an execution order.

- Benchmark plan: `results/tables/cascade_benchmark_plan.csv`
- Summary view: `results/figures/cascade_benchmark_plan.md`
- This sequences the controlled benchmark work into gold foundation, synthetic foundation, surface refresh, and cross-dataset refresh phases.

Update: a generated profile playbook now turns the recommendation tables into plain-language deployment guidance.

- Profile playbook: `results/tables/cascade_profile_playbook.csv`
- Summary view: `results/figures/cascade_profile_playbook.md`
- This explains when `balanced`, `accuracy_first`, and `cost_first` should be the default, the robustness-biased alternative, or the compute floor.

Update: a generated benchmark checklist now turns the plan into a per-run execution record.

- Benchmark checklist: `results/tables/cascade_benchmark_checklist.csv`
- Summary view: `results/figures/cascade_benchmark_checklist.md`
- This captures which metadata should be logged and what acceptance signal each benchmark phase must satisfy.

Update: a generated benchmark manifest template now turns the checklist into a fill-in session log.

- Manifest template: `results/tables/cascade_benchmark_manifest_template.csv`
- This gives future contributors a concrete table to fill while running controlled timing sweeps instead of collecting benchmark metadata ad hoc.

Update: a generated benchmark status board now turns the manifest template into an execution-progress tracker.

- Benchmark status: `results/tables/cascade_benchmark_status.csv`
- Summary view: `results/figures/cascade_benchmark_status.md`
- This shows which benchmark phases are still template-only, how many metadata fields remain open, which blocker category each phase belongs to, and which stages can move from planning into controlled execution next.

Update: a generated benchmark execution summary now turns the status board into a phase-level triage rollup.

- Benchmark execution summary: `results/tables/cascade_benchmark_execution_summary.csv`
- Summary view: `results/figures/cascade_benchmark_execution_summary.md`
- This shows blocker totals, readiness by phase, and the top next action before contributors dive into the lower-level status board.

Update: a generated benchmark execution queue now turns the rollup into an ordered next-run list.

- Benchmark execution queue: `results/tables/cascade_benchmark_execution_queue.csv`
- Summary view: `results/figures/cascade_benchmark_execution_queue.md`
- This shows which benchmark step should execute or be reviewed first once contributors move from planning into action.

Update: a generated benchmark session ledger now turns the queue into an evidence-tracking bridge.

- Benchmark session ledger: `results/tables/cascade_benchmark_session_ledger.csv`
- Summary view: `results/figures/cascade_benchmark_session_ledger.md`
- This shows which evidence anchor and completion note each queued benchmark step must satisfy once the run actually happens.

Update: a generated benchmark dependency graph now turns the run list into an unlock chain.

- Benchmark dependency graph: `results/tables/cascade_benchmark_dependency_graph.csv`
- Summary view: `results/figures/cascade_benchmark_dependency_graph.md`
- This shows which benchmark step unlocks the next downstream refresh and which pending steps are still blocked by earlier benchmark work.

Update: a generated benchmark blocker matrix now turns the unlock chain into a triage panel.

- Benchmark blocker matrix: `results/tables/cascade_benchmark_blocker_matrix.csv`
- Summary view: `results/figures/cascade_benchmark_blocker_matrix.md`
- This shows blocker type, queue priority, dependency state, and pending-field scale in one place for faster execution triage.

Update: a generated external validation candidate card now turns the external mini-validation frontier into a concrete dataset triage step.

- External validation candidates: `results/tables/external_validation_candidates.csv`
- Summary view: `results/figures/external_validation_candidates.md`
- This records source, license, fit, first preprocessing step, and next action for AISHELL-4, AliMeeting, AMI, and LibriCSS, while staying explicitly scoped to `external/sanity-check` planning rather than claiming a completed benchmark.

Update: a generated external validation prioritization card now turns that triage step into a first-action recommendation.

- External validation prioritization: `results/tables/external_validation_prioritization.csv`
- Summary view: `results/figures/external_validation_prioritization.md`
- This recommends `AISHELL-4` as the first tiny sanity-check target and records priority tier, recommended order, readiness note, and why-now context without claiming a completed external evaluation.

Update: a generated external validation slice handoff now turns that recommendation into a first-slice packet.

- External validation slice handoff: `results/tables/external_validation_slice_handoff.csv`
- Summary view: `results/figures/external_validation_slice_handoff.md`
- This keeps the scope narrow and honest: it defines the first slice shape, license gate, mapping artifact, and dry-run goal without implying that any external slice has already been staged or executed.

Update: a generated external validation slice receipt now creates the first evidence writeback slot.

- External validation slice receipt: `results/tables/external_validation_slice_receipt.json`
- Summary view: `results/figures/external_validation_slice_receipt.md`
- This stays on the same safe side of the line: it prepares the template-only receipt for a future narrow dry run without implying that any external sanity-check has already happened.

Update: the first external validation slice scaffold now exists.

- Slice mapping stub: `results/tables/external_validation_slice_mapping.json`
- Summary view: `results/figures/external_validation_slice_scaffold.md`
- AISHELL-4 remains `scaffold_only` with `license_status = pending_confirmation`; no external audio or benchmark evaluation has been run yet.

Update: `external_validation` now also has a license gate checklist.

- License gate checklist: `results/tables/external_validation_license_gate.csv`
- Summary view: `results/figures/external_validation_license_gate.md`
- This documents preflight license steps while external audio staging remains blocked.

Update: `external_validation` now also has a license gate bridge checklist.

- License gate bridge checklist: `results/tables/external_validation_license_gate_bridge_checklist.csv`
- Summary view: `results/figures/external_validation_license_gate_bridge_checklist.md`
- This connects the license gate to the slice manifest while staging remains blocked.

Update: `external_validation` now also has a license confirmation scaffold.

- License confirmation scaffold: `results/tables/external_validation_license_confirmation_scaffold.json`
- Summary view: `results/figures/external_validation_license_confirmation_scaffold.md`
- `confirmation_status = template_only`; no license decision has been recorded yet.

Update: `external_validation` now also has a license confirmation scaffold bridge checklist.

- License confirmation scaffold bridge checklist: `results/tables/external_validation_license_confirmation_scaffold_bridge_checklist.csv`
- Summary view: `results/figures/external_validation_license_confirmation_scaffold_bridge_checklist.md`
- This connects the confirmation scaffold to staging readiness without claiming benchmark execution.

Update: `external_validation` now also has a license confirmation receipt bridge.

- License confirmation receipt bridge: `results/tables/external_validation_license_confirmation_receipt_bridge.csv`
- Summary view: `results/figures/external_validation_license_confirmation_receipt_bridge.md`
- This links the confirmation scaffold bridge checklist to the slice receipt without claiming benchmark execution.

Update: `external_validation` now also has a license confirmation receipt bridge checklist.

- License confirmation receipt bridge checklist: `results/tables/external_validation_license_confirmation_receipt_bridge_checklist.csv`
- Summary view: `results/figures/external_validation_license_confirmation_receipt_bridge_checklist.md`
- This connects the receipt bridge to the slice receipt without claiming benchmark execution.

Update: `external_validation` now also has a slice manifest.

- Slice manifest: `results/tables/external_validation_slice_manifest.json`
- Summary view: `results/figures/external_validation_slice_manifest.md`
- Staging remains `blocked_by_license_gate` for the first AISHELL-4 excerpt.

Update: `external_validation` now also has a slice manifest bridge checklist.

- Slice manifest bridge checklist: `results/tables/external_validation_slice_manifest_bridge_checklist.csv`
- Summary view: `results/figures/external_validation_slice_manifest_bridge_checklist.md`
- This keeps the manifest and manifest receipt visible together while external audio staging remains blocked.

Update: `external_validation` now also has a slice staging readiness audit.

- Staging readiness table: `results/tables/external_validation_slice_staging_readiness.csv`
- Summary view: `results/figures/external_validation_slice_staging_readiness.md`
- `readiness_status = not_ready` with `blocker = license_confirmation_pending`.

Update: `external_validation` now also has a slice staging readiness bridge checklist.

- Staging readiness bridge checklist: `results/tables/external_validation_slice_staging_readiness_bridge_checklist.csv`
- Summary view: `results/figures/external_validation_slice_staging_readiness_bridge_checklist.md`
- This connects staging readiness to the slice manifest bridge checklist without claiming benchmark execution.

Update: `external_validation` now also has a slice staging readiness handoff.

- Staging readiness handoff: `results/tables/external_validation_slice_staging_readiness_handoff.csv`
- Summary view: `results/figures/external_validation_slice_staging_readiness_handoff.md`
- The handoff records `blocker = license_confirmation_pending` for AISHELL-4; external audio staging remains pending.

Update: `speaker_profile` now also has an embedding scaffold.

- Embedding scaffold: `results/tables/speaker_profile_embedding_scaffold.json`
- Summary view: `results/figures/speaker_profile_embedding_scaffold.md`
- This points toward `embedding_or_voiceprint_baseline` without claiming improved speaker attribution.

Update: `speaker_profile` now also has an embedding scaffold bridge checklist.

- Embedding scaffold bridge checklist: `results/tables/speaker_profile_embedding_scaffold_bridge_checklist.csv`
- Summary view: `results/figures/speaker_profile_embedding_scaffold_bridge_checklist.md`
- This connects the embedding scaffold to the method receipt without claiming voiceprint success.

Update: `speaker_profile` now also has an embedding trial handoff.

- Embedding trial handoff: `results/tables/speaker_profile_embedding_trial_handoff.csv`
- Summary view: `results/figures/speaker_profile_embedding_trial_handoff.md`
- This targets `NoOverlap` for a narrow embedding-or-voiceprint diagnostic trial without claiming improved speaker attribution.

Update: `speaker_profile` now also has an embedding trial scaffold.

- Embedding trial: `results/tables/speaker_profile_embedding_trial.csv`
- Summary view: `results/figures/speaker_profile_embedding_trial.md`
- The embedding trial scaffold records `trial_status = scaffold_only` for `NoOverlap`; voiceprint execution remains pending.

Update: `speaker_profile` now also has an embedding trial handoff bridge checklist.

- Embedding trial handoff bridge checklist: `results/tables/speaker_profile_embedding_trial_handoff_bridge_checklist.csv`
- Summary view: `results/figures/speaker_profile_embedding_trial_handoff_bridge_checklist.md`
- This connects the embedding trial scaffold to the handoff without claiming voiceprint success.

Update: `speaker_profile` now also has an embedding trial execution scaffold.

- Embedding trial execution scaffold: `results/tables/speaker_profile_embedding_trial_execution_scaffold.csv`
- Summary view: `results/figures/speaker_profile_embedding_trial_execution_scaffold.md`
- The execution scaffold records `scaffold_status = execution_scaffold_only`; voiceprint execution remains pending.

Update: `speaker_profile` now also has an embedding trial execution scaffold bridge checklist.

- Embedding trial execution scaffold bridge checklist: `results/tables/speaker_profile_embedding_trial_execution_scaffold_bridge_checklist.csv`
- Summary view: `results/figures/speaker_profile_embedding_trial_execution_scaffold_bridge_checklist.md`
- This connects the execution scaffold to voiceprint execution without claiming attribution success.

Update: `llm_critic` now has a first qualitative review pass.

- Review pass table: `results/tables/llm_critic_review_pass.csv`
- Summary view: `results/figures/llm_critic_review_pass.md`
- `HeavyOverlap` is `review_complete` without any verified repair claim.

Update: `llm_critic` now also has a review pass bridge checklist.

- Review pass bridge checklist: `results/tables/llm_critic_review_pass_bridge_checklist.csv`
- Summary view: `results/figures/llm_critic_review_pass_bridge_checklist.md`
- This keeps the qualitative pass and receipt visible together without claiming verified transcript repair.

Update: `llm_critic` now also has a second qualitative review pass advance.

- Review pass advance table: `results/tables/llm_critic_review_pass_advance.csv`
- Second pass table: `results/tables/llm_critic_review_pass_second.csv`
- Summary view: `results/figures/llm_critic_review_pass_advance.md`
- `LightOverlap` is the second queue pass after `HeavyOverlap`; no verified repair claim is made.

Update: `llm_critic` now also has a review pass advance bridge checklist.

- Review pass advance bridge checklist: `results/tables/llm_critic_review_pass_advance_bridge_checklist.csv`
- Summary view: `results/figures/llm_critic_review_pass_advance_bridge_checklist.md`
- This keeps the second qualitative pass and advance receipt visible together without claiming verified repair.

Update: `llm_critic` now also has a review pass status rollup.

- Review pass status table: `results/tables/llm_critic_review_pass_status.csv`
- Summary view: `results/figures/llm_critic_review_pass_status.md`
- `completed_count = 5/5` with `queue_status = queue_complete`; no verified repair claim is made.

Update: `llm_critic` now also has a third qualitative review pass.

- Review pass next table: `results/tables/llm_critic_review_pass_next.csv`
- Third pass table: `results/tables/llm_critic_review_pass_third.csv`
- Summary view: `results/figures/llm_critic_review_pass_third.md`
- `MidOverlap` is the third queue pass; no verified repair claim is made.

Update: `llm_critic` now also has a review pass status bridge checklist.

- Review pass status bridge checklist: `results/tables/llm_critic_review_pass_status_bridge_checklist.csv`
- Summary view: `results/figures/llm_critic_review_pass_status_bridge_checklist.md`
- This connects the status rollup to the next pass receipt without claiming verified repair.

Update: `llm_critic` now also has a fourth qualitative review pass continue layer.

- Review pass continue table: `results/tables/llm_critic_review_pass_continue.csv`
- Fourth pass table: `results/tables/llm_critic_review_pass_fourth.csv`
- Summary view: `results/figures/llm_critic_review_pass_fourth.md`
- `NoOverlap` is the fourth queue pass; no verified repair claim is made.

Update: `llm_critic` now also has a review pass continue bridge checklist.

- Review pass continue bridge checklist: `results/tables/llm_critic_review_pass_continue_bridge_checklist.csv`
- Summary view: `results/figures/llm_critic_review_pass_continue_bridge_checklist.md`
- This connects the fourth qualitative pass to the continue receipt without claiming verified repair.

Update: `llm_critic` now also has a final qualitative review pass.

- Review pass final table: `results/tables/llm_critic_review_pass_final.csv`
- Fifth pass table: `results/tables/llm_critic_review_pass_fifth.csv`
- Summary view: `results/figures/llm_critic_review_pass_fifth.md`
- `OppositeOverlap` closes the gold queue at `5/5`; no verified repair claim is made.

Update: `llm_critic` now also has a review pass completion summary.

- Completion summary table: `results/tables/llm_critic_review_pass_completion_summary.csv`
- Summary view: `results/figures/llm_critic_review_pass_completion_summary.md`
- `queue_status = queue_complete` without any verified transcript repair claim.

Update: `llm_critic` now also has a review pass final bridge checklist.

- Review pass final bridge checklist: `results/tables/llm_critic_review_pass_final_bridge_checklist.csv`
- Summary view: `results/figures/llm_critic_review_pass_final_bridge_checklist.md`
- This connects the final qualitative pass to the completion summary without claiming verified repair.

Update: a generated demo walkthrough now turns the storyboard into a short presentation sequence.

- Demo walkthrough: `results/tables/demo_walkthrough_steps.json`
- Summary view: `results/figures/demo_walkthrough.md`
- This keeps the `demo_excellence` frontier lightweight while making live demo or recording flow more explicit: each step points to an existing artifact rather than claiming new model evidence.

Update: a generated demo walkthrough receipt now creates the first evidence writeback slot.

- Demo walkthrough receipt: `results/tables/demo_walkthrough_receipt.json`
- Summary view: `results/figures/demo_walkthrough_receipt.md`
- This stays on the same safe side of the line: it prepares the template-only receipt for a future walkthrough pass without implying that any real demo delivery has already happened.

Update: a generated MeetEval dry-run checklist now turns the first diagnostic handoff into an ordered case queue.

- MeetEval dry-run checklist: `results/tables/meeteval_dry_run_checklist.csv`
- Summary view: `results/figures/meeteval_dry_run_checklist.md`
- This keeps the compatibility bridge in the coordination lane: it ranks the verified cases for the first diagnostic dry run without claiming that MeetEval or cpWER has already been executed.

Update: the first MeetEval dry-run diagnostic pass now exists.

- Diagnostic table: `results/tables/meeteval_dry_run_diagnostic.csv`
- Summary view: `results/figures/meeteval_dry_run_diagnostic.md`
- The `NoOverlap` export path passed speaker and time-range checks; the receipt moved to `diagnostic_complete` while cpWER evaluation remains pending.

Update: `meeteval_compatibility` now also has a dry-run receipt checklist.

- Dry-run receipt checklist: `results/tables/meeteval_dry_run_receipt_checklist.csv`
- Summary view: `results/figures/meeteval_dry_run_receipt_checklist.md`
- This keeps the receipt path visible in an ordered verification layer while staying explicit that cpWER has not yet been executed.

Update: `meeteval_compatibility` now also has a dry-run receipt board.

- Dry-run receipt board: `results/tables/meeteval_dry_run_receipt_board.csv`
- Summary view: `results/figures/meeteval_dry_run_receipt_board.md`
- This keeps the dry-run receipt path visible in one compact snapshot while staying explicit that cpWER has not yet been executed.

Update: `meeteval_compatibility` now also has a dry-run receipt map.

- Dry-run receipt map: `results/tables/meeteval_dry_run_receipt_map.csv`
- Summary view: `results/figures/meeteval_dry_run_receipt_map.md`
- This keeps the dry-run receipt path visible across the receipt, checklist, and board layers while staying explicit that cpWER has not yet been executed.

Update: the first MeetEval cpWER bridge-lite pass now exists.

- cpWER bridge table: `results/tables/meeteval_cpwer_bridge.csv`
- Summary view: `results/figures/meeteval_cpwer_bridge.md`
- All five gold cases now report `average_cpwer_bridge_lite = 0.120823` with `direct_mapping_count = 5/5`. This remains `experimental/frontier` rather than a full MeetEval benchmark claim.

Update: `meeteval_compatibility` now also has a cpWER bridge summary.

- cpWER bridge summary: `results/tables/meeteval_cpwer_bridge_summary.csv`
- Summary view: `results/figures/meeteval_cpwer_bridge_summary.md`
- This condenses the all-gold bridge-lite pass without promoting it into a finished MeetEval evaluation claim.

Update: `meeteval_compatibility` now also has a cpWER alignment audit.

- cpWER alignment table: `results/tables/meeteval_cpwer_alignment.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment.md`
- Cross-metric alignment reports `matched_count = 4/5` with `HeavyOverlap` as the only drift case.

Update: `meeteval_compatibility` now also has a cpWER alignment bridge checklist.

- cpWER alignment bridge checklist: `results/tables/meeteval_cpwer_alignment_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_bridge_checklist.md`
- This keeps the alignment audit and bridge handoff visible together while full MeetEval evaluation remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift diagnostic.

- Drift diagnostic table: `results/tables/meeteval_cpwer_alignment_drift_diagnostic.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_diagnostic.md`
- `HeavyOverlap` is the only drift case with `drift_severity = moderate`; cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift bridge checklist.

- Drift bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_bridge_checklist.md`
- This connects the drift diagnostic to the alignment bridge checklist without claiming MeetEval execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift handoff.

- Drift handoff table: `results/tables/meeteval_cpwer_alignment_drift_handoff.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_handoff.md`
- `HeavyOverlap` drift is handed off for segment inspection while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift handoff bridge checklist.

- Drift handoff bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_handoff_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_handoff_bridge_checklist.md`
- This connects the drift handoff back to the drift bridge checklist without claiming MeetEval execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment scaffold.

- Drift segment scaffold: `results/tables/meeteval_cpwer_alignment_drift_segment_scaffold.json`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_scaffold.md`
- `HeavyOverlap` segment inspection remains `scaffold_only`; cpWER execution is still pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment scaffold bridge checklist.

- Drift segment scaffold bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_scaffold_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_scaffold_bridge_checklist.md`
- This connects the segment scaffold to the drift handoff bridge checklist while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment handoff.

- Drift segment handoff table: `results/tables/meeteval_cpwer_alignment_drift_segment_handoff.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_handoff.md`
- `HeavyOverlap` segment inspection is handed off while reconciliation and cpWER execution remain pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment handoff bridge checklist.

- Drift segment handoff bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_handoff_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_handoff_bridge_checklist.md`
- This connects the segment handoff to the segment scaffold bridge checklist while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment inspection.

- Drift segment inspection table: `results/tables/meeteval_cpwer_alignment_drift_segment_inspection.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_inspection.md`
- The first narrow inspection on `HeavyOverlap` reports `inspection_pass = true` with `segment_count_delta = 0`; reconciliation and cpWER execution remain pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment inspection bridge checklist.

- Drift segment inspection bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_inspection_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_inspection_bridge_checklist.md`
- This connects the segment inspection to the segment handoff bridge checklist without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment reconciliation scaffold.

- Drift segment reconciliation scaffold: `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold.json`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold.md`
- `HeavyOverlap` reconciliation remains `scaffold_only` after `segment_inspection_complete`; reconciled alignment and cpWER execution remain pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment reconciliation scaffold bridge checklist.

- Drift segment reconciliation scaffold bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold_bridge_checklist.md`
- This connects the reconciliation scaffold to the segment inspection bridge checklist while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment reconciliation handoff.

- Drift segment reconciliation handoff: `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff.md`
- `HeavyOverlap` reconciliation diagnostic is handed off while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment reconciliation diagnostic.

- Drift segment reconciliation diagnostic: `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic.md`
- `HeavyOverlap` reports `reconciliation_pass = false` because per-speaker segment counts do not match even though total segment counts align.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment reconciliation diagnostic bridge checklist.

- Drift segment reconciliation diagnostic bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic_bridge_checklist.md`
- This connects the reconciliation diagnostic to the reconciliation handoff without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment reconciliation handoff bridge checklist.

- Drift segment reconciliation handoff bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff_bridge_checklist.md`
- This connects the reconciliation handoff to the reconciliation scaffold bridge checklist while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment speaker count diagnostic.

- Drift segment speaker count diagnostic: `results/tables/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_summary.md`
- `HeavyOverlap` reports `mismatched_speaker_count = 2/2` with `SPEAKER_1 delta=-1` and `SPEAKER_2 delta=+1`.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment speaker count diagnostic bridge checklist.

- Drift segment speaker count diagnostic bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_bridge_checklist.md`
- This connects the speaker count diagnostic to the reconciliation diagnostic bridge checklist without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment speaker count diagnostic handoff.

- Drift segment speaker count diagnostic handoff: `results/tables/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff.md`
- This hands off `HeavyOverlap` to per-speaker timing diagnostic follow-up while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment timing diagnostic.

- Drift segment timing diagnostic: `results/tables/meeteval_cpwer_alignment_drift_segment_timing_diagnostic.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_summary.md`
- `HeavyOverlap` reports `mismatched_speaker_count = 1/2` with `SPEAKER_1 delta=-2.360s`; reconciled alignment and cpWER execution remain pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment timing diagnostic bridge checklist.

- Drift segment timing diagnostic bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_bridge_checklist.md`
- This connects the timing diagnostic to the speaker count handoff bridge without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment speaker count diagnostic handoff bridge checklist.

- Drift segment speaker count diagnostic handoff bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff_bridge_checklist.md`
- This connects the speaker count handoff to the timing diagnostic bridge without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment timing diagnostic handoff.

- Drift segment timing diagnostic handoff: `results/tables/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff.md`
- This hands off `HeavyOverlap` to per-speaker granularity diagnostic follow-up while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment granularity diagnostic.

- Drift segment granularity diagnostic: `results/tables/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_summary.md`
- `HeavyOverlap` reports `mismatched_speaker_count = 1/2` with `SPEAKER_2 delta=-0.173s`; reconciled alignment and cpWER execution remain pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment timing diagnostic handoff bridge checklist.

- Drift segment timing diagnostic handoff bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff_bridge_checklist.md`
- This connects the timing handoff to the granularity diagnostic bridge without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment granularity diagnostic bridge checklist.

- Drift segment granularity diagnostic bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_bridge_checklist.md`
- This connects the granularity diagnostic to the timing handoff bridge without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment granularity diagnostic handoff.

- Drift segment granularity diagnostic handoff: `results/tables/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff.md`
- This hands off `HeavyOverlap` to per-speaker redistribution diagnostic follow-up while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment redistribution diagnostic.

- Drift segment redistribution diagnostic: `results/tables/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_summary.md`
- `HeavyOverlap` reports `redistribution_mismatch_count = 2/2` with `SPEAKER_1 hypothesis_merged` and `SPEAKER_2 hypothesis_split`; reconciled alignment and cpWER execution remain pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment granularity diagnostic handoff bridge checklist.

- Drift segment granularity diagnostic handoff bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff_bridge_checklist.md`
- This connects the granularity handoff to the redistribution diagnostic bridge without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment redistribution diagnostic bridge checklist.

- Drift segment redistribution diagnostic bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_bridge_checklist.md`
- This connects the redistribution diagnostic to the granularity handoff bridge without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment redistribution diagnostic handoff.

- Drift segment redistribution diagnostic handoff: `results/tables/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff.md`
- This hands off `HeavyOverlap` to the cpWER bridge handoff while cpWER execution remains pending.

Update: `meeteval_compatibility` now also has a cpWER alignment drift segment redistribution diagnostic handoff bridge checklist.

- Drift segment redistribution diagnostic handoff bridge checklist: `results/tables/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff_bridge_checklist.md`
- This connects the redistribution handoff to the cpWER bridge handoff without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER bridge handoff.

- cpWER bridge handoff: `results/tables/meeteval_cpwer_bridge_handoff.csv`
- Summary view: `results/figures/meeteval_cpwer_bridge_handoff.md`
- This keeps the bridge-lite result visible as the next narrow frontier step while full MeetEval evaluation remains pending.

Update: `meeteval_compatibility` now also has a cpWER bridge handoff bridge checklist.

- cpWER bridge handoff bridge checklist: `results/tables/meeteval_cpwer_bridge_handoff_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_bridge_handoff_bridge_checklist.md`
- This connects the cpWER bridge handoff to full MeetEval evaluation without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER execution scaffold.

- cpWER execution scaffold: `results/tables/meeteval_cpwer_execution_scaffold.csv`
- Summary view: `results/figures/meeteval_cpwer_execution_scaffold.md`
- The scaffold records `scaffold_status = scaffold_only`; official cpWER evaluation remains pending.

Update: `meeteval_compatibility` now also has a cpWER execution scaffold bridge checklist.

- cpWER execution scaffold bridge checklist: `results/tables/meeteval_cpwer_execution_scaffold_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_execution_scaffold_bridge_checklist.md`
- This connects the execution scaffold to official MeetEval evaluation without claiming cpWER execution.

Update: `meeteval_compatibility` now also has a cpWER execution handoff.

- cpWER execution handoff: `results/tables/meeteval_cpwer_execution_handoff.csv`
- Summary view: `results/figures/meeteval_cpwer_execution_handoff.md`
- The handoff targets official cpWER evaluation; benchmark completion remains pending.

Update: a generated llm critic review queue now turns the qualitative note into a first-pass triage order.

- LLM critic review queue: `results/tables/llm_critic_review_queue.csv`
- Summary view: `results/figures/llm_critic_review_queue.md`
- This remains a `qualitative/demo` artifact. It does not claim repaired transcripts; it simply orders which case should receive the next critic-style review pass and exposes that swapped-profile uncertainty is still common.

Update: a generated llm critic review receipt now creates the first evidence writeback slot.

- LLM critic review receipt: `results/tables/llm_critic_review_receipt.json`
- Summary view: `results/figures/llm_critic_review_receipt.md`
- This stays on the same safe side of the line: it prepares the template-only receipt for a future critic-style pass without implying that any repair loop has already succeeded.

Update: a generated benchmark runbook card now turns the triage panel into a one-page execution brief.

- Benchmark runbook card: `results/tables/cascade_benchmark_runbook_card.csv`
- Summary view: `results/figures/cascade_benchmark_runbook_card.md`
- This shows the first benchmark action, the required evidence payload, and the completion target without needing to open the wider handoff stack.

Update: a generated benchmark milestone card now turns the execution brief into a progress boundary.

- Benchmark milestone card: `results/tables/cascade_benchmark_milestone_card.csv`
- Summary view: `results/figures/cascade_benchmark_milestone_card.md`
- This shows the next milestone, what the current first step unlocks, and how many benchmark phases remain before the controlled stack is fully refreshed.

Update: a generated benchmark phase checkpoint card now turns the progress boundary into a per-phase execution check.

- Benchmark phase checkpoint card: `results/tables/cascade_benchmark_phase_checkpoint_card.csv`
- Summary view: `results/figures/cascade_benchmark_phase_checkpoint_card.md`
- This shows each phase's blocker, next action, and completion signal without reopening the larger packet.

Update: a generated benchmark completion dashboard now turns the phase checks into a top-level pending-state overview.

- Benchmark completion dashboard: `results/tables/cascade_benchmark_completion_dashboard.csv`
- Summary view: `results/figures/cascade_benchmark_completion_dashboard.md`
- This shows the current start step, dominant blocker family, and pending phase count in one place for quick progress scanning.

Update: a generated benchmark operator brief now turns the pending-state overview into a plain-language operator note.

- Benchmark operator brief: `results/tables/cascade_benchmark_operator_brief.csv`
- Summary view: `results/figures/cascade_benchmark_operator_brief.md`
- This shows the single benchmark step to run now, the evidence to collect, and the urgency note without opening the wider stack first.

Update: a generated benchmark frontier bridge now connects that operator note back to the breadth-first frontier queue.

- Benchmark frontier bridge: `results/tables/cascade_benchmark_frontier_bridge.csv`
- Summary view: `results/figures/cascade_benchmark_frontier_bridge.md`
- This stays strictly at the coordination layer: it explains why the benchmark runtime foundation still belongs at the front of the broader work stream without claiming any new timing evidence.

Update: a generated benchmark frontier bridge checklist now turns that bridge into a verification path.

- Benchmark frontier bridge checklist: `results/tables/cascade_benchmark_frontier_bridge_checklist.csv`
- Summary view: `results/figures/cascade_benchmark_frontier_bridge_checklist.md`
- This keeps the same runtime-foundation link visible while making the bridge itself row-by-row checkable before the frontier queue advances.

Update: a generated benchmark evidence receipt now turns the operator note into a writeback closeout card.

- Benchmark evidence receipt: `results/tables/cascade_benchmark_evidence_receipt.csv`
- Summary view: `results/figures/cascade_benchmark_evidence_receipt.md`
- This shows what the current benchmark run must write back, which completion signal closes it, and what follow-up note should remain after the run.

Update: a generated benchmark handoff packet now turns the execution stack into a single benchmark entrypoint.

- Handoff packet: `results/figures/cascade_benchmark_handoff_packet.md`
- This lets future contributors start from one note before diving into readiness, plan, checklist, manifest, execution-summary, execution-queue, session-ledger, dependency-graph, blocker-matrix, runbook-card, milestone-card, phase-checkpoint-card, completion-dashboard, operator-brief, evidence-receipt, and status details.

Update: a generated benchmark receipt bridge now connects that entrypoint to the receipt target.

- Benchmark receipt bridge: `results/tables/cascade_benchmark_receipt_bridge.csv`
- Summary view: `results/figures/cascade_benchmark_receipt_bridge.md`
- This keeps the benchmark coordination stack easier to finish without overstating progress: it points the current benchmark step from the handoff packet down to the evidence receipt without implying that any timing capture has already happened.

Update: a generated benchmark receipt bridge checklist now turns that bridge into an ordered writeback path.

- Benchmark receipt bridge checklist: `results/tables/cascade_benchmark_receipt_bridge_checklist.csv`
- Summary view: `results/figures/cascade_benchmark_receipt_bridge_checklist.md`
- This keeps the same receipt-target link visible while making the bridge itself row-by-row checkable before the benchmark closeout sequence advances.

Update: a generated external validation slice bridge checklist now turns the first external handoff into a bridge verification path.

- External validation slice bridge checklist: `results/tables/external_validation_slice_bridge_checklist.csv`
- Summary view: `results/figures/external_validation_slice_bridge_checklist.md`
- This keeps the external handoff and receipt targets visible together while staying explicit that no external benchmark execution has yet happened.

Update: a generated MeetEval dry run bridge checklist now turns the handoff into a bridge verification path.

- MeetEval dry run bridge checklist: `results/tables/meeteval_dry_run_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_dry_run_bridge_checklist.md`
- This keeps the MeetEval handoff and receipt targets visible together while staying explicit that no cpWER execution has yet happened.

Remaining stretch work:

- replace proxy costs with a controlled hardware/runtime benchmark
- evaluate a true stronger-model fallback when compute budget allows

## Phase 4: Speaker Profile / Voiceprint

- known-speaker enrollment
- speaker attribution risk detection
- contaminated track detection

## Phase 5: Agentic LLM Critic and Repair

- transcript critique
- repair suggestion loops
- uncertainty-aware review

## Phase 6: External Mini Validation

- small sanity check on an external dataset
- license/source documented
- gold/silver separation preserved

## Phase 7: Demo and Public-facing GitHub Excellence

- Streamlit demo
- presentation / video polish
- architecture diagrams
- onboarding clarity

Update: the project harness now includes a breadth-first frontier status view.

- Harness report: `results/figures/project_harness_report.md`
- This table makes the current status, evidence path, expected output, and next step visible for `speaker_profile`, `meeteval_compatibility`, `llm_critic`, `external_validation`, and `demo_excellence`.

Update: the project harness now also includes a frontier execution queue.

- Frontier queue: `results/tables/frontier_execution_queue.json`
- Summary view: `results/figures/frontier_execution_queue.md`
- This keeps the breadth-first layer actionable without overstating completion: it simply orders the next frontier handoffs that already exist in the repository.
- Current queue head: `meeteval_compatibility`
- First move: use the MeetEval readiness path to stage a narrow dry run before the backlog branches out again.

Update: the project harness now also includes a frontier focus card.

- Frontier focus card: `results/tables/frontier_focus_card.json`
- Summary view: `results/figures/frontier_focus_card.md`
- This is the shortest coordination layer in the stack: it shows the current queue head without adding any new experimental claim.

Update: the project harness now also includes a frontier handoff packet.

- Frontier handoff packet: `results/tables/frontier_handoff_packet.json`
- Summary view: `results/figures/frontier_handoff_packet.md`
- This keeps the breadth-first layer moving with less ambiguity: it points the current queue head directly at the next artifact and expected evidence target while remaining coordination-only.

Update: the project harness now also includes a frontier receipt packet.

- Frontier receipt packet: `results/tables/frontier_receipt_packet.json`
- Summary view: `results/figures/frontier_receipt_packet.md`
- This keeps the same coordination thread intact while making the writeback target more explicit: it points the current queue head at the prerequisite artifact and receipt slot without implying that the frontier step has already happened.

Update: the project harness now also includes a frontier receipt map.

- Frontier receipt map: `results/tables/frontier_receipt_map.json`
- Summary view: `results/figures/frontier_receipt_map.md`
- This broadens the same idea across every current frontier: it lets contributors scan queue order, prerequisite artifact, and receipt target in one table without changing priority or implying execution.

Update: the project harness now also includes a frontier parallel picklist.

- Frontier parallel picklist: `results/tables/frontier_parallel_picklist.json`
- Summary view: `results/figures/frontier_parallel_picklist.md`
- This keeps the same breadth-first set visible while making parallel pickup easier: it lets contributors scan queue order, pickup artifact, and receipt target without changing priority or implying execution.

Update: the project harness now also includes a frontier receipt board.

- Frontier receipt board: `results/tables/frontier_receipt_board.json`
- Summary view: `results/figures/frontier_receipt_board.md`
- This consolidates the same breadth-first set into a single receipt snapshot: it keeps queue order, pickup artifact, and receipt target visible together while remaining coordination-only.

Update: the project harness now also includes a frontier coordination matrix.

- Frontier coordination matrix: `results/tables/frontier_coordination_matrix.json`
- Summary view: `results/figures/frontier_coordination_matrix.md`
- This combines the same breadth-first set into a richer scan table: it keeps queue order, entry artifact, pickup artifact, and receipt target visible together while staying coordination-only.

Update: the project harness now also includes a frontier writeback index.

- Frontier writeback index: `results/tables/frontier_writeback_index.json`
- Summary view: `results/figures/frontier_writeback_index.md`
- This isolates the writeback target for each current frontier: it keeps queue order, entry artifact, and receipt target visible together without changing priority or implying execution.

Update: `meeteval_compatibility` now has a first concrete bridge artifact.

- Compatibility note: `results/figures/meeteval_compatibility_note.md`
- Segment exports: `results/tables/meeteval_reference_segments.jsonl`, `results/tables/meeteval_hypothesis_segments.jsonl`
- This is a compatibility bridge only: it exports segment-level reference and hypothesis candidates for future MeetEval / cpWER work without claiming that standard meeting metrics have already been run.

Update: `meeteval_compatibility` now also has a readiness handoff card.

- Readiness card: `results/tables/meeteval_readiness.csv`
- Summary view: `results/figures/meeteval_readiness.md`
- This keeps the scope narrow: it says the export is ready for a diagnostic dry run, while also recording that cleaned fallback remains common and therefore the bridge is not yet a clean raw-transcript benchmark story.

Update: `meeteval_compatibility` now also has a dry-run handoff packet.

- Handoff table: `results/tables/meeteval_dry_run_handoff.csv`
- Handoff view: `results/figures/meeteval_dry_run_handoff.md`
- This is still a coordination artifact rather than an evaluation result: it translates readiness into a single recommended first slice, blocker, and evidence target so the next contributor can run one narrow diagnostic step without overstating progress.

Update: `meeteval_compatibility` now also has a dry-run receipt template.

- Receipt table: `results/tables/meeteval_dry_run_receipt.json`
- Receipt view: `results/figures/meeteval_dry_run_receipt.md`
- This stays on the same safe side of the line: it creates the evidence slot for a future dry run without implying that the run has already happened.

Update: `speaker_profile` now has a first lightweight risk-signal artifact.

- Profile summary: `results/figures/speaker_profile_risk_summary.md`
- Table: `results/tables/speaker_profile_similarity.csv`
- This remains a narrow text-profile bridge rather than a voiceprint result, and its current value is diagnostic: the simple profile signal prefers swapped alignment across the verified gold cases, so it is useful as a warning sign rather than a deployment-ready attribution tool.

Update: `speaker_profile` now also has a triage handoff card.

- Triage card: `results/tables/speaker_profile_triage.csv`
- Summary view: `results/figures/speaker_profile_triage.md`
- This keeps the scope deliberately modest: it aggregates the current failure pattern, records that the gold cases currently collapse into `swapped_bias`, and uses that evidence to justify a stronger next profile method rather than any speaker-ID claim.

Update: `speaker_profile` now also has a method handoff packet.

- Method handoff: `results/tables/speaker_profile_method_handoff.csv`
- Summary view: `results/figures/speaker_profile_method_handoff.md`
- This keeps the frontier executable without overstating progress: it translates the current `swapped_bias` finding into a first stronger-method direction and expected evidence target while remaining diagnostic-only.

Update: `speaker_profile` now also has a method receipt template.

- Method receipt: `results/tables/speaker_profile_method_receipt.json`
- Summary view: `results/figures/speaker_profile_method_receipt.md`
- This stays on the same safe side of the line: it creates the evidence slot for a future stronger-method trial without implying that any improved profile baseline has already succeeded.

Update: `speaker_profile` now also has a method bridge checklist.

- Method bridge checklist: `results/tables/speaker_profile_method_bridge_checklist.csv`
- Summary view: `results/figures/speaker_profile_method_bridge_checklist.md`
- This keeps the method handoff and receipt visible together while staying explicit that no stronger speaker-profile method has yet been executed.

Update: `llm_critic` now has a first qualitative artifact.

- Critic note: `results/figures/llm_critic_qualitative_note.md`
- Table: `results/tables/llm_critic_qualitative_summary.csv`
- This is intentionally a qualitative/demo bridge only: it converts structured risk cues into critic-style explanations, candidate repairs, and uncertainty notes without claiming that an actual LLM has verified or fixed the transcript.

Update: `llm_critic` now also has a review bridge checklist.

- Review bridge checklist: `results/tables/llm_critic_review_bridge_checklist.csv`
- Summary view: `results/figures/llm_critic_review_bridge_checklist.md`
- This keeps the critic queue and receipt visible together while staying explicit that no repaired transcript has yet been verified.

Update: `demo_excellence` now has a first lightweight onboarding artifact.

- Demo storyboard: `results/figures/demo_storyboard.md`
- Story cards: `results/tables/demo_storyboard_cards.json`
- This is a simple demo-facing bridge rather than a full app: it gives a new visitor a one-page explanation of the problem, pipeline, findings, and frontier directions before heavier UI work exists.

Update: `demo_excellence` now also has a storyboard receipt.

- Storyboard receipt: `results/tables/demo_storyboard_receipt.json`
- Summary view: `results/figures/demo_storyboard_receipt.md`
- This keeps the storyboard review path explicit while staying clear that no live demo or recording has yet been completed.

Update: `demo_excellence` now also has a storyboard receipt bridge.

- Storyboard receipt bridge: `results/tables/demo_storyboard_receipt_bridge.csv`
- Summary view: `results/figures/demo_storyboard_receipt_bridge.md`
- This keeps the storyboard cards and storyboard receipt visible together while staying explicit that no live demo or recording has yet been completed.

Update: `demo_excellence` now also has a storyboard receipt checklist.

- Storyboard receipt checklist: `results/tables/demo_storyboard_receipt_checklist.csv`
- Summary view: `results/figures/demo_storyboard_receipt_checklist.md`
- This keeps the storyboard and receipt visible together while staying explicit that no live demo or recording has yet been completed.

Update: `demo_excellence` now also has a storyboard receipt board.

- Storyboard receipt board: `results/tables/demo_storyboard_receipt_board.csv`
- Summary view: `results/figures/demo_storyboard_receipt_board.md`
- This keeps the storyboard receipt path visible in one compact snapshot while staying explicit that no live demo or recording has yet been completed.

Update: `demo_excellence` now also has a storyboard receipt map.

- Storyboard receipt map: `results/tables/demo_storyboard_receipt_map.csv`
- Summary view: `results/figures/demo_storyboard_receipt_map.md`
- This keeps the storyboard receipt path visible across the receipt, checklist, and board layers while staying explicit that no live demo or recording has yet been completed.

Update: `demo_excellence` now also has a storyboard bridge checklist.

- Storyboard bridge checklist: `results/tables/demo_storyboard_bridge_checklist.csv`
- Summary view: `results/figures/demo_storyboard_bridge_checklist.md`
- This keeps the storyboard and walkthrough visible together while staying explicit that no live demo or recording has yet been completed.

Update: `demo_excellence` now also has a walkthrough bridge checklist.

- Walkthrough bridge checklist: `results/tables/demo_walkthrough_bridge_checklist.csv`
- Summary view: `results/figures/demo_walkthrough_bridge_checklist.md`
- This keeps the walkthrough and receipt visible together while staying explicit that no live demo or recording has yet been completed.

Update: `demo_excellence` now also has a walkthrough review pass.

- Walkthrough review pass: `results/tables/demo_walkthrough_review_pass.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass.md`
- The first qualitative walkthrough review pass records `review_status = review_complete` without claiming live demo or recording delivery.

Update: `demo_excellence` now also has a walkthrough review pass advance layer.

- Walkthrough review pass advance: `results/tables/demo_walkthrough_review_pass_advance.csv`
- Second pass table: `results/tables/demo_walkthrough_review_pass_second.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_advance.md`
- Step `2` (`Baseline evidence`) is the second queue pass after step `1`; no live demo delivery is claimed.

Update: `demo_excellence` now also has a walkthrough review pass continue layer.

- Walkthrough review pass continue: `results/tables/demo_walkthrough_review_pass_continue.csv`
- Third pass table: `results/tables/demo_walkthrough_review_pass_third.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_continue.md`
- Step `3` (`Routing takeaway`) is the third queue pass after steps `1` and `2`; no live demo delivery is claimed.

Update: `demo_excellence` now also has a walkthrough review pass continue bridge checklist.

- Walkthrough review pass continue bridge checklist: `results/tables/demo_walkthrough_review_pass_continue_bridge_checklist.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_continue_bridge_checklist.md`
- This connects step `3` to the step `4` second-continue pass without claiming live demo delivery.

Update: `demo_excellence` now also has a walkthrough review pass second continue layer.

- Walkthrough review pass second continue: `results/tables/demo_walkthrough_review_pass_second_continue.csv`
- Fourth pass table: `results/tables/demo_walkthrough_review_pass_fourth.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_second_continue.md`
- Step `4` (`Frontier breadth`) is the fourth queue pass after steps `1`–`3`; no live demo delivery is claimed.

Update: `demo_excellence` now also has a walkthrough review pass third continue layer.

- Walkthrough review pass third continue: `results/tables/demo_walkthrough_review_pass_third_continue.csv`
- Fifth pass table: `results/tables/demo_walkthrough_review_pass_fifth.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_third_continue.md`
- Step `5` (`Next-step framing`) closes the gold walkthrough queue at `5/5`; no live demo delivery is claimed.

Update: `demo_excellence` now also has a walkthrough review pass status rollup.

- Walkthrough review pass status: `results/tables/demo_walkthrough_review_pass_status.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_status.md`
- `queue_status = queue_complete` without any live demo or recording claim.

Update: `demo_excellence` now also has a walkthrough review pass status bridge checklist.

- Walkthrough review pass status bridge checklist: `results/tables/demo_walkthrough_review_pass_status_bridge_checklist.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_status_bridge_checklist.md`
- This connects the status rollup to the final pass bridge without claiming live demo delivery.

Update: `demo_excellence` now also has a walkthrough review pass final bridge checklist.

- Walkthrough review pass final bridge checklist: `results/tables/demo_walkthrough_review_pass_final_bridge_checklist.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_final_bridge_checklist.md`
- This connects step `5` to the completion summary without claiming live demo delivery.

Update: `demo_excellence` now also has a walkthrough review pass completion summary.

- Walkthrough review pass completion summary: `results/tables/demo_walkthrough_review_pass_completion_summary.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_completion_summary.md`
- `queue_status = queue_complete` at `5/5` without any live demo or recording claim.

Update: `demo_excellence` now also has a walkthrough review pass completion summary bridge checklist.

- Walkthrough review pass completion summary bridge checklist: `results/tables/demo_walkthrough_review_pass_completion_summary_bridge_checklist.csv`
- Summary view: `results/figures/demo_walkthrough_review_pass_completion_summary_bridge_checklist.md`
- This connects the walkthrough completion summary to the storyboard review pass without claiming live demo delivery.

Update: `demo_excellence` now also has a storyboard review pass.

- Storyboard review pass: `results/tables/demo_storyboard_review_pass.csv`
- Summary view: `results/figures/demo_storyboard_review_pass.md`
- The first qualitative storyboard review pass records `review_complete` for the `Problem` card without claiming live demo delivery.

Update: `demo_excellence` now also has a storyboard review pass advance.

- Storyboard review pass advance: `results/tables/demo_storyboard_review_pass_advance.csv`
- Second pass table: `results/tables/demo_storyboard_review_pass_second.csv`
- Summary view: `results/figures/demo_storyboard_review_pass_advance.md`
- Card `2` (`Pipeline`) is the second queue pass after card `1`; no live demo delivery is claimed.

Update: `demo_excellence` now also has a storyboard review pass advance bridge checklist.

- Storyboard review pass advance bridge checklist: `results/tables/demo_storyboard_review_pass_advance_bridge_checklist.csv`
- Summary view: `results/figures/demo_storyboard_review_pass_advance_bridge_checklist.md`
- This connects card `2` to the third-card review pass without claiming live demo delivery.

Update: `demo_excellence` now also has a storyboard review pass continue.

- Storyboard review pass continue: `results/tables/demo_storyboard_review_pass_continue.csv`
- Third pass table: `results/tables/demo_storyboard_review_pass_third.csv`
- Summary view: `results/figures/demo_storyboard_review_pass_continue.md`
- Card `3` (`Findings`) is the third queue pass after cards `1` and `2`; no live demo delivery is claimed.

Update: `demo_excellence` now also has a storyboard review pass second continue.

- Storyboard review pass second continue: `results/tables/demo_storyboard_review_pass_second_continue.csv`
- Fourth pass table: `results/tables/demo_storyboard_review_pass_fourth.csv`
- Summary view: `results/figures/demo_storyboard_review_pass_second_continue.md`
- Card `4` (`Frontier`) closes the storyboard queue at `4/4`; no live demo delivery is claimed.

Update: `demo_excellence` now also has a storyboard review pass continue bridge checklist.

- Storyboard review pass continue bridge checklist: `results/tables/demo_storyboard_review_pass_continue_bridge_checklist.csv`
- Summary view: `results/figures/demo_storyboard_review_pass_continue_bridge_checklist.md`
- This connects card `3` to the fourth-card review pass without claiming live demo delivery.

Update: `demo_excellence` now also has a storyboard review pass status rollup.

- Storyboard review pass status: `results/tables/demo_storyboard_review_pass_status.csv`
- Summary view: `results/figures/demo_storyboard_review_pass_status.md`
- `queue_status = queue_complete` at `4/4` without any live demo or recording claim.

Update: `demo_excellence` now also has a storyboard review pass status bridge checklist.

- Storyboard review pass status bridge checklist: `results/tables/demo_storyboard_review_pass_status_bridge_checklist.csv`
- Summary view: `results/figures/demo_storyboard_review_pass_status_bridge_checklist.md`
- This connects the status rollup to the completion summary without claiming live demo delivery.

Update: `demo_excellence` now also has a storyboard review pass completion summary.

- Storyboard review pass completion summary: `results/tables/demo_storyboard_review_pass_completion_summary.csv`
- Summary view: `results/figures/demo_storyboard_review_pass_completion_summary.md`
- `queue_status = queue_complete` at `4/4` without any live demo or recording claim.

Update: `demo_excellence` now also has a storyboard review pass completion summary bridge checklist.

- Storyboard review pass completion summary bridge checklist: `results/tables/demo_storyboard_review_pass_completion_summary_bridge_checklist.csv`
- Summary view: `results/figures/demo_storyboard_review_pass_completion_summary_bridge_checklist.md`
- This connects the storyboard completion summary to the demo excellence queue status without claiming live demo delivery.

Update: `demo_excellence` now also has a unified queue status rollup.

- Demo excellence queue status: `results/tables/demo_excellence_queue_status.csv`
- Summary view: `results/figures/demo_excellence_queue_status.md`
- `combined_queue_status = queue_complete` when both walkthrough and storyboard queues are complete; no live demo delivery is claimed.

Update: `external_validation` now has a dedicated skill card.

- Skill card: `docs/skills/skill_07_external_validation.md`
- This makes the external mini-validation frontier directly pickable from the skills index, so the queue head is no longer only discoverable from the roadmap or project-state layers.

Update: `meeteval_compatibility` now also has execution status bridge checklists.

- MeetEval execution status bridge: `results/tables/meeteval_cpwer_execution_status_bridge_checklist.csv`
- Summary view: `results/figures/meeteval_cpwer_execution_status_bridge_checklist.md`
- This connects the execution-chain status rollup to the official cpWER receipt gate without claiming benchmark execution.

Update: `speaker_profile` now also has execution status bridge checklists.

- Speaker profile execution status bridge: `results/tables/speaker_profile_embedding_trial_execution_status_bridge_checklist.csv`
- Summary view: `results/figures/speaker_profile_embedding_trial_execution_status_bridge_checklist.md`
- This connects the embedding execution-chain status rollup to the execution receipt without claiming voiceprint success.

Update: `external_validation` now also has staging receipt scaffold bridge checklists and execution status.

- Staging receipt scaffold bridge: `results/tables/external_validation_slice_staging_handoff_receipt_scaffold_bridge_checklist.csv`
- Staging execution status: `results/tables/external_validation_slice_staging_execution_status.csv`
- Summary views: `results/figures/external_validation_slice_staging_handoff_receipt_scaffold_bridge_checklist.md`, `results/figures/external_validation_slice_staging_execution_status.md`
- External audio staging remains pending; no benchmark execution is claimed.

Update: the frontier now has a unified execution queue status rollup.

- Frontier execution queue status: `results/tables/frontier_execution_queue_status.csv`
- Frontier execution queue status bridge: `results/tables/frontier_execution_queue_status_bridge_checklist.csv`
- Summary views: `results/figures/frontier_execution_queue_status.md`, `results/figures/frontier_execution_queue_status_bridge_checklist.md`
- `combined_chain_status = execution_chain_ready` when MeetEval, speaker profile, and external staging chains are all ready; no benchmark execution is claimed.

Update: `meeteval_compatibility` now has a dedicated skill card.

- Skill card: `docs/skills/skill_04_meeteval_compatibility.md`
- The frontier queue head is now directly pickable from the skills index.

## Healthy Project Principles

- New experiments should be isolated.
- Stable results should not be overwritten.
- Gold / silver / experimental / demo labels must be clear.
- Every ambitious module needs an owner and output path.
