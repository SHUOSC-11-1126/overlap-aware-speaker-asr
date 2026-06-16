# MeetEval cpWER Execution Preflight Bridge Checklist

This generated checklist turns the cpWER execution preflight into a row-by-row bridge verification path. It remains experimental/frontier coordination only and does not claim official cpWER execution.

| checklist_order | case_id | preflight_pass | prerequisite_artifact | receipt_target | checklist_goal | bridge_note | next_gate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | NoOverlap | True | results/figures/meeteval_cpwer_execution_preflight.md | results/tables/meeteval_cpwer_execution_receipt.json | Verify the cpWER execution preflight for NoOverlap before opening the official execution receipt. | Execution preflight reports preflight_pass=True with hypothesis_source=separated_whisper; confirm segment-export readiness before advancing to official cpWER execution. | Confirm this bridge before opening the official MeetEval cpWER execution receipt target. |
