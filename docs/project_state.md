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
- AudioDepth-Router frontier prototype with deployable depth-augmented spectrogram maps
- Balanced Route-Sensitive Benchmark v2 frontier validation
- AudioDepth-centric deployable v2 and Stage-1 gate frontier validation

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
11. AudioDepth-Router is an experimental/frontier learned-router probe, not a stable baseline. The first deployable synthetic split run underperforms router_v2, which is a useful negative finding about audio-only depth proxies.
12. The AudioDepth frontier has now been expanded into a model-zoo and hybrid-routing exploration scaffold. That broader sweep is designed to test whether richer architectures, class balancing, and transcript-instability features can recover more signal than the MVP.

## AudioDepth-Router Frontier Finding

Label: `experimental/frontier` plus `synthetic/silver`

- Skill card: `docs/skills/skill_07_audio_depth_router.md`
- Dataset manifest: `results/tables/audio_depth_router_dataset.csv`
- Map metadata: `resources/audio_depth_maps/metadata_audio_depth_maps.csv`
- Deployable model: `models/audio_depth_router_deployable.pt`
- Summary: `results/figures/audio_depth_router_summary.md`
- Ablation: `results/figures/audio_depth_router_ablation.md`

AudioDepth-Router is inspired by RGB-D image recognition. It treats overlapping speech as time-frequency occlusion and augments a log-mel spectrogram with overlap/depth and uncertainty channels. Deployable mode uses only mixed audio. Analysis-only mode uses separated tracks and must not be claimed as deployable.

Current deployable synthetic split TEST result:

- `audio_depth_cnn_deployable`: accuracy `0.7200`, macro-F1 `0.2791`, routing CER `0.436666`
- `router_v2 / v2_full_features`: routing CER `0.335326`
- `oracle_best`: routing CER `0.115181`

Interpretation: the first AudioDepth pass did not improve over router_v2. The likely failure modes are insufficient synthetic training size, weak overlap proxy channels, noisy oracle-style labels, and the missing text-level instability features that router_v2 already uses.

## AudioDepth Model Zoo Frontier

The frontier has now been widened beyond the MVP into a model-zoo and hybrid feature exploration pass.

- Skill card: `docs/skills/skill_08_audio_depth_model_zoo.md`
- Hybrid feature table: `results/tables/audio_depth_zoo_hybrid_features.csv`
- Training logs: `results/tables/audio_depth_zoo_training_log.csv`
- Model status: `results/tables/audio_depth_zoo_model_status.csv`

This phase is still an experimental/frontier study. It is meant to answer whether log-mel-only models, depth-augmented CNN variants, class balancing, late fusion, and confidence cascades can recover ground that the first MVP did not.

Current synthetic split TEST results:

- `mlp_handcrafted`: routing CER `0.166381`
- `hybrid_late_fusion`: routing CER `0.176381`
- best confidence cascade: routing CER `0.165545`
- matched `router_v2`: routing CER `0.335326`
- `oracle_best`: routing CER `0.115181`

Interpretation: hybrid/text-risk features are doing most of the useful work in this run. Pure depth models improve the experiment matrix but do not yet explain the routing boundary as well as the handcrafted/hybrid rows.

## Systematic AudioDepth-Hybrid Validation

Stage 23 extends AudioDepth-Hybrid from a model-zoo result into a system validation pass.

- Stress benchmark: `150` generated samples in `resources/audio_depth_stress_v1/`
- Stress proxy route evaluation: `80` samples in `results/tables/audio_depth_systematic_stress_cer.csv`
- Best systematic frontier model: `hybrid_late_fusion_v2`
- Best systematic frontier CER: `0.249477` on `64` held-out systematic samples
- Old router_v2 proxy row: `0.355793`
- Previous model-zoo best row in this systematic table: `0.392813`
- Oracle: `0.127504`

Important interpretation: this pass improves over the old router_v2 proxy row and the MVP-style separated route, but does not beat the Stage 22 model-zoo best result (`0.166381`) or the fixed-cleaned proxy row (`0.196876`). Stress CER is `synthetic/silver_proxy`, not real Whisper CER.

## AudioDepth Real Whisper ASR Validation

Stage 24 adds a sampled real-ASR layer without replacing Stage 23 proxy evidence.

- Backend: `faster-whisper` `1.2.1`
- Model size: `base`
- System ffmpeg command: missing; faster-whisper/PyAV path used
- Stress samples evaluated: `10`
- Transcript rows: `50`
- Reference type: `synthetic/silver_reference`
- Gold sanity: not yet available for this stress subset
- Best systematic router: `hybrid_late_fusion_v2`
- Real Whisper CER, router_v2: `0.718965`
- Real Whisper CER, best systematic router: `0.718965`
- Real Whisper CER, oracle: `0.713965`

Interpretation: this sampled real-ASR run is a boundary finding rather than a win claim. It distinguishes Stage 23 proxy CER from Stage 24 real Whisper CER and shows that the proxy improvement does not automatically transfer on a small real-ASR slice.

## Real-ASR Validation Gap Analysis

Stage 25 audits the proxy-to-real gap before doing more router training.

- Audit pack: `results/figures/audio_depth_real_asr_audit_pack.md`
- Reference quality: `results/figures/audio_depth_real_asr_reference_quality.md`
- Normalized summary: `results/figures/audio_depth_real_asr_normalized_summary.md`
- Whisper config sweep: `results/figures/audio_depth_whisper_config_sweep_summary.md`
- Stratified expansion: `results/figures/audio_depth_real_asr_stratified_summary.md`
- Proxy-to-real gap: `results/figures/audio_depth_proxy_real_gap.md`
- Route-gap subset: `results/figures/audio_depth_real_asr_route_gap_subset.md`

Current conclusion: Stage 23 proxy evidence is strong, but Stage 24/25 real-ASR evidence does not yet transfer. Oracle real CER also improves only slightly, so the sampled slice may not provide enough route-choice contrast. This is a validation-pipeline finding, not a reason to erase the frontier experiment.

## Controlled Route-Sensitive Benchmark

Stage 26 adds a controlled benchmark designed to make route choices matter.

- Utterance inventory: `26` source snippets
- Verification status: candidate Whisper-small transcripts only; no verified micro-gold yet
- Controlled samples generated: `80`
- Real Whisper evaluated: `40`
- Reference type: `silver_plus_unverified`
- Fixed mixed CER: `0.467818`
- Fixed separated CER: `0.260124`
- Oracle CER: `0.255923`
- router_v2 CER: `0.383122`
- controlled hybrid/fusion CER: `0.256816`

Interpretation: controlled real-ASR evidence now supports a hybrid router beating router_v2, but the set is separation-dominant and not yet gold. The next improvement is manual verification plus more mixed-favored and cleaned-favored samples.

## Balanced Route-Sensitive Benchmark v2

Stage 27 creates a route-balanced frontier follow-up to Stage 26.

- Candidate pool: `240`
- Final v2 benchmark: `120`
- Real Whisper evaluated: `60`
- Evaluated anchor balance: `15` mixed-win, `15` separated-win, `15` cleaned-win, `15` review-needed
- Reference type: `silver_plus_unverified`
- Oracle route distribution: mixed `34`, separated `26`, cleaned `0`
- Review-needed candidates: `57`
- Fixed mixed CER: `0.726484`
- Fixed separated CER: `0.667789`
- Fixed cleaned CER: `0.667789`
- router_v2 CER: `0.643520`
- balanced route-winner router CER: `0.502854`
- oracle CER: `0.502854`
- balanced route-winner route accuracy: `0.983333`

Interpretation: this is more balanced than Stage 26 and proves the learned v2 router is not blindly selecting separated; it predicts mixed `33` and separated `27` on the 60-sample slice. It does not prove cleaned routing: cleaned wins `0` oracle cases, so cleaned remains a negative finding and review-target rather than a solved route.

AudioDepth v2 maps were generated under `analysis_only_irm_proxy` for the 60 evaluated samples. They are inspired by RGB-D/depth-augmented image recognition and treat overlap as time-frequency occlusion, but they use source-track energy proxies and must not be described as deployable.

## AudioDepth-Centric Routing Frontier

Stage 28 upgrades AudioDepth from an auxiliary router feature into a deployable acoustic representation line.

- Deployable maps: `200` total
- Sources: `120` controlled_v2, `80` controlled_v1; synthetic_split skipped because no direct source manifest was available
- Deployable channels: mixed logmel, mixed-only overlap proxy, mixed-only uncertainty proxy
- Labelled audit rows: `100`
- Best embedding probe: resnet oracle-route accuracy `0.655172`, macro-F1 `0.618421`
- Stage-1 gate held-out accuracy: `0.758621`
- Stage-1 gate macro-F1: `0.431525`
- easy_mixed recall: `0.0`
- separation_helpful recall: `0.0`
- ambiguous/review recall: `0.958333`
- false-safe rate: `0.034483`
- controlled_v2 two-stage cascade CER: `0.643520`
- text-probe reduction rate: `0.016667`

Interpretation: AudioDepth is not intended to replace transcript-instability features. Instead, it provides a pre-ASR acoustic view of time-frequency occlusion, while text features provide post-ASR evidence of decoding instability. Current deployable proxies show independent representation structure but are too conservative for confident Stage-1 resolution.

## AudioDepth Gate Calibration Follow-up

Stage 29 calibrates the Stage-1 gate labels by separating route-action labels from risk flags and using separation gain over mixed to recover `likely_separation_helpful` examples.

- calibrated held-out accuracy: `0.724138`
- calibrated macro-F1: `0.475000`
- easy_mixed recall: `0.400000`
- separation_helpful recall: `0.800000`
- best controlled_v2 threshold CER: `0.533160`
- text-probe reduction at best CER threshold: `0.716667`
- false-safe rate in the threshold sweep: `0.183333`

Interpretation: calibration turns AudioDepth from a mostly conservative risk detector into a useful pre-ASR gate. It improves over router_v2 on controlled_v2 but still trails the Stage 27 balanced router and oracle rows, so it is a promising frontier result rather than a stable replacement.

## AudioDepth Risk-Guarded Gate Follow-up

Stage 30 adds a mixed-only risk-guarded policy sweep on top of the calibrated AudioDepth gate. The guard uses uncertainty, overlap, and overlap-uncertainty product proxies from deployable AudioDepth v2 maps to block unsafe direct bypass decisions and send high-risk cases to Stage-2 text routing or review handling.

- balanced controlled_v2 CER: `0.529082`
- balanced route accuracy: `0.833333`
- balanced direct-bypass false-safe rate: `0.000000`
- balanced text-probe reduction: `0.416667`
- aggressive controlled_v2 CER: `0.537082`
- aggressive text-probe reduction: `0.650000`
- selected mixed high-error cases after fallback/review handling: `12`

Interpretation: the risk guard fixes the main Stage 29 acoustic-gate safety weakness by eliminating observed unsafe direct bypasses in the selected policies while preserving a CER advantage over router_v2. It does not make the whole system safe yet, because Stage-2 fallback can still choose mixed on high-error review-like samples. This strengthens AudioDepth's role as a deployable Stage-1 acoustic triage module, but the result stays `experimental/frontier` because the controlled_v2 references are still `silver_plus_unverified`.

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

MeetEval dry run receipt map bridge:

- `results/figures/meeteval_dry_run_receipt_map.md`
- `results/tables/meeteval_dry_run_receipt_map.csv`
- This map condenses the dry-run receipt path across the receipt, checklist, and board views. It stays coordination-only and does not claim a finished MeetEval or cpWER evaluation.

MeetEval cpWER bridge:

- `results/figures/meeteval_cpwer_bridge.md`
- `results/tables/meeteval_cpwer_bridge.csv`
- The all-gold cpWER bridge-lite pass reports `average_cpwer_bridge_lite = 0.120823` with `direct_mapping_count = 5/5`. This is `experimental/frontier` evidence, not a full MeetEval benchmark claim.

MeetEval cpWER bridge summary:

- `results/figures/meeteval_cpwer_bridge_summary.md`
- `results/tables/meeteval_cpwer_bridge_summary.csv`
- The summary condenses the five verified gold cases without promoting bridge-lite evidence into a finished MeetEval evaluation claim.

MeetEval cpWER alignment:

- `results/figures/meeteval_cpwer_alignment.md`
- `results/tables/meeteval_cpwer_alignment.csv`
- Cross-metric alignment reports `matched_count = 4/5` with `HeavyOverlap` as the only drift case against speaker_macro_cer.

MeetEval cpWER alignment bridge checklist:

- `results/figures/meeteval_cpwer_alignment_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_bridge_checklist.csv`
- This checklist turns the alignment audit into an ordered bridge verification path between the alignment note and bridge handoff.

MeetEval cpWER alignment drift diagnostic:

- `results/figures/meeteval_cpwer_alignment_drift_diagnostic.md`
- `results/tables/meeteval_cpwer_alignment_drift_diagnostic.csv`
- The only drift case is `HeavyOverlap` with `alignment_gap = 0.016292` and `drift_severity = moderate`.

MeetEval cpWER alignment drift bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_bridge_checklist.csv`
- This checklist connects the drift diagnostic to the alignment bridge checklist while cpWER execution remains pending.

MeetEval cpWER alignment drift handoff:

- `results/figures/meeteval_cpwer_alignment_drift_handoff.md`
- `results/tables/meeteval_cpwer_alignment_drift_handoff.csv`
- The drift handoff targets `HeavyOverlap` segment inspection before any broader cpWER bridge advance.

MeetEval cpWER alignment drift handoff bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_handoff_bridge_checklist.csv`
- This checklist connects the drift handoff back to the drift bridge checklist without claiming MeetEval execution.

MeetEval cpWER alignment drift segment scaffold:

- `results/figures/meeteval_cpwer_alignment_drift_segment_scaffold.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_scaffold.json`
- The segment inspection scaffold for `HeavyOverlap` remains `scaffold_only` with no reconciliation claim.

MeetEval cpWER alignment drift segment scaffold bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_scaffold_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_scaffold_bridge_checklist.csv`
- This checklist connects the segment scaffold to the drift handoff bridge checklist while cpWER execution remains pending.

MeetEval cpWER alignment drift segment handoff:

- `results/figures/meeteval_cpwer_alignment_drift_segment_handoff.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_handoff.csv`
- The segment handoff targets `HeavyOverlap` inspection before any reconciliation or cpWER execution claim.

MeetEval cpWER alignment drift segment handoff bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_handoff_bridge_checklist.csv`
- This checklist connects the segment handoff to the segment scaffold bridge checklist while cpWER execution remains pending.

MeetEval cpWER alignment drift segment inspection:

- `results/figures/meeteval_cpwer_alignment_drift_segment_inspection.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_inspection.csv`
- The first narrow segment inspection on `HeavyOverlap` reports `inspection_pass = true` with `segment_count_delta = 0`; reconciliation and cpWER execution remain pending.

MeetEval cpWER alignment drift segment inspection bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_inspection_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_inspection_bridge_checklist.csv`
- This checklist connects the segment inspection to the segment handoff bridge checklist without claiming cpWER execution.

MeetEval cpWER alignment drift segment reconciliation scaffold:

- `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold.json`
- The reconciliation scaffold for `HeavyOverlap` remains `scaffold_only` with `inspection_status = segment_inspection_complete`; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment reconciliation scaffold bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold_bridge_checklist.csv`
- This checklist connects the reconciliation scaffold to the segment inspection bridge checklist while cpWER execution remains pending.

MeetEval cpWER alignment drift segment reconciliation handoff:

- `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff.csv`
- The reconciliation handoff targets `HeavyOverlap` diagnostic follow-up before any cpWER bridge advance.

MeetEval cpWER alignment drift segment reconciliation diagnostic:

- `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic.csv`
- The first narrow reconciliation diagnostic on `HeavyOverlap` reports `reconciliation_pass = false` because `speaker_segment_count_match = false` even though total segment counts align; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment reconciliation diagnostic bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic_bridge_checklist.csv`
- This checklist connects the reconciliation diagnostic to the reconciliation handoff without claiming cpWER execution.

MeetEval cpWER alignment drift segment reconciliation handoff bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff_bridge_checklist.csv`
- This checklist connects the reconciliation handoff to the reconciliation scaffold bridge checklist while cpWER execution remains pending.

MeetEval cpWER alignment drift segment speaker count diagnostic:

- `results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic.csv`
- Per-speaker comparison on `HeavyOverlap` reports `mismatched_speaker_count = 2/2` with `SPEAKER_1 delta=-1` and `SPEAKER_2 delta=+1`; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment speaker count diagnostic bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_bridge_checklist.csv`
- This checklist connects the speaker count diagnostic to the reconciliation diagnostic bridge checklist without claiming cpWER execution.

MeetEval cpWER alignment drift segment speaker count diagnostic handoff:

- `results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff.csv`
- The speaker count diagnostic handoff targets per-speaker timing follow-up for `HeavyOverlap`; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment timing diagnostic:

- `results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_timing_diagnostic.csv`
- Per-speaker timing on `HeavyOverlap` reports `mismatched_speaker_count = 1/2` with `SPEAKER_1 delta=-2.360s`; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment timing diagnostic bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_bridge_checklist.csv`
- This checklist connects the timing diagnostic to the speaker count handoff bridge without claiming cpWER execution.

MeetEval cpWER alignment drift segment speaker count diagnostic handoff bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff_bridge_checklist.csv`
- This checklist connects the speaker count handoff to the timing diagnostic bridge without claiming cpWER execution.

MeetEval cpWER alignment drift segment timing diagnostic handoff:

- `results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff.csv`
- The timing diagnostic handoff targets per-speaker granularity follow-up for `HeavyOverlap`; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment granularity diagnostic:

- `results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic.csv`
- Per-speaker granularity on `HeavyOverlap` reports `mismatched_speaker_count = 1/2` with `SPEAKER_2 delta=-0.173s`; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment timing diagnostic handoff bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff_bridge_checklist.csv`
- This checklist connects the timing handoff to the granularity diagnostic bridge without claiming cpWER execution.

MeetEval cpWER alignment drift segment granularity diagnostic bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_bridge_checklist.csv`
- This checklist connects the granularity diagnostic to the timing handoff bridge without claiming cpWER execution.

MeetEval cpWER alignment drift segment granularity diagnostic handoff:

- `results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff.csv`
- The granularity diagnostic handoff targets per-speaker redistribution follow-up for `HeavyOverlap`; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment redistribution diagnostic:

- `results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic.csv`
- Per-speaker redistribution on `HeavyOverlap` reports `redistribution_mismatch_count = 2/2` with `SPEAKER_1 hypothesis_merged` and `SPEAKER_2 hypothesis_split`; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment granularity diagnostic handoff bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff_bridge_checklist.csv`
- This checklist connects the granularity handoff to the redistribution diagnostic bridge without claiming cpWER execution.

MeetEval cpWER alignment drift segment redistribution diagnostic bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_bridge_checklist.csv`
- This checklist connects the redistribution diagnostic to the granularity handoff bridge without claiming cpWER execution.

MeetEval cpWER alignment drift segment redistribution diagnostic handoff:

- `results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff.csv`
- The redistribution diagnostic handoff targets the cpWER bridge handoff for `HeavyOverlap`; reconciled alignment and cpWER execution remain pending.

MeetEval cpWER alignment drift segment redistribution diagnostic handoff bridge checklist:

- `results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff_bridge_checklist.csv`
- This checklist connects the redistribution handoff to the cpWER bridge handoff without claiming cpWER execution.

MeetEval cpWER bridge handoff:

- `results/figures/meeteval_cpwer_bridge_handoff.md`
- `results/tables/meeteval_cpwer_bridge_handoff.csv`
- This handoff turns the bridge-lite result into the next narrow frontier step while keeping full MeetEval evaluation explicitly pending.

MeetEval cpWER bridge handoff bridge checklist:

- `results/figures/meeteval_cpwer_bridge_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_bridge_handoff_bridge_checklist.csv`
- This checklist connects the cpWER bridge handoff to full MeetEval evaluation without claiming cpWER execution.

MeetEval cpWER execution scaffold:

- `results/figures/meeteval_cpwer_execution_scaffold.md`
- `results/tables/meeteval_cpwer_execution_scaffold.csv`
- The cpWER execution scaffold records `scaffold_status = scaffold_only` for one verified case; official cpWER evaluation remains pending.

MeetEval cpWER execution scaffold bridge checklist:

- `results/figures/meeteval_cpwer_execution_scaffold_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_scaffold_bridge_checklist.csv`
- This checklist connects the execution scaffold to official MeetEval evaluation without claiming cpWER execution.

MeetEval cpWER execution handoff:

- `results/figures/meeteval_cpwer_execution_handoff.md`
- `results/tables/meeteval_cpwer_execution_handoff.csv`
- The execution handoff targets official cpWER evaluation for one verified case; benchmark completion remains pending.

MeetEval cpWER execution handoff bridge checklist:

- `results/figures/meeteval_cpwer_execution_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_handoff_bridge_checklist.csv`
- This checklist connects the execution handoff to the official cpWER execution receipt without claiming cpWER execution.

MeetEval cpWER execution preflight:

- `results/figures/meeteval_cpwer_execution_preflight.md`
- `results/tables/meeteval_cpwer_execution_preflight.csv`
- The first narrow execution preflight on `NoOverlap` reports `preflight_pass = true` with aligned segment exports; official cpWER evaluation remains pending.

MeetEval cpWER execution preflight bridge checklist:

- `results/figures/meeteval_cpwer_execution_preflight_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_preflight_bridge_checklist.csv`
- This checklist connects the execution preflight to the official cpWER execution receipt without claiming cpWER execution.

MeetEval cpWER execution receipt scaffold:

- `results/figures/meeteval_cpwer_execution_receipt_scaffold.md`
- `results/tables/meeteval_cpwer_execution_receipt_scaffold.csv`
- `results/tables/meeteval_cpwer_execution_receipt.json`
- The receipt scaffold records `scaffold_status = receipt_scaffold_only` for `NoOverlap` after `preflight_pass = true`; official MeetEval evaluation remains pending.

MeetEval cpWER execution receipt scaffold bridge checklist:

- `results/figures/meeteval_cpwer_execution_receipt_scaffold_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_receipt_scaffold_bridge_checklist.csv`
- This checklist connects the receipt scaffold to the official cpWER execution receipt without claiming benchmark execution.

MeetEval cpWER execution status:

- `results/figures/meeteval_cpwer_execution_status.md`
- `results/tables/meeteval_cpwer_execution_status.csv`
- The execution-chain rollup reports `execution_chain_status = execution_chain_ready` for `NoOverlap`; official MeetEval evaluation remains pending.

MeetEval cpWER execution status bridge checklist:

- `results/figures/meeteval_cpwer_execution_status_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_status_bridge_checklist.csv`
- This checklist connects the execution-chain status rollup to the official cpWER execution receipt without claiming benchmark execution.

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

Speaker profile embedding scaffold bridge:

- `results/figures/speaker_profile_embedding_scaffold.md`
- `results/tables/speaker_profile_embedding_scaffold.json`
- The stronger-method scaffold is `scaffold_only` and points toward `embedding_or_voiceprint_baseline` without claiming improved speaker attribution.

Speaker profile audio proxy bridge:

- `results/figures/speaker_profile_audio_proxy_trial.md`
- `results/tables/speaker_profile_audio_proxy_trial.csv`
- `results/figures/speaker_profile_audio_proxy_summary.md`
- `results/tables/speaker_profile_audio_proxy_summary.csv`
- The first narrow audio-profile proxy trial now exists as a real acoustic-side experiment rather than a text-only scaffold. It still argues for caution, not confidence: all five gold cases remain `swapped_bias`, but the average confidence gap is only `0.000013`, so the lightweight proxy currently looks too weak for attribution claims and is best treated as diagnostic-only frontier evidence.

Speaker profile multi-signal diagnostic:

- `results/figures/speaker_profile_multisignal_diagnostic.md`
- `results/tables/speaker_profile_multisignal_diagnostic.csv`
- `results/figures/speaker_profile_multisignal_summary.md`
- `results/tables/speaker_profile_multisignal_summary.csv`
- The text-profile and audio-profile proxy branches now agree on swapped-bias direction for all five gold cases, but the acoustic side remains `weak_support` throughout. This is useful frontier evidence for advancing to a narrow embedding baseline, not for making attribution claims.

Speaker profile embedding scaffold bridge checklist:

- `results/figures/speaker_profile_embedding_scaffold_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_scaffold_bridge_checklist.csv`
- This checklist connects the embedding scaffold to the method receipt without claiming voiceprint success.

Speaker profile embedding trial handoff:

- `results/figures/speaker_profile_embedding_trial_handoff.md`
- `results/tables/speaker_profile_embedding_trial_handoff.csv`
- The embedding trial handoff targets `NoOverlap` for a narrow embedding-or-voiceprint diagnostic trial; improved speaker attribution remains unverified.

Speaker profile embedding trial:

- `results/figures/speaker_profile_embedding_trial.md`
- `results/tables/speaker_profile_embedding_trial.csv`
- The embedding trial scaffold records `trial_status = scaffold_only` for `NoOverlap` using text-profile proxy scores; voiceprint execution remains pending.

Speaker profile text-proxy trial diagnostic:

- `results/figures/speaker_profile_text_proxy_trial_diagnostic.md`
- `results/tables/speaker_profile_text_proxy_trial_diagnostic.csv`
- All-gold text-profile proxy diagnostic reports `5/5` swapped bias; next direction remains `embedding_or_voiceprint_baseline`.

Speaker profile text-proxy trial diagnostic bridge checklist:

- `results/figures/speaker_profile_text_proxy_trial_diagnostic_bridge_checklist.md`
- `results/tables/speaker_profile_text_proxy_trial_diagnostic_bridge_checklist.csv`
- This checklist connects the text-proxy diagnostic to the embedding trial handoff without claiming voiceprint success.

Speaker profile text-proxy trial diagnostic completion summary:

- `results/figures/speaker_profile_text_proxy_trial_diagnostic_completion_summary.md`
- `results/tables/speaker_profile_text_proxy_trial_diagnostic_completion_summary.csv`
- `queue_status = queue_complete` at `5/5` swapped bias; no voiceprint success is claimed.

Speaker profile text-proxy trial diagnostic completion summary bridge checklist:

- `results/figures/speaker_profile_text_proxy_trial_diagnostic_completion_summary_bridge_checklist.md`
- `results/tables/speaker_profile_text_proxy_trial_diagnostic_completion_summary_bridge_checklist.csv`
- This checklist connects the completion summary to the embedding trial handoff without claiming voiceprint success.

Speaker profile embedding trial handoff readiness:

- `results/figures/speaker_profile_embedding_trial_handoff_readiness.md`
- `results/tables/speaker_profile_embedding_trial_handoff_readiness.csv`
- `readiness_status = handoff_ready` when text-proxy diagnostic is `queue_complete` and handoff is ready; no voiceprint claim.

Speaker profile embedding trial handoff readiness bridge checklist:

- `results/figures/speaker_profile_embedding_trial_handoff_readiness_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_handoff_readiness_bridge_checklist.csv`
- This checklist connects handoff readiness to the embedding trial scaffold without claiming voiceprint success.

Speaker profile embedding trial handoff completion summary:

- `results/figures/speaker_profile_embedding_trial_handoff_completion_summary.md`
- `results/tables/speaker_profile_embedding_trial_handoff_completion_summary.csv`
- `queue_status = queue_complete` when handoff readiness is satisfied; execution scaffold remains next.

Speaker profile embedding trial handoff completion summary bridge checklist:

- `results/figures/speaker_profile_embedding_trial_handoff_completion_summary_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_handoff_completion_summary_bridge_checklist.csv`
- This checklist connects handoff completion to the embedding trial execution scaffold without claiming voiceprint success.

Speaker profile embedding trial execution scaffold readiness:

- `results/figures/speaker_profile_embedding_trial_execution_scaffold_readiness.md`
- `results/tables/speaker_profile_embedding_trial_execution_scaffold_readiness.csv`
- `readiness_status = scaffold_ready` when handoff completion is satisfied; voiceprint execution remains pending.

Speaker profile embedding trial execution scaffold readiness bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_scaffold_readiness_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_scaffold_readiness_bridge_checklist.csv`
- This checklist connects scaffold readiness to the execution preflight without claiming voiceprint success.

Speaker profile embedding trial execution scaffold completion summary:

- `results/figures/speaker_profile_embedding_trial_execution_scaffold_completion_summary.md`
- `results/tables/speaker_profile_embedding_trial_execution_scaffold_completion_summary.csv`
- `queue_status = queue_complete` when scaffold readiness is satisfied; execution handoff remains next.

Speaker profile embedding trial execution scaffold completion summary bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_scaffold_completion_summary_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_scaffold_completion_summary_bridge_checklist.csv`
- This checklist connects scaffold completion to the execution handoff without claiming voiceprint success.

Speaker profile embedding trial execution preflight readiness:

- `results/figures/speaker_profile_embedding_trial_execution_preflight_readiness.md`
- `results/tables/speaker_profile_embedding_trial_execution_preflight_readiness.csv`
- `readiness_status = preflight_ready` when scaffold completion and preflight pass align; voiceprint execution remains pending.

Speaker profile embedding trial execution preflight readiness bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_preflight_readiness_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_preflight_readiness_bridge_checklist.csv`
- This checklist connects preflight readiness to the execution receipt target without claiming voiceprint success.

Speaker profile embedding trial handoff bridge checklist:

- `results/figures/speaker_profile_embedding_trial_handoff_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_handoff_bridge_checklist.csv`
- This checklist connects the embedding trial scaffold to the handoff without claiming voiceprint success.

Speaker profile embedding trial execution scaffold:

- `results/figures/speaker_profile_embedding_trial_execution_scaffold.md`
- `results/tables/speaker_profile_embedding_trial_execution_scaffold.csv`
- The embedding execution scaffold records `scaffold_status = execution_scaffold_only` for `NoOverlap`; voiceprint execution remains pending.

Speaker profile embedding trial execution scaffold bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_scaffold_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_scaffold_bridge_checklist.csv`
- This checklist connects the execution scaffold to voiceprint execution without claiming attribution success.

Speaker profile embedding trial execution handoff:

- `results/figures/speaker_profile_embedding_trial_execution_handoff.md`
- `results/tables/speaker_profile_embedding_trial_execution_handoff.csv`
- The embedding execution handoff targets `NoOverlap` for a narrow embedding-or-voiceprint diagnostic trial; improved speaker attribution remains unverified.

Speaker profile embedding trial execution handoff bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_handoff_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_handoff_bridge_checklist.csv`
- This checklist connects the embedding execution handoff to the execution receipt without claiming voiceprint success.

Speaker profile embedding trial execution preflight:

- `results/figures/speaker_profile_embedding_trial_execution_preflight.md`
- `results/tables/speaker_profile_embedding_trial_execution_preflight.csv`
- The first narrow execution preflight on `NoOverlap` reports `preflight_pass = true` with `swapped_bias_detected = true` and `combined_signal_status = text_swapped_audio_weak`; voiceprint execution remains pending and attribution claims remain blocked.

Speaker profile embedding trial execution receipt scaffold:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_scaffold.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_scaffold.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt.json`
- The receipt scaffold records `scaffold_status = receipt_scaffold_only` for `NoOverlap` with `swapped_bias_detected = true`; voiceprint execution remains pending.

Speaker profile embedding trial execution preflight bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_preflight_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_preflight_bridge_checklist.csv`
- This checklist connects the embedding execution preflight to the execution receipt without claiming voiceprint success.

Speaker profile embedding trial execution receipt scaffold bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_scaffold_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_scaffold_bridge_checklist.csv`
- This checklist connects the embedding receipt scaffold to the execution receipt without claiming voiceprint success.

Speaker profile embedding trial execution status:

- `results/figures/speaker_profile_embedding_trial_execution_status.md`
- `results/tables/speaker_profile_embedding_trial_execution_status.csv`
- The execution-chain rollup reports `execution_chain_status = execution_chain_ready` for `NoOverlap` with `swapped_bias_detected = true` and `combined_signal_status = text_swapped_audio_weak`; voiceprint execution remains pending.

Speaker profile embedding trial execution status bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_status_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_status_bridge_checklist.csv`
- This checklist connects the embedding execution-chain status rollup to the execution receipt without claiming voiceprint success.

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

LLM critic review pass bridge:

- `results/figures/llm_critic_review_pass.md`
- `results/tables/llm_critic_review_pass.csv`
- The first qualitative pass on `HeavyOverlap` is `review_complete` without any verified transcript repair claim.

LLM critic review pass bridge checklist:

- `results/figures/llm_critic_review_pass_bridge_checklist.md`
- `results/tables/llm_critic_review_pass_bridge_checklist.csv`
- This checklist turns the review pass into an ordered bridge verification path between the pass note and receipt.

LLM critic review pass advance bridge:

- `results/figures/llm_critic_review_pass_advance.md`
- `results/tables/llm_critic_review_pass_advance.csv`
- The queue advanced to `LightOverlap` after `HeavyOverlap` reached `review_complete` without any verified repair claim.

LLM critic review pass second bridge:

- `results/figures/llm_critic_review_pass_second.md`
- `results/tables/llm_critic_review_pass_second.csv`
- The second qualitative pass records critic-style notes for `LightOverlap` only; no verified transcript repair is claimed.

LLM critic review pass advance bridge checklist:

- `results/figures/llm_critic_review_pass_advance_bridge_checklist.md`
- `results/tables/llm_critic_review_pass_advance_bridge_checklist.csv`
- This checklist connects the second qualitative pass to the advance receipt without claiming verified repair.

LLM critic review pass status rollup:

- `results/figures/llm_critic_review_pass_status.md`
- `results/tables/llm_critic_review_pass_status.csv`
- The queue rollup reports `completed_count = 5/5` with `queue_status = queue_complete` and no verified repair claim.

LLM critic review pass third bridge:

- `results/figures/llm_critic_review_pass_third.md`
- `results/tables/llm_critic_review_pass_third.csv`
- The third qualitative pass records critic-style notes for `MidOverlap` only; no verified transcript repair is claimed.

LLM critic review pass next bridge:

- `results/figures/llm_critic_review_pass_next.md`
- `results/tables/llm_critic_review_pass_next.csv`
- The queue advance note records the third pass selection after two completed qualitative passes.

LLM critic review pass status bridge checklist:

- `results/figures/llm_critic_review_pass_status_bridge_checklist.md`
- `results/tables/llm_critic_review_pass_status_bridge_checklist.csv`
- This checklist connects the status rollup to the next pass receipt without claiming verified repair.

LLM critic review pass fourth bridge:

- `results/figures/llm_critic_review_pass_fourth.md`
- `results/tables/llm_critic_review_pass_fourth.csv`
- The fourth qualitative pass records critic-style notes for `NoOverlap` only; no verified transcript repair is claimed.

LLM critic review pass continue bridge:

- `results/figures/llm_critic_review_pass_continue.md`
- `results/tables/llm_critic_review_pass_continue.csv`
- The continue note records queue advancement to the fourth qualitative pass without any verified repair claim.

LLM critic review pass continue bridge checklist:

- `results/figures/llm_critic_review_pass_continue_bridge_checklist.md`
- `results/tables/llm_critic_review_pass_continue_bridge_checklist.csv`
- This checklist connects the fourth qualitative pass to the continue receipt without claiming verified repair.

LLM critic review pass fifth bridge:

- `results/figures/llm_critic_review_pass_fifth.md`
- `results/tables/llm_critic_review_pass_fifth.csv`
- The fifth qualitative pass records critic-style notes for `OppositeOverlap` and closes the gold queue without any verified repair claim.

LLM critic review pass final bridge:

- `results/figures/llm_critic_review_pass_final.md`
- `results/tables/llm_critic_review_pass_final.csv`
- The final pass note records gold-queue completion at `5/5` without any verified transcript repair claim.

LLM critic review pass completion summary bridge:

- `results/figures/llm_critic_review_pass_completion_summary.md`
- `results/tables/llm_critic_review_pass_completion_summary.csv`
- The completion summary reports `queue_status = queue_complete` with `pending_count = 0`.

LLM critic review pass final bridge checklist:

- `results/figures/llm_critic_review_pass_final_bridge_checklist.md`
- `results/tables/llm_critic_review_pass_final_bridge_checklist.csv`
- This checklist connects the final qualitative pass to the completion summary without claiming verified repair.

LLM critic review bridge checklist:

- `results/figures/llm_critic_review_bridge_checklist.md`
- `results/tables/llm_critic_review_bridge_checklist.csv`
- This checklist turns the review queue into an ordered bridge verification path between the queue and receipt. It stays qualitative/demo and does not claim that any repair has already been verified.

LLM critic review checklist bridge:

- `results/figures/llm_critic_review_checklist.md`
- `results/tables/llm_critic_review_checklist.csv`
- This bridge now turns the review queue into an ordered execution checklist. It stays explicitly `qualitative/demo`, keeps the receipt target visible, and helps a future agent pick the first critic-style pass without implying that any repair has already been verified.

LLM critic go-no-go board:

- `results/figures/llm_critic_go_no_go_board.md`
- `results/tables/llm_critic_go_no_go_board.csv`
- The board shows `4/5` checkpoints are ready for a narrow qualitative writeback path.

LLM critic go-no-go summary:

- `results/figures/llm_critic_go_no_go_summary.md`
- `results/tables/llm_critic_go_no_go_summary.csv`
- `overall_state = qualitative_writeback_ready` while `primary_boundary = verified_repair_claims_still_blocked`.

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

External validation slice scaffold bridge:

- `results/figures/external_validation_slice_scaffold.md`
- `results/tables/external_validation_slice_mapping.json`
- The first AISHELL-4 mapping stub is `scaffold_only` with `license_status = pending_confirmation`. No external audio or benchmark evaluation has been run yet.

External validation license gate bridge:

- `results/figures/external_validation_license_gate.md`
- `results/tables/external_validation_license_gate.csv`
- The license gate checklist documents preflight steps while `license_status` remains `pending_confirmation` and external audio staging stays blocked.

External validation license gate bridge checklist:

- `results/figures/external_validation_license_gate_bridge_checklist.md`
- `results/tables/external_validation_license_gate_bridge_checklist.csv`
- This checklist connects the license gate to the slice manifest while external audio staging remains blocked.

External validation license confirmation scaffold:

- `results/figures/external_validation_license_confirmation_scaffold.md`
- `results/tables/external_validation_license_confirmation_scaffold.json`
- The license confirmation scaffold remains `template_only` with `license_status = pending_confirmation`.

External validation license confirmation scaffold bridge checklist:

- `results/figures/external_validation_license_confirmation_scaffold_bridge_checklist.md`
- `results/tables/external_validation_license_confirmation_scaffold_bridge_checklist.csv`
- This checklist connects the confirmation scaffold to staging readiness without claiming benchmark execution.

External validation license confirmation receipt bridge:

- `results/figures/external_validation_license_confirmation_receipt_bridge.md`
- `results/tables/external_validation_license_confirmation_receipt_bridge.csv`
- This bridge links the confirmation scaffold bridge checklist to the slice receipt without claiming benchmark execution.

External validation license confirmation receipt bridge checklist:

- `results/figures/external_validation_license_confirmation_receipt_bridge_checklist.md`
- `results/tables/external_validation_license_confirmation_receipt_bridge_checklist.csv`
- This checklist connects the receipt bridge to the slice receipt without claiming benchmark execution.

External validation slice manifest bridge:

- `results/figures/external_validation_slice_manifest.md`
- `results/tables/external_validation_slice_manifest.json`
- The slice manifest records `staging_status = blocked_by_license_gate` for the first AISHELL-4 excerpt.

External validation slice manifest bridge checklist:

- `results/figures/external_validation_slice_manifest_bridge_checklist.md`
- `results/tables/external_validation_slice_manifest_bridge_checklist.csv`
- This checklist turns the slice manifest into an ordered bridge verification path between the manifest note and manifest receipt.

External validation slice staging readiness bridge:

- `results/figures/external_validation_slice_staging_readiness.md`
- `results/tables/external_validation_slice_staging_readiness.csv`
- Staging readiness remains `not_ready` with `blocker = license_confirmation_pending`.

External validation slice staging readiness bridge checklist:

- `results/figures/external_validation_slice_staging_readiness_bridge_checklist.md`
- `results/tables/external_validation_slice_staging_readiness_bridge_checklist.csv`
- This checklist connects staging readiness to the slice manifest bridge checklist without claiming benchmark execution.

External validation slice staging readiness handoff:

- `results/figures/external_validation_slice_staging_readiness_handoff.md`
- `results/tables/external_validation_slice_staging_readiness_handoff.csv`
- The staging handoff records `blocker = license_confirmation_pending` for AISHELL-4; external audio staging remains pending.

External validation slice staging readiness handoff bridge checklist:

- `results/figures/external_validation_slice_staging_readiness_handoff_bridge_checklist.md`
- `results/tables/external_validation_slice_staging_readiness_handoff_bridge_checklist.csv`
- This checklist connects the staging handoff to the slice staging receipt without claiming benchmark execution.

External validation slice staging handoff receipt scaffold:

- `results/figures/external_validation_slice_staging_handoff_receipt_scaffold.md`
- `results/tables/external_validation_slice_staging_handoff_receipt_scaffold.csv`
- `results/tables/external_validation_slice_staging_handoff_receipt.json`
- The staging receipt scaffold records `scaffold_status = receipt_scaffold_only` for AISHELL-4 with `blocker = license_confirmation_pending`; external audio staging remains pending.

External validation slice staging handoff receipt scaffold bridge checklist:

- `results/figures/external_validation_slice_staging_handoff_receipt_scaffold_bridge_checklist.md`
- `results/tables/external_validation_slice_staging_handoff_receipt_scaffold_bridge_checklist.csv`
- This checklist connects the staging receipt scaffold to the external slice staging receipt without claiming benchmark execution.

External validation slice staging execution status:

- `results/figures/external_validation_slice_staging_execution_status.md`
- `results/tables/external_validation_slice_staging_execution_status.csv`
- The staging execution-chain rollup reports `execution_chain_status = execution_chain_ready` for AISHELL-4; external audio staging remains pending.

External validation slice staging execution status bridge checklist:

- `results/figures/external_validation_slice_staging_execution_status_bridge_checklist.md`
- `results/tables/external_validation_slice_staging_execution_status_bridge_checklist.csv`
- This checklist connects the staging execution-chain status rollup to the external slice staging receipt without claiming benchmark execution.

Frontier execution queue status:

- `results/figures/frontier_execution_queue_status.md`
- `results/tables/frontier_execution_queue_status.csv`
- The unified frontier rollup now uses the same five-track surface as the top-level frontier board and reports `combined_chain_status = execution_chain_ready` only when MeetEval, speaker profile, external staging, LLM critic, and demo excellence are all chain-ready; no benchmark execution is claimed.

Frontier execution queue status bridge checklist:

- `results/figures/frontier_execution_queue_status_bridge_checklist.md`
- `results/tables/frontier_execution_queue_status_bridge_checklist.csv`
- This checklist connects the unified frontier rollup to per-frontier execution receipt gates without claiming benchmark completion.

Frontier execution queue completion summary:

- `results/figures/frontier_execution_queue_completion_summary.md`
- `results/tables/frontier_execution_queue_completion_summary.csv`
- The coordination queue rollup reports `queue_status = queue_complete` at `5/5` ready chains; no benchmark execution is claimed.

Frontier go-no-go board:

- `results/figures/frontier_go_no_go_board.md`
- `results/tables/frontier_go_no_go_board.csv`
- The board shows `4/5` frontier tracks are ready for narrow next-step execution in the current queue state.

Frontier go-no-go summary:

- `results/figures/frontier_go_no_go_summary.md`
- `results/tables/frontier_go_no_go_summary.csv`
- `highest_priority_ready_frontier = meeteval_compatibility`, `highest_priority_blocked_frontier = external_validation`, and `coordination_state = mixed_ready_state`.

Frontier operator next-action card:

- `results/figures/frontier_operator_next_action_card.md`
- `results/tables/frontier_operator_next_action_card.csv`
- The card turns the top-level frontier board into two operator lanes: advance the ready MeetEval receipt path and independently clear the external validation license blocker.

Frontier operator next-action summary:

- `results/figures/frontier_operator_next_action_summary.md`
- `results/tables/frontier_operator_next_action_summary.csv`
- `operator_sequence = ready_lane:meeteval_compatibility -> blocked_lane:external_validation`.

Frontier operator next-action bridge checklist:

- `results/figures/frontier_operator_next_action_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_bridge_checklist.csv`
- The checklist preserves the operator-lane order and bridges the top-level card to the next target artifacts without claiming that either lane has already been completed.

Frontier operator next-action operator brief:

- `results/figures/frontier_operator_next_action_operator_brief.md`
- `results/tables/frontier_operator_next_action_operator_brief.csv`
- The brief converts the two-lane operator state into one plain-language summary with `meeteval_compatibility` as the first action and `external_validation` as the current unblock target.

Frontier operator next-action runbook card:

- `results/figures/frontier_operator_next_action_runbook_card.md`
- `results/tables/frontier_operator_next_action_runbook_card.csv`
- The runbook card condenses the ready lane into a one-page execution card with the required evidence path and the narrow coordination completion signal.

Frontier operator next-action frontier bridge:

- `results/figures/frontier_operator_next_action_frontier_bridge.md`
- `results/tables/frontier_operator_next_action_frontier_bridge.csv`
- The bridge confirms that the runbook-ready frontier still matches the broader frontier queue head without claiming that any frontier execution has happened.

Frontier operator next-action frontier bridge checklist:

- `results/figures/frontier_operator_next_action_frontier_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_frontier_bridge_checklist.csv`
- The checklist verifies top-level queue alignment before the runbook card is reopened and keeps the whole transition coordination-only.

Frontier operator next-action handoff packet:

- `results/figures/frontier_operator_next_action_handoff_packet.md`
- `results/tables/frontier_operator_next_action_handoff_packet.csv`
- The packet collects the whole top-level operator chain into one single-entry coordination artifact with an explicit first-open sequence.

Frontier operator next-action handoff packet bridge checklist:

- `results/figures/frontier_operator_next_action_handoff_packet_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_handoff_packet_bridge_checklist.csv`
- The checklist verifies the handoff packet before the top-level operator card is reopened and keeps the whole loop coordination-only.

Frontier operator next-action phase checkpoint card:

- `results/figures/frontier_operator_next_action_phase_checkpoint_card.md`
- `results/tables/frontier_operator_next_action_phase_checkpoint_card.csv`
- The checkpoint card isolates the current frontier, action, and narrow completion signal for the top-level ready lane.

Frontier operator next-action milestone card:

- `results/figures/frontier_operator_next_action_milestone_card.md`
- `results/tables/frontier_operator_next_action_milestone_card.csv`
- The milestone card records the immediate unlock boundary after the current ready-lane checkpoint closes and keeps the next coordination target explicit.

Frontier operator next-action completion dashboard:

- `results/figures/frontier_operator_next_action_completion_dashboard.md`
- `results/tables/frontier_operator_next_action_completion_dashboard.csv`
- The dashboard summarizes the current first frontier, current blocker, next milestone, and remaining top-level frontier count in one operator-facing state view.

Frontier operator next-action completion dashboard bridge checklist:

- `results/figures/frontier_operator_next_action_completion_dashboard_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_completion_dashboard_bridge_checklist.csv`
- The checklist verifies the dashboard before the top-level runbook card is reopened and keeps the transition coordination-only.

Frontier operator next-action status:

- `results/figures/frontier_operator_next_action_status.md`
- `results/tables/frontier_operator_next_action_status.csv`
- The status rollup compresses the ready lane, blocker lane, milestone, and dashboard bridge into one machine-friendly top-level coordination snapshot, with the current combined state recorded as `operator_status_mixed_ready`.

Frontier operator next-action status bridge checklist:

- `results/figures/frontier_operator_next_action_status_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_bridge_checklist.csv`
- The checklist verifies that unified top-level status snapshot before the broader operator handoff packet is opened, keeping the transition coordination-only.

Frontier operator next-action status handoff:

- `results/figures/frontier_operator_next_action_status_handoff.md`
- `results/tables/frontier_operator_next_action_status_handoff.csv`
- The handoff splits the unified top-level status snapshot into one ready-lane action for `meeteval_compatibility` and one blocker-lane containment action for `external_validation`.

Frontier operator next-action status handoff bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_bridge_checklist.csv`
- The checklist verifies each lane-specific top-level handoff before the lane target artifact is opened, keeping the transition coordination-only.

Frontier operator next-action status handoff completion summary:

- `results/figures/frontier_operator_next_action_status_handoff_completion_summary.md`
- `results/tables/frontier_operator_next_action_status_handoff_completion_summary.csv`
- The summary compresses the top-level ready/block handoff into one queue-level state row and currently records `queue_status = queue_complete`.

Frontier operator next-action status handoff completion summary bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_completion_summary_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_completion_summary_bridge_checklist.csv`
- The checklist verifies that queue-level top-level handoff summary before the lane-level handoff is reopened, keeping the transition coordination-only.

Frontier operator next-action status handoff packet:

- `results/figures/frontier_operator_next_action_status_handoff_packet.md`
- `results/tables/frontier_operator_next_action_status_handoff_packet.csv`
- The packet consolidates the top-level status snapshot, lane handoff, queue summary, operator brief, operator-brief bridge, operator-brief bridge checklist, runbook, runbook bridge checklist, checkpoint, phase-checkpoint bridge checklist, milestone, milestone bridge checklist, completion dashboard, status preflight bridge checklist, bridge checkpoints, and the newer `status_handoff_status` rollup layer into one single-entry coordination artifact.

Frontier operator next-action status handoff packet bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_packet_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_packet_bridge_checklist.csv`
- The checklist verifies that packet before the plain-language `status/handoff` operator brief is reopened, keeping the transition coordination-only.

Frontier operator next-action status handoff operator brief:

- `results/figures/frontier_operator_next_action_status_handoff_operator_brief.md`
- `results/tables/frontier_operator_next_action_status_handoff_operator_brief.csv`
- The brief turns the queue-level status/handoff stack into one plain-language next-step card with the current ready frontier, blocked frontier, and evidence path.

Frontier operator next-action status handoff operator brief bridge:

- `results/figures/frontier_operator_next_action_status_handoff_operator_brief_bridge.md`
- `results/tables/frontier_operator_next_action_status_handoff_operator_brief_bridge.csv`
- The bridge connects the plain-language `status/handoff` operator brief to the current runbook card target without claiming frontier execution.

Frontier operator next-action status handoff operator brief bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_operator_brief_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_operator_brief_bridge_checklist.csv`
- The checklist verifies that bridge before the runbook card is reopened, keeping the transition coordination-only.

Frontier operator next-action status handoff runbook card:

- `results/figures/frontier_operator_next_action_status_handoff_runbook_card.md`
- `results/tables/frontier_operator_next_action_status_handoff_runbook_card.csv`
- The runbook card condenses the current ready-lane action into a one-page execution card with a concrete completion signal tied to the ready target artifact.

Frontier operator next-action status handoff runbook bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_runbook_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_runbook_bridge_checklist.csv`
- The checklist verifies that runbook card before the phase checkpoint card is reopened, keeping the transition coordination-only.

Frontier operator next-action status handoff phase checkpoint card:

- `results/figures/frontier_operator_next_action_status_handoff_phase_checkpoint_card.md`
- `results/tables/frontier_operator_next_action_status_handoff_phase_checkpoint_card.csv`
- The phase checkpoint card narrows that runbook to the exact completion signal that should be satisfied before the `status/handoff` subchain advances.

Frontier operator next-action status handoff phase checkpoint bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_phase_checkpoint_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_phase_checkpoint_bridge_checklist.csv`
- The checklist verifies that phase checkpoint card before the milestone card is reopened, keeping the transition coordination-only.

Frontier operator next-action status handoff milestone card:

- `results/figures/frontier_operator_next_action_status_handoff_milestone_card.md`
- `results/tables/frontier_operator_next_action_status_handoff_milestone_card.csv`
- The milestone card records the immediate unlock boundary after the current ready-lane checkpoint closes, keeping `external_validation` visible as the next explicit coordination target inside the `status/handoff` subchain.

Frontier operator next-action status handoff milestone bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_milestone_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_milestone_bridge_checklist.csv`
- The checklist verifies that milestone card before the completion dashboard is reopened, keeping the transition coordination-only.

Frontier operator next-action status handoff completion dashboard:

- `results/figures/frontier_operator_next_action_status_handoff_completion_dashboard.md`
- `results/tables/frontier_operator_next_action_status_handoff_completion_dashboard.csv`
- The completion dashboard compresses the current `status/handoff` subchain into one operator-facing view with the current first frontier, dominant blocker, next milestone, and remaining visible lane count.

Frontier operator next-action status handoff completion dashboard bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_completion_dashboard_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_completion_dashboard_bridge_checklist.csv`
- The bridge checklist verifies that `status/handoff` dashboard snapshot before the current runbook card is reopened, keeping the transition coordination-only.

Frontier operator next-action status handoff status preflight bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_status_preflight_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_status_preflight_bridge_checklist.csv`
- The checklist verifies that completion-dashboard bridge layer before the machine-readable status rollup is reopened, keeping the transition coordination-only.

Frontier operator next-action status handoff status:

- `results/figures/frontier_operator_next_action_status_handoff_status.md`
- `results/tables/frontier_operator_next_action_status_handoff_status.csv`
- The status rollup compresses the current `status/handoff` queue state, milestone, dashboard, and dashboard bridge into one machine-friendly coordination snapshot.

Frontier operator next-action status handoff status bridge checklist:

- `results/figures/frontier_operator_next_action_status_handoff_status_bridge_checklist.md`
- `results/tables/frontier_operator_next_action_status_handoff_status_bridge_checklist.csv`
- The bridge checklist verifies that `status/handoff` status rollup before the broader `status/handoff` packet is reopened, keeping the transition coordination-only.

Frontier execution queue completion summary bridge checklist:

- `results/figures/frontier_execution_queue_completion_summary_bridge_checklist.md`
- `results/tables/frontier_execution_queue_completion_summary_bridge_checklist.csv`
- This checklist connects the coordination queue completion summary to the execution handoff without claiming benchmark completion.

Frontier execution queue handoff:

- `results/figures/frontier_execution_queue_handoff.md`
- `results/tables/frontier_execution_queue_handoff.csv`
- This handoff turns the unified frontier rollup into per-frontier execution receipt actions for MeetEval, speaker profile, and external staging.

Frontier execution queue handoff bridge checklist:

- `results/figures/frontier_execution_queue_handoff_bridge_checklist.md`
- `results/tables/frontier_execution_queue_handoff_bridge_checklist.csv`
- This checklist connects the execution handoff to per-frontier execution receipts without claiming benchmark execution.

Frontier execution queue handoff packet:

- `results/figures/frontier_execution_queue_handoff_packet.md`
- `results/tables/frontier_execution_queue_handoff_packet.csv`
- This packet consolidates the execution queue status, queue summary, per-frontier handoff layers, the operator brief, the runbook card, the runbook bridge checklist, the phase checkpoint card, the phase checkpoint bridge checklist, the milestone card, the completion dashboard, and the receipt readiness board into one single-entry coordination artifact.

Frontier execution queue handoff packet bridge checklist:

- `results/figures/frontier_execution_queue_handoff_packet_bridge_checklist.md`
- `results/tables/frontier_execution_queue_handoff_packet_bridge_checklist.csv`
- This checklist verifies that execution queue handoff packet before the execution queue operator brief is reopened.

Frontier execution queue operator brief:

- `results/figures/frontier_execution_queue_operator_brief.md`
- `results/tables/frontier_execution_queue_operator_brief.csv`
- This brief turns the first execution-queue handoff row into a plain-language next-step card for the current operator.

Frontier execution queue runbook card:

- `results/figures/frontier_execution_queue_runbook_card.md`
- `results/tables/frontier_execution_queue_runbook_card.csv`
- This runbook card turns the execution queue operator brief into a one-page first-action execution card for the current first execution-queue target.

Frontier execution queue runbook bridge checklist:

- `results/figures/frontier_execution_queue_runbook_bridge_checklist.md`
- `results/tables/frontier_execution_queue_runbook_bridge_checklist.csv`
- This checklist verifies that execution queue runbook card before the current receipt target is reopened.

Frontier execution queue phase checkpoint card:

- `results/figures/frontier_execution_queue_phase_checkpoint_card.md`
- `results/tables/frontier_execution_queue_phase_checkpoint_card.csv`
- This checkpoint card narrows the execution queue runbook to the exact completion signal for the current first execution-queue target.

Frontier execution queue phase checkpoint bridge checklist:

- `results/figures/frontier_execution_queue_phase_checkpoint_bridge_checklist.md`
- `results/tables/frontier_execution_queue_phase_checkpoint_bridge_checklist.csv`
- This checklist verifies the phase checkpoint card before the execution queue milestone card is reopened for the current first frontier.

Frontier execution queue milestone card:

- `results/figures/frontier_execution_queue_milestone_card.md`
- `results/tables/frontier_execution_queue_milestone_card.csv`
- This milestone card records what the current first execution-queue checkpoint unlocks next and how many visible execution fronts remain afterward.

Frontier execution queue milestone bridge checklist:

- `results/figures/frontier_execution_queue_milestone_bridge_checklist.md`
- `results/tables/frontier_execution_queue_milestone_bridge_checklist.csv`
- This checklist verifies the execution-queue milestone unlock path before the completion dashboard is reopened.

Frontier execution queue completion dashboard:

- `results/figures/frontier_execution_queue_completion_dashboard.md`
- `results/tables/frontier_execution_queue_completion_dashboard.csv`
- This dashboard compresses the current execution queue state into one operator-facing view with the current first frontier, next milestone, remaining visible fronts, and the dominant coordination blocker.

Frontier execution queue completion dashboard bridge checklist:

- `results/figures/frontier_execution_queue_completion_dashboard_bridge_checklist.md`
- `results/tables/frontier_execution_queue_completion_dashboard_bridge_checklist.csv`
- This checklist turns the execution queue dashboard into a verification gate before the runbook card is reopened for the current first frontier.

Frontier execution queue status preflight bridge checklist:

- `results/figures/frontier_execution_queue_status_preflight_bridge_checklist.md`
- `results/tables/frontier_execution_queue_status_preflight_bridge_checklist.csv`
- This checklist verifies the completion-dashboard bridge before the execution queue status rollup is reopened.

Frontier execution queue status reentry card:

- `results/figures/frontier_execution_queue_status_reentry_card.md`
- `results/tables/frontier_execution_queue_status_reentry_card.csv`
- This card gives the next contributor a one-page instruction for reopening the execution queue status rollup after preflight.

Frontier execution queue status reentry bridge checklist:

- `results/figures/frontier_execution_queue_status_reentry_bridge_checklist.md`
- `results/tables/frontier_execution_queue_status_reentry_bridge_checklist.csv`
- This checklist verifies the status reentry card before the execution queue handoff bridge is opened.

Frontier execution queue receipt open card:

- `results/figures/frontier_execution_queue_receipt_open_card.md`
- `results/tables/frontier_execution_queue_receipt_open_card.csv`
- This card gives the next contributor the first receipt target to open after the execution queue handoff bridge is confirmed.

Frontier execution queue receipt readiness board:

- `results/figures/frontier_execution_queue_receipt_readiness_board.md`
- `results/tables/frontier_execution_queue_receipt_readiness_board.csv`
- This board splits the frontier receipts into `ready_for_receipt_fill` vs `bridge_or_scaffold_pending` after the execution handoff has already been verified.

Frontier execution queue receipt readiness bridge checklist:

- `results/figures/frontier_execution_queue_receipt_readiness_bridge_checklist.md`
- `results/tables/frontier_execution_queue_receipt_readiness_bridge_checklist.csv`
- This checklist verifies each execution queue receipt readiness row before the unified frontier receipt queue status is reopened.

MeetEval cpWER execution receipt readiness:

- `results/figures/meeteval_cpwer_execution_receipt_readiness.md`
- `results/tables/meeteval_cpwer_execution_receipt_readiness.csv`
- Receipt readiness reports `readiness_status = receipt_ready_to_fill` for `NoOverlap`; official MeetEval evaluation remains pending.

Speaker profile embedding trial execution receipt readiness:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_readiness.csv`
- Receipt readiness reports `readiness_status = receipt_ready_to_fill` for `NoOverlap` with `swapped_bias_detected = true`; voiceprint execution remains pending.

Speaker profile go-no-go board:

- `results/figures/speaker_profile_go_no_go_board.md`
- `results/tables/speaker_profile_go_no_go_board.csv`
- The board shows `4/4` execution checkpoints are ready for a narrow `NoOverlap` embedding-baseline path.

Speaker profile go-no-go summary:

- `results/figures/speaker_profile_go_no_go_summary.md`
- `results/tables/speaker_profile_go_no_go_summary.csv`
- `overall_state = narrow_execution_ready` while `primary_boundary = attribution_claims_still_blocked_by_weak_support`.

Speaker profile go-no-go board bridge checklist:

- `results/figures/speaker_profile_go_no_go_board_bridge_checklist.md`
- `results/tables/speaker_profile_go_no_go_board_bridge_checklist.csv`
- This checklist connects the go-no-go board to the embedding trial execution preflight without claiming speaker identification success.

Speaker profile go-no-go board handoff:

- `results/figures/speaker_profile_go_no_go_board_handoff.md`
- `results/tables/speaker_profile_go_no_go_board_handoff.csv`
- `handoff_status = speaker_profile_go_handoff_ready` for `NoOverlap`; narrow embedding preflight remains coordination-only.

Speaker profile go-no-go board handoff bridge checklist:

- `results/figures/speaker_profile_go_no_go_board_handoff_bridge_checklist.md`
- `results/tables/speaker_profile_go_no_go_board_handoff_bridge_checklist.csv`

Speaker profile go-no-go board handoff completion summary:

- `results/figures/speaker_profile_go_no_go_board_handoff_completion_summary.md`
- `results/tables/speaker_profile_go_no_go_board_handoff_completion_summary.csv`
- `queue_status = queue_complete` for `NoOverlap`; embedding trial execution scaffold readiness remains next.

Speaker profile go-no-go board handoff completion summary bridge checklist:

- `results/figures/speaker_profile_go_no_go_board_handoff_completion_summary_bridge_checklist.md`
- `results/tables/speaker_profile_go_no_go_board_handoff_completion_summary_bridge_checklist.csv`

Speaker profile go-no-go handoff packet:

- `results/figures/speaker_profile_go_no_go_handoff_packet.md`
- `results/tables/speaker_profile_go_no_go_handoff_packet.csv`
- Consolidates the go-no-go board through handoff completion layers into one coordination entrypoint.

External validation slice staging handoff receipt readiness:

- `results/figures/external_validation_slice_staging_handoff_receipt_readiness.md`
- `results/tables/external_validation_slice_staging_handoff_receipt_readiness.csv`
- Receipt readiness reports `readiness_status = receipt_ready_to_fill` for AISHELL-4; external audio staging remains pending.

Frontier execution receipt queue status:

- `results/figures/frontier_execution_receipt_queue_status.md`
- `results/tables/frontier_execution_receipt_queue_status.csv`
- The unified receipt readiness rollup reports `combined_readiness_status = receipt_ready_to_fill`; no benchmark execution is claimed.

MeetEval cpWER execution receipt readiness bridge checklist:

- `results/figures/meeteval_cpwer_execution_receipt_readiness_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_receipt_readiness_bridge_checklist.csv`
- This checklist connects the cpWER receipt readiness rollup to the execution receipt without claiming official evaluation.

Speaker profile embedding trial execution receipt readiness bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_readiness_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_readiness_bridge_checklist.csv`
- This checklist connects the embedding receipt readiness rollup to the execution receipt without claiming voiceprint success.

Speaker profile embedding trial execution receipt open card:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_open_card.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_open_card.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_open_card.json`
- This card gives the next contributor the current speaker-profile execution receipt target to open for `NoOverlap` after the readiness bridge is confirmed.

Speaker profile embedding trial execution receipt open card bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_open_card_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_open_card_bridge_checklist.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_open_card_bridge_checklist.json`
- This checklist turns the current speaker-profile execution receipt open card into an ordered verification gate before the targeted receipt is reopened.

Speaker profile embedding trial execution receipt handoff packet:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_handoff_packet.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_handoff_packet.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_handoff_packet.json`
- This packet consolidates the current speaker-profile receipt readiness, open-card, handoff, operator-brief, runbook, checkpoint, milestone, completion-dashboard, and status-reentry layers into one coordination entrypoint for `NoOverlap`, while remaining explicitly experimental/frontier only.

Speaker profile embedding trial execution receipt handoff packet bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_handoff_packet_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_handoff_packet_bridge_checklist.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_handoff_packet_bridge_checklist.json`
- This checklist turns that speaker-profile receipt handoff packet into a first-gate verification step before the readiness rollup is reopened.

Speaker profile embedding trial execution receipt operator brief:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_operator_brief.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_operator_brief.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_operator_brief.json`
- This brief turns the handoff-packet bridge into one plain-language next action for `NoOverlap`, while staying explicitly coordination-only and not claiming any voiceprint success.

Speaker profile embedding trial execution receipt operator brief bridge:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge.json`
- This bridge connects the plain-language operator brief back to the current speaker-profile readiness target, still without filling the receipt or claiming voiceprint success.

Speaker profile embedding trial execution receipt operator brief bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge_checklist.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge_checklist.json`
- This checklist turns the operator brief bridge into an explicit verification gate before the current speaker-profile readiness target is reopened.

Speaker profile embedding trial execution receipt runbook card:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_runbook_card.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_runbook_card.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_runbook_card.json`
- This runbook card condenses the current speaker-profile receipt action for `NoOverlap` into a one-page execution card, while remaining explicitly coordination-only and not claiming voiceprint success.

Speaker profile embedding trial execution receipt runbook bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_runbook_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_runbook_bridge_checklist.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_runbook_bridge_checklist.json`
- This checklist turns the speaker-profile runbook card into an explicit verification gate before the current readiness target is reopened.

Speaker profile embedding trial execution receipt phase checkpoint card:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_card.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_card.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_card.json`
- This checkpoint card narrows the current speaker-profile receipt runbook to one explicit completion signal for `NoOverlap`, while remaining coordination-only and not claiming voiceprint success.

Speaker profile embedding trial execution receipt phase checkpoint bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_bridge_checklist.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_bridge_checklist.json`
- This checklist turns the speaker-profile phase checkpoint card into an explicit verification gate before the current readiness target is reopened.

Speaker profile embedding trial execution receipt milestone card:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_milestone_card.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_milestone_card.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_milestone_card.json`
- This milestone card shows the immediate unlock boundary after the current speaker-profile receipt checkpoint closes, while remaining coordination-only and not claiming voiceprint success.

Speaker profile embedding trial execution receipt milestone bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_milestone_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_milestone_bridge_checklist.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_milestone_bridge_checklist.json`
- This checklist turns the speaker-profile milestone card into an explicit verification gate before the current readiness target is reopened.

Speaker profile embedding trial execution receipt completion dashboard:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_completion_dashboard.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_completion_dashboard.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_completion_dashboard.json`
- This dashboard compresses the current speaker-profile receipt state into one operator-facing view with the current case, next milestone, remaining visible gates, and the dominant coordination blocker.

Speaker profile embedding trial execution receipt completion dashboard bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_completion_dashboard_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_completion_dashboard_bridge_checklist.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_completion_dashboard_bridge_checklist.json`
- This checklist turns the speaker-profile completion dashboard into an explicit verification gate before the current readiness target is reopened.

Speaker profile embedding trial execution receipt status preflight bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_status_preflight_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_status_preflight_bridge_checklist.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_status_preflight_bridge_checklist.json`
- This checklist verifies the completion-dashboard bridge before the machine-readable speaker-profile status rollup is reopened.

Speaker profile embedding trial execution receipt status reentry card:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_status_reentry_card.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_status_reentry_card.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_status_reentry_card.json`
- This card reopens the machine-readable speaker-profile status rollup with one explicit reentry action after the status preflight bridge, while remaining coordination-only and not claiming voiceprint success.

Speaker profile embedding trial execution receipt status reentry bridge checklist:

- `results/figures/speaker_profile_embedding_trial_execution_receipt_status_reentry_bridge_checklist.md`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_status_reentry_bridge_checklist.csv`
- `results/tables/speaker_profile_embedding_trial_execution_receipt_status_reentry_bridge_checklist.json`
- This checklist verifies the speaker-profile status reentry card before the receipt readiness target is reopened, while remaining coordination-only and not claiming voiceprint success.

External validation slice staging handoff receipt readiness bridge checklist:

- `results/figures/external_validation_slice_staging_handoff_receipt_readiness_bridge_checklist.md`
- `results/tables/external_validation_slice_staging_handoff_receipt_readiness_bridge_checklist.csv`
- This checklist connects the staging receipt readiness rollup to the staging receipt without claiming benchmark execution.

Frontier execution receipt queue status bridge checklist:

- `results/figures/frontier_execution_receipt_queue_status_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_status_bridge_checklist.csv`
- This checklist connects the unified receipt readiness rollup to the completion summary without claiming benchmark execution.

Frontier execution receipt queue completion summary:

- `results/figures/frontier_execution_receipt_queue_completion_summary.md`
- `results/tables/frontier_execution_receipt_queue_completion_summary.csv`
- The receipt coordination queue rollup reports `queue_status = queue_complete` at `3/3`; no benchmark execution is claimed.

Frontier execution receipt queue completion summary bridge checklist:

- `results/figures/frontier_execution_receipt_queue_completion_summary_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_completion_summary_bridge_checklist.csv`
- This checklist connects the receipt coordination completion summary to the receipt-fill handoff without claiming benchmark execution.

Frontier execution receipt queue handoff:

- `results/figures/frontier_execution_receipt_queue_handoff.md`
- `results/tables/frontier_execution_receipt_queue_handoff.csv`
- This handoff turns the unified receipt readiness rollup into per-frontier receipt-fill actions for MeetEval, speaker profile, and external staging.

Frontier execution receipt queue handoff bridge checklist:

- `results/figures/frontier_execution_receipt_queue_handoff_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_handoff_bridge_checklist.csv`
- This checklist connects the receipt-fill handoff to per-frontier execution receipts without claiming benchmark execution.

Frontier execution receipt queue operator brief:

- `results/figures/frontier_execution_receipt_queue_operator_brief.md`
- `results/tables/frontier_execution_receipt_queue_operator_brief.csv`
- This brief turns the first receipt-queue handoff row into a plain-language next-step card for the current operator.

Frontier execution receipt queue runbook card:

- `results/figures/frontier_execution_receipt_queue_runbook_card.md`
- `results/tables/frontier_execution_receipt_queue_runbook_card.csv`
- This runbook card turns the receipt queue operator brief into a one-page first-action execution card for the current first receipt-queue target.

Frontier execution receipt queue runbook bridge checklist:

- `results/figures/frontier_execution_receipt_queue_runbook_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_runbook_bridge_checklist.csv`
- This checklist verifies the receipt queue runbook card before the current receipt target is reopened.

Frontier execution receipt queue phase checkpoint card:

- `results/figures/frontier_execution_receipt_queue_phase_checkpoint_card.md`
- `results/tables/frontier_execution_receipt_queue_phase_checkpoint_card.csv`
- This checkpoint card narrows the receipt queue runbook to the exact completion signal for the current first receipt-queue target.

Frontier execution receipt queue phase checkpoint bridge checklist:

- `results/figures/frontier_execution_receipt_queue_phase_checkpoint_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_phase_checkpoint_bridge_checklist.csv`
- This checklist verifies the receipt queue phase checkpoint card before the milestone card is reopened for the current first receipt-queue target.

Frontier execution receipt queue milestone card:

- `results/figures/frontier_execution_receipt_queue_milestone_card.md`
- `results/tables/frontier_execution_receipt_queue_milestone_card.csv`
- This milestone card records what the current first receipt-queue checkpoint unlocks next and how many visible receipt fronts remain afterward.

Frontier execution receipt queue milestone bridge checklist:

- `results/figures/frontier_execution_receipt_queue_milestone_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_milestone_bridge_checklist.csv`
- This checklist verifies the receipt queue milestone unlock path before the completion dashboard is reopened.

Frontier execution receipt queue completion dashboard:

- `results/figures/frontier_execution_receipt_queue_completion_dashboard.md`
- `results/tables/frontier_execution_receipt_queue_completion_dashboard.csv`
- This dashboard compresses the current receipt queue state into one operator-facing view with the current first frontier, next milestone, remaining visible fronts, and the dominant coordination blocker.

Frontier execution receipt queue completion dashboard bridge checklist:

- `results/figures/frontier_execution_receipt_queue_completion_dashboard_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_completion_dashboard_bridge_checklist.csv`
- This checklist turns the receipt queue dashboard into a verification gate before the runbook card is reopened for the current first frontier.

Frontier execution receipt queue status preflight bridge checklist:

- `results/figures/frontier_execution_receipt_queue_status_preflight_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_status_preflight_bridge_checklist.csv`
- This checklist verifies the completion-dashboard bridge before the receipt queue status rollup is reopened.

Frontier execution receipt queue status reentry card:

- `results/figures/frontier_execution_receipt_queue_status_reentry_card.md`
- `results/tables/frontier_execution_receipt_queue_status_reentry_card.csv`
- This card gives the next contributor a one-page instruction for reopening the receipt queue status rollup after preflight.

Frontier execution receipt queue status reentry bridge checklist:

- `results/figures/frontier_execution_receipt_queue_status_reentry_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_status_reentry_bridge_checklist.csv`
- This checklist verifies the receipt queue status reentry card before the handoff bridge is reopened.

Frontier execution receipt queue receipt open card:

- `results/figures/frontier_execution_receipt_queue_receipt_open_card.md`
- `results/tables/frontier_execution_receipt_queue_receipt_open_card.csv`
- This card gives the next contributor the first receipt target to open after the receipt queue handoff bridge is confirmed.

Frontier execution receipt queue handoff packet:

- `results/figures/frontier_execution_receipt_queue_handoff_packet.md`
- `results/tables/frontier_execution_receipt_queue_handoff_packet.csv`
- This packet consolidates the receipt queue status, queue summary, per-frontier handoff layers, the operator brief, the runbook card, the runbook bridge checklist, the phase checkpoint card, the phase checkpoint bridge checklist, the milestone card, the milestone bridge checklist, the completion dashboard, the completion-dashboard bridge checklist, the status preflight layer, the status reentry layer, and the first receipt target card into one single-entry coordination artifact.

Frontier execution receipt queue handoff packet bridge checklist:

- `results/figures/frontier_execution_receipt_queue_handoff_packet_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_handoff_packet_bridge_checklist.csv`
- This checklist verifies the receipt queue handoff packet before the receipt queue operator brief is reopened.

Frontier execution receipt queue frontier bridge:

- `results/figures/frontier_execution_receipt_queue_frontier_bridge.md`
- `results/tables/frontier_execution_receipt_queue_frontier_bridge.csv`
- `results/tables/frontier_execution_receipt_queue_frontier_bridge.json`
- This bridge connects the current receipt queue frontier to the breadth-first frontier queue head so contributors can verify coordination alignment before reopening execution layers.

Frontier execution receipt queue frontier bridge checklist:

- `results/figures/frontier_execution_receipt_queue_frontier_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_frontier_bridge_checklist.csv`
- `results/tables/frontier_execution_receipt_queue_frontier_bridge_checklist.json`
- This checklist turns the frontier bridge into an ordered verification gate before the receipt queue runbook card is reopened.

Frontier execution receipt queue receipt bridge:

- `results/figures/frontier_execution_receipt_queue_receipt_bridge.md`
- `results/tables/frontier_execution_receipt_queue_receipt_bridge.csv`
- `results/tables/frontier_execution_receipt_queue_receipt_bridge.json`
- This bridge connects the receipt queue operator brief to the current execution receipt target so contributors can reopen the right receipt path without claiming benchmark execution.

Frontier execution receipt queue receipt bridge checklist:

- `results/figures/frontier_execution_receipt_queue_receipt_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_receipt_bridge_checklist.csv`
- `results/tables/frontier_execution_receipt_queue_receipt_bridge_checklist.json`
- This checklist turns the receipt bridge into an ordered verification gate before the current execution receipt is reopened.

Frontier execution receipt queue evidence receipt:

- `results/figures/frontier_execution_receipt_queue_evidence_receipt.md`
- `results/tables/frontier_execution_receipt_queue_evidence_receipt.csv`
- `results/tables/frontier_execution_receipt_queue_evidence_receipt.json`
- This receipt records what evidence should be written back for the current receipt-queue frontier before the execution receipt JSON stops being template-only.

Frontier execution receipt queue evidence receipt bridge checklist:

- `results/figures/frontier_execution_receipt_queue_evidence_receipt_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_evidence_receipt_bridge_checklist.csv`
- `results/tables/frontier_execution_receipt_queue_evidence_receipt_bridge_checklist.json`
- This checklist connects the receipt queue handoff packet to the evidence receipt before any execution receipt JSON is reopened.

Frontier execution receipt queue execution receipt bridge:

- `results/figures/frontier_execution_receipt_queue_execution_receipt_bridge.md`
- `results/tables/frontier_execution_receipt_queue_execution_receipt_bridge.csv`
- `results/tables/frontier_execution_receipt_queue_execution_receipt_bridge.json`
- This bridge connects the evidence receipt to the current execution receipt JSON target before any benchmark receipt writeback is claimed.

Frontier execution receipt queue execution receipt bridge checklist:

- `results/figures/frontier_execution_receipt_queue_execution_receipt_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_execution_receipt_bridge_checklist.csv`
- `results/tables/frontier_execution_receipt_queue_execution_receipt_bridge_checklist.json`
- This checklist turns the execution receipt bridge into an ordered verification gate before the current execution receipt JSON is reopened.

Frontier execution receipt queue writeback packet:

- `results/figures/frontier_execution_receipt_queue_writeback_packet.md`
- `results/tables/frontier_execution_receipt_queue_writeback_packet.csv`
- `results/tables/frontier_execution_receipt_queue_writeback_packet.json`
- This packet provides a single entrypoint for the current receipt-queue writeback sub-stack from operator brief through execution receipt bridge.

Frontier execution receipt queue writeback packet bridge checklist:

- `results/figures/frontier_execution_receipt_queue_writeback_packet_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_writeback_packet_bridge_checklist.csv`
- `results/tables/frontier_execution_receipt_queue_writeback_packet_bridge_checklist.json`
- This checklist verifies the writeback packet before the current receipt-queue operator brief is reopened.

Frontier execution receipt queue writeback status:

- `results/figures/frontier_execution_receipt_queue_writeback_status.md`
- `results/tables/frontier_execution_receipt_queue_writeback_status.csv`
- `results/tables/frontier_execution_receipt_queue_writeback_status.json`
- `results/tables/frontier_execution_receipt_queue_writeback_summary.json`
- This dynamic rollup records which receipt-queue execution receipts are already written back, which remain template-only, and whether the overall writeback stack is still in progress.

Frontier execution receipt queue writeback handoff:

- `results/figures/frontier_execution_receipt_queue_writeback_handoff.md`
- `results/tables/frontier_execution_receipt_queue_writeback_handoff.csv`
- `results/tables/frontier_execution_receipt_queue_writeback_handoff.json`
- This handoff turns the dynamic writeback status into per-frontier next actions, correctly separating `meeteval` review/archive from the still-pending `speaker_profile` and `external_validation` writeback paths.

Frontier execution receipt queue writeback handoff bridge checklist:

- `results/figures/frontier_execution_receipt_queue_writeback_handoff_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_writeback_handoff_bridge_checklist.csv`
- `results/tables/frontier_execution_receipt_queue_writeback_handoff_bridge_checklist.json`
- This checklist turns the writeback handoff into a row-by-row verification gate before any frontier receipt is reopened for writeback.

Frontier execution receipt queue writeback open card:

- `results/figures/frontier_execution_receipt_queue_writeback_open_card.md`
- `results/tables/frontier_execution_receipt_queue_writeback_open_card.csv`
- `results/tables/frontier_execution_receipt_queue_writeback_open_card.json`
- This card selects the first still-pending writeback target after the handoff bridge, which currently prioritizes `speaker_profile` over the already-complete `meeteval` receipt.

Frontier execution receipt queue writeback open card bridge checklist:

- `results/figures/frontier_execution_receipt_queue_writeback_open_card_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_writeback_open_card_bridge_checklist.csv`
- `results/tables/frontier_execution_receipt_queue_writeback_open_card_bridge_checklist.json`
- This checklist turns the current writeback open card into an ordered verification gate before the targeted execution receipt is reopened.

Frontier execution receipt queue writeback handoff packet:

- `results/figures/frontier_execution_receipt_queue_writeback_handoff_packet.md`
- `results/tables/frontier_execution_receipt_queue_writeback_handoff_packet.csv`
- `results/tables/frontier_execution_receipt_queue_writeback_handoff_packet.json`
- This packet provides a compact entrypoint for the current writeback handoff sub-stack, bundling status, handoff, open-card, and their verification gates.

Frontier execution receipt queue writeback handoff packet bridge checklist:

- `results/figures/frontier_execution_receipt_queue_writeback_handoff_packet_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_queue_writeback_handoff_packet_bridge_checklist.csv`
- `results/tables/frontier_execution_receipt_queue_writeback_handoff_packet_bridge_checklist.json`
- This checklist verifies the compact writeback handoff packet before reopening the writeback status rollup.

Frontier execution receipt fill queue status:

- `results/figures/frontier_execution_receipt_fill_queue_status.md`
- `results/tables/frontier_execution_receipt_fill_queue_status.csv`
- `results/tables/frontier_execution_receipt_fill_queue_summary.json`
- The fill queue rollup reports `combined_fill_status = fill_queue_ready` with `awaiting_fill_count = 3/3`; template-only receipts remain unfilled and no benchmark execution is claimed.

Frontier execution receipt fill queue status bridge checklist:

- `results/figures/frontier_execution_receipt_fill_queue_status_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_queue_status_bridge_checklist.csv`
- This checklist connects the fill queue status to per-frontier execution receipts without claiming benchmark execution.

Frontier execution receipt fill queue completion summary:

- `results/figures/frontier_execution_receipt_fill_queue_completion_summary.md`
- `results/tables/frontier_execution_receipt_fill_queue_completion_summary.csv`
- The fill coordination queue rollup reports `combined_fill_status = fill_queue_ready` at `3/3` awaiting fill; no benchmark execution is claimed.

Frontier execution receipt fill queue handoff:

- `results/figures/frontier_execution_receipt_fill_queue_handoff.md`
- `results/tables/frontier_execution_receipt_fill_queue_handoff.csv`
- This handoff turns the fill queue status into per-frontier fill execution actions for MeetEval, speaker profile, and external staging.

Frontier execution receipt fill queue completion summary bridge checklist:

- `results/figures/frontier_execution_receipt_fill_queue_completion_summary_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_queue_completion_summary_bridge_checklist.csv`
- This checklist connects the fill coordination completion summary to the fill execution handoff without claiming benchmark execution.

Frontier execution receipt fill queue handoff bridge checklist:

- `results/figures/frontier_execution_receipt_fill_queue_handoff_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_queue_handoff_bridge_checklist.csv`
- This checklist connects the fill execution handoff to per-frontier execution receipts without claiming benchmark execution.

Frontier execution receipt fill execution packet:

- `results/figures/frontier_execution_receipt_fill_execution_packet.md`
- `results/tables/frontier_execution_receipt_fill_execution_packet.csv`
- This packet provides a single entrypoint for the receipt fill execution stack while `combined_fill_status = fill_queue_ready`.

Frontier execution receipt fill execution packet bridge checklist:

- `results/figures/frontier_execution_receipt_fill_execution_packet_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_execution_packet_bridge_checklist.csv`
- This checklist connects the fill execution packet to the unified fill execution status rollup.

Frontier execution receipt fill execution status:

- `results/figures/frontier_execution_receipt_fill_execution_status.md`
- `results/tables/frontier_execution_receipt_fill_execution_status.csv`
- The unified fill execution rollup reports `combined_fill_execution_status = fill_execution_ready` with all three receipts still `template_only`.

Frontier execution receipt fill execution status bridge checklist:

- `results/figures/frontier_execution_receipt_fill_execution_status_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_execution_status_bridge_checklist.csv`
- This checklist connects the fill execution status rollup to the fill execution handoff.

Frontier execution receipt fill execution handoff:

- `results/figures/frontier_execution_receipt_fill_execution_handoff.md`
- `results/tables/frontier_execution_receipt_fill_execution_handoff.csv`
- This handoff turns the unified fill execution status into per-frontier fill execution actions for MeetEval, speaker profile, and external staging.

Frontier execution receipt fill execution handoff bridge checklist:

- `results/figures/frontier_execution_receipt_fill_execution_handoff_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_execution_handoff_bridge_checklist.csv`
- This checklist connects the fill execution handoff to per-frontier execution receipts without claiming benchmark execution.

Frontier execution receipt fill execution completion summary:

- `results/figures/frontier_execution_receipt_fill_execution_completion_summary.md`
- `results/tables/frontier_execution_receipt_fill_execution_completion_summary.csv`
- The unified fill execution completion rollup reports `combined_fill_execution_status = fill_execution_ready` with `awaiting_fill_execution_count = 3/3`.

Frontier execution receipt fill execution completion summary bridge checklist:

- `results/figures/frontier_execution_receipt_fill_execution_completion_summary_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_execution_completion_summary_bridge_checklist.csv`
- This checklist connects the fill execution completion summary to the fill execution handoff.

Frontier execution receipt fill execution operator brief:

- `results/figures/frontier_execution_receipt_fill_execution_operator_brief.md`
- `results/tables/frontier_execution_receipt_fill_execution_operator_brief.csv`
- This brief gives the current frontier operator a plain-language next step for the first fill target (`meeteval_compatibility`).

Frontier execution receipt fill execution receipt bridge:

- `results/figures/frontier_execution_receipt_fill_execution_receipt_bridge.md`
- `results/tables/frontier_execution_receipt_fill_execution_receipt_bridge.csv`
- This bridge connects the operator brief to the MeetEval execution receipt target without claiming benchmark execution.

Frontier execution receipt fill execution receipt bridge checklist:

- `results/figures/frontier_execution_receipt_fill_execution_receipt_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_execution_receipt_bridge_checklist.csv`
- This checklist turns the receipt bridge into an ordered writeback verification path.

Frontier execution receipt fill execution handoff packet:

- `results/figures/frontier_execution_receipt_fill_execution_handoff_packet.md`
- `results/tables/frontier_execution_receipt_fill_execution_handoff_packet.csv`
- This packet consolidates the fill execution coordination stack into one entrypoint.

Frontier execution receipt fill execution evidence receipt:

- `results/figures/frontier_execution_receipt_fill_execution_evidence_receipt.md`
- `results/tables/frontier_execution_receipt_fill_execution_evidence_receipt.csv`
- This receipt shows what the current fill execution run must write back before advancing the stack.

Frontier execution receipt fill execution evidence receipt bridge checklist:

- `results/figures/frontier_execution_receipt_fill_execution_evidence_receipt_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_execution_evidence_receipt_bridge_checklist.csv`
- This checklist connects the handoff packet to the evidence receipt without claiming benchmark execution.

Frontier execution receipt fill execution runbook card:

- `results/figures/frontier_execution_receipt_fill_execution_runbook_card.md`
- `results/tables/frontier_execution_receipt_fill_execution_runbook_card.csv`
- This runbook card condenses the first fill execution action into a one-page execution card.

Frontier execution receipt fill execution completion dashboard:

- `results/figures/frontier_execution_receipt_fill_execution_completion_dashboard.md`
- `results/tables/frontier_execution_receipt_fill_execution_completion_dashboard.csv`
- This dashboard summarizes the current fill execution queue state at a glance.

Frontier execution receipt fill execution milestone card:

- `results/figures/frontier_execution_receipt_fill_execution_milestone_card.md`
- `results/tables/frontier_execution_receipt_fill_execution_milestone_card.csv`
- This milestone card shows the immediate completion boundary for the fill execution queue.

Frontier execution receipt fill execution execution receipt bridge:

- `results/figures/frontier_execution_receipt_fill_execution_execution_receipt_bridge.md`
- `results/tables/frontier_execution_receipt_fill_execution_execution_receipt_bridge.csv`
- This bridge connects the evidence receipt to the JSON execution receipt target.

Frontier execution receipt fill execution execution receipt bridge checklist:

- `results/figures/frontier_execution_receipt_fill_execution_execution_receipt_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_execution_execution_receipt_bridge_checklist.csv`
- This checklist turns the execution receipt bridge into an ordered verification path.

Frontier execution receipt fill execution phase checkpoint card:

- `results/figures/frontier_execution_receipt_fill_execution_phase_checkpoint_card.md`
- `results/tables/frontier_execution_receipt_fill_execution_phase_checkpoint_card.csv`
- This checkpoint card shows the per-phase completion signal for the current fill execution step.

Frontier execution receipt fill execution runbook bridge checklist:

- `results/figures/frontier_execution_receipt_fill_execution_runbook_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_execution_runbook_bridge_checklist.csv`
- This checklist connects the runbook card to the evidence receipt target.

MeetEval cpWER execution preflight batch:

- `results/figures/meeteval_cpwer_execution_preflight_batch.md`
- `results/tables/meeteval_cpwer_execution_preflight_batch.csv`
- All five verified gold cases pass segment-export preflight; official cpWER evaluation remains pending.

Frontier execution receipt fill execution frontier bridge:

- `results/figures/frontier_execution_receipt_fill_execution_frontier_bridge.md`
- `results/tables/frontier_execution_receipt_fill_execution_frontier_bridge.csv`
- This bridge connects fill execution to the breadth-first frontier queue head.

Frontier execution receipt fill execution dashboard bridge checklist:

- `results/figures/frontier_execution_receipt_fill_execution_dashboard_bridge_checklist.md`
- `results/tables/frontier_execution_receipt_fill_execution_dashboard_bridge_checklist.csv`
- This checklist connects the completion dashboard to the runbook card target.

MeetEval cpWER execution receipt batch scaffold:

- `results/figures/meeteval_cpwer_execution_receipt_batch_scaffold.md`
- `results/tables/meeteval_cpwer_execution_receipt_batch_scaffold.csv`
- Template-only official cpWER execution receipt scaffolds for all five verified gold cases; official evaluation remains pending.

MeetEval cpWER execution receipt batch scaffold bridge checklist:

- `results/figures/meeteval_cpwer_execution_receipt_batch_scaffold_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_receipt_batch_scaffold_bridge_checklist.csv`
- This checklist connects the batch receipt scaffold to the official execution receipt target.

MeetEval cpWER execution status batch:

- `results/figures/meeteval_cpwer_execution_status_batch.md`
- `results/tables/meeteval_cpwer_execution_status_batch.csv`
- Now rolls up per-case execution receipt reality across all five verified gold cases: `execution_chain_complete` when the official narrow dry run is already recorded, otherwise `execution_chain_ready` or `execution_chain_in_progress`.

MeetEval cpWER execution status batch bridge checklist:

- `results/figures/meeteval_cpwer_execution_status_batch_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_status_batch_bridge_checklist.csv`
- This checklist connects the batch execution status to the official execution receipt target.

MeetEval cpWER execution status batch completion summary:

- `results/figures/meeteval_cpwer_execution_status_batch_completion_summary.md`
- `results/tables/meeteval_cpwer_execution_status_batch_completion_summary.csv`
- Rolls up batch execution-chain queue completion using the stricter per-case status model, so `queue_complete` now means all five cases are already `execution_chain_complete`.

MeetEval cpWER execution status batch completion summary bridge checklist:

- `results/figures/meeteval_cpwer_execution_status_batch_completion_summary_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_status_batch_completion_summary_bridge_checklist.csv`
- Connects the batch completion summary to the batch execution handoff.

MeetEval cpWER execution status batch handoff:

- `results/figures/meeteval_cpwer_execution_status_batch_handoff.md`
- `results/tables/meeteval_cpwer_execution_status_batch_handoff.csv`
- Per-case official cpWER execution handoff actions across all five verified gold cases.

MeetEval cpWER execution status batch handoff completion summary:

- `results/figures/meeteval_cpwer_execution_status_batch_handoff_completion_summary.md`
- `results/tables/meeteval_cpwer_execution_status_batch_handoff_completion_summary.csv`
- `queue_status = queue_complete` across all five batch handoff rows; official MeetEval evaluation is not claimed.

MeetEval cpWER execution status batch handoff completion summary bridge checklist:

- `results/figures/meeteval_cpwer_execution_status_batch_handoff_completion_summary_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_status_batch_handoff_completion_summary_bridge_checklist.csv`
- Connects batch handoff completion to official cpWER execution completion review.

MeetEval cpWER execution status batch handoff completion summary handoff:

- `results/figures/meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff.md`
- `results/tables/meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff.csv`
- `handoff_status = batch_handoff_completion_handoff_ready` at `5/5` complete handoffs; official execution completion review remains next.

MeetEval cpWER execution status batch handoff completion summary handoff bridge checklist:

- `results/figures/meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_status_batch_handoff_completion_summary_handoff_bridge_checklist.csv`
- Connects batch handoff completion handoff to official cpWER execution completion review.

MeetEval cpWER execution status batch handoff bridge checklist:

- `results/figures/meeteval_cpwer_execution_status_batch_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_execution_status_batch_handoff_bridge_checklist.csv`
- Connects the batch handoff to the official cpWER execution module.

MeetEval cpWER official execution:

- `results/figures/meeteval_cpwer_official_execution.md`
- `results/tables/meeteval_cpwer_official_execution.csv`
- All-gold official MeetEval cpWER narrow dry run via `python -m src.meeteval_cpwer_official_execution --all`; receipt writeback on success.
- All five cases report `official_cpwer_narrow_dry_run_complete`; official cpWER scores show moderate drift vs bridge-lite due to Chinese tokenization (MeetEval word-level vs character-level bridge-lite).

MeetEval cpWER official execution bridge checklist:

- `results/figures/meeteval_cpwer_official_execution_bridge_checklist.md`
- Connects official execution output to the execution receipt without claiming full benchmark completion.

MeetEval cpWER official execution completion summary:

- `results/figures/meeteval_cpwer_official_execution_completion_summary.md`
- `queue_status = queue_complete` at `5/5` when all gold cases complete narrow dry run.

MeetEval cpWER official execution alignment audit:

- `results/figures/meeteval_cpwer_official_execution_alignment_audit.md`
- The audit now explicitly ties the observed moderate drift to Chinese word-level tokenization mismatch when tokenization diagnostic and character-spaced reconciliation evidence are both present, instead of ambiguously blaming segment or speaker mapping.
- Compares official cpWER against bridge-lite; all five gold cases currently report `moderate_drift`.

MeetEval cpWER official execution alignment audit bridge checklist:

- `results/figures/meeteval_cpwer_official_execution_alignment_audit_bridge_checklist.md`
- `results/tables/meeteval_cpwer_official_execution_alignment_audit_bridge_checklist.csv`
- This checklist connects alignment drift findings to the tokenization diagnostic before escalating any mapping concern.

MeetEval cpWER official execution completion summary bridge checklist:

- `results/figures/meeteval_cpwer_official_execution_completion_summary_bridge_checklist.md`
- Connects completion summary to alignment audit verification path.

MeetEval cpWER official execution tokenization diagnostic:

- `results/figures/meeteval_cpwer_official_execution_tokenization_diagnostic.md`
- All five gold cases report `no_whitespace_word_tokenization` root cause for raw official cpWER drift.

MeetEval cpWER character-level official execution:

- `results/figures/meeteval_cpwer_character_level_official_execution.md`
- Character-spaced MeetEval cpWER via `python -m src.meeteval_cpwer_character_level_official_execution --all`.

MeetEval cpWER official execution reconciliation audit:

- `results/figures/meeteval_cpwer_official_execution_reconciliation_audit.md`
- After character tokenization, `5/5` cases align with bridge-lite within tolerance.

MeetEval cpWER official execution reconciliation audit bridge checklist:

- `results/figures/meeteval_cpwer_official_execution_reconciliation_audit_bridge_checklist.md`
- `results/tables/meeteval_cpwer_official_execution_reconciliation_audit_bridge_checklist.csv`
- This checklist connects character-spaced reconciliation evidence to the character-level official execution path before promoting it as the preferred frontier metric.

MeetEval cpWER tokenization adaptation completion summary:

- `results/figures/meeteval_cpwer_tokenization_adaptation_completion_summary.md`
- `results/tables/meeteval_cpwer_tokenization_adaptation_completion_summary.csv`
- `queue_status = queue_complete` at `5/5` reconciled cases; no full MeetEval benchmark claim.

MeetEval cpWER tokenization gain scorecard:

- `results/figures/meeteval_cpwer_tokenization_gain_scorecard.md`
- `results/tables/meeteval_cpwer_tokenization_gain_scorecard.csv`
- All five gold cases show positive raw-to-character adaptation gain and aligned character-level scores against bridge-lite.

MeetEval cpWER tokenization gain scorecard summary:

- `results/figures/meeteval_cpwer_tokenization_gain_scorecard_summary.md`
- `results/tables/meeteval_cpwer_tokenization_gain_scorecard_summary.csv`
- `average_raw_to_character_gain = 3.679091`, `max_gain_case = NoOverlap`, and `recommended_default_mode = character_spaced`.

MeetEval cpWER tokenization gain scorecard bridge checklist:

- `results/figures/meeteval_cpwer_tokenization_gain_scorecard_bridge_checklist.md`
- `results/tables/meeteval_cpwer_tokenization_gain_scorecard_bridge_checklist.csv`
- This checklist verifies the gain scorecard before advancing to the tokenization adaptation completion summary without claiming benchmark completion.

MeetEval cpWER tokenization gain scorecard handoff:

- `results/figures/meeteval_cpwer_tokenization_gain_scorecard_handoff.md`
- `results/tables/meeteval_cpwer_tokenization_gain_scorecard_handoff.csv`
- `handoff_status = tokenization_gain_handoff_ready` at `5/5` adapted-and-aligned cases; adaptation completion remains coordination-only.

MeetEval cpWER tokenization gain scorecard handoff bridge checklist:

- `results/figures/meeteval_cpwer_tokenization_gain_scorecard_handoff_bridge_checklist.md`
- `results/tables/meeteval_cpwer_tokenization_gain_scorecard_handoff_bridge_checklist.csv`
- This checklist connects the gain handoff to the tokenization adaptation handoff without claiming benchmark completion.

MeetEval cpWER tokenization gain scorecard handoff completion summary:

- `results/figures/meeteval_cpwer_tokenization_gain_scorecard_handoff_completion_summary.md`
- `results/tables/meeteval_cpwer_tokenization_gain_scorecard_handoff_completion_summary.csv`
- `queue_status = queue_complete` at `5/5` adapted-and-aligned cases; tokenization adaptation handoff remains next.

MeetEval cpWER tokenization gain scorecard handoff completion summary bridge checklist:

- `results/figures/meeteval_cpwer_tokenization_gain_scorecard_handoff_completion_summary_bridge_checklist.md`
- `results/tables/meeteval_cpwer_tokenization_gain_scorecard_handoff_completion_summary_bridge_checklist.csv`
- This checklist verifies gain handoff completion before advancing the tokenization adaptation handoff.

MeetEval tokenization gain to frontier fill handoff:

- `results/figures/meeteval_tokenization_gain_to_frontier_fill_handoff.md`
- `results/tables/meeteval_tokenization_gain_to_frontier_fill_handoff.csv`
- `handoff_status = tokenization_gain_frontier_fill_handoff_ready` at `5/5` adapted-and-aligned cases; frontier fill runbook remains coordination-only.

MeetEval tokenization gain to frontier fill handoff bridge checklist:

- `results/figures/meeteval_tokenization_gain_to_frontier_fill_handoff_bridge_checklist.md`
- `results/tables/meeteval_tokenization_gain_to_frontier_fill_handoff_bridge_checklist.csv`
- This checklist connects tokenization-to-fill handoff to the frontier fill operator brief without claiming benchmark completion.

MeetEval tokenization gain frontier fill runbook card:

- `results/figures/meeteval_tokenization_gain_frontier_fill_runbook_card.md`
- `results/tables/meeteval_tokenization_gain_frontier_fill_runbook_card.csv`
- `runbook_status = tokenization_gain_frontier_fill_runbook_ready` at `5/5` adapted cases; MeetEval receipt fill remains coordination-only.

MeetEval tokenization gain frontier fill runbook bridge checklist:

- `results/figures/meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist.md`
- `results/tables/meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist.csv`
- This checklist connects the runbook card to the MeetEval execution receipt JSON without claiming benchmark completion.

MeetEval tokenization gain frontier fill execution receipt bridge:

- `results/figures/meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge.md`
- `results/tables/meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge.csv`
- Bridges the runbook bridge checklist to `results/tables/meeteval_cpwer_execution_receipt.json`.

MeetEval tokenization gain frontier fill execution receipt bridge checklist:

- `results/figures/meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge_checklist.md`
- `results/tables/meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge_checklist.csv`
- Ordered verification path before updating the MeetEval execution receipt.

MeetEval tokenization gain frontier fill operator brief:

- `results/figures/meeteval_tokenization_gain_frontier_fill_operator_brief.md`
- `results/tables/meeteval_tokenization_gain_frontier_fill_operator_brief.csv`
- Plain-language operator action for character-spaced cpWER receipt writeback.

MeetEval cpWER tokenization adaptation completion summary bridge checklist:

- `results/figures/meeteval_cpwer_tokenization_adaptation_completion_summary_bridge_checklist.md`
- `results/tables/meeteval_cpwer_tokenization_adaptation_completion_summary_bridge_checklist.csv`
- This checklist connects the tokenization adaptation completion summary to frontier fill execution without claiming benchmark completion.

MeetEval cpWER tokenization adaptation handoff:

- `results/figures/meeteval_tokenization_adaptation_handoff.md`
- `results/tables/meeteval_tokenization_adaptation_handoff.csv`
- `handoff_status = tokenization_adaptation_handoff_ready` at `5/5` reconciled cases; frontier fill execution remains coordination-only.

MeetEval cpWER tokenization adaptation handoff bridge checklist:

- `results/figures/meeteval_tokenization_adaptation_handoff_bridge_checklist.md`
- `results/tables/meeteval_tokenization_adaptation_handoff_bridge_checklist.csv`
- This checklist connects the tokenization handoff to the frontier fill evidence receipt without claiming benchmark completion.

MeetEval cpWER tokenization adaptation handoff completion summary:

- `results/figures/meeteval_tokenization_adaptation_handoff_completion_summary.md`
- `results/tables/meeteval_tokenization_adaptation_handoff_completion_summary.csv`
- `queue_status = queue_complete` at `5/5` reconciled cases; frontier fill runbook remains next.

MeetEval cpWER tokenization adaptation handoff completion summary bridge checklist:

- `results/figures/meeteval_tokenization_adaptation_handoff_completion_summary_bridge_checklist.md`
- `results/tables/meeteval_tokenization_adaptation_handoff_completion_summary_bridge_checklist.csv`
- This checklist connects handoff completion to the frontier fill runbook card without claiming benchmark completion.

MeetEval cpWER tokenization adaptation handoff packet:

- `results/figures/meeteval_tokenization_adaptation_handoff_packet.md`
- `results/tables/meeteval_tokenization_adaptation_handoff_packet.csv`
- `results/tables/meeteval_tokenization_adaptation_handoff_packet.json`
- This packet consolidates the tokenization diagnostic through adaptation handoff completion, tokenization-to-fill handoff, and frontier fill bridge layers into one coordination entrypoint without claiming full benchmark completion.

MeetEval compatibility skill card:

- `docs/skills/skill_04_meeteval_compatibility.md`
- The frontier queue head now has a dedicated skill card so MeetEval compatibility work is directly pickable from the skills index.

External validation checklist bridge:

- `results/figures/external_validation_checklist.md`
- `results/tables/external_validation_checklist.csv`
- This bridge now turns the prioritized external candidates into an execution checklist. It still stays in `external/sanity-check` mode and does not claim that any external validation run has been completed.

External validation go-no-go board:

- `results/figures/external_validation_go_no_go_board.md`
- `results/tables/external_validation_go_no_go_board.csv`
- The board shows `5/5` checkpoints still at `no_go` for the first AISHELL-4 slice.

External validation go-no-go summary:

- `results/figures/external_validation_go_no_go_summary.md`
- `results/tables/external_validation_go_no_go_summary.csv`
- `overall_state = blocked_by_license_confirmation` with `primary_blocker = license_confirmation_pending`.

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

Demo walkthrough review pass:

- `results/figures/demo_walkthrough_review_pass.md`
- `results/tables/demo_walkthrough_review_pass.csv`
- The first qualitative walkthrough review pass records `review_status = review_complete` for the opening step without claiming live demo or recording delivery.

Demo walkthrough review pass advance:

- `results/figures/demo_walkthrough_review_pass_advance.md`
- `results/tables/demo_walkthrough_review_pass_advance.csv`
- The walkthrough review queue advanced to step `2` (`Baseline evidence`) after step `1` reached `review_complete` without claiming live demo delivery.

Demo walkthrough review pass second:

- `results/figures/demo_walkthrough_review_pass_second.md`
- `results/tables/demo_walkthrough_review_pass_second.csv`
- The second qualitative walkthrough review pass records critic-style notes for step `2` only; no live demo or recording is claimed.

Demo walkthrough review pass continue:

- `results/figures/demo_walkthrough_review_pass_continue.md`
- `results/tables/demo_walkthrough_review_pass_continue.csv`
- The walkthrough review queue advanced to step `3` (`Routing takeaway`) after steps `1` and `2` reached `review_complete` without claiming live demo delivery.

Demo walkthrough review pass third:

- `results/figures/demo_walkthrough_review_pass_third.md`
- `results/tables/demo_walkthrough_review_pass_third.csv`
- The third qualitative walkthrough review pass records notes for step `3` only; no live demo or recording is claimed.

Demo walkthrough review pass continue bridge checklist:

- `results/figures/demo_walkthrough_review_pass_continue_bridge_checklist.md`
- `results/tables/demo_walkthrough_review_pass_continue_bridge_checklist.csv`
- This checklist connects step `3` to the step `4` second-continue pass without claiming live demo delivery.

Demo walkthrough review pass second continue:

- `results/figures/demo_walkthrough_review_pass_second_continue.md`
- `results/tables/demo_walkthrough_review_pass_second_continue.csv`
- The walkthrough review queue advanced to step `4` (`Frontier breadth`) after steps `1`–`3` reached `review_complete` without claiming live demo delivery.

Demo walkthrough review pass fourth:

- `results/figures/demo_walkthrough_review_pass_fourth.md`
- `results/tables/demo_walkthrough_review_pass_fourth.csv`
- The fourth qualitative walkthrough review pass records notes for step `4` only; no live demo or recording is claimed.

Demo walkthrough review pass third continue:

- `results/figures/demo_walkthrough_review_pass_third_continue.md`
- `results/tables/demo_walkthrough_review_pass_third_continue.csv`
- The walkthrough review queue advanced to step `5` (`Next-step framing`) after steps `1`–`4` reached `review_complete` without claiming live demo delivery.

Demo walkthrough review pass fifth:

- `results/figures/demo_walkthrough_review_pass_fifth.md`
- `results/tables/demo_walkthrough_review_pass_fifth.csv`
- The fifth qualitative walkthrough review pass records notes for step `5` only; no live demo or recording is claimed.

Demo walkthrough review pass status:

- `results/figures/demo_walkthrough_review_pass_status.md`
- `results/tables/demo_walkthrough_review_pass_status.csv`
- The walkthrough review queue rollup reports `queue_status = queue_complete` with `completed_count = 5/5`; no live demo delivery is claimed.

Demo walkthrough review pass status bridge checklist:

- `results/figures/demo_walkthrough_review_pass_status_bridge_checklist.md`
- `results/tables/demo_walkthrough_review_pass_status_bridge_checklist.csv`
- This checklist connects the status rollup to the final pass bridge without claiming live demo delivery.

Demo walkthrough review pass final bridge checklist:

- `results/figures/demo_walkthrough_review_pass_final_bridge_checklist.md`
- `results/tables/demo_walkthrough_review_pass_final_bridge_checklist.csv`
- This checklist connects step `5` to the completion summary without claiming live demo delivery.

Demo walkthrough review pass completion summary:

- `results/figures/demo_walkthrough_review_pass_completion_summary.md`
- `results/tables/demo_walkthrough_review_pass_completion_summary.csv`
- The completion summary reports `queue_status = queue_complete` with `completed_count = 5/5`; no live demo delivery is claimed.

Demo go-no-go board:

- `results/figures/demo_go_no_go_board.md`
- `results/tables/demo_go_no_go_board.csv`
- The board shows `4/6` checkpoints are ready for a narrow presentation writeback path.

Demo go-no-go summary:

- `results/figures/demo_go_no_go_summary.md`
- `results/tables/demo_go_no_go_summary.csv`
- `overall_state = presentation_writeback_ready` while `primary_boundary = live_demo_claims_still_blocked`.

Demo walkthrough review pass completion summary bridge checklist:

- `results/figures/demo_walkthrough_review_pass_completion_summary_bridge_checklist.md`
- `results/tables/demo_walkthrough_review_pass_completion_summary_bridge_checklist.csv`
- This checklist connects the walkthrough completion summary to the storyboard review pass without claiming live demo delivery.

Demo storyboard review pass:

- `results/figures/demo_storyboard_review_pass.md`
- `results/tables/demo_storyboard_review_pass.csv`
- The first qualitative storyboard review pass records `review_complete` for the `Problem` card without claiming live demo or recording delivery.

Demo storyboard review pass advance:

- `results/figures/demo_storyboard_review_pass_advance.md`
- `results/tables/demo_storyboard_review_pass_advance.csv`
- The storyboard review queue advanced to card `2` (`Pipeline`) after card `1` reached `review_complete` without claiming live demo delivery.

Demo storyboard review pass second:

- `results/figures/demo_storyboard_review_pass_second.md`
- `results/tables/demo_storyboard_review_pass_second.csv`
- The second qualitative storyboard review pass records notes for card `2` only; no live demo or recording is claimed.

Demo storyboard review pass advance bridge checklist:

- `results/figures/demo_storyboard_review_pass_advance_bridge_checklist.md`
- `results/tables/demo_storyboard_review_pass_advance_bridge_checklist.csv`
- This checklist connects card `2` to the third-card review pass without claiming live demo delivery.

Demo storyboard review pass continue:

- `results/figures/demo_storyboard_review_pass_continue.md`
- `results/tables/demo_storyboard_review_pass_continue.csv`
- The storyboard review queue advanced to card `3` (`Findings`) after cards `1` and `2` reached `review_complete` without claiming live demo delivery.

Demo storyboard review pass third:

- `results/figures/demo_storyboard_review_pass_third.md`
- `results/tables/demo_storyboard_review_pass_third.csv`
- The third qualitative storyboard review pass records notes for card `3` only; no live demo or recording is claimed.

Demo storyboard review pass second continue:

- `results/figures/demo_storyboard_review_pass_second_continue.md`
- `results/tables/demo_storyboard_review_pass_second_continue.csv`
- The storyboard review queue advanced to card `4` (`Frontier`) after cards `1`–`3` reached `review_complete` without claiming live demo delivery.

Demo storyboard review pass fourth:

- `results/figures/demo_storyboard_review_pass_fourth.md`
- `results/tables/demo_storyboard_review_pass_fourth.csv`
- The fourth qualitative storyboard review pass records notes for card `4` only; no live demo or recording is claimed.

Demo storyboard review pass continue bridge checklist:

- `results/figures/demo_storyboard_review_pass_continue_bridge_checklist.md`
- `results/tables/demo_storyboard_review_pass_continue_bridge_checklist.csv`
- This checklist connects card `3` to the fourth-card review pass without claiming live demo delivery.

Demo storyboard review pass status:

- `results/figures/demo_storyboard_review_pass_status.md`
- `results/tables/demo_storyboard_review_pass_status.csv`
- `queue_status = queue_complete` at `4/4` without any live demo or recording claim.

Demo storyboard review pass status bridge checklist:

- `results/figures/demo_storyboard_review_pass_status_bridge_checklist.md`
- `results/tables/demo_storyboard_review_pass_status_bridge_checklist.csv`
- This checklist connects the status rollup to the completion summary without claiming live demo delivery.

Demo storyboard review pass completion summary:

- `results/figures/demo_storyboard_review_pass_completion_summary.md`
- `results/tables/demo_storyboard_review_pass_completion_summary.csv`
- `queue_status = queue_complete` at `4/4` without any live demo or recording claim.

Demo storyboard review pass completion summary bridge checklist:

- `results/figures/demo_storyboard_review_pass_completion_summary_bridge_checklist.md`
- `results/tables/demo_storyboard_review_pass_completion_summary_bridge_checklist.csv`
- This checklist connects the storyboard completion summary to the demo excellence queue status without claiming live demo delivery.

Demo excellence queue status:

- `results/figures/demo_excellence_queue_status.md`
- `results/tables/demo_excellence_queue_status.csv`
- `combined_queue_status = queue_complete` when both walkthrough and storyboard queues are complete; no live demo delivery is claimed.

Streamlit demo scaffold:

- `demo/app.py`
- `requirements-demo.txt`
- Run with `streamlit run demo/app.py` after installing `requirements-demo.txt`; tabs cover storyboard, walkthrough, gold CER, and frontier fill queue status. This is qualitative/demo support only and does not run live ASR.

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
python -m src.export_meeteval_compatibility
python -m src.meeteval_dry_run
python -m src.meeteval_cpwer_bridge --case all
python -m src.meeteval_cpwer_alignment
python -m src.meeteval_cpwer_alignment_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_diagnostic
python -m src.meeteval_cpwer_alignment_drift_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_handoff
python -m src.meeteval_cpwer_alignment_drift_handoff_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_scaffold
python -m src.meeteval_cpwer_alignment_drift_segment_scaffold_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_handoff
python -m src.meeteval_cpwer_alignment_drift_segment_handoff_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_inspection
python -m src.meeteval_cpwer_alignment_drift_segment_inspection_bridge_checklist
python -m src.external_validation_slice_scaffold
python -m src.external_validation_license_gate
python -m src.external_validation_license_gate_bridge_checklist
python -m src.external_validation_license_confirmation_scaffold
python -m src.external_validation_license_confirmation_scaffold_bridge_checklist
python -m src.external_validation_license_confirmation_receipt_bridge
python -m src.meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold
python -m src.meeteval_cpwer_alignment_drift_segment_reconciliation_scaffold_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_reconciliation_handoff
python -m src.meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic
python -m src.meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_reconciliation_handoff_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic
python -m src.meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff
python -m src.meeteval_cpwer_alignment_drift_segment_timing_diagnostic
python -m src.meeteval_cpwer_alignment_drift_segment_timing_diagnostic_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff
python -m src.meeteval_cpwer_alignment_drift_segment_granularity_diagnostic
python -m src.meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff
python -m src.meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic
python -m src.meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_bridge_checklist
python -m src.meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff
python -m src.meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_handoff_bridge_checklist
python -m src.demo_walkthrough_review_pass
python -m src.demo_walkthrough_review_pass_advance
python -m src.demo_walkthrough_review_pass_continue
python -m src.demo_walkthrough_review_pass_continue_bridge_checklist
python -m src.demo_walkthrough_review_pass_second_continue
python -m src.demo_walkthrough_review_pass_third_continue
python -m src.demo_walkthrough_review_pass_status
python -m src.demo_walkthrough_review_pass_status_bridge_checklist
python -m src.demo_walkthrough_review_pass_final_bridge_checklist
python -m src.demo_walkthrough_review_pass_completion_summary
python -m src.demo_walkthrough_review_pass_completion_summary_bridge_checklist
python -m src.demo_storyboard_review_pass
python -m src.demo_storyboard_review_pass_advance
python -m src.demo_storyboard_review_pass_advance_bridge_checklist
python -m src.demo_storyboard_review_pass_continue
python -m src.demo_storyboard_review_pass_second_continue
python -m src.demo_storyboard_review_pass_continue_bridge_checklist
python -m src.demo_storyboard_review_pass_status
python -m src.demo_storyboard_review_pass_status_bridge_checklist
python -m src.demo_storyboard_review_pass_completion_summary
python -m src.demo_storyboard_review_pass_completion_summary_bridge_checklist
python -m src.demo_excellence_queue_status
python -m src.meeteval_cpwer_execution_scaffold
python -m src.meeteval_cpwer_execution_scaffold_bridge_checklist
python -m src.meeteval_cpwer_execution_handoff
python -m src.meeteval_cpwer_execution_handoff_bridge_checklist
python -m src.meeteval_cpwer_execution_preflight
python -m src.meeteval_cpwer_execution_preflight_bridge_checklist
python -m src.meeteval_cpwer_execution_receipt_scaffold
python -m src.meeteval_cpwer_execution_receipt_scaffold_bridge_checklist
python -m src.meeteval_cpwer_execution_status
python -m src.meeteval_cpwer_execution_status_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_scaffold
python -m src.speaker_profile_embedding_trial_execution_receipt_scaffold
python -m src.speaker_profile_embedding_trial_execution_preflight_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_scaffold_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_status
python -m src.speaker_profile_embedding_trial_execution_status_bridge_checklist
python -m src.external_validation_slice_staging_handoff_receipt_scaffold
python -m src.external_validation_slice_staging_handoff_receipt_scaffold_bridge_checklist
python -m src.external_validation_slice_staging_execution_status
python -m src.external_validation_slice_staging_execution_status_bridge_checklist
python -m src.frontier_execution_queue_status
python -m src.frontier_execution_queue_status_bridge_checklist
python -m src.frontier_execution_queue_completion_summary
python -m src.frontier_execution_queue_completion_summary_bridge_checklist
python -m src.frontier_execution_queue_handoff
python -m src.frontier_execution_queue_handoff_packet
python -m src.frontier_execution_queue_handoff_packet_bridge_checklist
python -m src.frontier_execution_queue_operator_brief
python -m src.frontier_execution_queue_runbook_card
python -m src.frontier_execution_queue_runbook_bridge_checklist
python -m src.frontier_execution_queue_phase_checkpoint_card
python -m src.frontier_execution_queue_phase_checkpoint_bridge_checklist
python -m src.frontier_execution_queue_milestone_card
python -m src.frontier_execution_queue_milestone_bridge_checklist
python -m src.frontier_execution_queue_completion_dashboard
python -m src.frontier_execution_queue_completion_dashboard_bridge_checklist
python -m src.frontier_execution_queue_status_preflight_bridge_checklist
python -m src.frontier_execution_queue_status_reentry_card
python -m src.frontier_execution_queue_status_reentry_bridge_checklist
python -m src.frontier_execution_queue_handoff_bridge_checklist
python -m src.frontier_execution_queue_receipt_open_card
python -m src.frontier_execution_queue_receipt_readiness_board
python -m src.frontier_execution_queue_receipt_readiness_bridge_checklist
python -m src.meeteval_cpwer_execution_receipt_readiness
python -m src.speaker_profile_embedding_trial_execution_receipt_readiness
python -m src.speaker_profile_embedding_trial_execution_receipt_open_card
python -m src.speaker_profile_embedding_trial_execution_receipt_open_card_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_handoff_packet
python -m src.speaker_profile_embedding_trial_execution_receipt_handoff_packet_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_operator_brief
python -m src.speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge
python -m src.speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_runbook_card
python -m src.speaker_profile_embedding_trial_execution_receipt_runbook_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_card
python -m src.speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_milestone_card
python -m src.speaker_profile_embedding_trial_execution_receipt_milestone_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_completion_dashboard
python -m src.speaker_profile_embedding_trial_execution_receipt_completion_dashboard_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_status_preflight_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_status_reentry_card
python -m src.speaker_profile_embedding_trial_execution_receipt_status_reentry_bridge_checklist
python -m src.external_validation_slice_staging_handoff_receipt_readiness
python -m src.frontier_execution_receipt_queue_status
python -m src.meeteval_cpwer_execution_receipt_readiness_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_receipt_readiness_bridge_checklist
python -m src.external_validation_slice_staging_handoff_receipt_readiness_bridge_checklist
python -m src.frontier_execution_receipt_queue_status_bridge_checklist
python -m src.frontier_execution_receipt_queue_completion_summary
python -m src.frontier_execution_receipt_queue_completion_summary_bridge_checklist
python -m src.frontier_execution_receipt_queue_handoff
python -m src.frontier_execution_receipt_queue_handoff_bridge_checklist
python -m src.frontier_execution_receipt_queue_operator_brief
python -m src.frontier_execution_receipt_queue_runbook_card
python -m src.frontier_execution_receipt_queue_runbook_bridge_checklist
python -m src.frontier_execution_receipt_queue_phase_checkpoint_card
python -m src.frontier_execution_receipt_queue_phase_checkpoint_bridge_checklist
python -m src.frontier_execution_receipt_queue_milestone_card
python -m src.frontier_execution_receipt_queue_milestone_bridge_checklist
python -m src.frontier_execution_receipt_queue_completion_dashboard
python -m src.frontier_execution_receipt_queue_completion_dashboard_bridge_checklist
python -m src.frontier_execution_receipt_queue_status_preflight_bridge_checklist
python -m src.frontier_execution_receipt_queue_status_reentry_card
python -m src.frontier_execution_receipt_queue_status_reentry_bridge_checklist
python -m src.frontier_execution_receipt_queue_receipt_open_card
python -m src.frontier_execution_receipt_queue_handoff_packet
python -m src.frontier_execution_receipt_queue_handoff_packet_bridge_checklist
python -m src.frontier_execution_receipt_queue_frontier_bridge
python -m src.frontier_execution_receipt_queue_frontier_bridge_checklist
python -m src.frontier_execution_receipt_queue_receipt_bridge
python -m src.frontier_execution_receipt_queue_receipt_bridge_checklist
python -m src.frontier_execution_receipt_queue_evidence_receipt
python -m src.frontier_execution_receipt_queue_evidence_receipt_bridge_checklist
python -m src.frontier_execution_receipt_queue_execution_receipt_bridge
python -m src.frontier_execution_receipt_queue_execution_receipt_bridge_checklist
python -m src.frontier_execution_receipt_queue_writeback_packet
python -m src.frontier_execution_receipt_queue_writeback_packet_bridge_checklist
python -m src.frontier_execution_receipt_queue_writeback_status
python -m src.frontier_execution_receipt_queue_writeback_handoff
python -m src.frontier_execution_receipt_queue_writeback_handoff_bridge_checklist
python -m src.frontier_execution_receipt_queue_writeback_open_card
python -m src.frontier_execution_receipt_queue_writeback_open_card_bridge_checklist
python -m src.frontier_execution_receipt_queue_writeback_handoff_packet
python -m src.frontier_execution_receipt_queue_writeback_handoff_packet_bridge_checklist
python -m src.frontier_execution_receipt_fill_queue_status
python -m src.frontier_execution_receipt_fill_queue_status_bridge_checklist
python -m src.frontier_execution_receipt_fill_queue_completion_summary
python -m src.frontier_execution_receipt_fill_queue_handoff
python -m src.frontier_execution_receipt_fill_queue_completion_summary_bridge_checklist
python -m src.frontier_execution_receipt_fill_queue_handoff_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_packet
python -m src.frontier_execution_receipt_fill_execution_packet_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_status
python -m src.frontier_execution_receipt_fill_execution_status_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_handoff
python -m src.frontier_execution_receipt_fill_execution_handoff_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_completion_summary
python -m src.frontier_execution_receipt_fill_execution_completion_summary_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_operator_brief
python -m src.frontier_execution_receipt_fill_execution_receipt_bridge
python -m src.frontier_execution_receipt_fill_execution_receipt_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_handoff_packet
python -m src.frontier_execution_receipt_fill_execution_evidence_receipt
python -m src.frontier_execution_receipt_fill_execution_evidence_receipt_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_runbook_card
python -m src.frontier_execution_receipt_fill_execution_completion_dashboard
python -m src.frontier_execution_receipt_fill_execution_milestone_card
python -m src.frontier_execution_receipt_fill_execution_execution_receipt_bridge
python -m src.frontier_execution_receipt_fill_execution_execution_receipt_bridge_checklist
python -m src.frontier_execution_receipt_fill_execution_handoff_packet
python -m src.meeteval_cpwer_official_execution_alignment_audit_bridge_checklist
python -m src.meeteval_cpwer_official_execution_reconciliation_audit_bridge_checklist
python -m src.meeteval_tokenization_adaptation_handoff_packet
python -m src.meeteval_tokenization_gain_frontier_fill_runbook_card
python -m src.meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist
python -m src.meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge
python -m src.meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge_checklist
python -m src.meeteval_tokenization_gain_frontier_fill_operator_brief
python -m src.speaker_profile_embedding_trial_execution_handoff
python -m src.speaker_profile_embedding_trial_execution_handoff_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_preflight
python -m src.external_validation_slice_staging_readiness_handoff_bridge_checklist
python -m src.speaker_profile_embedding_trial_execution_scaffold_bridge_checklist
python -m src.speaker_profile_embedding_trial_handoff
python -m src.speaker_profile_embedding_trial
python -m src.speaker_profile_embedding_trial_handoff_bridge_checklist
python -m src.external_validation_license_confirmation_receipt_bridge_checklist
python -m src.external_validation_slice_manifest
python -m src.external_validation_slice_manifest_bridge_checklist
python -m src.external_validation_slice_staging_readiness
python -m src.external_validation_slice_staging_readiness_bridge_checklist
python -m src.external_validation_slice_staging_readiness_handoff
python -m src.speaker_profile_embedding_scaffold
python -m src.speaker_profile_embedding_scaffold_bridge_checklist
python -m src.llm_critic_review_pass
python -m src.llm_critic_review_pass_bridge_checklist
python -m src.llm_critic_review_pass_advance
python -m src.llm_critic_review_pass_advance_bridge_checklist
python -m src.llm_critic_review_pass_status
python -m src.llm_critic_review_pass_next
python -m src.llm_critic_review_pass_continue
python -m src.llm_critic_review_pass_status_bridge_checklist
python -m src.llm_critic_review_pass_continue_bridge_checklist
python -m src.llm_critic_review_pass_final
python -m src.llm_critic_review_pass_completion_summary
python -m src.llm_critic_review_pass_final_bridge_checklist
python -m src.project_harness
```

## Notes for Future Agents

- Do not use ground-truth CER or reference transcripts as routing input.
- References and CER are for evaluation only.
- Keep gold and synthetic evaluation clearly separated.
- Prefer adding new outputs over overwriting existing benchmark files.
- If a new stage changes the main conclusion, update README and REPORT together.
