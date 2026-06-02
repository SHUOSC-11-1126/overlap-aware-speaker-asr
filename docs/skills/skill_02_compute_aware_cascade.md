# Skill 02: Compute-aware Cascaded Recognition

## What question does this skill explore?

When should the system spend more compute?

## Why is it relevant to the current project?

The current pipeline already has cheap and more expensive paths. This skill frames the problem as an accuracy-cost trade-off rather than a single best model chase.

## Inputs

- Router outputs
- Runtime measurements
- CER results
- Risk-aware selection outputs

## Outputs

- `results/tables/cascade_performance.csv`
- `results/figures/cer_runtime_tradeoff.png`

## What not to do

- Do not assume the largest model is always the answer.
- Do not use test CER to tune a cascade rule.
- Do not add a new heavy ASR model without a clear need.

## Success criteria

- The cascade shows a measurable accuracy/runtime trade-off.
- The proposal can be explained in one page.
- Manual review is used only when needed.

## Owner suggestion

Systems / deployment owner.
