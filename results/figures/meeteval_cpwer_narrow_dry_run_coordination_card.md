# MeetEval cpWER Narrow Dry-Run Coordination Card (experimental/frontier)

Narrow dry-run boundary coordination — not an official benchmark completion claim.

| section_id | headline | artifact_anchor | result_label |
| --- | --- | --- | --- |
| character_level_dry_run | Character-spaced cpWER narrow dry-run complete on 5/5 gold cases | results/tables/meeteval_cpwer_character_level_official_execution.json | experimental/frontier |
| receipt_fill_boundary | Execution receipt fill documents per-case character-level cpWER | results/tables/meeteval_cpwer_execution_receipt.json | experimental/frontier |
| tokenization_gain | Tokenization gain scorecard reconciles raw vs character-level cpWER | results/figures/meeteval_cpwer_tokenization_gain_scorecard_summary.md | experimental/frontier |
| wave10_boundary | Wave10 closure keeps MeetEval coordination separate from gold baseline CER | results/figures/wave10_exploration_baseline_closure_card.md | experimental/frontier |

- **character_level_dry_run**: experimental/frontier dry-run only; not an official benchmark claim.
- **receipt_fill_boundary**: Receipt fill complete; official benchmark completion still blocked.
- **tokenization_gain**: Analysis artifact only; does not upgrade to gold evaluation.
- **wave10_boundary**: Coordination writeback only; stable gold CER tables unchanged.
