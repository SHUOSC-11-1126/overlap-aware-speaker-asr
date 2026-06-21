# Generative AudioDepth Runtime

This first pass benchmarks dependency-light prototypes, not a neural U-Net.

| model | params/prototypes | file bytes | CPU ms | overhead |
|---|---:|---:|---:|---|
| handcrafted_audiodepth_v2 | 0 | 0 | 2.4e-05 | none |
| direct_classifier | 0 | 0 | 0.05512 | none |
| promptable_generator_prototype | 42 | 254 | 0.00399 | nearest_prototype_map_lookup |
| route_regret_model | 42 | 254 | 0.052785 | none |
