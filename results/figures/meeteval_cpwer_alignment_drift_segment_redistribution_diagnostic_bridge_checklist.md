# MeetEval cpWER Alignment Drift Segment Redistribution Diagnostic Bridge Checklist

This generated checklist turns the per-speaker redistribution diagnostic into a row-by-row bridge verification path. It remains experimental/frontier coordination only and does not claim cpWER execution.

| checklist_order | case_id | redistribution_mismatch_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | HeavyOverlap | 2 | results/figures/meeteval_cpwer_alignment_drift_segment_redistribution_diagnostic_summary.md | results/figures/meeteval_cpwer_alignment_drift_segment_granularity_diagnostic_handoff_bridge_checklist.md | Verify the redistribution diagnostic bridge for HeavyOverlap before reopening the granularity handoff bridge. | redistribution_mismatch_count=2 with dominant_blocker=SPEAKER_1 hypothesis_merged; confirm per-speaker redistribution drift before advancing the granularity handoff bridge. | Confirm this bridge before opening the cpWER segment granularity diagnostic handoff bridge checklist target. |
