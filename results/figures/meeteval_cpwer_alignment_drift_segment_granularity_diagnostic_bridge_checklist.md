# MeetEval cpWER Alignment Drift Segment Granularity Diagnostic Bridge Checklist

This generated checklist turns the per-speaker granularity diagnostic into a row-by-row bridge verification path. It remains experimental/frontier coordination only and does not claim cpWER execution.

| checklist_order | case_id | mismatched_speaker_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | HeavyOverlap | 1 | results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_summary.md | results/figures/meeteval_cpwer_alignment_drift_segment_timing_diagnostic_handoff_bridge_checklist.md | Verify the granularity diagnostic bridge for HeavyOverlap before reopening the timing handoff bridge. | mismatched_speaker_count=1 with dominant_blocker=SPEAKER_2 delta=-0.173s; confirm per-speaker granularity drift before advancing the timing handoff bridge. | Confirm this bridge before opening the cpWER segment timing diagnostic handoff bridge checklist target. |
