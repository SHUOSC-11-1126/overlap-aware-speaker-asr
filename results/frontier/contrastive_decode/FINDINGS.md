# Contrastive Decoding — Findings

## Label: experimental/frontier (Issue #857)

## Research Question
Can proactive contrastive decoding (greedy vs temperature-fallback comparison)
suppress separation-induced hallucinations during decode?

## Key Results (25 conditions: 5 pairs × 5 overlap ratios, Whisper-tiny, zh)

### RQ1: Divergence as Detection Signal — CONFIRMED ✅

| Condition | Mean CER |
|-----------|----------|
| Divergent (div > 0.1) | 0.517 |
| Agreeing (div ≤ 0.1) | 0.413 |

AUC for detecting CER > 0.5 using greedy-fallback divergence: **0.765** (decent).
Divergence IS a valid quality signal — when greedy and fallback disagree, the
output is more likely to be poor.

### RQ2: Hybrid Correction — REJECTED ❌

| Method | Mean CER | Samples helped | Samples hurt |
|--------|----------|---------------|-------------|
| Greedy | 0.467 | — | — |
| Fallback | 0.547 | — | — |
| Hybrid | 0.543 | 1/25 | 10/25 |

**The hybrid is 0.076 CER worse than pure greedy.** Whisper's fallback does NOT
correct hallucinations — it introduces different (often worse) errors.

### RQ3: Divergence by Overlap — MIXED

| Overlap | Divergence Rate | Greedy CER | Fallback CER |
|---------|----------------|-----------|-------------|
| 0.00 | 60% | 0.467 | 0.576 (worse) |
| 0.15 | 40% | 0.467 | 0.508 (worse) |
| 0.35 | 60% | 0.467 | 0.466 (**better**) |
| 0.60 | 60% | 0.467 | 0.595 (worse) |
| 0.90 | 40% | 0.467 | 0.590 (worse) |

Fallback is only better at overlap=0.35 — the one condition where separation
helps (the phase boundary). Everywhere else, fallback degrades.

### Signal Divergence (from existing phase_curve, 300 rows, no new ASR)

At low overlap (0.0–0.15), greedy CR is 1.5–3.0 vs fallback CR of 0.8 — massive
signal divergence confirming the hallucination mechanism. At mid-high overlap
(0.2–0.9), CR divergence is near zero (<0.04) — fallback and greedy converge.

## Interpretation

**Contrastive decoding with temperature perturbation is the wrong axis for
Whisper-tiny hallucination suppression.** The model's hallucination attractors
are deterministic (encoder-decoder decoupling, as shown in #855) — temperature
changes cannot escape them. When fallback fires, it produces different text, but
not BETTER text.

This extends the #855 causal hallucination finding: not only is hallucination
deterministic, but the "anti-hallucination" mechanism (temperature fallback) is
also insufficient to cure it for separated audio.

## What Would Change This Conclusion

- **Contrastive decoding between MIXED and SEPARATED outputs** (not greedy vs
  fallback) — using the mixed transcript as a semantic prior to validate the
  separated transcript. This is a different research direction.
- **Larger models** where the hallucination basins may be shallower
- **Logit-level manipulation** (subtracting mixed-prior logits) — requires
  lower-level Whisper API access than `model.transcribe()` provides

## Files
- `contrastive_curve.csv` — raw per-condition data
- `contrastive_summary.json` — full analysis
- `divergence_by_ratio.csv` — per-overlap breakdown
- `signal_divergence_summary.json` — analysis from existing phase_curve (no ASR)
- `contrastive_analysis.png` — visualization
