# LLM Critic Qualitative Note

This generated note is qualitative only. It uses structured heuristics to imitate a transcript critic and does not claim verified transcript repair.

## NoOverlap

- Label: `qualitative/demo`
- Risk explanation: The selector reports a medium risk state even without explicit flags, so the current transcript still deserves critic review.
- Candidate repair: Try base separated output is stable enough before treating the current transcript as final.
- Uncertainty note: Profile alignment still prefers swapped, so attribution remains uncertain.

## LightOverlap

- Label: `qualitative/demo`
- Risk explanation: The selector reports a high risk state even without explicit flags, so the current transcript still deserves critic review.
- Candidate repair: Try keep mixed output because separated looks risky before treating the current transcript as final.
- Uncertainty note: Profile alignment still prefers swapped, so attribution remains uncertain.

## MidOverlap

- Label: `qualitative/demo`
- Risk explanation: The selector reports a high risk state even without explicit flags, so the current transcript still deserves critic review.
- Candidate repair: Try keep mixed output because separated looks risky before treating the current transcript as final.
- Uncertainty note: Profile alignment still prefers swapped, so attribution remains uncertain.

## HeavyOverlap

- Label: `qualitative/demo`
- Risk explanation: The selector reports a medium risk state even without explicit flags, so the current transcript still deserves critic review.
- Candidate repair: Try repair separated output with cleaned transcript before treating the current transcript as final.
- Uncertainty note: Profile alignment still prefers swapped, so attribution remains uncertain.

## OppositeOverlap

- Label: `qualitative/demo`
- Risk explanation: The selector reports a medium risk state even without explicit flags, so the current transcript still deserves critic review.
- Candidate repair: Try repair separated output with cleaned transcript before treating the current transcript as final.
- Uncertainty note: Profile alignment still prefers swapped, so attribution remains uncertain.

