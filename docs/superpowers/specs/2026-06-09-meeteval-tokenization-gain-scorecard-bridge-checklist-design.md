# MeetEval Tokenization Gain Scorecard Bridge Checklist Design

## Goal

Add one coordination bridge that verifies the tokenization gain scorecard before advancing to the tokenization adaptation completion summary path.

## Why This Increment

The gain scorecard already quantifies per-case raw-to-character cpWER gain and recommends `character_spaced` as the default mode on all five gold cases. The next contributor still needs an explicit verification gate before treating that scorecard as settled evidence for the adaptation completion stack.

## Inputs

- `results/tables/meeteval_cpwer_tokenization_gain_scorecard_summary.json`

## Outputs

- `results/tables/meeteval_cpwer_tokenization_gain_scorecard_bridge_checklist.csv`
- `results/tables/meeteval_cpwer_tokenization_gain_scorecard_bridge_checklist.json`
- `results/figures/meeteval_cpwer_tokenization_gain_scorecard_bridge_checklist.md`

## Rules

- Use `recommended_default_mode`, `adapted_and_aligned_count`, and `case_count` from the scorecard summary.
- Bridge to `results/figures/meeteval_cpwer_tokenization_adaptation_completion_summary.md`.
- Keep all outputs labeled `experimental/frontier`.
