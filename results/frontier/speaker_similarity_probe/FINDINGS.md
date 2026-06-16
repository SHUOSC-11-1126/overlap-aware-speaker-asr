# Speaker similarity vs separation benefit — Findings

**Label:** `experimental/frontier`. Reuses the 600-condition sweep
(`results/frontier/separation_tax/phase_curve.csv`) + per-snippet MFCC embeddings computed
here. ASR Whisper-tiny; references synthetic/silver; CER is the analysis target only, never
a routing input. No gold tables touched. Reproduce: `python -m src.speaker_similarity_probe`.

## Question

A plausible alternative to the hallucination story: maybe separation helps most when the two
talkers are *acoustically similar* (harder for Whisper to disentangle in the mixture). Test
it by correlating a per-snippet MFCC speaker-embedding distance with each (con × pro) pair's
measured separation benefit (mean ΔCER across overlap ratios).

## Result: not supported — and the apparent signal is a hallucination-tail artifact

| benefit aggregation | Spearman | Pearson |
|---|---:|---:|
| mean ΔCER (tail-sensitive) | +0.09 | **+0.49** |
| median ΔCER (tail-robust) | +0.03 | **+0.08** |
| capped ΔCER (∈[−1,1]) | +0.12 | +0.19 |

Under a tail-sensitive *mean* benefit the correlation looks moderate (Pearson +0.49), which
would suggest "more different talkers → more separation benefit." But that correlation
**collapses to ≈ 0 under the tail-robust median** (+0.08) — so it was driven entirely by a few
pairs whose catastrophic hallucination tail (CER ≫ 1, the Separation Tax finding) inflated
their mean benefit, not by any speaker-similarity relationship.

Two honest caveats make the question only weakly answerable in this corpus anyway:
the debate snippets are **acoustically homogeneous** (within-side cosine 0.973 vs cross-side
0.956 — a structure gap of just 0.017, i.e. con and pro clips are barely distinguishable by a
clip-level MFCC descriptor), the dissimilarity variance is tiny (0.001), and n = 20 pairs.

## What this changes

1. **Rules out** acoustic speaker similarity as a strong driver of the separation decision
   here, which **reinforces the Separation Tax thesis**: the benefit is governed by *whether
   Whisper hallucinates*, not by *who* is speaking.
2. **Methodological caution** for this repo: CER has heavy tails, so report tail-robust
   statistics (median / capped). A mean-based correlation here was misleading by 6× (0.49 vs
   0.08). This applies to any future ΔCER correlation analysis in the project.

## Honest limitations

Coarse clip-level MFCC mean+std descriptor (not a trained speaker embedding); homogeneous
corpus with little speaker structure; n = 20; Whisper-tiny. A stronger test would need a real
speaker-verification embedding and a corpus with known, varied speaker identities. Artifact:
`speaker_similarity_summary.json`.
