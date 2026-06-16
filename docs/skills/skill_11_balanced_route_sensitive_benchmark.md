# Balanced Route-Sensitive Benchmark v2

## Research question

Can we construct a balanced benchmark where mixed, separated, cleaned, and review routes each have realistic winning conditions?

## Motivation

Stage 26 proved route sensitivity but was separation-dominant. A stronger proof requires balanced route winners and explicit review-needed cases.

## Route winner classes

- mixed-win
- separated-win
- cleaned-win
- review-needed / LLM-candidate

## Control factors

- overlap ratio
- speaker dominance ratio
- backchannel duration
- reverberation / distortion proxy
- crosstalk / leakage
- silence-channel hallucination
- route gap

## Success criteria

- oracle route distribution is not dominated by one route
- mixed wins at least 15-25% of evaluated samples
- separated wins at least 30-50%
- cleaned wins at least 10-20%
- review-needed cases are identified rather than forced into a wrong route
- hybrid router improves over router_v2 and fixed separated on route-balanced subsets

## Current Stage 27 result

- Candidate pool: `240`
- Final benchmark: `120`
- Real Whisper evaluated: `60`
- Oracle distribution: mixed `34`, separated `26`, cleaned `0`
- Review-needed candidates: `57`
- Balanced route-winner router CER: `0.502854`
- router_v2 CER: `0.643520`
- Oracle CER: `0.502854`

This pass is more balanced than Stage 26 and proves the balanced router is not blindly separated: it predicts mixed `33` and separated `27`. It does not prove cleaned routing. Cleaned-win anchors did not become real cleaned-oracle cases, so that is a useful negative finding.
