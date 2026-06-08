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
- MeetEval tokenization adaptation handoff: `results/figures/meeteval_tokenization_adaptation_handoff.md`

MeetEval compatibility remains the recommended first fill target. Character-spaced official cpWER (`python -m src.meeteval_cpwer_character_level_official_execution --all`) reconciles `5/5` gold cases with bridge-lite. Raw word-level official cpWER drift is diagnosed as a Chinese tokenization artifact, not a speaker-mapping failure.

Speaker profile text-proxy diagnostic is complete at `5/5` swapped bias (`queue_status = queue_complete`). Embedding trial handoff readiness is `handoff_ready` for `NoOverlap`; next step is the execution scaffold — still diagnostic-only, not voiceprint success.

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
