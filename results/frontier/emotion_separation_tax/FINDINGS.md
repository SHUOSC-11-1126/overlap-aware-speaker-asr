# The Emotional Separation Tax: separation helps emotion but hurts ASR at low/mid overlap — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; references synthetic/silver (clean-source
prosody + con/pro snippet text); emotion = offline acoustic PROSODY (arousal), no SER model, no
emotion labels. CER and prosody distance are post-hoc only. No gold tables touched. Outputs in
`results/frontier/emotion_separation_tax/`. Reproduce: `python -m src.emotion_separation_tax --pairs 8`
(prosody phase diagram) and `python -m src.emotion_separation_tax --crosslink --crosslink-alpha 0.0`
(and `--crosslink-alpha 0.15`) for the ASR×emotion cross-link; `--figure` renders both plots.

## Question

The project's signature result is an *ASR* separation tax: separating overlapping speakers helps
Whisper at high overlap but **hurts** at low/mid overlap (insertion/repetition hallucination). This
study asks the same "when should we separate?" question for each speaker's **emotion**: does
separating help or hurt recovery of their emotional prosody — and does emotion want the *same*
separate-or-not decision as ASR?

Offline, with no SER model and no emotion labels, emotion is operationalized as **gain-invariant
acoustic prosody** (`src/prosody.py`): pitch height/range, energy *dynamics* in dB, spectral shape,
voicing. The reference is the **clean source's own prosody** (label-free ground truth, exactly as the
verified transcript is ground truth for CER). No real separator ships offline, so separation quality
is a **cross-talk leakage** knob `separated_k(α) = track_k + α·track_other` (α=0 oracle, α=1 = raw
mixture; realistic separators ≈ 0.1–0.3).

## Result 1 — emotion has no separation tax (no crossover)

Emotion-recovery benefit = `distortion(mixed vs source) − distortion(separated(α) vs source)`
(>0 ⇒ separation recovers emotion). Mean benefit by overlap (8 pairs):

| separator α | ov 0.0 | 0.1 | 0.3 | 0.6 | 0.9 | crossover |
|---|---:|---:|---:|---:|---:|:--:|
| 0.0 (oracle) | +0.000 | +0.151 | +0.174 | +0.263 | +0.310 | no |
| 0.15 (good) | +0.000 | +0.118 | +0.091 | +0.132 | +0.160 | no |
| 0.30 (poor) | +0.000 | +0.108 | +0.037 | +0.098 | +0.016 | no |

Separation **never hurts** emotion (benefit ≥ 0 everywhere) and helps **more** as overlap grows —
the opposite of the ASR tax, which is *negative* at low/mid overlap. Separator quality matters most at
high overlap: a poor separator (α=0.3) erodes the benefit to ≈0 at 0.9 overlap. Because the metric is
gain-invariant, this is not a loudness effect (mean `gain_component_db` is reported separately and is
small). Honest caveat: at α=0 the monotone-positive shape is partly structural (oracle separated =
clean truth in-region, so benefit = mixed_distortion ≥ 0); the α=0.15/0.30 rows — a *leaky* separator —
show the same qualitative pattern, so the "no tax for emotion" conclusion is not purely an oracle artifact.

## Result 2 — the headline: ASR and emotion DISAGREE on whether to separate

The cross-link runs Whisper on the *same* conditions and compares the ASR benefit
(`CER_mixed − CER_sep`, >0 ⇒ separate helps ASR) with the emotion benefit, per overlap:

**α = 0 (oracle):**

| overlap | ASR benefit | emotion benefit | agree? |
|---|---:|---:|:--:|
| 0.0 | −0.030 | 0.000 | — |
| **0.1** | **−1.382** | **+0.151** | **DISAGREE** |
| 0.3 | +0.070 | +0.174 | agree |
| 0.6 | +0.229 | +0.263 | agree |
| 0.9 | +0.321 | +0.310 | agree |

**α = 0.15 (realistic separator):**

| overlap | ASR benefit | emotion benefit | agree? |
|---|---:|---:|:--:|
| 0.0 | −0.425 | 0.000 | — |
| **0.1** | **−0.362** | **+0.118** | **DISAGREE** |
| **0.3** | **−1.716** | **+0.091** | **DISAGREE** |
| 0.6 | +0.000 | +0.132 | agree |
| 0.9 | +0.232 | +0.160 | agree |

In the **light/mid-overlap band**, separation **hurts ASR** (Whisper hallucinates on the
sparse/leaky separated track — the project's tax, reproduced: −1.38 at α=0/ov0.1, −1.72 at
α=0.15/ov0.3) but **helps emotion** (cleaner per-speaker prosody). They agree only at high overlap.
Overall the two benefits are weakly correlated (Pearson 0.08 at α=0, 0.11 at α=0.15; Spearman 0.40 /
0.31, n=40) — confirming the objectives are *loosely* aligned with an active sign disagreement where
it matters.

## Synthesis: the separate-or-not decision is objective-dependent

This extends the project's thesis into a two-objective regime. A single reference-free
separate-vs-mixed switch (router_v2) is **ASR-optimal**: it must keep low/mid-overlap audio mixed to
avoid hallucination. But that same choice **forfeits emotional prosody**, which separation recovers at
every overlap. A system that needs *both* an accurate transcript *and* per-speaker emotion cannot use
one switch — it needs **objective-aware routing**: transcribe from the mixture (or a conservative
route) while estimating emotion from the separated track, in exactly the light/mid-overlap band where
the two disagree. That band is identifiable reference-free (it is where the existing degeneracy/overlap
signals fire), so this is buildable — the concrete next step (issue backlog).

## Hypothesis verdicts

- **H1 (emotion mirrors the ASR tax, with a crossover): FALSIFIED.** No crossover; emotion benefit ≥ 0
  at all overlaps and grows with overlap.
- **H2 (not loudness): HELD.** Metric is gain-invariant by construction; `gain_component_db` reported
  separately and small. The effect survives a leaky (α=0.15/0.30) separator.
- **H3 (cross-link): DIVERGENCE confirmed.** Weak global correlation + sign disagreement at low/mid
  overlap — the bold pre-registered alternative, not the "same decision" null.

## Honest limitations

Whisper-`tiny`; synthetic oracle/leaky mixtures (no real separator offline); emotion = **arousal-side
acoustic prosody only** (valence is not claimed; no human emotion labels, so this measures prosody
*preservation*, a proxy for emotion preservation, not classified emotion accuracy). n=40 for the
cross-link (8 pairs × 5 overlaps) with heavy CER tails — the robust claim is the **sign pattern** in the
low/mid band, not exact magnitudes. The α=0 emotion benefit is partly structural (see Result 1). pyin
F0 is sparse on short/contaminated tracks, so energy + spectral cues carry most of the arousal signal
(by design). `src/prosody.py` is gain-invariance-tested (9 tests); the experiment's pure logic is
unit-tested without librosa/Whisper (14 tests). `experimental/frontier`, not a gold result. Artifacts:
`prosody_tax_curve.csv` (120 rows), `prosody_tax_summary.json`, `crosslink_curve_a0.csv` /
`crosslink_curve_a015.csv` (+ summaries), `emotion_separation_tax.png`, `emotion_asr_divergence.png`.
