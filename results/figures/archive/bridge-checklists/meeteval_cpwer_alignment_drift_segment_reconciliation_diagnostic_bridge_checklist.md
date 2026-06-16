# MeetEval cpWER Alignment Drift Segment Reconciliation Diagnostic Bridge Checklist

This generated checklist turns the reconciliation diagnostic into a row-by-row bridge verification path. It remains experimental/frontier coordination only and does not claim cpWER execution.

| checklist_order | case_id | reconciliation_status | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | HeavyOverlap | reconciliation_diagnostic_complete | results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_diagnostic.md | results/figures/meeteval_cpwer_alignment_drift_segment_reconciliation_handoff.md | Verify the reconciliation diagnostic bridge for HeavyOverlap before reopening the reconciliation handoff. | Reconciliation status=reconciliation_diagnostic_complete with speaker_segment_count_match=False; confirm per-speaker drift context before advancing the handoff bridge. | Confirm this bridge before opening the cpWER segment reconciliation handoff target. |
