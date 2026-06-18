# Arousal does NOT predict ASR difficulty — a bounding negative result (Findings)

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; references synthetic/silver; arousal = the
offline, reference-free, pre-decode acoustic prosody index from `src/prosody.py`. CER and the
compression-ratio degeneracy signal are post-hoc. No gold tables touched. Outputs in
`results/frontier/arousal_asr_probe/`. Reproduce: `python -m src.arousal_asr_probe --pairs 8`
(8 pairs × overlap {0,0.1,0.3,0.6,0.9} × {mixed, sep1, sep2} = 120 tracks).

## Question

Experiment #1 (the Emotional Separation Tax) asked what separation does *to* emotion. This asks the
other direction: is a track's acoustic **arousal** a reference-free predictor of *where ASR fails* —
and does it add signal **beyond** overlap and the existing compression-ratio degeneracy guard? If yes,
emotion becomes a new routing feature; if no, that bounds emotion's usefulness for ASR routing.

## Result: no predictive signal (kill criterion met)

The arousal index is genuinely informative as a measurement (mean 2.58, std 0.82, range 0.73–3.61
over 120 tracks), so this is a real null, not a degenerate one. Yet:

| relationship | value | reading |
|---|---:|---|
| Pearson(arousal, CER), all tracks | **0.002** | no linear relationship |
| Spearman(arousal, CER), all | −0.086 | no monotone relationship |
| Partial Pearson(arousal, CER \| overlap) | **0.002** | nothing hidden behind overlap |
| mean within-overlap Pearson | −0.134 | sign **flips** across strata (+0.20 at ov0 → −0.50 at ov0.9): inconsistent |
| Pearson(arousal, compression_ratio) | −0.037 | arousal is **orthogonal** to the degeneracy guard |

Arousal is also nearly flat across overlap (mean 2.53–2.64 at every overlap), so it is not even an
overlap proxy. The pre-registered **kill criterion is met**: partial correlation ≈ 0 and arousal does
not duplicate or beat the compression-ratio signal — **acoustic arousal adds no independent
reference-free ASR-routing signal here.**

## On hallucination detection (reported honestly, underpowered)

The grid produced only **1 catastrophic hallucination (CER>1) out of 120** tracks (sep2, ov0.1,
CER 24.25). The compression-ratio signal flagged it loudly (CR 16.3) while arousal was unremarkable
(2.73 ≈ the global mean) — so per-track, the degeneracy signal warned and arousal did not. But an AUC
on a **single** positive is not meaningful, so the headline rests on the correlation result above, not
on the hallucination AUC (arousal 0.41 vs CR 1.0 — recorded in the summary JSON with this caveat).

## Synthesis: the emotion ↔ ASR relationship is asymmetric

Reading experiments #1 and #2 together gives a clean, two-sided picture:

- **Separation strongly affects emotion** (#1): a gain-invariant "emotional separation tax" that
  *diverges* from the ASR decision at low/mid overlap.
- **Emotion does not predict ASR difficulty** (#2): arousal is uncorrelated with CER and orthogonal to
  the degeneracy guard.

So emotion is a **downstream consequence to preserve**, not an **upstream feature for routing**. A
practical system should keep its ASR router on the proven reference-free signals (overlap /
compression-ratio) and treat per-speaker emotion as a separate output recovered from the separated
track — exactly the objective-aware decoupling that #1 motivated. Spending effort to fold arousal into
the ASR router is, on this evidence, not worthwhile.

## Honest limitations

Whisper-`tiny`; synthetic oracle mixtures; arousal-side prosody only (no valence; no human emotion
labels — `arousal_index` is a relative acoustic proxy, not a classifier). n=120 with only 1
hallucination, so the binary-detection comparison is underpowered (stated as such); the robust claim is
the ≈0 correlation (and its stability under partial-correlation control), which n=120 supports. A
different ASR model, real (artifact-laden) separation, or a true SER model could change the picture and
is the natural re-test. Pure statistics (Pearson/Spearman/partial-correlation/AUC) are unit-tested
(12 tests); the acoustic path reuses the gain-invariant `src/prosody.py`. `experimental/frontier`, a
deliberately-reported negative result. Artifacts: `arousal_probe_curve.csv` (120 rows),
`arousal_probe_summary.json`, `arousal_asr_probe.png`.
