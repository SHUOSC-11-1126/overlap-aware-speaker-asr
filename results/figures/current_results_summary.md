# Current Results Summary

## Core Findings

- Separated speaker-track ASR is the best method on NoOverlap, HeavyOverlap, and OppositeOverlap.
- Mixed ASR remains the best method on LightOverlap and MidOverlap.
- Duplicate suppression improves the separated transcript on LightOverlap and MidOverlap, but does not overtake mixed ASR there.
- Oracle routing across the verified cases gives the lowest average CER among the three fixed pipelines.

## Average CER

- Mixed average: 0.302093
- Separated average: 0.191846
- Cleaned average: 0.181681
- Adaptive best average: 0.120042

## Best Method By Case

| case_id | best_method | best_cer |
| --- | --- | ---: |
| HeavyOverlap | separated_whisper | 0.109489 |
| LightOverlap | mixed_whisper | 0.210714 |
| MidOverlap | mixed_whisper | 0.178947 |
| NoOverlap | separated_whisper | 0.053957 |
| OppositeOverlap | separated_whisper | 0.047101 |