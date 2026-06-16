# Reference-free Quality Estimation for Overlap ASR — Findings

**Label:** `experimental/frontier`. A deeper read of the 600 conditions already in
`results/frontier/separation_tax/phase_curve.csv` (no new ASR run) — it extends RQ4 of the
Separation Tax study from binary catastrophe detection to graded CER prediction. Honest
limitation: this reuses the same Whisper-tiny transcripts that produced RQ4, so it is a
richer analysis of that evidence, not an independent replication. CER is the analysis
target only and is never a routing input. Reproduce: `python -m src.reference_free_qe`.

## Question

Can purely reference-free signals — segment compression ratio, n-gram repetition, max
no-speech probability — predict a separated track's *actual CER* (not just the catastrophic
tail)? A graded reference-free CER proxy would enable fine-grained risk-aware routing and
active-learning sample selection.

## Result: these signals are catastrophe *gates*, not graded quality *meters*

Across 600 separated-track samples:

| signal | Spearman vs CER | AUC (CER>0.3) | AUC (CER>0.5) | AUC (CER>1.0) |
|---|---:|---:|---:|---:|
| compression_ratio | −0.20 | 0.48 | 0.47 | **1.00** |
| repetition | +0.17 | 0.51 | 0.51 | **1.00** |
| no_speech_prob | +0.13 | 0.55 | 0.59 | 0.61 |

Compression ratio and repetition flag the **catastrophic** tail (CER>1.0) perfectly
(AUC 1.0), confirming RQ4 — but at moderate thresholds they are **no better than chance**
(AUC ≈ 0.5), and the overall rank correlation with CER is weak and even negative.

The calibration of the strongest signal (compression ratio, 5 equal-count bins) is
**non-monotone — U-shaped**:

| bin | mean compression ratio | mean CER |
|---:|---:|---:|
| 1 | 0.665 | 0.693 |
| 2 | 0.712 | 0.475 |
| 3 | 0.742 | **0.344** |
| 4 | 0.795 | 0.494 |
| 5 | 1.610 | **1.212** |

Both extremes are bad: a *very low* compression ratio means a short/sparse transcript
(the track was mostly silence → content missed → high CER), while a *very high* ratio means
runaway repetition (hallucination → CER ≫ 1). A *healthy* mid ratio (~0.74) has the lowest
CER. So the signal is threshold-shaped, not linear.

## What this changes

This is a useful negative result. It says: **use the reference-free signal as a binary
catastrophe gate (which the trim-and-guard recipe already does correctly), not as a
continuous quality score.** Do not rank utterances by raw compression ratio for
active-learning prioritization — the relationship is U-shaped, so a "distance from the
healthy band" feature (e.g. |compression_ratio − ~0.74|) would be the right next probe.
This validates the guard-threshold design (Separation Tax RQ4–RQ6) over a graded risk score.

## Honest limitations

Whisper-tiny, silver references, oracle separation, one Chinese-debate corpus; reuses RQ4
transcripts (not an independent run); `avg_logprob` was not captured in `phase_curve.csv`
so it is absent here (a worthwhile addition for a future, independent QE run with a
dev/test split). Artifacts: `qe_summary.json`, `qe_signal_table.csv`.
