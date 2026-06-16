# MeetEval cpWER Official Execution Reconciliation Audit

This generated audit compares character-spaced MeetEval cpWER against bridge-lite after tokenization adaptation. Results remain experimental/frontier and do not constitute a full benchmark claim.

Summary: `5/5` aligned, `0/5` minor drift (delta <= 0.05).

| case_id | character_level_cpwer | cpwer_bridge_lite | reconciliation_delta | reconciliation_status | audit_note |
| --- | ---: | ---: | ---: | --- | --- |
| NoOverlap | 0.053957 | 0.054312 | -0.000355 | aligned | Character-spaced MeetEval cpWER aligns with bridge-lite within tolerance. |
| LightOverlap | 0.135714 | 0.135164 | 0.00055 | aligned | Character-spaced MeetEval cpWER aligns with bridge-lite within tolerance. |
| MidOverlap | 0.168421 | 0.16862 | -0.000199 | aligned | Character-spaced MeetEval cpWER aligns with bridge-lite within tolerance. |
| HeavyOverlap | 0.163121 | 0.162827 | 0.000294 | aligned | Character-spaced MeetEval cpWER aligns with bridge-lite within tolerance. |
| OppositeOverlap | 0.083333 | 0.083193 | 0.00014 | aligned | Character-spaced MeetEval cpWER aligns with bridge-lite within tolerance. |
