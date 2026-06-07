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

Update: `external_validation` now has a dedicated skill card.

- Skill card: `docs/skills/skill_07_external_validation.md`
- This makes the external mini-validation frontier directly pickable from the skills index, so the queue head is no longer only discoverable from the roadmap or project-state layers.

## Healthy Project Principles

- New experiments should be isolated.
- Stable results should not be overwritten.
- Gold / silver / experimental / demo labels must be clear.
- Every ambitious module needs an owner and output path.
