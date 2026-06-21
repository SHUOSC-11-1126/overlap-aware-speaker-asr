# Generative AudioDepth Reliability Information Value

A single nearest-neighbor probe is used across all inputs to avoid capacity differences.

- generated maps vs shuffled maps on review-risk: 1.000000 vs 0.555556
- logmel + generated maps vs logmel only on review-risk: 1.000000 vs 1.000000
- generated maps vs shuffled maps on route-gap buckets: 1.000000 vs 0.555556
- logmel + generated maps vs logmel only on route-gap buckets: 1.000000 vs 0.888889
- teacher-map upper bound vs generated maps on review-risk: 0.444444 vs 1.000000

## Interpretation

Generated map summaries provide measurable weak information for at least one safety or generalization-facing probe.

The current probe should be read as a reliability screen, not as a final model comparison.
