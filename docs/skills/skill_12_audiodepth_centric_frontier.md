# AudioDepth-Centric Routing Frontier

## New positioning

AudioDepth is not merely a small router feature. It is a deployable acoustic representation of time-frequency occlusion in overlapping speech.

## Core hypothesis

AudioDepth can capture pre-ASR acoustic occlusion structure that transcript-level instability features cannot see.

## Role in the system

- AudioDepth: Stage-1 acoustic gate
- Whisper-tiny / transcript features: Stage-2 posterior stability checker
- Hybrid router: final route selection
- Review selector: low-confidence safety layer

## What AudioDepth should prove

- distinguish clean/easy mixed regions
- identify likely separation-helpful regions
- flag ambiguous or high-risk regions
- reduce unnecessary text-probe or separation calls
- improve cost-aware routing when used as Stage-1 gate

## What AudioDepth should not overclaim

- not a replacement for text-instability features
- not proof of generalization without real-ASR validation
- not gold evidence unless references are verified

## Current Stage 28 result

- Deployable mixed-only maps: `200` total, with `120` controlled_v2 and `80` controlled_v1.
- Labelled audit samples: `100`.
- Best embedding probe: resnet oracle-route accuracy `0.655172`, macro-F1 `0.618421`.
- Stage-1 gate held-out accuracy: `0.758621`, macro-F1 `0.431525`.
- Gate is conservative: ambiguous/review recall `0.958333`, but easy_mixed and separation_helpful recall are currently `0.0`.
- Two-stage cascade CER on controlled_v2: `0.643520`, matching router_v2 rather than improving it.

Interpretation: AudioDepth v2 already has measurable representation structure, especially for oracle-route and target-family probes, but the current mixed-only handcrafted proxies are too conservative for confident easy_mixed / separation_helpful routing. This is a useful frontier finding: AudioDepth has independent pre-ASR signal, but Stage-1 gate quality likely needs learned overlap detection or stronger deployable channels.

## Calibrated gate follow-up

The next pass separates route-action labels from review/risk flags. This avoids treating every high-CER separated-helpful sample as pure review risk.

- Held-out accuracy: `0.724138`
- Macro-F1: `0.475000`
- easy_mixed recall: `0.400000`
- separation_helpful recall: `0.800000`
- Best controlled_v2 threshold-sweep CER: `0.533160`
- Text-probe reduction at that setting: `0.716667`
- False-safe rate: `0.183333`

This supports the AudioDepth-centric positioning more strongly: deployable AudioDepth can act as a pre-ASR acoustic gate, but it still needs false-safe control before it can be treated as deployment-ready.

## Risk-guarded gate follow-up

The next pass adds a mixed-only risk guard on top of the calibrated gate. It uses uncertainty, overlap, and overlap-uncertainty product proxies from deployable AudioDepth v2 maps to override high-risk mixed fallback decisions.

- Selected confidence threshold: `0.30`
- Selected risk quantile: `0.45`
- Controlled_v2 CER: `0.525160`
- Text-probe reduction: `0.716667`
- False-safe rate: `0.050000`
- Risk-guard overrides: `9`

Interpretation: this is the strongest deployable AudioDepth gate evidence so far. It lowers the calibrated sweep false-safe rate from `0.183333` to `0.050000` while slightly improving CER, but it remains an `experimental/frontier` result because the controlled_v2 references are still `silver_plus_unverified`.
