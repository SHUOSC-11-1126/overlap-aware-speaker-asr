# Generative AudioDepth Reliability Split Audit

The split is rebuilt from unique samples and then expanded back to task rows.

| split | samples | task rows | groups | oracle routes | target families |
|---|---:|---:|---:|---|---|
| train | 16 | 80 | 16 | {'mixed': 11, 'separated': 5} | {'mixed_win_anchor': 5, 'separated_win_anchor': 3, 'cleaned_win_anchor': 4, 'review_needed_anchor': 4} |
| validation | 7 | 35 | 7 | {'mixed': 5, 'separated': 2} | {'cleaned_win_anchor': 1, 'mixed_win_anchor': 2, 'separated_win_anchor': 2, 'review_needed_anchor': 2} |
| test | 9 | 45 | 9 | {'separated': 4, 'mixed': 5} | {'separated_win_anchor': 3, 'review_needed_anchor': 3, 'mixed_win_anchor': 2, 'cleaned_win_anchor': 1} |

- source-token connected components: 1
- retained strict source-disjoint samples: 32
- dropped cross-partition samples: 28

## Challenge Splits

- unseen overlap samples: 2
- unseen dominance samples: 3

## Leakage Checks

- source utterance leaks: 0
- source pair leaks: 0
- counterfactual family leaks: 0
- mixed wav leaks: 0

## Teacher Boundary

Source-track teacher maps remain target construction artifacts only. Student/probe inference uses mixed-only metadata or generated summaries.
