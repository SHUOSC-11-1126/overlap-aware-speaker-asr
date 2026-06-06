# Cascade Benchmark Readiness

This generated note identifies which cascade artifacts most need controlled hardware/runtime evidence next.

## high priority

| artifact_id | dataset | benchmark_status | readiness_tier | artifact_path | next_evidence_step |
| --- | --- | --- | --- | --- | --- |
| gold_cascade_performance | gold | repo_local_runtime_only | benchmark_surface | results/tables/cascade_performance.csv | Rebuild this artifact after controlled route timing is collected. |
| gold_runtime_audit | gold | repo_local_runtime_only | benchmark_foundation | results/tables/cascade_runtime_audit.csv | Run a controlled same-hardware timing sweep for the selected routes. |
| gold_runtime_normalization | gold | repo_local_runtime_only | benchmark_foundation | results/tables/cascade_runtime_normalization.csv | Run a controlled same-hardware timing sweep for the selected routes. |
| gold_tradeoff_figure | gold | repo_local_runtime_only | benchmark_surface | results/figures/cer_runtime_tradeoff.png | Rebuild this artifact after controlled route timing is collected. |
| synthetic_split_cascade_performance | synthetic_split | repo_local_runtime_only | benchmark_surface | results/tables/synthetic_split_cascade_performance.csv | Rebuild this artifact after controlled route timing is collected. |
| synthetic_split_runtime_audit | synthetic_split | repo_local_runtime_only | benchmark_foundation | results/tables/synthetic_split_cascade_runtime_audit.csv | Run a controlled same-hardware timing sweep for the selected routes. |
| synthetic_split_runtime_normalization | synthetic_split | repo_local_runtime_only | benchmark_foundation | results/tables/synthetic_split_cascade_runtime_normalization.csv | Run a controlled same-hardware timing sweep for the selected routes. |
| synthetic_split_tradeoff_figure | synthetic_split | repo_local_runtime_only | benchmark_surface | results/figures/synthetic_split_cer_runtime_tradeoff.png | Rebuild this artifact after controlled route timing is collected. |

## medium priority

| artifact_id | dataset | benchmark_status | readiness_tier | artifact_path | next_evidence_step |
| --- | --- | --- | --- | --- | --- |
| cross_dataset_benchmark_blocker_matrix | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_blocker_matrix.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_checklist | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_checklist.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_dependency_graph | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_dependency_graph.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_execution_queue | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_execution_queue.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_execution_summary | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_execution_summary.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_handoff_packet | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_handoff_packet.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_manifest_template | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/tables/cascade_benchmark_manifest_template.csv | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_milestone_card | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_milestone_card.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_phase_checkpoint_card | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_phase_checkpoint_card.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_plan | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_plan.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_readiness | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_readiness.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_runbook_card | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_runbook_card.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_session_ledger | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_session_ledger.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_benchmark_status | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_benchmark_status.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_decision_matrix | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/tables/cascade_decision_matrix.csv | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_family_stability | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/tables/cascade_recommendation_family_stability.csv | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_profile_playbook | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_profile_playbook.md | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_recommendation_stability | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/tables/cascade_recommendation_stability.csv | Refresh after gold and synthetic controlled benchmark evidence lands. |
| cross_dataset_robustness_gap | cross_dataset | inherits_repo_local_runtime | downstream_summary | results/tables/cascade_robustness_gap.csv | Refresh after gold and synthetic controlled benchmark evidence lands. |
| gold_cascade_summary | gold | inherits_repo_local_runtime | downstream_summary | results/figures/compute_aware_cascade_summary.md | Refresh after controlled benchmark evidence replaces repository-local timing. |
| gold_frontier_report | gold | inherits_repo_local_runtime | downstream_summary | results/figures/cascade_frontier_report.md | Refresh after controlled benchmark evidence replaces repository-local timing. |
| gold_recommendations | gold | inherits_repo_local_runtime | downstream_summary | results/tables/cascade_recommendations.csv | Refresh after controlled benchmark evidence replaces repository-local timing. |
| synthetic_split_cascade_summary | synthetic_split | inherits_repo_local_runtime | downstream_summary | results/figures/synthetic_split_cascade_summary.md | Refresh after controlled benchmark evidence replaces repository-local timing. |
| synthetic_split_recommendations | synthetic_split | inherits_repo_local_runtime | downstream_summary | results/tables/synthetic_split_cascade_recommendations.csv | Refresh after controlled benchmark evidence replaces repository-local timing. |

## low priority

| artifact_id | dataset | benchmark_status | readiness_tier | artifact_path | next_evidence_step |
| --- | --- | --- | --- | --- | --- |
| gold_pareto | gold | reference_only | registry_support | results/tables/cascade_pareto.csv | Keep as lookup support unless benchmark scope expands. |
| synthetic_split_pareto | synthetic_split | reference_only | registry_support | results/tables/synthetic_split_cascade_pareto.csv | Keep as lookup support unless benchmark scope expands. |

