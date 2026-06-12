# Demo Presentation Polish Card (qualitative/demo)

Presentation writeback only — not a live demo or recording claim.

| section_id | headline | artifact_anchor | result_label |
| --- | --- | --- | --- |
| hero | Overlap-aware speaker ASR: when separation helps and when it hurts | README.md | qualitative/demo |
| architecture | Mixed → separated → cleaned ASR with risk-aware routing | results/figures/frontier_status_checklist.md | qualitative/demo |
| results | Verified gold CER tables and phase/boundary diagnostics | results/tables/cer_results.csv | qualitative/demo |
| frontier_wave3 | External AISHELL-4 sanity-check slice (not gold) | results/figures/external_validation_narrow_audio_eval.md | qualitative/demo |
| frontier_wave4 | Receipt-fill frontier: speaker profile + LLM critic qualitative paths | results/figures/frontier_execution_receipt_fill_execution_status.md | qualitative/demo |
| frontier_wave5 | MeetEval + cascade + separation phase coordination chain | results/figures/separation_phase_coordination_card.md | qualitative/demo |
| frontier_wave6 | Wave6 closure + cascade benchmark timing boundary | results/figures/wave6_frontier_coordination_closure_card.md | qualitative/demo |

- **hero**: Lead with the stable gold baseline finding before any frontier claim.
- **architecture**: Point visitors to the frontier status checklist for module map context.
- **results**: Keep gold and experimental/frontier tables visually separated in any README refresh.
- **frontier_wave3**: Label external validation as external/sanity-check only.
- **frontier_wave4**: Show unified receipt-fill completion without claiming live demo delivery.
- **frontier_wave5**: Show Wave5 coordination cards only; label MeetEval as experimental/frontier and phase diagram as boundary evidence — not deployment proof.
- **frontier_wave6**: Show Wave6 closure and benchmark readiness cards only; controlled timing remains blocked — qualitative/demo labeling required.
