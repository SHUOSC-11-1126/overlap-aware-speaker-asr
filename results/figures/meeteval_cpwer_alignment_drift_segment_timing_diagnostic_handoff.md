# MeetEval cpWER Alignment Drift Segment Timing Diagnostic Handoff

This generated handoff turns the per-speaker timing diagnostic into the next narrow MeetEval frontier step. It does not claim reconciled alignment or cpWER execution.

| handoff_status | case_id | mismatched_speaker_count | dominant_blocker | granularity_diagnostic_target | handoff_goal | expected_evidence | handoff_note |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| timing_handoff_ready | HeavyOverlap | 1 | SPEAKER_1 delta=-2.360s | results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_summary.md | Run a narrow per-speaker segment granularity diagnostic for HeavyOverlap after the timing drift finding. | results/tables/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_receipt.json | experimental/frontier timing handoff only; reconciled alignment and cpWER execution remain pending. |
