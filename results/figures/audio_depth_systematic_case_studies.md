# AudioDepth Systematic Case Studies

## SyntheticHeavyOverlap_test_01 (low_confidence)
- tier: `SyntheticHeavyOverlap`, overlap_ratio: `0.7`
- router_v2 route/CER: `mixed` / `0.342857`
- hybrid route/CER/confidence: `separated` / `2.742857` / `0.446506`
- oracle route: `mixed`
- explanation: separated favored because overlap_ratio=0.70 suggests separation can reduce occlusion; confidence=0.45

## SyntheticHeavyOverlap_test_02 (low_confidence)
- tier: `SyntheticHeavyOverlap`, overlap_ratio: `0.7`
- router_v2 route/CER: `separated` / `0.76`
- hybrid route/CER/confidence: `separated` / `0.76` / `0.353394`
- oracle route: `mixed`
- explanation: separated favored because overlap_ratio=0.70 suggests separation can reduce occlusion; confidence=0.35
