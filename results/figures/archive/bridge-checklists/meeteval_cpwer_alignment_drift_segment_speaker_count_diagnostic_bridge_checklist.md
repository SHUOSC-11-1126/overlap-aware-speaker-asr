# MeetEval cpWER Alignment Drift Segment Speaker Count Diagnostic Bridge Checklist

This generated checklist turns the per-speaker count diagnostic into a row-by-row bridge verification path. It remains experimental/frontier coordination only and does not claim cpWER execution.

| checklist_order | case_id | mismatched_speaker_count | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |
| --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | HeavyOverlap | 2 | results/figures/meeteval_cpwer_alignment_drift_segment_speaker_count_diagnostic_summary.md | results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic_bridge_checklist.md | Verify the speaker count diagnostic bridge for HeavyOverlap before reopening the reconciliation diagnostic bridge. | mismatched_speaker_count=2 with dominant_blocker=SPEAKER_1 delta=-1; confirm per-speaker drift before advancing the reconciliation diagnostic bridge. | Confirm this bridge before opening the cpWER segment reconciliation diagnostic bridge checklist target. |
