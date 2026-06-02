# Skill 03: Speaker Profile / Voiceprint-assisted Risk Detection

## What question does this skill explore?

Under known-speaker enrollment, can speaker profiles help detect speaker attribution risk?

## Why is it relevant to the current project?

The repository already has speaker snippets and speaker-aware evaluation. This skill explores whether light enrollment can improve attribution confidence without becoming full speaker ID.

## Inputs

- `resources/snippets/con_*.wav`
- `resources/snippets/pro_*.wav`
- Speaker-track outputs

## Outputs

- `results/tables/speaker_profile_similarity.csv`
- `results/figures/speaker_profile_risk_summary.md`

## What not to do

- Do not turn this into general-purpose speaker identification.
- Do not claim open-set robustness.
- Do not replace the core ASR evaluation with profile matching.

## Success criteria

- The profile similarity is useful for risk detection.
- It helps detect speaker swap risk or contaminated separation.
- It remains a lightweight assistance signal.

## Owner suggestion

Speaker analysis / evaluation owner.
