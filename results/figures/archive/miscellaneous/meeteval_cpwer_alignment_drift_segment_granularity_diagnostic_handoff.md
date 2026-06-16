# MeetEval cpWER Alignment Drift Segment Granularity Diagnostic Handoff

This generated handoff turns the per-speaker granularity diagnostic into the next narrow MeetEval frontier step. It does not claim reconciled alignment or cpWER execution.

| handoff_status | case_id | mismatched_speaker_count | dominant_blocker | redistribution_diagnostic_target | handoff_goal | expected_evidence | handoff_note |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| granularity_handoff_ready | HeavyOverlap | 1 | SPEAKER_2 delta=-0.173s | results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_summary.md | Run a narrow per-speaker redistribution diagnostic for HeavyOverlap after the granularity drift finding. | results/tables/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_receipt.json | experimental/frontier granularity handoff only; reconciled alignment and cpWER execution remain pending. |
