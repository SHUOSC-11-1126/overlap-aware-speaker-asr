# Results Index

This file is the curated map for result summaries. It separates reviewer-facing
results from generated historical records.

## Recommended Reading Order

1. [Current results summary](../results/figures/curated/current_results_summary.md)
2. [Adaptive routing summary](../results/figures/curated/best_method_by_case.md)
3. [Risk-aware selector summary](../results/figures/curated/risk_aware_selection_summary.md)
4. [Compute-aware cascade summary](../results/figures/curated/compute_aware_cascade_summary.md)
5. [Mode B cascade tiers summary](../results/figures/curated/cascade_tiers_summary.md)
6. Historical records under `results/figures/archive/`, only when traceability is needed

## Core Summaries

| File | Purpose | Evidence Type | Priority |
|---|---|---|---|
| `results/figures/curated/current_results_summary.md` | Main result overview | gold + synthetic/silver labels | High |
| `results/figures/curated/best_method_by_case.md` | Adaptive routing by case | gold | High |
| `results/figures/curated/error_type_summary.md` | Error mode interpretation | gold | High |
| `results/figures/curated/speaker_cer_summary.md` | Speaker-aware CER | gold | High |
| `results/figures/curated/cpcer_lite_summary.md` | Permutation-aware speaker check | gold | High |

## Router and Cascade Summaries

| File | Purpose | Evidence Type | Priority |
|---|---|---|---|
| `results/figures/curated/risk_aware_selection_summary.md` | Risk-aware selector behavior | gold | High |
| `results/figures/curated/compute_aware_cascade_summary.md` | Cost-aware cascade | experimental/frontier | High |
| `results/figures/curated/cascade_tiers_summary.md` | Mode B tiered cascade | experimental/frontier | High |
| `results/figures/curated/cascade_tiers_comparison_summary.md` | Mode B strategy comparison | experimental/frontier | Medium |
| `results/figures/curated/cascade_pareto.md` | Pareto audit | experimental/frontier | Medium |
| `results/figures/curated/cascade_recommendations.md` | Cascade recommendation card | experimental/frontier | Medium |
| `results/figures/curated/cascade_decision_matrix.md` | Cascade decision matrix | experimental/frontier | Medium |

## Silver / Synthetic Summaries

| File | Purpose | Evidence Type | Priority |
|---|---|---|---|
| `results/figures/curated/synthetic_routing_summary.md` | Synthetic routing behavior | synthetic/silver | High |
| `results/figures/curated/synthetic_split_routing_summary.md` | Held-out split routing | synthetic/silver | High |
| `results/figures/curated/synthetic_split_cascade_summary.md` | Synthetic split cascade | synthetic/silver + experimental/frontier | Medium |

## Optional Frontier Summaries

| File | Purpose | Evidence Type | Priority |
|---|---|---|---|
| `results/figures/curated/meeteval_compatibility_note.md` | MeetEval compatibility note | optional/frontier | Medium |
| `results/figures/curated/meeteval_readiness.md` | MeetEval readiness | optional/frontier | Medium |
| `results/figures/curated/speaker_profile_audio_proxy_summary.md` | Speaker-profile proxy summary | frontier scaffold | Medium |

## Frontier Research Notes

| File | Purpose | Treat As |
|---|---|---|
| `docs/frontier/audio-depth-router.md` | AudioDepth router merge strategy and claim boundary | Frontier Branch Only / Exploratory Research; not a final result claim |
| `docs/frontier/agentic_research_entropy.md` | Meta-analysis of substance-vs-ceremony collapse in this workspace (`results/entropy_audit/`) | experimental/frontier (analysis-only); not an ASR result |

## Historical Archive

Generated records have been moved to:

| Category | Location | Treat As |
|---|---|---|
| Wave records | `results/figures/archive/waves/` | Historical trace |
| Receipts | `results/figures/archive/receipts/` | Execution trace |
| Writebacks | `results/figures/archive/writebacks/` | Agent writeback trace |
| Bridge checklists | `results/figures/archive/bridge-checklists/` | Automation/checklist trace |
| Demo presentation records | `results/figures/archive/demo-presentations/` | Demo history |
| Miscellaneous generated coordination records | `results/figures/archive/miscellaneous/` | Historical coordination |

## What Not To Treat As Final Claims

- Coordination targets
- Receipts
- Writebacks
- Bridge checklists
- Frontier queues
- AudioDepth exploratory branch notes before separate review
- Demo presentation writebacks
- Synthetic/silver validation when discussing gold benchmark results

## Archive Policy

Historical records are not deleted. They are moved out of the main reading path,
indexed here, and tracked in [readability-cleanup-manifest.md](readability-cleanup-manifest.md)
and [readability-cleanup-moved-files.tsv](readability-cleanup-moved-files.tsv).
