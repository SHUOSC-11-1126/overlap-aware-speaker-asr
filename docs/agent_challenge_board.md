# Agent Challenge Board

This board is for future agents that want to do more than preserve the baseline.

## Current Frontier Sequence

Use this order when picking a new breadth-first frontier task:

1. MeetEval compatibility
2. External mini validation
3. Speaker profile / voiceprint-assisted risk detection
4. Agentic LLM critic and repair loop
5. Demo and public-facing GitHub excellence

This sequence is coordination guidance only. It does not claim that any frontier item has been completed.

## Current Coordination Focus

The frontier receipt-fill execution stack now has an operator brief and receipt bridge:

- Entry: `results/figures/frontier_execution_receipt_fill_execution_handoff_packet.md`
- Runbook card: `results/figures/frontier_execution_receipt_fill_execution_runbook_card.md`
- Dashboard: `results/figures/frontier_execution_receipt_fill_execution_completion_dashboard.md`
- Operator brief: `results/figures/frontier_execution_receipt_fill_execution_operator_brief.md`
- Receipt bridge: `results/figures/frontier_execution_receipt_fill_execution_receipt_bridge.md`
- Bridge checklist: `results/figures/frontier_execution_receipt_fill_execution_receipt_bridge_checklist.md`
- Evidence receipt: `results/figures/frontier_execution_receipt_fill_execution_evidence_receipt.md`
- Execution receipt bridge: `results/figures/frontier_execution_receipt_fill_execution_execution_receipt_bridge.md`
- MeetEval preflight batch: `results/figures/meeteval_cpwer_execution_preflight_batch.md`
- MeetEval receipt batch scaffold: `results/figures/meeteval_cpwer_execution_receipt_batch_scaffold.md`
- MeetEval execution status batch: `results/figures/meeteval_cpwer_execution_status_batch.md`
- MeetEval batch completion summary: `results/figures/meeteval_cpwer_execution_status_batch_completion_summary.md`
- MeetEval batch handoff: `results/figures/meeteval_cpwer_execution_status_batch_handoff.md`
- MeetEval official execution: `results/figures/meeteval_cpwer_official_execution.md`
- MeetEval official execution bridge checklist: `results/figures/meeteval_cpwer_official_execution_bridge_checklist.md`
- MeetEval official execution completion summary: `results/figures/meeteval_cpwer_official_execution_completion_summary.md`
- MeetEval official execution alignment audit: `results/figures/meeteval_cpwer_official_execution_alignment_audit.md`
- MeetEval tokenization diagnostic: `results/figures/meeteval_cpwer_official_execution_tokenization_diagnostic.md`
- MeetEval character-level official execution: `results/figures/meeteval_cpwer_character_level_official_execution.md`
- MeetEval reconciliation audit: `results/figures/meeteval_cpwer_official_execution_reconciliation_audit.md`
- MeetEval tokenization adaptation completion summary: `results/figures/meeteval_cpwer_tokenization_adaptation_completion_summary.md`
- MeetEval tokenization adaptation bridge checklist: `results/figures/meeteval_cpwer_tokenization_adaptation_completion_summary_bridge_checklist.md`
- Speaker profile text-proxy diagnostic bridge checklist: `results/figures/speaker_profile_text_proxy_trial_diagnostic_bridge_checklist.md`
- Speaker profile text-proxy completion summary: `results/figures/speaker_profile_text_proxy_trial_diagnostic_completion_summary.md`
- Speaker profile text-proxy completion bridge checklist: `results/figures/speaker_profile_text_proxy_trial_diagnostic_completion_summary_bridge_checklist.md`
- Speaker profile embedding handoff readiness: `results/figures/speaker_profile_embedding_trial_handoff_readiness.md`
- Speaker profile embedding handoff completion summary: `results/figures/speaker_profile_embedding_trial_handoff_completion_summary.md`
- Speaker profile audio proxy trial: `results/figures/speaker_profile_audio_proxy_trial.md`
- Speaker profile audio proxy summary: `results/figures/speaker_profile_audio_proxy_summary.md`
- Speaker profile multi-signal diagnostic: `results/figures/speaker_profile_multisignal_diagnostic.md`
- Speaker profile multi-signal summary: `results/figures/speaker_profile_multisignal_summary.md`
- MeetEval tokenization adaptation handoff: `results/figures/meeteval_tokenization_adaptation_handoff.md`
- MeetEval tokenization handoff completion: `results/figures/meeteval_tokenization_adaptation_handoff_completion_summary.md`
- MeetEval tokenization gain scorecard handoff completion summary: `results/figures/meeteval_cpwer_tokenization_gain_scorecard_handoff_completion_summary.md`
- MeetEval tokenization gain frontier fill runbook card: `results/figures/meeteval_tokenization_gain_frontier_fill_runbook_card.md`
- MeetEval tokenization gain frontier fill runbook bridge checklist: `results/figures/meeteval_tokenization_gain_frontier_fill_runbook_bridge_checklist.md`
- MeetEval tokenization gain frontier fill execution receipt bridge: `results/figures/meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge.md`
- MeetEval tokenization gain frontier fill execution receipt bridge checklist: `results/figures/meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge_checklist.md`
- MeetEval tokenization gain frontier fill operator brief: `results/figures/meeteval_tokenization_gain_frontier_fill_operator_brief.md`
- Speaker profile go-no-go board bridge checklist: `results/figures/speaker_profile_go_no_go_board_bridge_checklist.md`
- Speaker profile scaffold completion: `results/figures/speaker_profile_embedding_trial_execution_scaffold_completion_summary.md`
- Speaker profile preflight readiness: `results/figures/speaker_profile_embedding_trial_execution_preflight_readiness.md`

MeetEval compatibility remains the recommended first fill target. Character-spaced official cpWER (`python -m src.meeteval_cpwer_character_level_official_execution --all`) reconciles `5/5` gold cases with bridge-lite. Tokenization gain handoff completion is `queue_complete`; the tokenization gain frontier fill runbook card, bridge checklist, execution receipt bridge, and operator brief now record the ready receipt-fill path without claiming full benchmark completion.

Speaker profile execution scaffold completion is `queue_complete` for `NoOverlap`; preflight readiness tracks swapped-bias proxy data before any voiceprint execution — still diagnostic-only. The lightweight audio-profile proxy trial reproduces the swapped-bias pattern, but with only a near-tie confidence gap. The new multi-signal diagnostic now makes that boundary explicit: text and audio agree on direction, yet audio remains only `weak_support`, so the next justified move is a narrow embedding baseline rather than any attribution claim.

## Level 1: Documentation / Presentation

- README beautification
- GitHub hero figure
- contribution table
- final slides
- video script

## Level 2: Engineering Demo

- Streamlit demo
- result dashboard
- audio player
- transcript comparison UI
- router decision explanation UI

## Level 3: Research Extension

- separation phase diagram
- compute-aware cascade
- speaker profile
- MeetEval-compatible export
- external mini validation

## Level 4: Agentic Frontier

- local Ollama ASR critic
- multi-agent transcript debate
- self-repairing transcript pipeline
- uncertainty-aware human review
- active learning sample selector
- benchmark generation agent

## Level 5: High-risk / High-reward

- learned router from synthetic split
- stronger ASR model cascade
- integration with diarization model
- voiceprint-assisted diarization correction
- external dataset mini paper replication
- AudioDepth model zoo and hybrid routing exploration
- systematic AudioDepth-Hybrid validation with stress benchmark, bootstrap CI, cost cascade, and case studies

## Task Template

For each challenge, write:

- difficulty
- expected owner
- expected output
- success criteria
- risk
- why it matters

## Board Rule

If a task does not answer a clear research question, it should stay out of the core pipeline and move into a skill card, a demo note, or future work.
