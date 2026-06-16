# MeetEval Tokenization Gain Scorecard Design

## Goal

Add one small `experimental/frontier` artifact that quantifies how much character-spaced tokenization improves official MeetEval cpWER on the five verified gold cases, and whether the adapted scores stay aligned with the existing bridge-lite evidence.

## Why This Increment

The repository already proves three pieces separately:

- raw official MeetEval cpWER is badly distorted on Chinese text
- tokenization root cause has been diagnosed
- character-spaced official cpWER reconciles with bridge-lite

What is still missing is a single scorecard that answers the practical next-step question: how large is the adaptation gain, and should future contributors default to character-spaced MeetEval for this benchmark family?

## Scope

In scope:

- new generator under `src/`
- focused unit tests under `tests/`
- generated `results/tables/` and `results/figures/` scorecard artifacts
- doc updates that reference the new scorecard

Out of scope:

- changing gold CER tables
- changing router logic
- claiming a full MeetEval benchmark
- adding external data

## Data Inputs

The scorecard should read only existing generated artifacts:

- `results/tables/meeteval_cpwer_official_execution.json`
- `results/tables/meeteval_cpwer_character_level_official_execution.json`
- `results/tables/meeteval_cpwer_bridge.csv`

## Output Shape

Per-case scorecard rows should include:

- `case_id`
- `raw_official_cpwer`
- `character_level_cpwer`
- `cpwer_bridge_lite`
- `raw_to_character_gain`
- `character_to_bridge_delta`
- `adaptation_status`
- `recommendation`

An aggregate summary row should include:

- total case count
- adapted-and-aligned case count
- average raw-to-character gain
- max-gain case
- recommended default mode

## Decision Rules

- `raw_to_character_gain = raw_official_cpwer - character_level_cpwer`
- `character_to_bridge_delta = character_level_cpwer - cpwer_bridge_lite`
- `adaptation_status = adapted_and_aligned` when gain is positive and absolute residual delta is at most `0.01`
- recommendation should explicitly say to default to `character_spaced` for these CJK gold cases when all cases satisfy that rule

## Verification

- unit tests for row-building and summary logic
- run the generator and confirm table + markdown artifacts are written
- run the related MeetEval tests plus the new test file

## Labeling

All new outputs stay `experimental/frontier` and must not be described as full benchmark completion.
