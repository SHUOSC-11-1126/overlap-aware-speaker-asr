# AudioDepth Model Zoo and Hybrid Routing Exploration

## Research question

Can richer audio-depth models and hybrid audio-text routers better predict when speech separation helps or hurts ASR?

## Motivation

The first AudioDepth MVP used a small CNN and did not beat router_v2. That does not invalidate the direction. It suggests we should test more expressive architectures, class balancing, and hybrid audio/text features before drawing a conclusion.

## Experiment families

- log-mel only models
- depth-augmented spectrogram models
- handcrafted feature models
- hybrid audio-depth + transcript-instability models
- confidence-based cascade with router_v2 fallback

## Why this is more ambitious

This turns AudioDepth from a single prototype into a systematic model zoo and ablation study.

## Minimum viable completion

At least 4 model variants trained and evaluated.

## Stretch goal

A hybrid model or confidence cascade that improves over the pure AudioDepth MVP and approaches router_v2.

## Important caution

Do not claim victory unless routing CER genuinely improves. Weak results are still useful if the ablation explains why.
