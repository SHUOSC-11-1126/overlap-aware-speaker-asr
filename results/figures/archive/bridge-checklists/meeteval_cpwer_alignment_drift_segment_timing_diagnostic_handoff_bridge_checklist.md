# MeetEval cpWER Alignment Drift Segment Timing Diagnostic Handoff Bridge Checklist

This generated checklist turns the timing diagnostic handoff into a row-by-row bridge verification path. It remains experimental/frontier coordination only and does not claim cpWER execution.

| checklist_order | case_id | handoff_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | HeavyOverlap | timing_handoff_ready | results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff.md | results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_bridge_checklist.md | Verify the timing diagnostic handoff bridge for HeavyOverlap before reopening the granularity diagnostic bridge. | Timing handoff remains timing_handoff_ready with mismatched_speaker_count=1; confirm granularity diagnostic context before advancing the granularity bridge. | Confirm this bridge before opening the cpWER segment granularity diagnostic bridge checklist target. |
