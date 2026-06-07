# MeetEval cpWER Alignment Drift Segment Granularity Diagnostic Handoff Bridge Checklist

This generated checklist turns the granularity diagnostic handoff into a row-by-row bridge verification path. It remains experimental/frontier coordination only and does not claim cpWER execution.

| checklist_order | case_id | handoff_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | HeavyOverlap | granularity_handoff_ready | results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff.md | results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_bridge_checklist.md | Verify the granularity diagnostic handoff bridge for HeavyOverlap before reopening the redistribution diagnostic bridge. | Granularity handoff remains granularity_handoff_ready with mismatched_speaker_count=1; confirm redistribution diagnostic context before advancing the redistribution bridge. | Confirm this bridge before opening the cpWER segment redistribution diagnostic bridge checklist target. |
