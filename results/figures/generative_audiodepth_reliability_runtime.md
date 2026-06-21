# Generative AudioDepth Reliability Runtime

| component | params | file bytes | total overhead ms |
|---|---:|---:|---:|
| stage30_handcrafted_gate | 12 | 6997 | 2e-05 |
| stage32_promptable_generator | 0 | 254 | 0.000668 |
| stage33_regret_ranker | 18 | 360 | 6.3e-05 |
| stage33_safe_fusion | 24 | 0 | 1.6e-05 |
| stage27_balanced_router | 8 | 0 | 2e-05 |

All Stage 33 reliability components are deterministic CPU prototypes; no large model or diffusion generator is used.
