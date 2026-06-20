# Runtime Compute Cascade — Findings

## Label: experimental/frontier (Issue #863)

## Key Result: Cascade Has a Binary Cliff, Not a Smooth Frontier

| Threshold | Escalation % | CER | Gap Recovery |
|-----------|-------------|-----|-------------|
| 0.0–0.5 | 100% | 0.200 | 100% (= base) |
| 0.7 | 80% | 0.222 | **91.7%** |
| 0.8 | 30% | 0.423 | 16.6% |
| 0.9+ | 0% | 0.467 | 0% (= tiny) |

There is NO smooth Pareto frontier — the cascade has a binary cliff between
threshold 0.7 and 0.8. You either escalate almost everything (80%+) or almost
nothing (0%).

### H1 REJECTED ❌
At 30% escalation (closest to 20% target), gap recovery is only 16.6%.
Target was >80%.

### H2 REJECTED ❌
Cascade at 30% escalation (CER 0.423) is WORSE than random 20% escalation
(CER 0.414). CR signal actively misleads on separated audio.

### Compute
- Base is 1.93× slower than tiny
- Runtime data unreliable (fields show 0.0 — timing extraction bug)

## Why: The CR Distribution Is Bimodal

On separated audio, tiny's CR is clustered just below 0.8 (the degenerate
threshold). At threshold 0.7, almost all segments are escalated. At threshold
0.8, almost none are. There's no middle ground because the signal doesn't
differentiate quality among separated segments — they ALL look risky to tiny.

## Implications

1. **CR-based cascade doesn't work for separated audio** — the signal is too
   coarsely distributed to enable fine-grained selection.
2. **A better cascade signal might be needed** — perhaps ensemble disagreement
   (if multiple models are available) or a lightweight classifier trained on
   segment-level features.
3. **In practice: just use base** — at 1.93× compute, the base model eliminates
   the separation tax entirely. The engineering complexity of a cascade isn't
   justified when base is this cheap.
