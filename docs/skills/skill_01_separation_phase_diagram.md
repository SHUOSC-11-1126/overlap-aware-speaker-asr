# Skill 01: Separation Phase Diagram

## What question does this skill explore?

When does speech separation help, and when does it hurt?

## Why is it relevant to the current project?

The benchmark already shows that separation is helpful in some overlap regimes and harmful in others. This skill turns that observation into a systematic curve over overlap ratio.

## Inputs

- Mixed audio cases with controlled overlap ratio
- Separated speaker-track outputs
- CER results for mixed and separated outputs

## Outputs

- `results/tables/separation_phase_diagram.csv`
- `results/figures/separation_phase_diagram.png`

## What not to do

- Do not replace the gold benchmark.
- Do not treat synthetic silver as gold.
- Do not adjust references just to make the curve look better.

## Success criteria

- The diagram shows a clear delta-CER trend across overlap ratios.
- `delta CER = CER(separated) - CER(mixed)` is interpretable.
- The plot helps explain why routing should be selective.

## Owner suggestion

Research / evaluation owner.
