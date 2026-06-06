# When Should We Separate? Boundary-aware, Compute-aware, Speaker-aware, and Agent-augmented ASR for Overlapping Speech

We study when speech separation helps or hurts multi-speaker ASR, and we build adaptive routing, risk-aware evaluation, and agent-friendly research infrastructure for speaker-attributed transcription.

## What This Project Is

- ASR pipeline optimization
- adaptive routing
- error type analysis
- speaker-aware evaluation
- synthetic robustness validation
- risk-aware selection
- agentic research workspace

## What This Project Is Not

- not training a new ASR model
- not training a new speech separation model
- not claiming synthetic silver results as gold
- not using ground-truth CER as router input

## Main Results

### Gold Benchmark Averages

| strategy | average CER |
| --- | ---: |
| fixed_mixed_whisper | 0.302093 |
| fixed_separated_whisper | 0.191846 |
| fixed_separated_whisper_cleaned | 0.181681 |
| router_v2 | 0.120042 |
| oracle_best | 0.120042 |

### Synthetic Validation

| setting | v1 | v2 | oracle |
| --- | ---: | ---: | ---: |
| original 25 | 0.350902 | 0.167553 | 0.082239 |
| held-out split test | 0.361350 | 0.335326 | 0.115181 |

### Risk-Aware Selector

| strategy | average CER |
| --- | ---: |
| risk_aware_selector | 0.134587 |
| router_v2 | 0.120042 |
| oracle_best | 0.120042 |

### Experimental Compute-aware Cascade

| strategy | average CER | relative cost vs fixed separated |
| --- | ---: | ---: |
| router_v2_costed | 0.120042 | 0.929533 |
| risk_aware_costed | 0.134587 | 0.929533 |
| budget_cascade | 0.134587 | 0.929533 |

This result is labeled `experimental/frontier`. It uses observed runtime fields when available and proxy costs otherwise; CER is used only after each route is fixed.

Current runtime provenance audit result:

- gold cascade strategies: `5/5` observed runtime selections for every reported strategy
- proxy cost is currently a safety fallback, not an active source for the committed gold cascade tables

### Synthetic Split Cascade Validation

| strategy | average CER | relative cost vs fixed separated |
| --- | ---: | ---: |
| router_v2_synthetic_costed | 0.285187 | 0.704888 |
| budget_cascade | 0.367582 | 0.854921 |
| cleaned_preferred_cascade | 0.249877 | 0.945686 |

This result is labeled `synthetic/silver` plus `experimental/frontier`. It extends the cascade analysis onto the held-out synthetic split benchmark without promoting silver evidence into gold claims.

Current runtime provenance audit result:

- synthetic split cascade strategies: `100/100` observed runtime selections on `ALL`, and `50/50` on both `DEV` and `TEST`
- proxy cost remains available for missing-runtime edge cases, but it is not currently driving the committed synthetic split cascade outputs

Current runtime normalization audit result:

- gold `router_v2_costed / risk_aware_costed / budget_cascade`: average selected-route `RTF = 0.080646`
- synthetic split `router_v2_synthetic_costed`: average selected-route `RTF = 0.148342`
- synthetic split `budget_cascade`: average selected-route `RTF = 0.148228`
- this `RTF` is normalized by the selected route's processed audio duration, so separated routes divide by two-stream duration rather than one mixed-stream duration

Current Pareto frontier audit result:

- gold `ALL` frontier: `fixed_mixed_whisper`, `router_v2_costed`
- gold `risk_aware_costed` and `budget_cascade` are dominated by `router_v2_costed`
- synthetic split `ALL` frontier: `fixed_mixed_whisper`, `fixed_separated_whisper_cleaned`, `router_v2_synthetic_costed`, `cleaned_preferred_cascade`
- synthetic split `budget_cascade` is dominated by `router_v2_synthetic_costed`

Current recommendation card result:

- gold `ALL`
  - `accuracy_first`: `router_v2_costed`
  - `cost_first`: `fixed_mixed_whisper`
  - `balanced`: `router_v2_costed`
- synthetic split `ALL`
  - `accuracy_first`: `fixed_separated_whisper_cleaned`
  - `cost_first`: `fixed_mixed_whisper`
  - `balanced`: `router_v2_synthetic_costed`

Current robustness gap result:

- best shared cross-dataset stability: `fixed_separated_whisper_cleaned` with `cer_gap_vs_gold = -0.00266`
- strongest adaptive shared route: `router_v2` with `cer_gap_vs_gold = 0.165145`
- `budget_cascade` degrades more on synthetic split, with `cer_gap_vs_gold = 0.232995`

Current recommendation stability result:

- `cost_first` is fully stable across the audited scopes with `consensus_ratio = 1.0`
- `balanced` has `consensus_ratio = 0.75`, splitting between `router_v2_costed` and `router_v2_synthetic_costed`
- `accuracy_first` also has `consensus_ratio = 0.75`, splitting between `router_v2_costed` and `fixed_separated_whisper_cleaned`

Current family-level recommendation stability result:

- after normalizing `router_v2_costed` and `router_v2_synthetic_costed` into the same family, `balanced` rises to `consensus_ratio = 1.0`
- `cost_first` remains fully stable at `consensus_ratio = 1.0`
- `accuracy_first` still splits between `router_v2` and `fixed_separated_whisper_cleaned`

Current decision matrix result:

- `accuracy_first`: gold points to `router_v2_costed`, synthetic `ALL` points to `fixed_separated_whisper_cleaned`, and the shared robustness rank is `1`
- `balanced`: points to the `router_v2` family with `family_consensus_ratio = 1.0`
- `cost_first`: stays on `fixed_mixed_whisper` with `family_consensus_ratio = 1.0`, but carries the weakest synthetic `ALL` CER among the three profiles

Current frontier report result:

- `results/figures/cascade_frontier_report.md` now consolidates the decision matrix, family stability, and robustness highlights in one generated note

Current artifact index result:

- `results/figures/cascade_artifact_index.md` now acts as the registry for the cascade evidence stack, with per-artifact labels, generator commands, and intended usage notes

Current benchmark readiness result:

- `results/figures/cascade_benchmark_readiness.md` now prioritizes which cascade artifacts should be refreshed first once controlled hardware/runtime evidence replaces the current repo-local timing signals

Current benchmark plan result:

- `results/figures/cascade_benchmark_plan.md` now turns that readiness ordering into a staged handoff plan with dataset scope, command, and refresh targets

Current profile playbook result:

- `results/figures/cascade_profile_playbook.md` now translates `accuracy_first / balanced / cost_first` into a concise deployment-facing guide for when to use each profile

Current benchmark checklist result:

- `results/figures/cascade_benchmark_checklist.md` now records which hardware/runtime metadata and acceptance checks should be captured for each benchmark phase

Current benchmark manifest template result:

- `results/tables/cascade_benchmark_manifest_template.csv` now provides a fill-in template for recording per-phase benchmark session metadata during controlled timing runs

Current benchmark status result:

- `results/figures/cascade_benchmark_status.md` now acts as a phase-by-phase status board that shows which benchmark steps are still template-only and which metadata gaps still block execution

Current benchmark handoff packet result:

- `results/figures/cascade_benchmark_handoff_packet.md` now acts as the single-entry benchmark handoff note across readiness, plan, checklist, manifest template, and status tracking

## Core Findings

- Speech separation is useful, but not universally beneficial.
- `NoOverlap`, `HeavyOverlap`, and `OppositeOverlap` benefit strongly from separated speaker-track ASR.
- `LightOverlap` and `MidOverlap` degradation is mainly caused by insertion and repetition hallucination.
- `cpCER-lite` did not find speaker swap as the dominant error source in the five gold cases.
- Feature-based router v2 is more stable than overlap-only v1 on synthetic validation.
- The risk-aware selector is an explainability and deployability layer, not the best-CER result.
- The repository is now also framed as an open-ended agentic research workspace for ambitious extensions.

## Beyond the Baseline: Open Challenge Directions

- Separation Phase Diagram
- Compute-aware Cascaded Recognition
- Speaker Profile / Voiceprint Risk Detection
- Agentic LLM Transcript Critic
- External Mini Validation
- GitHub Demo Excellence

The stable baseline is complete, but this repository is designed as an open-ended agentic research playground. Future contributors are encouraged to attempt ambitious extensions while keeping gold/silver/experimental results clearly separated.

## How to Reproduce

Run the main evaluation chain:

```powershell
python -m src.evaluate_cer --case all
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

## Figures and Summary Files

- [Current results summary](results/figures/current_results_summary.md)
- [CER by case](results/figures/cer_by_case.png)
- [CER by method average](results/figures/cer_by_method_average.png)
- [Adaptive routing summary](results/figures/best_method_by_case.md)
- [Error type summary](results/figures/error_type_summary.md)
- [Speaker-aware summary](results/figures/speaker_cer_summary.md)
- [cpCER-lite summary](results/figures/cpcer_lite_summary.md)
- [Risk-aware summary](results/figures/risk_aware_selection_summary.md)
- [Compute-aware cascade summary](results/figures/compute_aware_cascade_summary.md)
- [CER/runtime trade-off figure](results/figures/cer_runtime_tradeoff.png)
- [Cascade runtime provenance audit](results/figures/cascade_runtime_audit.md)
- [Cascade runtime normalization audit](results/figures/cascade_runtime_normalization.md)
- [Cascade Pareto frontier audit](results/figures/cascade_pareto.md)
- [Cascade recommendation card](results/figures/cascade_recommendations.md)
- [Cascade robustness gap audit](results/figures/cascade_robustness_gap.md)
- [Cascade recommendation stability audit](results/figures/cascade_recommendation_stability.md)
- [Cascade recommendation family stability audit](results/figures/cascade_recommendation_family_stability.md)
- [Cascade decision matrix](results/figures/cascade_decision_matrix.md)
- [Cascade frontier report](results/figures/cascade_frontier_report.md)
- [Cascade artifact index](results/figures/cascade_artifact_index.md)
- [Cascade benchmark readiness](results/figures/cascade_benchmark_readiness.md)
- [Cascade benchmark plan](results/figures/cascade_benchmark_plan.md)
- [Cascade profile playbook](results/figures/cascade_profile_playbook.md)
- [Cascade benchmark checklist](results/figures/cascade_benchmark_checklist.md)
- [Cascade benchmark status](results/figures/cascade_benchmark_status.md)
- [Cascade benchmark handoff packet](results/figures/cascade_benchmark_handoff_packet.md)
- [Synthetic split cascade summary](results/figures/synthetic_split_cascade_summary.md)
- [Synthetic split cascade trade-off figure](results/figures/synthetic_split_cer_runtime_tradeoff.png)
- [Synthetic split cascade runtime audit](results/figures/synthetic_split_cascade_runtime_audit.md)
- [Synthetic split cascade runtime normalization](results/figures/synthetic_split_cascade_runtime_normalization.md)
- [Synthetic split cascade Pareto audit](results/figures/synthetic_split_cascade_pareto.md)
- [Synthetic split cascade recommendation card](results/figures/synthetic_split_cascade_recommendations.md)
- [Router ablation summary](results/figures/router_ablation_summary.md)
- [Synthetic routing summary](results/figures/synthetic_routing_summary.md)
- [Synthetic split summary](results/figures/synthetic_split_routing_summary.md)

## Repository Structure

- `configs/`: project configuration
- `references/`: verified reference transcripts
- `resources/`: migrated audio inputs, snippets, and synthetic assets
- `src/`: experiment scripts and analysis utilities
- `results/`: generated transcripts, tables, figures, and summaries
- `docs/`: project docs, stage notes, skills, governance, and maintenance guidance
- `chat_upload/`: local-only upload bundles for draft preparation
- `backups/`: local-only backup outputs

## Documentation Map

New contributors should read these files before modifying code:

- [AGENTS.md](AGENTS.md)
- [docs/project_state.md](docs/project_state.md)
- [docs/roadmap.md](docs/roadmap.md)
- [docs/maintenance_harness.md](docs/maintenance_harness.md)
- [docs/README.md](docs/README.md)
- [docs/ambitious_research_agenda.md](docs/ambitious_research_agenda.md)
- [docs/agent_challenge_board.md](docs/agent_challenge_board.md)
- [docs/experiment_proposal_template.md](docs/experiment_proposal_template.md)
- [docs/skills/README.md](docs/skills/README.md)
- [docs/markdown_audit.md](docs/markdown_audit.md)

## Project Maintenance and Future Skills

The skill cards are not model-training prompts. They are challenge cards for future work:

- [Skill 01: Separation Phase Diagram](docs/skills/skill_01_separation_phase_diagram.md)
- [Skill 02: Compute-aware Cascaded Recognition](docs/skills/skill_02_compute_aware_cascade.md)
- [Skill 03: Speaker Profile / Voiceprint-assisted Risk Detection](docs/skills/skill_03_speaker_profile_voiceprint.md)
- [Skill 04: MeetEval / cpWER Compatibility Plan](docs/skills/skill_04_meeteval_compatibility.md)
- [Skill 05: Agentic LLM Transcript Critic](docs/skills/skill_05_agentic_llm_critic.md)
- [Skill 06: GitHub Demo Excellence](docs/skills/skill_06_github_demo_excellence.md)

Additional maintenance docs:

- [Contribution records](docs/contributions/)
- [Handoff notes](docs/handoff/)
- [Backup plan](docs/backup_plan.md)

If you are continuing the project, read the docs above first, then inspect the current results, and only then decide whether a new experiment is justified.

## Notes

- The repository keeps verified references for all five benchmark cases.
- `LLM` and `RAG` are future extensions rather than the core quantitative path.
- The current research focus is adaptive routing, error analysis, speaker-aware evaluation, stability checking, and ambitious frontier exploration.
