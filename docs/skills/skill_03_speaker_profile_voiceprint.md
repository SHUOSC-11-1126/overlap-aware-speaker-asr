# Skill 03: Speaker Profile / Voiceprint-assisted Risk Detection

## What question does this skill explore?

Under known-speaker enrollment, can speaker profiles help detect speaker attribution risk?

## Why is it relevant to the current project?

The repository already has speaker snippets and speaker-aware evaluation. This skill explores whether light enrollment can improve attribution confidence without becoming full speaker ID.

## Current queue position

Third in the current frontier queue. Use it after the MeetEval and external validation handoffs are clearer, so the risk-signal work stays scoped and easy to compare.

## Challenge level

Level 3: Research Extension

## Minimum viable attempt

- Build simple speaker profiles from the `con` / `pro` snippets
- Measure similarity between profile and transcript-derived segments
- Use that similarity as a risk signal only

## Stretch goal

- Test whether profile similarity can detect contaminated separated tracks
- Compare direct speaker assignment, swapped assignment, and profile-assisted confidence

## Failure is useful if...

- Profiles do not help attribution, but they clarify why speaker swap is not the dominant issue
- The signal is weak, but the boundary between known-speaker and open-set settings becomes clearer
- The work reveals that light enrollment is insufficient for robust identity inference

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
- Do not overstate voiceprint confidence when only a small enrollment set is available.

## Success criteria

- The profile similarity is useful for risk detection.
- It helps detect speaker swap risk or contaminated separation.
- It remains a lightweight assistance signal.

## Suggested agent prompt

Explore known-speaker enrollment as a risk detector, not as a full speaker ID system. Keep the scope narrow, document limits, and report when the idea fails.

## Owner suggestion

Speaker analysis / evaluation owner.
