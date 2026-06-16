# MeetEval cpWER Alignment Drift Segment Speaker Count Diagnostic Handoff

This generated handoff turns the per-speaker count diagnostic into the next narrow MeetEval frontier step. It does not claim reconciled alignment or cpWER execution.

| handoff_status | case_id | mismatched_speaker_count | dominant_blocker | timing_diagnostic_target | handoff_goal | expected_evidence | handoff_note |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| speaker_count_handoff_ready | HeavyOverlap | 2 | SPEAKER_1 delta=-1 | results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_summary.md | Run a narrow per-speaker timing diagnostic for HeavyOverlap after the segment count drift finding. | results/tables/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_receipt.json | experimental/frontier speaker count handoff only; reconciled alignment and cpWER execution remain pending. |
