# Cascade Artifact Index

This generated index lists the current compute-aware cascade artifacts, labels, and intended entrypoints.

## cross_dataset

| artifact_id | label | artifact_group | artifact_path | generator_command | intended_use |
| --- | --- | --- | --- | --- | --- |
| cross_dataset_family_stability | experimental/frontier | audit | results/tables/cascade_recommendation_family_stability.csv | python -m src.compute_aware_cascade --dataset synthetic_split | Family-level recommendation stability across gold and synthetic scopes. |
| cross_dataset_recommendation_stability | experimental/frontier | audit | results/tables/cascade_recommendation_stability.csv | python -m src.compute_aware_cascade --dataset synthetic_split | Raw strategy recommendation stability across gold and synthetic scopes. |
| cross_dataset_robustness_gap | experimental/frontier | audit | results/tables/cascade_robustness_gap.csv | python -m src.compute_aware_cascade --dataset synthetic_split | Gold versus synthetic split robustness gap table for shared strategy families. |
| cross_dataset_benchmark_plan | experimental/frontier | report | results/figures/cascade_benchmark_plan.md | python -m src.compute_aware_cascade --dataset synthetic_split | Staged benchmark handoff plan derived from the readiness scaffold. |
| cross_dataset_benchmark_readiness | experimental/frontier | report | results/figures/cascade_benchmark_readiness.md | python -m src.compute_aware_cascade --dataset synthetic_split | Priority-ordered readiness scaffold for replacing repository-local timing with controlled benchmark evidence. |
| cross_dataset_decision_matrix | experimental/frontier | report | results/tables/cascade_decision_matrix.csv | python -m src.compute_aware_cascade --dataset synthetic_split | Deployment-facing matrix that merges recommendation and robustness evidence. |

## gold

| artifact_id | label | artifact_group | artifact_path | generator_command | intended_use |
| --- | --- | --- | --- | --- | --- |
| gold_pareto | experimental/frontier | audit | results/tables/cascade_pareto.csv | python -m src.compute_aware_cascade | CER/compute Pareto frontier audit for gold strategies. |
| gold_runtime_audit | experimental/frontier | audit | results/tables/cascade_runtime_audit.csv | python -m src.compute_aware_cascade | Observed-runtime versus proxy-runtime provenance audit for gold selections. |
| gold_runtime_normalization | experimental/frontier | audit | results/tables/cascade_runtime_normalization.csv | python -m src.compute_aware_cascade | Selected-route runtime normalization and RTF audit for gold strategies. |
| gold_tradeoff_figure | experimental/frontier | figure | results/figures/cer_runtime_tradeoff.png | python -m src.compute_aware_cascade | CER versus compute scatter plot for gold strategies. |
| gold_cascade_performance | experimental/frontier | performance | results/tables/cascade_performance.csv | python -m src.compute_aware_cascade | Primary gold compute-aware performance table. |
| gold_recommendations | experimental/frontier | recommendation | results/tables/cascade_recommendations.csv | python -m src.compute_aware_cascade | Deployment-profile recommendation card for gold strategies. |
| gold_frontier_report | experimental/frontier | report | results/figures/cascade_frontier_report.md | python -m src.compute_aware_cascade --dataset synthetic_split | Single-entry frontier report that consolidates the current cascade evidence stack. |
| gold_cascade_summary | experimental/frontier | summary | results/figures/compute_aware_cascade_summary.md | python -m src.compute_aware_cascade | Narrative summary of the gold cascade trade-off table. |

## synthetic_split

| artifact_id | label | artifact_group | artifact_path | generator_command | intended_use |
| --- | --- | --- | --- | --- | --- |
| synthetic_split_pareto | synthetic/silver | audit | results/tables/synthetic_split_cascade_pareto.csv | python -m src.compute_aware_cascade --dataset synthetic_split | CER/compute Pareto frontier audit for synthetic split strategies. |
| synthetic_split_runtime_audit | synthetic/silver | audit | results/tables/synthetic_split_cascade_runtime_audit.csv | python -m src.compute_aware_cascade --dataset synthetic_split | Observed-runtime versus proxy-runtime provenance audit for synthetic split selections. |
| synthetic_split_runtime_normalization | synthetic/silver | audit | results/tables/synthetic_split_cascade_runtime_normalization.csv | python -m src.compute_aware_cascade --dataset synthetic_split | Selected-route runtime normalization and RTF audit for synthetic split strategies. |
| synthetic_split_tradeoff_figure | synthetic/silver | figure | results/figures/synthetic_split_cer_runtime_tradeoff.png | python -m src.compute_aware_cascade --dataset synthetic_split | CER versus compute scatter plot for synthetic split strategies. |
| synthetic_split_cascade_performance | synthetic/silver | performance | results/tables/synthetic_split_cascade_performance.csv | python -m src.compute_aware_cascade --dataset synthetic_split | Held-out synthetic split cascade performance table. |
| synthetic_split_recommendations | synthetic/silver | recommendation | results/tables/synthetic_split_cascade_recommendations.csv | python -m src.compute_aware_cascade --dataset synthetic_split | Deployment-profile recommendation card for synthetic split strategies. |
| synthetic_split_cascade_summary | synthetic/silver | summary | results/figures/synthetic_split_cascade_summary.md | python -m src.compute_aware_cascade --dataset synthetic_split | Narrative summary of synthetic split cascade trade-offs. |

