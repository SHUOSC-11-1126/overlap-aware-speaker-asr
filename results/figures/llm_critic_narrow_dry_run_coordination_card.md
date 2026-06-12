# LLM Critic Narrow Dry-Run Coordination Card (qualitative/demo)

Narrow dry-run boundary coordination — not a verified repair completion claim.

| section_id | headline | artifact_anchor | result_label |
| --- | --- | --- | --- |
| review_pass_queue | Qualitative review pass queue dry-run complete on 5/5 gold cases | results/tables/llm_critic_review_pass_status.json | qualitative/demo |
| qualitative_brief_boundary | Light/Mid overlap qualitative brief documents critic hypotheses only | results/figures/llm_critic_qualitative_brief_light_mid.md | qualitative/demo |
| heavyoverlap_prior | HeavyOverlap diagnostic coordination precedes critic narrow dry-run | results/figures/speaker_profile_heavyoverlap_diagnostic_coordination_card.md | experimental/frontier |
| wave12_boundary | Wave12 closure keeps LLM critic dry-run separate from gold baseline CER | results/figures/wave12_exploration_baseline_closure_card.md | experimental/frontier |
| verified_repair_boundary | Narrow dry-run coordination does not upgrade qualitative notes to verified repair | results/figures/llm_critic_go_no_go_summary.md | qualitative/demo |

- **review_pass_queue**: qualitative/demo dry-run only; not verified transcript repair.
- **qualitative_brief_boundary**: Separation-harm hypotheses; does not claim verified correction.
- **heavyoverlap_prior**: Speaker profile diagnostic chain provides case-scope context only.
- **wave12_boundary**: Coordination writeback only; stable gold CER tables unchanged.
- **verified_repair_boundary**: README mentions must keep qualitative/demo labeling.
