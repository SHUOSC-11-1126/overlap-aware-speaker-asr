# Multi-Decode Self-Consistency Voting — Findings

## Label: experimental/frontier (Issue #858)

## Research Question
Does running Whisper N times at different temperatures and measuring inter-decode
agreement produce a reference-free quality signal stronger than compression_ratio?

## Key Results (25 conditions: 5 pairs × 5 overlap ratios, Whisper-tiny, zh)

### RQ1: Signal Quality — CR Wins Decisively

| Signal | Spearman vs CER | Interpretation |
|--------|----------------|----------------|
| Compression Ratio | **0.781** | Strong: higher CR → higher CER |
| Agreement Score | -0.404 | Moderate: higher agreement → lower CER |

**Compression ratio is nearly 2× more informative than inter-decode agreement.**

### RQ2: Hallucination Instability — Hypothesis Rejected

Contrary to the hypothesis, hallucinated outputs are NOT unstable across
temperatures. Whisper-tiny produces nearly identical (but wrong) text at
temperatures 0.0–0.4. The model is *stably bad*, not *unstably bad*.

Mean pairwise inter-decode CER is low (~0.02–0.05) regardless of whether the
output is correct or hallucinated. Agreement tracks decode *determinism*, not
decode *quality*.

### RQ3: Majority Voting — Hurts More Than Helps

| Metric | Value |
|--------|-------|
| Mean greedy CER | 0.455 |
| Mean vote CER | 0.473 |
| Vote improvement | **-0.019** (worse) |
| Samples helped | 4/25 |
| Samples hurt | 8/25 |

Character-level majority voting *amplifies* the dominant (often wrong) decode
rather than correcting it. At temperature 0.1–0.4, the perturbations are too
small to produce meaningfully different errors — they just add noise.

### Per-Overlap-Ratio Breakdown

| Overlap | Greedy CER | Vote CER | Agreement |
|---------|-----------|----------|-----------|
| 0.00 | 0.467 | 0.470 | 0.403 |
| 0.15 | 0.467 | 0.505 | 0.302 |
| 0.35 | 0.467 | 0.498 | 0.314 |
| 0.60 | 0.467 | 0.487 | 0.344 |
| 0.90 | 0.467 | 0.498 | 0.372 |

Interesting: agreement is HIGHEST at overlap=0 (no interference) and overlap=0.9
(full overlap — both tracks carry same content). It's LOWEST in the mid-overlap
regime where the acoustic mixture is most complex.

## Interpretation

**Multi-decode agreement does NOT beat compression_ratio as a reference-free
signal.** The fundamental reason: Whisper-tiny's temperature perturbation is too
weak to break out of hallucination attractors. The model has deep basins of
attraction in its decode space — once it falls into a hallucination pattern,
small temperature changes don't escape it.

This connects to the causal hallucination probe (#855): hallucination is driven
by encoder-decoder decoupling that is *deterministic*, not stochastic. Random
decode perturbation is the wrong axis to probe it.

## What Would Change This Conclusion

- **Larger models** (base/small) may have shallower attraction basins and show
  more temperature sensitivity — worth testing in the Model Scale Analysis (#859)
- **Larger temperature range** (0.6–1.0) might break out of attractors, but also
  produces much noisier output
- **Beam search diversity** (different beam_size, best_of) rather than temperature
  might produce more varied candidates
- **Prompt conditioning** (different initial prompts) rather than decode parameters

## Files

- `decode_curve.csv` — raw per-condition data
- `voting_summary.json` — full analysis
- `vote_by_ratio.csv` — per-overlap-ratio breakdown
- `multi_decode_analysis.png` — visualization
