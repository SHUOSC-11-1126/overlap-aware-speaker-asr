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

Update: a generated benchmark evidence receipt now turns the operator note into a writeback closeout card.

- Benchmark evidence receipt: `results/tables/cascade_benchmark_evidence_receipt.csv`
- Summary view: `results/figures/cascade_benchmark_evidence_receipt.md`
- This shows what the current benchmark run must write back, which completion signal closes it, and what follow-up note should remain after the run.

Update: a generated benchmark handoff packet now turns the execution stack into a single benchmark entrypoint.

- Handoff packet: `results/figures/cascade_benchmark_handoff_packet.md`
- This lets future contributors start from one note before diving into readiness, plan, checklist, manifest, execution-summary, execution-queue, session-ledger, dependency-graph, blocker-matrix, runbook-card, milestone-card, phase-checkpoint-card, completion-dashboard, operator-brief, evidence-receipt, and status details.

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

Update: `meeteval_compatibility` now has a first concrete bridge artifact.

- Compatibility note: `results/figures/meeteval_compatibility_note.md`
- Segment exports: `results/tables/meeteval_reference_segments.jsonl`, `results/tables/meeteval_hypothesis_segments.jsonl`
- This is a compatibility bridge only: it exports segment-level reference and hypothesis candidates for future MeetEval / cpWER work without claiming that standard meeting metrics have already been run.

## Healthy Project Principles

- New experiments should be isolated.
- Stable results should not be overwritten.
- Gold / silver / experimental / demo labels must be clear.
- Every ambitious module needs an owner and output path.
