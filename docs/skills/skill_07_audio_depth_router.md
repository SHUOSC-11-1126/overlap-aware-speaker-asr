# AudioDepth-Router: RGB-D Inspired Depth-Augmented Spectrogram Routing

## Research question

Can depth-augmented spectrogram representations help predict when speech separation helps or hurts ASR?

## Motivation

Overlapping speech can be viewed as acoustic occlusion in the time-frequency plane. Inspired by RGB-D image recognition, AudioDepth-Router encodes hidden overlap and speaker/risk structure into additional spectrogram channels.

## Representation

### Deployable mode

- Channel 1: log-mel spectrogram of mixed audio
- Channel 2: energy-based overlap proxy
- Channel 3: spectral flux, uncertainty, or entropy proxy

This mode only uses mixed audio and can be labeled `deployable`.

### Analysis-only mode

- Channel 1: log-mel spectrogram of mixed audio
- Channel 2: overlap activity map estimated from simultaneous `spk1` and `spk2` energy
- Channel 3: speaker dominance map based on the `spk1`/`spk2` energy ratio

This mode depends on separated tracks and must be labeled `analysis_only`.

## Output labels

- `mixed`
- `separated`
- `cleaned`

## Why this is ambitious

This transfers a representation-learning idea from computer vision to multi-speaker ASR routing. Instead of only handcrafting text instability features, it asks whether a model can learn useful route boundaries from depth-augmented time-frequency structure.

This first MVP is now the launch point for a broader model-zoo follow-up in `docs/skills/skill_08_audio_depth_model_zoo.md`.

## Minimum viable attempt

Train a small CNN on the synthetic split and evaluate routing CER with:

```bash
python -m src.build_audio_depth_router_dataset
python -m src.audio_depth_map --sample-limit 20 --mode deployable
python -m src.train_audio_depth_router --mode deployable --epochs 20
python -m src.evaluate_audio_depth_router --mode deployable
```

## Stretch goals

Compare:

- router_v2
- handcrafted logistic regression
- log-mel-only CNN
- depth-augmented CNN
- analysis-only upper bound

## Failure interpretation

If AudioDepth-Router fails, record whether the failure is caused by weak labels, synthetic data mismatch, insufficient training size, poor overlap proxy, local spectrogram pattern not being enough, or the need for text-level instability signals.

Synthetic split evidence remains `synthetic/silver` plus `experimental/frontier`; do not promote it into the stable gold baseline. If the later model zoo beats the MVP, treat that as a frontier improvement, not a reclassification of the original MVP.
