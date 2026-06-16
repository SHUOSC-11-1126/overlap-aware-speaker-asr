# MeetEval cpWER Execution Preflight Receipt

This receipt records the execution preflight writeback. It does not claim cpWER execution.

| execution_status | run_scope | case_id | hypothesis_source | preflight_pass | expected_inputs | expected_outputs | writeback_note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| preflight_complete | single_case_cpwer_execution_preflight | NoOverlap | separated_whisper | True | results/tables/meeteval_reference_segments.jsonl; results/tables/meeteval_hypothesis_segments.jsonl | Official cpWER score receipt for one verified gold case. | Execution preflight documented; official MeetEval cpWER evaluation remains pending. |
