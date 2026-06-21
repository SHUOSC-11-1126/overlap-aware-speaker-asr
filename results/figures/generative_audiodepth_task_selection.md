# Generative AudioDepth Task Selection

Recommended minimum task set: `overlap_plus_regret`.

| combo | utility | map MAE proxy | runtime units |
|---|---:|---:|---:|
| overlap_plus_regret | 0.883675 | 0.246642 | 2 |
| dominance_plus_regret | 0.866715 | 0.295101 | 2 |
| overlap_dominance_regret | 0.860195 | 0.270871 | 3 |
| all_excluding_review_map | 0.849854 | 0.257561 | 4 |
| all_excluding_uncertainty | 0.845195 | 0.270871 | 4 |
| all_five_tasks | 0.834854 | 0.257561 | 5 |
| overlap_only | 0.248675 | 0.246642 | 1 |
| dominance_only | 0.231715 | 0.295101 | 1 |
| overlap_plus_dominance | 0.225195 | 0.270871 | 2 |

Task count is penalized lightly so the selection does not default to all tasks.
