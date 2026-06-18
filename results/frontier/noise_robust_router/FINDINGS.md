# Reference-Free Noise-Robust Router — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; Resemblyzer speaker gate; references synthetic/silver; routing signals reference-free (decoder degeneracy of the gated output); CER post-hoc only; no gold tables touched. Issue #814.

Router: take separation+speaker-gate unless the gated output is degenerate (max_compression_ratio > 2.4 or repetition ≥ 5), else fall back to mixed.

## Pooled CER (lower is better)

- always-mixed: 1.2135
- always-(sep+speaker-gate): 1.5308
- **router (this work): 0.7778**
- per-utterance oracle: 0.7381
- regret vs oracle: 0.0397; oracle-gap recovered: 0.9166
- route distribution: {'mixed': 21, 'separate_gate': 249}

## Hypotheses

- **H1 — router beats both fixed strategies:** router 0.7778 vs always-mixed 1.2135 / always-gate 1.5308. Verdict: **SUPPORTED**.
- **H3 — degeneracy tracks the separation tax:** Pearson(compression_ratio, gate−mixed CER) = 0.8244. Verdict: **SUPPORTED** (positive ⇒ high CR predicts the gated arm is worse ⇒ correctly route to mixed).

## CER by overlap (mixed / gate / router / oracle)

| overlap | n | mixed | sep+gate | router | oracle |
|---:|---:|---:|---:|---:|---:|
| 0.0 | 54 | 0.7945 | 2.2855 | 0.7880 | 0.7235 |
| 0.1 | 54 | 0.8161 | 1.4909 | 0.7613 | 0.7237 |
| 0.3 | 54 | 1.0203 | 1.4352 | 0.7703 | 0.7396 |
| 0.6 | 54 | 1.0272 | 1.3821 | 0.7910 | 0.7448 |
| 0.8 | 54 | 2.4095 | 1.0605 | 0.7783 | 0.7589 |

## Honest limitations

Small grid; Whisper-`tiny`; synthetic oracle separation + synthetic white/pink/babble (real babble differs); Resemblyzer speaker gate. The routing signal is the gated output's decoder degeneracy; if additive noise itself inflates compression-ratio, the signal stops tracking the separation tax (the H3 bound). `experimental/frontier`, not a gold result.
