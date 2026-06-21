# Generative Safe Fusion Summary

| policy | CER | false-safe | review rate | coverage |
|---|---:|---:|---:|---:|
| F0_stage30_risk_guarded_gate | 0.529082 | 0 | 0.316667 | 0.683333 |
| F1_generative_regret_only | 0.519641 | 0 | 0.777778 | 0.222222 |
| F2_gate_plus_generative_confirmation | 0.519641 | 0 | 0.888889 | 0.111111 |
| F3_generated_review_risk_augmenter | 0.519641 | 0 | 0.777778 | 0.222222 |
| F4_balanced_router_disagreement_guard | 0.519641 | 3 | 0.0 | 1.0 |
| F5_stacked_lightweight_fusion | 0.519641 | 0 | 0.777778 | 0.222222 |

Best Stage 33 fusion by false-safe-first ordering: `F1_generative_regret_only`.

Conclusion: Generative AudioDepth is more suitable as a safety confirmer / review-risk augmenter than as a standalone router under the current data scale.
