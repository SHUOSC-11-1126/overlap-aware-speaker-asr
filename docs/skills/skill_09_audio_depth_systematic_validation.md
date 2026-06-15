# Systematic AudioDepth-Hybrid Routing Validation

## Research question

Can a hybrid routing system combining audio-depth features, transcript-instability signals, and confidence cascades provide a more robust decision policy for overlapping-speech ASR?

## Why this matters

The previous MVP showed pure CNN AudioDepth is weak, but model zoo exploration showed that hybrid and handcrafted features can outperform matched router_v2 on synthetic/silver validation. Now the project needs systematic validation and application-oriented proof.

## Hypothesis

A hybrid router will outperform fixed mixed, fixed separated, fixed cleaned, pure audio-depth CNN, and old router_v2 on matched synthetic/silver evaluation. Under controlled synthetic settings it may approach oracle routing.

## Required evidence

- larger synthetic validation
- matched comparison to router_v2
- gold sanity check where available
- per-overlap-tier performance
- confidence calibration
- cost-aware cascade
- explanation examples
- statistical bootstrap confidence intervals

## Success criteria

- clearly improves over the MVP
- ideally improves over matched router_v2 on synthetic/silver
- shows which overlap tiers benefit
- produces interpretable decisions
- does not overclaim gold generalization

## Important caution

Synthetic stress results are not gold. Proxy CER is useful for controlled validation only when real ASR is unavailable, and simulated cost is not hardware timing evidence.

## Real-ASR validation gap analysis

Stage 25 adds the missing audit layer for the Stage 24 boundary finding.

- Stage 23 proxy evidence is strong, but the Stage 24 real-ASR slice did not transfer to a router win.
- Oracle real CER also barely improves, which means the sampled slice may not leave enough room for routing.
- Reference quality is a limitation because the stress references are synthetic/silver rather than gold.
- Conservative CER normalization does not materially lower CER, so the problem is not just punctuation or spacing.
- A robust validation should run reference-quality audit, normalization, Whisper configuration sweep, stratified sample expansion, proxy-to-real gap analysis, and route-gap subset analysis before making any stable-routing claim.

This is scientific exploration, not failure. It shows that system innovation needs a reliable evaluation pipeline, not only a stronger router.
