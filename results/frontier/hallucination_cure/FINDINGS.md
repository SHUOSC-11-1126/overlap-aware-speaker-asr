# Curing separation-induced Whisper hallucination — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny` (offline); references synthetic/silver;
CER post-hoc only, never a routing input. No gold tables touched. 12 speaker pairs × 15
overlap ratios × 2 separated tracks = 360 tracks per cure. Reproduce:
`python -m src.hallucination_cure_eval --pairs 12` (then `--analyze-relative`); a fast probe on
the known-catastrophic tracks is `--smoke`.

## Question (closes Separation Tax RQ3's loose end)

RQ3 showed manual silence-trim cures the catastrophic separated-track hallucination but
temperature fallback does not. RQ3 never tested Whisper's **purpose-built**
`hallucination_silence_threshold` (skip silent periods > N s, requires `word_timestamps=True`)
or beam search. This is a head-to-head of five cures on the separated tracks.

## Result: the catastrophe is a greedy-decoding artifact, curable ≥3 independent ways

| cure | overall mean CER | median | tail rate (CER>1) | mean CER on 5 catastrophic | normal-clip Δ vs greedy |
|---|---:|---:|---:|---:|---:|
| greedy_baseline | 0.766 | 0.467 | 0.014 | 19.84 | (reference) |
| **silence_trim** | **0.464** | 0.456 | 0.000 | 0.54 | **−0.035** |
| halluc_silence (native) | 0.504 | 0.467 | 0.000 | 0.665 | +0.004 |
| halluc_silence_trim | 0.464 | 0.456 | 0.000 | 0.54 | −0.035 |
| beam5 | 0.507 | 0.500 | 0.003 | 0.628 | +0.007 |

Three things, all falsifiable:

1. **Every cure eliminates the catastrophic tail** — greedy's 5 blow-ups (mean CER 19.84,
   peak 24.25) drop to ≈ 0.54–0.67 under all of silence-trim, Whisper's native
   `hallucination_silence_threshold=2.0`, the combination, and even plain `beam_size=5`. The
   tail rate goes 0.014 → 0.000 (trim / native / combined) or 0.003 (beam). So the
   catastrophe is fundamentally a **greedy-decoding artifact**, not intrinsic to the audio —
   multiple unrelated mechanisms fix it.

2. **No cure hurts the non-catastrophic majority** (355/360 groups). The normal-subset CER
   delta vs greedy ranges from −0.035 (trim actually *helps* — tightening leading/trailing
   silence aids Whisper even on non-catastrophic clips) to +0.007 (beam, negligible). So
   these cures are essentially free: they kill the tail without collateral damage.

3. **Why temperature fallback (RQ3) was uniquely useless:** it resamples at higher
   temperature (more randomness) rather than addressing the *silence trigger*. Trim removes
   the silence, the native threshold skips it, and beam search avoids the greedy repetition
   trap — all attack the actual mechanism; temperature fallback does not.

## What this changes

Best deployable cure: **silence-trim the separated tracks** — cheapest, reference-free,
−39% mean CER (0.766 → 0.464), and it helps both the tail and the normal clips. Whisper's
native `hallucination_silence_threshold` (with `word_timestamps=True`) is a near-equal
**zero-preprocessing** alternative (mean 0.504, tail killed, normal-neutral) for pipelines
that prefer a built-in switch over an audio transform. Beam search is a partial fallback.
This supersedes the RQ3 caution "temperature fallback doesn't help" with a positive,
mechanism-grounded recommendation.

## Honest limitations

Whisper-`tiny`, silver references, oracle separation (real separators add their own
artifacts; on the real-separator gold cases the trim must be guard-gated — Separation Tax
RQ6). Only 5 catastrophic groups in this sample (the tail is rare), so tail means are
estimated on few points; `hallucination_silence_threshold` fixed at 2.0 s (threshold
sensitivity unexplored). `word_timestamps=True` adds DTW-alignment overhead. Frontier
evidence, not a gold result. Artifacts: `cure_curve.csv` (1800 rows), `cure_summary.json`,
`cure_relative.csv`, `cure_smoke.csv`.
