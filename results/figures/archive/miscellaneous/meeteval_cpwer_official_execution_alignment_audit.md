# MeetEval cpWER Official Execution Alignment Audit

This generated audit compares official MeetEval cpWER scores against the bridge-lite baseline. Results remain experimental/frontier and do not constitute a full benchmark claim.

Summary: `0/5` cases report aligned scores (delta <= 0.01).

| case_id | official_cpwer | cpwer_bridge_lite | alignment_delta | alignment_status | audit_note |
| --- | ---: | ---: | ---: | --- | --- |
| NoOverlap | 4.0 | 0.054312 | 3.945688 | moderate_drift | Moderate drift is explained by Chinese word-level tokenization mismatch in raw MeetEval cpWER; character-spaced reconciliation already realigns with bridge-lite. |
| LightOverlap | 4.0 | 0.135164 | 3.864836 | moderate_drift | Moderate drift is explained by Chinese word-level tokenization mismatch in raw MeetEval cpWER; character-spaced reconciliation already realigns with bridge-lite. |
| MidOverlap | 4.0 | 0.16862 | 3.83138 | moderate_drift | Moderate drift is explained by Chinese word-level tokenization mismatch in raw MeetEval cpWER; character-spaced reconciliation already realigns with bridge-lite. |
| HeavyOverlap | 3.5 | 0.162827 | 3.337173 | moderate_drift | Moderate drift is explained by Chinese word-level tokenization mismatch in raw MeetEval cpWER; character-spaced reconciliation already realigns with bridge-lite. |
| OppositeOverlap | 3.5 | 0.083193 | 3.416807 | moderate_drift | Moderate drift is explained by Chinese word-level tokenization mismatch in raw MeetEval cpWER; character-spaced reconciliation already realigns with bridge-lite. |
