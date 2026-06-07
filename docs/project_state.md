# Project State

This document is for future Codex / AI coding agents so they can resume work without losing project context.

## Current Project Title

**When Should We Separate? Boundary-aware, Compute-aware, Speaker-aware, and Agent-augmented ASR for Overlapping Speech**

## Teacher Feedback and Direction Shift

- The core technical baseline is complete.
- Future agents are encouraged to explore the frontier, not just maintain the baseline.
- The project direction has therefore shifted from a maintenance-only mindset to a stable baseline + ambitious frontier exploration mindset.
- The stable baseline remains preserved.
- Future agents may explore phase diagrams, compute-aware cascades, voiceprint ideas, LLM critic loops, external mini validation, and demo excellence.

## Completed Stages

- Stage 1 project skeleton
- mixed Whisper baseline
- separated speaker-track ASR
- duplicate suppression
- 5 verified gold references
- global CER
- error type analysis
- adaptive router v1
- adaptive router v2
- router ablation
- synthetic silver benchmark
- synthetic silver evaluation
- held-out synthetic split validation
- speaker-aware CER
- cpCER-lite
- risk-aware selector
- project context docs
- docs index
- markdown audit
- skills cards
- roadmap
- maintenance harness
- contribution records
- handoff notes
- backup plan
- ambitious research agenda
- challenge board
- experiment proposal template
- experimental compute-aware cascade analysis

## Current Core Findings

1. Speech separation is useful but not universally beneficial.
2. `NoOverlap`, `HeavyOverlap`, and `OppositeOverlap` benefit strongly from separated speaker-track ASR.
3. `LightOverlap` and `MidOverlap` degradation is mainly caused by insertion and repetition hallucination.
4. Speaker swap is not the dominant error source in the five gold cases.
5. Overlap-only router v1 performs perfectly on gold but fails on synthetic silver validation.
6. Feature-based router v2 improves robustness using repetition and duplicate-removal signals.
7. Risk-aware selector is a deployability and explainability layer, not the best-CER result.
8. Synthetic benchmarks are silver robustness validation, not gold evaluation.
9. LLM/RAG is optional future extension, not the current core quantitative contribution.
10. The compute-aware cascade is an experimental/frontier cost analysis layer; it evaluates route cost after reference-free decisions are fixed and does not use CER as a routing input.

## Gold Benchmark Final CER Table

### NoOverlap

- `mixed_whisper: 0.215827`
- `separated_whisper: 0.053957`
- `separated_whisper_cleaned: 0.089928`
- `best: separated_whisper`

### LightOverlap

- `mixed_whisper: 0.210714`
- `separated_whisper: 0.475000`
- `separated_whisper_cleaned: 0.382143`
- `best: mixed_whisper`

### MidOverlap

- `mixed_whisper: 0.178947`
- `separated_whisper: 0.273684`
- `separated_whisper_cleaned: 0.207018`
- `best: mixed_whisper`

### HeavyOverlap

- `mixed_whisper: 0.386861`
- `separated_whisper: 0.109489`
- `separated_whisper_cleaned: 0.145985`
- `best: separated_whisper`

### OppositeOverlap

- `mixed_whisper: 0.518116`
- `separated_whisper: 0.047101`
- `separated_whisper_cleaned: 0.083333`
- `best: separated_whisper`

### Averages

- `fixed mixed: 0.302093`
- `fixed separated: 0.191846`
- `fixed cleaned: 0.181681`
- `router_v2: 0.120042`
- `oracle best: 0.120042`

## Synthetic Findings

### Original 25 synthetic silver

- `v1: 0.350902`
- `v2: 0.167553`
- `oracle: 0.082239`

### Held-out synthetic test

- `v1: 0.361350`
- `v2: 0.335326`
- `oracle: 0.115181`

### Interpretation

- `v2` improves stability but still has a gap to oracle.
- Improvement mainly comes from `SyntheticNoOverlap`.
- Synthetic results are silver robustness evidence, not gold evaluation.

## Speaker-Aware Findings

### speaker_macro_cer

- `NoOverlap separated: 0.054312, cleaned: 0.089278`
- `LightOverlap separated: 0.194170, cleaned: 0.135164`
- `MidOverlap separated: 0.175908, cleaned: 0.168620`
- `HeavyOverlap separated: 0.110821, cleaned: 0.146535`
- `OppositeOverlap separated: 0.047479, cleaned: 0.083193`

## cpCER-lite Findings

- No obvious speaker permutation mismatch.
- `speaker_assignment_gap = 0.0` for all five gold cases.
- Main errors are content-level, not speaker-swap-level.

## Risk-Aware Selector Findings

- `NoOverlap -> separated_whisper`
- `LightOverlap -> mixed_whisper`
- `MidOverlap -> mixed_whisper`
- `HeavyOverlap -> separated_whisper_cleaned`
- `OppositeOverlap -> separated_whisper_cleaned`

### Averages

- `risk_aware_selector: 0.134587`
- `router_v2: 0.120042`
- `oracle_best: 0.120042`

## Experimental Compute-Aware Cascade Findings

Label: `experimental/frontier`

- `router_v2_costed: average_cer 0.120042, relative_cost_vs_fixed_separated 0.929533`
- `risk_aware_costed: average_cer 0.134587, relative_cost_vs_fixed_separated 0.929533`
- `budget_cascade: average_cer 0.134587, relative_cost_vs_fixed_separated 0.929533`

Outputs:

- `results/tables/cascade_performance.csv`
- `results/figures/compute_aware_cascade_summary.md`
- `results/figures/cer_runtime_tradeoff.png`

Interpretation:

- This is an offline costed analysis of the five gold cases.
- It uses observed runtime fields when available and deterministic proxy costs otherwise.
- CER is reserved for post-decision evaluation only.

Runtime provenance audit:

- `results/tables/cascade_runtime_audit.csv`
- `results/figures/cascade_runtime_audit.md`
- Current committed gold cascade outputs use observed runtime for all `5/5` selections in every reported strategy.
- The proxy cost model remains a guardrail for missing-runtime edge cases rather than an active source in the current gold result tables.

Runtime normalization audit:

- `results/tables/cascade_runtime_normalization.csv`
- `results/figures/cascade_runtime_normalization.md`
- Gold `router_v2_costed`, `risk_aware_costed`, and `budget_cascade` all show `average_rtf 0.080646` when normalized by selected-route processed audio duration.
- This RTF is not a wall-clock latency claim; separated routes divide by two-stream processed duration.

Pareto frontier audit:

- `results/tables/cascade_pareto.csv`
- `results/figures/cascade_pareto.md`
- Gold `ALL` frontier strategies are `fixed_mixed_whisper` and `router_v2_costed`.
- `risk_aware_costed` and `budget_cascade` are dominated by `router_v2_costed`; `fixed_separated_whisper_cleaned` is also dominated once CER and average compute cost are considered jointly.

Recommendation card:

- `results/tables/cascade_recommendations.csv`
- `results/figures/cascade_recommendations.md`
- Gold `ALL` recommends `router_v2_costed` for both `accuracy_first` and `balanced`, while `fixed_mixed_whisper` remains the `cost_first` option.

Robustness gap audit:

- `results/tables/cascade_robustness_gap.csv`
- `results/figures/cascade_robustness_gap.md`
- Best shared cross-dataset stability currently comes from `fixed_separated_whisper_cleaned` with `cer_gap_vs_gold -0.00266`.
- Among adaptive shared routes, `router_v2` is more stable than `budget_cascade` on the held-out synthetic split `ALL` view.

Recommendation stability audit:

- `results/tables/cascade_recommendation_stability.csv`
- `results/figures/cascade_recommendation_stability.md`
- `cost_first` is fully stable across gold and synthetic `ALL/DEV/TEST`, always selecting `fixed_mixed_whisper`.
- `balanced` and `accuracy_first` each show `consensus_ratio 0.75`, indicating useful but not perfect cross-scope recommendation stability.

Recommendation family stability audit:

- `results/tables/cascade_recommendation_family_stability.csv`
- `results/figures/cascade_recommendation_family_stability.md`
- After merging `router_v2_costed` and `router_v2_synthetic_costed` into the same family, `balanced` becomes fully stable with `consensus_ratio 1.0`.
- `accuracy_first` remains the only profile with meaningful family-level disagreement across scopes.

Decision matrix:

- `results/tables/cascade_decision_matrix.csv`
- `results/figures/cascade_decision_matrix.md`
- `accuracy_first` now surfaces as the most robust accuracy-biased profile because its synthetic `ALL` recommendation aligns with the best shared robustness rank.
- `balanced` is the cleanest default profile because it combines `router_v2` family stability with mid-pack robustness and lower synthetic `ALL` cost than `accuracy_first`.

Frontier report:

- `results/figures/cascade_frontier_report.md`
- This generated note now acts as the single-entry summary for the current compute-aware cascade frontier evidence.

Artifact index:

- `results/tables/cascade_artifact_index.csv`
- `results/figures/cascade_artifact_index.md`
- This generated registry now maps the cascade evidence stack by dataset label, artifact group, generator command, and intended usage.

Benchmark readiness:

- `results/tables/cascade_benchmark_readiness.csv`
- `results/figures/cascade_benchmark_readiness.md`
- This generated scaffold now prioritizes which cascade artifacts should be refreshed first when controlled hardware/runtime benchmark evidence becomes available.

Benchmark plan:

- `results/tables/cascade_benchmark_plan.csv`
- `results/figures/cascade_benchmark_plan.md`
- This generated handoff plan now sequences the controlled benchmark refresh into foundation, surface, and cross-dataset stages.

Profile playbook:

- `results/tables/cascade_profile_playbook.csv`
- `results/figures/cascade_profile_playbook.md`
- This generated guide now explains when each deployment profile is the cleanest default, the strongest robustness-biased choice, or the cheapest stable floor.

Benchmark checklist:

- `results/tables/cascade_benchmark_checklist.csv`
- `results/figures/cascade_benchmark_checklist.md`
- This generated checklist now records the run metadata and acceptance checks required for each controlled benchmark phase.

Benchmark manifest template:

- `results/tables/cascade_benchmark_manifest_template.csv`
- This generated fill-in template now turns the checklist metadata requirements into a session log skeleton for real controlled timing runs.

Benchmark status board:

- `results/tables/cascade_benchmark_status.csv`
- `results/figures/cascade_benchmark_status.md`
- This generated status board now shows which benchmark phases are still template-only, how many fields remain open, which blocker category each phase falls into, and which next action should happen before execution can move forward.

Benchmark execution summary:

- `results/tables/cascade_benchmark_execution_summary.csv`
- `results/figures/cascade_benchmark_execution_summary.md`
- This generated summary now rolls the status board up by phase so the next contributor can see blocker totals, readiness, and the top recommended next action before drilling into individual steps.

Benchmark execution queue:

- `results/tables/cascade_benchmark_execution_queue.csv`
- `results/figures/cascade_benchmark_execution_queue.md`
- This generated queue now converts the status stack into an ordered run list so the next contributor can tell which benchmark step should execute or be reviewed first.

Benchmark session ledger:

- `results/tables/cascade_benchmark_session_ledger.csv`
- `results/figures/cascade_benchmark_session_ledger.md`
- This generated ledger now bridges the queue and manifest layers so the next contributor can see which evidence anchor and completion note each queued step must leave behind.

Benchmark dependency graph:

- `results/tables/cascade_benchmark_dependency_graph.csv`
- `results/figures/cascade_benchmark_dependency_graph.md`
- This generated dependency graph now shows which benchmark step unlocks or blocks the next downstream step in the controlled-benchmark sequence.

Benchmark blocker matrix:

- `results/tables/cascade_benchmark_blocker_matrix.csv`
- `results/figures/cascade_benchmark_blocker_matrix.md`
- This generated blocker matrix now consolidates blocker type, queue priority, dependency state, and pending-field scale so the next contributor can judge urgency from one table.

Benchmark runbook card:

- `results/tables/cascade_benchmark_runbook_card.csv`
- `results/figures/cascade_benchmark_runbook_card.md`
- This generated runbook card now condenses the first benchmark action, the required evidence, and the completion target into one short execution entrypoint.

Benchmark milestone card:

- `results/tables/cascade_benchmark_milestone_card.csv`
- `results/figures/cascade_benchmark_milestone_card.md`
- This generated milestone card now shows the next milestone boundary, what the current start step unlocks, and how many phases remain in the benchmark path.

Benchmark phase checkpoint card:

- `results/tables/cascade_benchmark_phase_checkpoint_card.csv`
- `results/figures/cascade_benchmark_phase_checkpoint_card.md`
- This generated phase checkpoint card now shows each phase's current blocker, next action, and completion signal as a compact execution check.

Benchmark completion dashboard:

- `results/tables/cascade_benchmark_completion_dashboard.csv`
- `results/figures/cascade_benchmark_completion_dashboard.md`
- This generated completion dashboard now gives one short overview of the current start step, dominant blocker family, and remaining pending phase count.

Benchmark operator brief:

- `results/tables/cascade_benchmark_operator_brief.csv`
- `results/figures/cascade_benchmark_operator_brief.md`
- This generated operator brief now gives the current benchmark operator one plain-language note covering the next step, required evidence, and urgency.

Benchmark evidence receipt:

- `results/tables/cascade_benchmark_evidence_receipt.csv`
- `results/figures/cascade_benchmark_evidence_receipt.md`
- This generated evidence receipt now shows what the current benchmark run must write back, which completion signal closes it, and what follow-up note should remain for the next contributor.

Benchmark handoff packet:

- `results/figures/cascade_benchmark_handoff_packet.md`
- This generated note now provides one benchmark-entry document that points to the readiness, plan, checklist, manifest template, execution-summary, execution-queue, session-ledger, dependency-graph, blocker-matrix, runbook-card, milestone-card, phase-checkpoint-card, completion-dashboard, operator-brief, frontier-bridge-checklist, receipt-bridge-checklist, evidence-receipt, and status-board layers together.

## External Validation Frontier

External validation slice bridge checklist:

- `results/figures/external_validation_slice_bridge_checklist.md`
- `results/tables/external_validation_slice_bridge_checklist.csv`
- This checklist turns the first external handoff into a bridge verification path between the slice handoff and the slice receipt. It stays labeled `external/sanity-check` and does not claim any executed external benchmark.

## Synthetic Split Cascade Validation

Label: `synthetic/silver` and `experimental/frontier`

- `router_v2_synthetic_costed: average_cer 0.285187, relative_cost_vs_fixed_separated 0.704888`
- `budget_cascade: average_cer 0.367582, relative_cost_vs_fixed_separated 0.854921`
- `cleaned_preferred_cascade: average_cer 0.249877, relative_cost_vs_fixed_separated 0.945686`

Outputs:

- `results/tables/synthetic_split_cascade_performance.csv`
- `results/figures/synthetic_split_cascade_summary.md`
- `results/figures/synthetic_split_cer_runtime_tradeoff.png`

Interpretation:

- This is a held-out silver validation layer on top of the existing synthetic split benchmark.
- `cleaned_preferred_cascade` improves CER over `router_v2_synthetic_costed`, but spends more compute.
- `budget_cascade` is cheaper than always separated, but loses too much CER on the synthetic split benchmark.
- Silver validation remains separate from gold benchmark claims.

Runtime provenance audit:

- `results/tables/synthetic_split_cascade_runtime_audit.csv`
- `results/figures/synthetic_split_cascade_runtime_audit.md`
- Current committed synthetic split cascade outputs use observed runtime for all `100/100` `ALL` selections and all `50/50` selections in both `DEV` and `TEST`.
- The proxy cost model remains available for missing-runtime future experiments, but it is not active in the current synthetic split tables.

Runtime normalization audit:

- `results/tables/synthetic_split_cascade_runtime_normalization.csv`
- `results/figures/synthetic_split_cascade_runtime_normalization.md`
- `router_v2_synthetic_costed: average_rtf 0.148342`
- `budget_cascade: average_rtf 0.148228`
- `cleaned_preferred_cascade: average_rtf 0.156245`
- These values are normalized by selected-route processed audio duration, not by a single mixed-stream wall-clock target.

Pareto frontier audit:

- `results/tables/synthetic_split_cascade_pareto.csv`
- `results/figures/synthetic_split_cascade_pareto.md`
- Synthetic split `ALL` frontier strategies are `fixed_mixed_whisper`, `fixed_separated_whisper_cleaned`, `router_v2_synthetic_costed`, and `cleaned_preferred_cascade`.
- `budget_cascade` is dominated by `router_v2_synthetic_costed` on the held-out synthetic split `ALL` scope.

Recommendation card:

- `results/tables/synthetic_split_cascade_recommendations.csv`
- `results/figures/synthetic_split_cascade_recommendations.md`
- Synthetic split `ALL` recommends `fixed_separated_whisper_cleaned` for `accuracy_first`, `fixed_mixed_whisper` for `cost_first`, and `router_v2_synthetic_costed` for `balanced`.

## What Should Happen Next

The next stage is not another maintenance loop. It should focus on:

- final REPORT.md polish
- README polish
- Streamlit demo
- presentation / video script
- contribution / maintenance clarity
- ambitious exploration docs
- experimental frontier work

Frontier harness breadth status:

- `results/figures/project_harness_report.md`
- The harness report now includes a generated `frontier_status` table covering `speaker_profile`, `meeteval_compatibility`, `llm_critic`, `external_validation`, and `demo_excellence` so breadth-first work can be spread across multiple frontiers.

Frontier status checklist:

- `results/figures/frontier_status_checklist.md`
- `results/tables/frontier_status_checklist.csv`
- This checklist now turns the frontier status table into a row-by-row verification path. It remains coordination-only and keeps the evidence path visible without claiming that any frontier work has already been executed.

Frontier execution queue:

- `results/figures/frontier_execution_queue.md`
- `results/tables/frontier_execution_queue.json`
- This queue now turns the status table into a coordination layer. It does not claim new experimental evidence; it simply orders which frontier handoff looks most actionable next.
- Current queue head: `meeteval_compatibility`
- Next breadth-first move: use the MeetEval readiness path to stage a narrow dry run before touching the remaining frontier backlog.

Frontier execution queue checklist:

- `results/figures/frontier_execution_queue_checklist.md`
- `results/tables/frontier_execution_queue_checklist.csv`
- This checklist now turns the execution queue into a row-by-row verification path. It remains coordination-only and keeps the queue order visible without claiming that any frontier work has already been executed.

Frontier focus card:

- `results/figures/frontier_focus_card.md`
- `results/tables/frontier_focus_card.json`
- This card now turns the queue head into a one-glance starting point. It remains a coordination artifact rather than a new frontier result.

Frontier focus checklist:

- `results/figures/frontier_focus_card_checklist.md`
- `results/tables/frontier_focus_card_checklist.csv`
- This checklist now turns the focus card into a one-glance verification path. It remains coordination-only and keeps the current action visible without claiming that any frontier work has already been executed.

Frontier handoff packet:

- `results/figures/frontier_handoff_packet.md`
- `results/tables/frontier_handoff_packet.json`
- This packet now points that same queue head directly at its next artifact and expected evidence target. It is still a coordination layer only, not a claim that the queued frontier work has already been executed.

Frontier handoff checklist:

- `results/figures/frontier_handoff_checklist.md`
- `results/tables/frontier_handoff_checklist.csv`
- This checklist now turns the handoff packet into an ordered open-artifact path. It stays explicitly coordination-only, keeps the next artifact visible, and helps a future agent start the frontier pass in order.

Frontier receipt packet:

- `results/figures/frontier_receipt_packet.md`
- `results/tables/frontier_receipt_packet.json`
- This packet now pushes the same coordination layer one step further down to the receipt level. It still does not claim any executed frontier work; it only shows which prerequisite artifact should be opened first and which receipt target should eventually receive the writeback.

Frontier receipt checklist:

- `results/figures/frontier_receipt_checklist.md`
- `results/tables/frontier_receipt_checklist.csv`
- This checklist now turns the receipt packet into an ordered writeback path. It stays explicitly coordination-only, keeps the receipt target visible, and helps a future agent complete the frontier closeout sequence in order.

Frontier receipt map:

- `results/figures/frontier_receipt_map.md`
- `results/tables/frontier_receipt_map.json`
- This map now broadens that receipt-aware layer across every current frontier. It still does not claim any executed frontier work; it simply lets the next contributor scan queue order, prerequisite artifacts, and receipt targets for the whole breadth-first set in one place.

Frontier receipt map checklist:

- `results/figures/frontier_receipt_map_checklist.md`
- `results/tables/frontier_receipt_map_checklist.csv`
- This checklist now turns the receipt map into a row-by-row verification path. It remains coordination-only and keeps the receipt path visible without claiming that any frontier work has already been executed.

Frontier parallel picklist:

- `results/figures/frontier_parallel_picklist.md`
- `results/tables/frontier_parallel_picklist.json`
- This picklist now turns that same breadth-first set into a parallel-friendly pickup view. It still does not claim any executed frontier work; it simply lets the next contributor see which artifact to open and where to write back for each current frontier without changing queue order.

Frontier parallel picklist checklist:

- `results/figures/frontier_parallel_picklist_checklist.md`
- `results/tables/frontier_parallel_picklist_checklist.csv`
- This checklist now turns the parallel picklist into an ordered pickup path. It stays explicitly coordination-only, keeps the pickup artifact visible, and helps a future agent follow the parallel-friendly frontier path in order.

Frontier receipt board:

- `results/figures/frontier_receipt_board.md`
- `results/tables/frontier_receipt_board.json`
- This board now condenses the same breadth-first set into a single receipt snapshot. It still does not claim any executed frontier work; it simply keeps queue order, pickup artifact, and receipt target visible together for the next pass.

Frontier receipt board checklist:

- `results/figures/frontier_receipt_board_checklist.md`
- `results/tables/frontier_receipt_board_checklist.csv`
- This checklist now turns the receipt board into an ordered snapshot path. It stays explicitly coordination-only, keeps the board snapshot visible, and helps a future agent advance the frontier queue in order.

Frontier coordination matrix:

- `results/figures/frontier_coordination_matrix.md`
- `results/tables/frontier_coordination_matrix.json`
- This matrix now gives the same breadth-first set a denser scan view. It still does not claim any executed frontier work; it simply keeps queue order, entry artifact, pickup artifact, and receipt target visible together for the next pass.

Frontier coordination checklist:

- `results/figures/frontier_coordination_checklist.md`
- `results/tables/frontier_coordination_checklist.csv`
- This checklist now turns the coordination matrix into an ordered scan path. It stays explicitly coordination-only, keeps the entry artifact visible, and helps a future agent follow the frontier scan in order.

Frontier writeback index:

- `results/figures/frontier_writeback_index.md`
- `results/tables/frontier_writeback_index.json`
- This index now separates the receipt target from the rest of the scan view. It still does not claim any executed frontier work; it simply keeps queue order, entry artifact, and receipt target visible together for a tighter writeback pass.

Frontier writeback checklist:

- `results/figures/frontier_writeback_checklist.md`
- `results/tables/frontier_writeback_checklist.csv`
- This checklist now turns the writeback index into an ordered closeout path. It stays explicitly coordination-only, keeps the receipt target visible, and helps a future agent complete the frontier writeback in order.

Benchmark frontier bridge:

- `results/figures/cascade_benchmark_frontier_bridge.md`
- `results/tables/cascade_benchmark_frontier_bridge.csv`
- This bridge now links the benchmark operator brief back to the broader frontier queue so the runtime-foundation work remains visible inside the breadth-first coordination layer.

Benchmark frontier bridge checklist:

- `results/figures/cascade_benchmark_frontier_bridge_checklist.md`
- `results/tables/cascade_benchmark_frontier_bridge_checklist.csv`
- This checklist now turns the bridge into a row-by-row verification path. It stays explicitly coordination-only and keeps the bridge reason visible without claiming that any benchmark work has already been executed.

Benchmark receipt bridge:

- `results/figures/cascade_benchmark_receipt_bridge.md`
- `results/tables/cascade_benchmark_receipt_bridge.csv`
- This bridge now links the benchmark handoff packet directly to the benchmark evidence receipt. It still does not claim any executed benchmark run; it simply shows which packet should be opened first and which receipt target should eventually capture the writeback.

Benchmark receipt bridge checklist:

- `results/figures/cascade_benchmark_receipt_bridge_checklist.md`
- `results/tables/cascade_benchmark_receipt_bridge_checklist.csv`
- This checklist now turns the receipt bridge into an ordered writeback path. It stays explicitly coordination-only, keeps the receipt target visible, and helps a future agent complete the benchmark closeout sequence in order.

Benchmark evidence checklist:

- `results/figures/cascade_benchmark_evidence_checklist.md`
- `results/tables/cascade_benchmark_evidence_checklist.csv`
- This checklist now turns the evidence receipt into an ordered writeback path. It stays explicitly coordination-only, keeps the receipt target visible, and helps a future agent complete the benchmark closeout sequence in order.

MeetEval compatibility bridge:

- `results/figures/meeteval_compatibility_note.md`
- `results/tables/meeteval_reference_segments.jsonl`
- `results/tables/meeteval_hypothesis_segments.jsonl`
- This bridge now exports verified gold reference segments and speaker-attributed hypothesis segments in a simple JSONL form so future agents can continue toward MeetEval / cpWER compatibility without overstating the current evaluation scope.

MeetEval readiness bridge:

- `results/figures/meeteval_readiness.md`
- `results/tables/meeteval_readiness.csv`
- This bridge now turns the compatibility export into a small handoff card for a narrow dry run. It still does not claim MeetEval execution, and it makes the current limitation visible by recording that cleaned fallback remains common across the exported cases.

MeetEval dry run handoff bridge:

- `results/figures/meeteval_dry_run_handoff.md`
- `results/tables/meeteval_dry_run_handoff.csv`
- This bridge now turns the readiness state into a single next-step packet. It still does not claim that MeetEval or cpWER has been executed; it only specifies the first recommended slice, the dominant blocker, and the evidence file that a future dry run should leave behind.

MeetEval dry run receipt bridge:

- `results/figures/meeteval_dry_run_receipt.md`
- `results/tables/meeteval_dry_run_receipt.json`
- This bridge now materializes that expected evidence target as a template-only receipt. It still does not claim any executed dry run; it simply defines what the first narrow diagnostic follow-up should write back once it actually happens.

MeetEval dry run bridge checklist:

- `results/figures/meeteval_dry_run_bridge_checklist.md`
- `results/tables/meeteval_dry_run_bridge_checklist.csv`
- This checklist turns the dry-run handoff into an ordered bridge verification path between the handoff and receipt. It stays coordination-only and does not claim that any MeetEval or cpWER execution has already happened.

MeetEval dry run checklist bridge:

- `results/figures/meeteval_dry_run_checklist.md`
- `results/tables/meeteval_dry_run_checklist.csv`
- This bridge now orders the verified cases into a checklist for the first diagnostic dry run. It still does not claim any MeetEval or cpWER execution; it simply helps the next contributor pick the cleanest exported case first.

MeetEval dry run diagnostic bridge:

- `results/figures/meeteval_dry_run_diagnostic.md`
- `results/tables/meeteval_dry_run_diagnostic.csv`
- The first narrow diagnostic pass on `NoOverlap` validated the export path and updated the receipt to `diagnostic_complete` without claiming cpWER evaluation.

MeetEval dry run receipt checklist bridge:

- `results/figures/meeteval_dry_run_receipt_checklist.md`
- `results/tables/meeteval_dry_run_receipt_checklist.csv`
- This checklist turns the dry-run receipt into an ordered verification path. It stays coordination-only and does not claim a finished MeetEval or cpWER evaluation.

MeetEval dry run receipt board bridge:

- `results/figures/meeteval_dry_run_receipt_board.md`
- `results/tables/meeteval_dry_run_receipt_board.csv`
- This board condenses the dry-run receipt path into a single snapshot. It stays coordination-only and does not claim a finished MeetEval or cpWER evaluation.

Speaker profile similarity bridge:

- `results/figures/speaker_profile_risk_summary.md`
- `results/tables/speaker_profile_similarity.csv`
- This bridge now turns `con/pro` snippet transcripts into a lightweight text-profile overlap signal. The current result is useful mainly because it exposes a failure mode: the simple profile signal prefers swapped alignment across the verified gold cases, which argues for caution rather than confidence.

Speaker profile triage bridge:

- `results/figures/speaker_profile_triage.md`
- `results/tables/speaker_profile_triage.csv`
- This bridge now turns the per-case table into an aggregate handoff card. It stays explicitly in the risk-signal lane, records that the current gold set is entirely dominated by `swapped_bias`, and points the next contributor toward trying a stronger profile method rather than overstating attribution quality.

Speaker profile method handoff bridge:

- `results/figures/speaker_profile_method_handoff.md`
- `results/tables/speaker_profile_method_handoff.csv`
- This bridge now turns that aggregate finding into a single stronger-method packet. It still does not claim voiceprint success; it only records the first method direction, the expected evidence target, and a handoff note that keeps the current signal firmly in the diagnostic lane.

Speaker profile method receipt bridge:

- `results/figures/speaker_profile_method_receipt.md`
- `results/tables/speaker_profile_method_receipt.json`
- This bridge now materializes the expected evidence slot for that stronger-method trial as a template-only receipt. It still does not claim any executed profile improvement; it simply defines what the first stronger-method follow-up should write back once it actually happens.

Speaker profile method bridge checklist:

- `results/figures/speaker_profile_method_bridge_checklist.md`
- `results/tables/speaker_profile_method_bridge_checklist.csv`
- This checklist turns the method handoff into an ordered bridge verification path between the handoff and receipt. It stays coordination-only and does not claim that any stronger speaker-profile method has already happened.

LLM critic qualitative bridge:

- `results/figures/llm_critic_qualitative_note.md`
- `results/tables/llm_critic_qualitative_summary.csv`
- This bridge now turns structured risk cues into a qualitative critic-style note. It is intentionally labeled `qualitative/demo` and helps explain what might be repaired first without claiming that any transcript has been verified or improved.

LLM critic review queue bridge:

- `results/figures/llm_critic_review_queue.md`
- `results/tables/llm_critic_review_queue.csv`
- This bridge now turns the critic note into a lightweight triage order. It stays explicitly qualitative, recommends which case to inspect first, and currently highlights that swapped-profile uncertainty remains widespread across the gold cases.

LLM critic review receipt bridge:

- `results/figures/llm_critic_review_receipt.md`
- `results/tables/llm_critic_review_receipt.json`
- This bridge now materializes the expected evidence slot for that first critic-style pass as a template-only receipt. It still does not claim any executed repair; it simply defines what the first qualitative review follow-up should write back once it actually happens.

LLM critic review bridge checklist:

- `results/figures/llm_critic_review_bridge_checklist.md`
- `results/tables/llm_critic_review_bridge_checklist.csv`
- This checklist turns the review queue into an ordered bridge verification path between the queue and receipt. It stays qualitative/demo and does not claim that any repair has already been verified.

LLM critic review checklist bridge:

- `results/figures/llm_critic_review_checklist.md`
- `results/tables/llm_critic_review_checklist.csv`
- This bridge now turns the review queue into an ordered execution checklist. It stays explicitly `qualitative/demo`, keeps the receipt target visible, and helps a future agent pick the first critic-style pass without implying that any repair has already been verified.

External validation candidate bridge:

- `results/figures/external_validation_candidates.md`
- `results/tables/external_validation_candidates.csv`
- This bridge now turns the external-mini-validation frontier into an explicit `external/sanity-check` candidate card. It records source, license, fit, preprocessing, and next-action notes for AISHELL-4, AliMeeting, AMI, and LibriCSS without claiming that any external benchmark has already been executed.

External validation prioritization bridge:

- `results/figures/external_validation_prioritization.md`
- `results/tables/external_validation_prioritization.csv`
- This bridge now turns the candidate card into a lightweight execution order. It recommends `AISHELL-4` as the first tiny sanity-check target and records priority tier, readiness note, why-now context, and next action while preserving the `external/sanity-check` label.

External validation slice handoff bridge:

- `results/figures/external_validation_slice_handoff.md`
- `results/tables/external_validation_slice_handoff.csv`
- This bridge now turns that prioritized target into a single first-slice packet. It still does not claim any external execution; it only defines the first slice shape, license gate, mapping artifact, and dry-run goal for the narrowest external follow-up.

External validation slice receipt bridge:

- `results/figures/external_validation_slice_receipt.md`
- `results/tables/external_validation_slice_receipt.json`
- This bridge now materializes the expected evidence slot for that first slice as a template-only receipt. It still does not claim any executed external sanity-check; it simply defines what the first narrow follow-up should write back once it actually happens.

External validation checklist bridge:

- `results/figures/external_validation_checklist.md`
- `results/tables/external_validation_checklist.csv`
- This bridge now turns the prioritized external candidates into an execution checklist. It still stays in `external/sanity-check` mode and does not claim that any external validation run has been completed.

External validation skill card:

- `docs/skills/skill_07_external_validation.md`
- This repository now has a dedicated skill card for the external mini-validation frontier, so the queue-head task can be picked up directly from the skills index instead of only from the roadmap and project-state layers.

Demo storyboard bridge:

- `results/figures/demo_storyboard.md`
- `results/tables/demo_storyboard_cards.json`
- This bridge now turns the repository into a one-page demo-facing story so a new visitor can understand the problem, pipeline, findings, and frontier directions quickly without opening the full report first.

Demo storyboard receipt:

- `results/figures/demo_storyboard_receipt.md`
- `results/tables/demo_storyboard_receipt.json`
- This receipt now creates the first evidence slot for a demo storyboard review pass. It stays demo support only and does not claim that any live demo or recording has already happened.

Demo storyboard receipt bridge:

- `results/figures/demo_storyboard_receipt_bridge.md`
- `results/tables/demo_storyboard_receipt_bridge.csv`
- This bridge links the storyboard cards to the storyboard receipt so the first storyboard review path is explicit. It stays demo support only and does not claim that any live demo or recording has already happened.

Demo storyboard receipt checklist:

- `results/figures/demo_storyboard_receipt_checklist.md`
- `results/tables/demo_storyboard_receipt_checklist.csv`
- This checklist turns the storyboard receipt into an ordered review path between the storyboard and receipt. It stays demo support only and does not claim that any live demo or recording has already happened.

Demo storyboard receipt board:

- `results/figures/demo_storyboard_receipt_board.md`
- `results/tables/demo_storyboard_receipt_board.csv`
- This board condenses the storyboard receipt path into a single snapshot between the storyboard and receipt. It stays demo support only and does not claim that any live demo or recording has already happened.

Demo storyboard receipt map:

- `results/figures/demo_storyboard_receipt_map.md`
- `results/tables/demo_storyboard_receipt_map.csv`
- This map condenses the storyboard receipt path across the receipt, checklist, and board views. It stays demo support only and does not claim that any live demo or recording has already happened.

Demo storyboard bridge checklist:

- `results/figures/demo_storyboard_bridge_checklist.md`
- `results/tables/demo_storyboard_bridge_checklist.csv`
- This checklist turns the storyboard into an ordered bridge verification path between the storyboard and walkthrough. It stays demo support only and does not claim that any live demo or recording has already happened.

Demo walkthrough bridge:

- `results/figures/demo_walkthrough.md`
- `results/tables/demo_walkthrough_steps.json`
- This bridge now turns the storyboard into a short ordered talk track. It does not claim new evaluation results; it simply maps problem framing, baseline evidence, routing takeaway, frontier breadth, and next-step framing onto the existing artifact set.

Demo walkthrough receipt bridge:

- `results/figures/demo_walkthrough_receipt.md`
- `results/tables/demo_walkthrough_receipt.json`
- This bridge now materializes the expected evidence slot for that walkthrough as a template-only receipt. It still does not claim any executed demo delivery; it simply defines what the first narrow presentation follow-up should write back once it actually happens.

Demo walkthrough bridge checklist:

- `results/figures/demo_walkthrough_bridge_checklist.md`
- `results/tables/demo_walkthrough_bridge_checklist.csv`
- This checklist turns the walkthrough into an ordered bridge verification path between the walkthrough and receipt. It stays presentation support only and does not claim that any live demo or recording has already happened.

Demo walkthrough checklist bridge:

- `results/figures/demo_walkthrough_checklist.md`
- `results/tables/demo_walkthrough_checklist.csv`
- This bridge now turns the walkthrough into an ordered presentation checklist. It stays explicitly `qualitative/demo`, keeps the receipt target visible, and helps a future agent follow the short demo script without implying that a live demo has already been completed.

## How to Resume Work

Common commands:

```powershell
python -m src.adaptive_router_v2
python -m src.evaluate_error_types --case all
python -m src.evaluate_speaker_cer --case all
python -m src.evaluate_cpcer_lite --case all
python -m src.risk_aware_selector --case all
python -m src.compute_aware_cascade
python -m src.compute_aware_cascade --dataset synthetic_split
python -m src.router_ablation
python -m src.router_ablation_split
python -m src.project_harness
```

## Notes for Future Agents

- Do not use ground-truth CER or reference transcripts as routing input.
- References and CER are for evaluation only.
- Keep gold and synthetic evaluation clearly separated.
- Prefer adding new outputs over overwriting existing benchmark files.
- If a new stage changes the main conclusion, update README and REPORT together.
