# Generative AudioDepth Ablation

This first pass compares dependency-light baselines. It is not yet a neural U-Net result.

| ablation | route accuracy | selected CER | regret MAE | map MAE | interpretation |
|---|---:|---:|---:|---:|---|
| logmel_direct_classifier | 0.777778 | 0.671608 |  |  | first-pass deterministic baseline |
| multitask_direct_model | 0.777778 | 0.671608 | 0.077426 |  | first-pass deterministic baseline |
| map_generation_unconditioned |  |  |  | 0.246685 | first-pass deterministic baseline |
| promptable_map_generator |  |  |  | 0.241263 | first-pass deterministic baseline |
| generative_regret_no_cost | 0.777778 | 0.671608 | 0.077426 |  | route-regret selection policy |
| generative_regret_cost_aware | 0.777778 | 0.671608 | 0.077426 |  | route-regret selection policy |
