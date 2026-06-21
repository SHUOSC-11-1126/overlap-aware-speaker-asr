# Generative AudioDepth Split Audit

Rows are split by source utterance IDs plus counterfactual family ID, not by individual target-task rows.

## Split Counts

- train: 210 target rows / 42 samples
- validation: 45 target rows / 9 samples
- test: 45 target rows / 9 samples
- unseen_overlap_test: 35 target rows / 7 samples
- unseen_dominance_test: 35 target rows / 7 samples

## Leakage Checks

- source/counterfactual group leakage: none
- exact sample leakage: none

## Target Task Distribution

- train: {'OVERLAP_MAP': 42, 'DOMINANCE_MAP': 42, 'UNCERTAINTY_MAP': 42, 'ROUTE_REGRET': 42, 'REVIEW_RISK': 42}
- validation: {'OVERLAP_MAP': 9, 'DOMINANCE_MAP': 9, 'UNCERTAINTY_MAP': 9, 'ROUTE_REGRET': 9, 'REVIEW_RISK': 9}
- test: {'OVERLAP_MAP': 9, 'DOMINANCE_MAP': 9, 'UNCERTAINTY_MAP': 9, 'ROUTE_REGRET': 9, 'REVIEW_RISK': 9}
