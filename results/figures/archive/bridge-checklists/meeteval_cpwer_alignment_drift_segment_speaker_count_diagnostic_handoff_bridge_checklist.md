# MeetEval cpWER Alignment Drift Segment Speaker Count Diagnostic Handoff Bridge Checklist

This generated checklist turns the speaker count diagnostic handoff into a row-by-row bridge verification path. It remains experimental/frontier coordination only and does not claim cpWER execution.

| checklist_order | case_id | handoff_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | HeavyOverlap | speaker_count_handoff_ready | results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_handoff.md | results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_bridge_checklist.md | Verify the speaker count diagnostic handoff bridge for HeavyOverlap before reopening the timing diagnostic bridge. | Speaker count handoff remains speaker_count_handoff_ready with mismatched_speaker_count=2; confirm timing diagnostic context before advancing the timing bridge. | Confirm this bridge before opening the cpWER segment timing diagnostic bridge checklist target. |
