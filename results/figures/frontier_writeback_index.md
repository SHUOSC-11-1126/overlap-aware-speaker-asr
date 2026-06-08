# Frontier Writeback Index

This generated index isolates the writeback target for each current frontier. It does not claim that any frontier work has already been executed.

| queue_order | frontier_id | entry_artifact | receipt_target | writeback_note | writeback_scope |
| --- | --- | --- | --- | --- | --- |
| 1 | meeteval_compatibility | MeetEval readiness card | results/tables/meeteval_cpwer_bridge_receipt.json | Open results/figures/meeteval_cpwer_bridge_handoff.md first, then write back to results/tables/meeteval_cpwer_bridge_receipt.json. | Coordination-only index; not a claim of completed frontier execution. |
| 2 | external_validation | external sanity-check prioritization card | results/tables/external_validation_slice_receipt.json | Open results/figures/external_validation_prioritization.md first, then write back to results/tables/external_validation_slice_receipt.json. | Coordination-only index; not a claim of completed frontier execution. |
| 3 | speaker_profile | speaker profile triage card | results/tables/speaker_profile_method_receipt.json | Open results/figures/speaker_profile_triage.md first, then write back to results/tables/speaker_profile_method_receipt.json. | Coordination-only index; not a claim of completed frontier execution. |
| 4 | llm_critic | qualitative critic queue | results/tables/llm_critic_review_receipt.json | Open results/figures/llm_critic_review_queue.md first, then write back to results/tables/llm_critic_review_receipt.json. | Coordination-only index; not a claim of completed frontier execution. |
| 5 | demo_excellence | demo-facing storyboard or walkthrough | results/tables/demo_walkthrough_receipt.json | Open results/figures/demo_walkthrough.md first, then write back to results/tables/demo_walkthrough_receipt.json. | Coordination-only index; not a claim of completed frontier execution. |
