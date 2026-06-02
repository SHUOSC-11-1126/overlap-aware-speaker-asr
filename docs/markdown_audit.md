# Markdown Audit

This audit classifies the repository's Markdown files by how they should be treated after the Stage 18 refresh.

## Current Files

| file | category | recommended action |
| --- | --- | --- |
| `AGENTS.md` | current | keep as the primary handoff file for future agents |
| `README.md` | current | keep as the top-level entry point |
| `REPORT.md` | current | keep as the paper-style report |
| `docs/README.md` | current | keep as the docs index |
| `docs/markdown_audit.md` | current | keep as the Markdown audit record |
| `docs/project_state.md` | current | keep synchronized with project changes |
| `docs/roadmap.md` | current | keep as the forward-looking roadmap |
| `docs/maintenance_harness.md` | current | keep as the maintenance policy |
| `docs/technical_implementation_plan_v2.md` | current | keep as the current implementation reference |
| `docs/skills/README.md` | current | keep as the skill-card index |
| `docs/skills/skill_01_separation_phase_diagram.md` | current | keep as a future skill card |
| `docs/skills/skill_02_compute_aware_cascade.md` | current | keep as a future skill card |
| `docs/skills/skill_03_speaker_profile_voiceprint.md` | current | keep as a future skill card |
| `docs/skills/skill_04_meeteval_compatibility.md` | current | keep as a future skill card |
| `results/figures/current_results_summary.md` | current | keep as the results summary hub |
| `results/figures/best_method_by_case.md` | current | keep as supporting interpretation |
| `results/figures/cpcer_lite_summary.md` | current | keep as supporting interpretation |
| `results/figures/error_type_summary.md` | current | keep as supporting interpretation |
| `results/figures/project_harness_report.md` | current | keep as a lightweight maintenance report |
| `results/figures/risk_aware_selection_summary.md` | current | keep as supporting interpretation |
| `results/figures/router_ablation_summary.md` | current | keep as supporting interpretation |
| `results/figures/router_ablation_synthetic_split_summary.md` | current | keep as supporting interpretation |
| `results/figures/routing_performance_v2.md` | current | keep as supporting interpretation |
| `results/figures/speaker_cer_summary.md` | current | keep as supporting interpretation |
| `results/figures/synthetic_audit_report.md` | current | keep as supporting interpretation |
| `results/figures/synthetic_routing_summary.md` | current | keep as supporting interpretation |
| `results/figures/synthetic_routing_summary_v2.md` | current | keep as supporting interpretation |
| `results/figures/synthetic_split_routing_summary.md` | current | keep as supporting interpretation |
| `results/error_analysis/LightOverlap_mixed_whisper_error_analysis.md` | current | keep as analysis artifact |
| `results/error_analysis/LightOverlap_separated_whisper_error_analysis.md` | current | keep as analysis artifact |

## Historical Files

| file | category | recommended action |
| --- | --- | --- |
| `docs/technical_implementation_plan.md` | historical | keep for traceability, but do not treat as current direction |
| `docs/stage10_adaptive_router_plan.md` | historical | keep for traceability, but do not treat as current direction |
| `docs/stage13_synthetic_benchmark_plan.md` | historical | keep for traceability, but do not treat as current direction |
| `docs/stage14_feature_router_v2_plan.md` | historical | keep for traceability, but do not treat as current direction |

## Optional Archive Files

| file | category | recommended action |
| --- | --- | --- |
| `docs/contribution.md` | optional archive | either fill it with the final contribution summary or mark it archived |
| `docs/experiment_notes.md` | optional archive | keep if useful for lab notes, otherwise archive |
| `docs/video_script.md` | optional archive | keep if the presentation is still being refined |

## Needs Update / Watch List

| file | issue | recommended action |
| --- | --- | --- |
| `README.md` | must stay synchronized with REPORT and current results | refresh whenever the main conclusion changes |
| `REPORT.md` | must stay synchronized with README and current results | refresh whenever the main conclusion changes |
| `docs/project_state.md` | must stay synchronized with the active project direction | refresh after every major stage |
| `docs/roadmap.md` | should reflect the current next steps, not the old LLM/RAG-first plan | refresh when priorities change |
| `docs/maintenance_harness.md` | should encode the freshness policy and do-not-repeat rules | refresh when project governance changes |

## Audit Notes

- The repository now separates gold, synthetic silver, and held-out synthetic work more clearly than the early plans did.
- Older stage documents are preserved for traceability, but the current direction lives in `AGENTS.md`, `docs/project_state.md`, `docs/roadmap.md`, `docs/README.md`, `README.md`, and `REPORT.md`.
- TODO-style docs should be either completed or explicitly archived so they do not confuse future contributors.
