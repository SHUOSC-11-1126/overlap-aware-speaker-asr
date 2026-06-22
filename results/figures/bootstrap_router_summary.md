# Bootstrap router uncertainty

- paired bootstrap iterations: `1000`
- paired sample count: `7`

| policy | mean | 95% CI |
| --- | ---: | --- |
| fixed_mixed | 0.876656 | [0.661047, 1.030612] |
| fixed_separated | 0.676441 | [0.366524, 0.904762] |
| fixed_cleaned | 0.674321 | [0.362245, 0.904762] |
| router_v2_refit | 0.574149 | [0.328725, 0.884793] |
| balanced_router_refit | 0.57361 | [0.324446, 0.884793] |
| stage29_calibrated_audiodepth_gate_refit | 0.576584 | [0.318165, 0.882653] |
| stage30_risk_guarded_gate_refit | 0.574018 | [0.305082, 0.884793] |
| stage31_stage2_review_guard_refit | 0.568721 | [0.318165, 0.809524] |
| stage33_regret_regressor_refit | 0.573079 | [0.320166, 0.809524] |
| stage33_regret_ranker_refit | 0.575005 | [0.326585, 0.809524] |
| stage33_safe_regret_fusion_refit | 0.570734 | [0.322306, 0.882653] |
| oracle_best | 0.577353 | [0.316026, 0.884793] |
