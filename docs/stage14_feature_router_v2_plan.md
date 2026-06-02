# Stage 14: Feature-Based Adaptive Router v2

## Motivation

The v1 adaptive router used only `overlap_level`. It worked well on the five verified gold benchmark cases, but the synthetic silver validation exposed a failure mode on `SyntheticNoOverlap`, where v1 incorrectly chose the separated transcript and performed very poorly.

That result suggests the v1 rule is too coarse. It captures the benchmark trend, but it is not robust enough to serve as a general overlap router.

## Objective

Design a v2 router that still avoids using CER as an input feature, but relies on richer observable signals:

- overlap level
- mixed and separated segment counts
- mixed and separated text lengths
- text length ratio
- runtime ratio
- duplicate removal count
- cleaned transcript availability
- cleaned-vs-mixed length closeness

## Router Principle

The v2 router should treat transcript instability as a signal that separated ASR may be hallucinating or inflating output length.

In practice, this means:

- keep separated ASR for strongly overlapping and stable cases;
- prefer mixed ASR when separated output is obviously unstable;
- use cleaned separated output only when it is a better fallback than the raw separated transcript.

## Evaluation Scope

v2 is evaluated on two benchmarks:

1. the five gold verified benchmark cases;
2. the 25-sample synthetic silver benchmark.

The gold benchmark remains the primary result set.
The synthetic benchmark is a stability check, not a gold evaluation.

## Expected Outcome

The goal is not to guarantee a lower score than v1 on every dataset.
The goal is to reduce pathological failures, especially the synthetic NoOverlap case, while keeping the router rule-based and interpretable.
