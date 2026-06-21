# Generative AudioDepth Downstream Summary

First-pass downstream comparison on the source-disjoint test split.

| model | selected CER | oracle gap | route accuracy | false-safe |
|---|---:|---:|---:|---:|
| fixed_mixed | 0.739509 | 0.117901 | 0.777778 | 6 |
| fixed_separated | 0.840462 | 0.218854 | 0.222222 | 0 |
| fixed_cleaned | 0.840462 | 0.218854 | 0.0 | 0 |
| generative_regret_no_cost | 0.671608 | 0.05 | 0.777778 | 4 |
| generative_regret_cost_aware | 0.671608 | 0.05 | 0.777778 | 4 |
| oracle | 0.621608 | 0.0 | 1.0 | 4 |
