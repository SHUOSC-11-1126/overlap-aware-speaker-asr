# Three-Tier Compute-Aware Cascade — Summary

**Label:** experimental/frontier

## Architecture

| Tier | Name | Trigger | Methods | Cost Range |
|------|------|---------|---------|------------|
| 1 | Cheap | Always (default) | mixed_whisper, separated_whisper | 1.0–2.0 |
| 2 | Stronger | Unstable signals | separated_whisper_cleaned, stronger_model | 2.1–2.5 |
| 3 | Critic | Extreme instability | llm_critic, manual_review | 3.5–4.0 |

## Escalation Logic (Reference-Free)

- **Tier 1 → Tier 2:** text_length_ratio > 2.8 OR duplicates >= 5 OR runtime_ratio > 1.5 OR (overlap >= 3 AND duplicates >= 3)
- **Tier 2 → Tier 3:** >= 2 severe signals (text_length_ratio > 3.5, duplicates >= 12, runtime_ratio > 2.5, overlap >= 4 + duplicates >= 6)

## Tier Distribution

| Metric | Value |
|--------|-------|
| Total cases | 5 |
| Tier 1 (cheap) | 3 (60.0%) |
| Tier 2 (stronger) | 2 (40.0%) |
| Tier 3 (critic) | 0 (0.0%) |
| Strong model calls | 1 |
| Manual/critic flags | 0 |
| Average compute cost | 1.9200 |
| Automatic coverage | 100.0% |

## Per-Case Routing Table

| Case ID | Tier | Route | Cost | Instability | CER |
|---------|------|-------|------|-------------|-----|
| NoOverlap | 1 | separated_whisper | 2.0 | 0.000 | 0.0540 |
| LightOverlap | 2 | separated_whisper_cleaned | 2.1 | 0.337 | 0.3821 |
| MidOverlap | 1 | mixed_whisper | 1.0 | 0.234 | 0.1789 |
| HeavyOverlap | 1 | separated_whisper | 2.0 | 0.000 | 0.1095 |
| OppositeOverlap | 2 | stronger_model | 2.5 | 0.600 | N/A |

## Notes

- All escalation decisions use ONLY reference-free observable signals.
- CER is reserved for post-decision evaluation and is never used as a routing input.
- `stronger_model` represents a hypothetical larger ASR model (e.g., whisper-medium)
  with cost modeled at 2.5× the cheap baseline.
- `llm_critic` and `manual_review` represent escalation gates for the hardest cases.
- This is experimental/frontier evidence — not a deployment recommendation.