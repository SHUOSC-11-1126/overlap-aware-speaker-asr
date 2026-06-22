# Unified router evaluation on source-disjoint v2

- Evaluation subset: strict source-disjoint test rows with existing real Whisper CER.
- Review rows are scored under an explicit `oracle_for_abstained_rows` handoff assumption and also reported with coverage.

| policy | mean selected CER | covered CER | false-safe | high-error mixed | review rate | coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fixed_mixed | 0.875111 | 0.875111 | 3 | 6 | 0.0 | 1.0 |
| fixed_separated | 0.672207 | 0.672207 | 0 | 0 | 0.0 | 1.0 |
| fixed_cleaned | 0.672207 | 0.672207 | 0 | 0 | 0.0 | 1.0 |
| router_v2_refit | 0.572829 | 0.572829 | 0 | 3 | 0.0 | 1.0 |
| balanced_router_refit | 0.572829 | 0.572829 | 0 | 3 | 0.0 | 1.0 |
| stage29_calibrated_audiodepth_gate_refit | 0.572829 | 0.572829 | 0 | 3 | 0.0 | 1.0 |
| stage30_risk_guarded_gate_refit | 0.572829 | 0.40196 | 0 | 1 | 0.285714 | 0.714286 |
| stage31_stage2_review_guard_refit | 0.572829 | 0.545894 | 0 | 1 | 0.571429 | 0.428571 |
| stage33_regret_regressor_refit | 0.572829 | 0.572829 | 0 | 3 | 0.0 | 1.0 |
| stage33_regret_ranker_refit | 0.572829 | 0.572829 | 0 | 2 | 0.0 | 1.0 |
| stage33_safe_regret_fusion_refit | 0.572829 | 0.545894 | 0 | 1 | 0.571429 | 0.428571 |
| oracle_best | 0.572829 | 0.572829 | 0 | 3 | 0.0 | 1.0 |
