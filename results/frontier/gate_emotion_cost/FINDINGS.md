# Do the CER-tuned hallucination-cure gates damage emotion? — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; references synthetic/silver; emotion =
gain-invariant prosody distance to the clean source (`src/prosody.py`); babble noise; speaker embedder
resemblyzer GE2E. No gold tables touched. Outputs in `results/frontier/gate_emotion_cost/`. Reproduce:
`python -m src.gate_emotion_cost --pairs 8` (8 pairs × overlap {0.1,0.3} × SNR {10,5} × 2 speakers × 2
gates = 128 rows, babble).

## Question — the closing loop of the emotion frontier

Findings #11–#13 built gates (spectral-flatness, speaker-conditioned) that cure separation-induced
Whisper hallucination — all tuned to lower CER. A gate cures CER by **cropping** audio, and #14 showed
emotion lives in regions a CER-blind decision can discard. So: do these CER-tuned cures have a hidden
**emotion cost**?

For each separated track under babble (where the gates fire), measured against the clean source:
CER benefit = CER(raw separated) − CER(gated) (>0 ⇒ cures), emotion cost = prosody_dist(gated) −
prosody_dist(raw) (>0 ⇒ damages emotion).

## Result — yes, the cures are objective-blind; but the speaker gate damages least

| gate | mean CER benefit (cure) | mean emotion cost (damage) | fired |
|---|---:|---:|---:|
| flatness (#11) | +0.397 | **+0.057** | 54/64 |
| speaker (#12/#13) | **+0.460** | **+0.023** | 60/64 |

- **Both gates cure CER AND damage emotion** (positive on both axes) — the CER-tuned cures are
  objective-blind, extending the #14 "objective-dependent" thesis to the cures themselves: curing the
  transcript moves the track's prosody away from the clean source.
- **The speaker gate dominates on both axes**: it cures CER *more* (+0.46 vs +0.40) while damaging
  emotion *less* (+0.023 vs +0.057). So #13's recommendation ("make the speaker gate the default
  post-separation cure") is reinforced from the emotion side — it is also the most emotion-preserving
  cure. The flatness gate is both the weaker cure and the more emotionally destructive.
- The per-track benefit↔cost correlation is weak (flatness −0.30, speaker −0.01), so this is a
  population-level cost, not a tight per-utterance trade-off.

## Synthesis

The emotion cost of gating (+0.02 to +0.06) is **second-order** relative to the separate-vs-mixed
decision (#14 showed separation changes emotion distortion by +0.1 to +0.3). So the deployment ordering
is: (1) the first-order emotion lever is whether to separate at all (#14/#18 — decouple it from the ASR
route); (2) given separation, prefer the speaker gate, which is the least emotionally destructive cure;
(3) the fidelity meter (#19) flags grossly contaminated tracks. Every CER-tuned cure carries a small
emotion tax, but the project's already-recommended cure (speaker gate) is the one that minimizes it.

## Honest limitations

Whisper-`tiny`; babble only (where gates fire); synthetic oracle/leaky separation; emotion is
arousal-side prosody *preservation* vs the clean source (no labels); n=64/gate with high-variance
prosody (robust claim is the ordering — both cure & damage, speaker < flatness on cost — not exact
magnitudes); the gated track's prosody is computed on the cropped track as-is. Pure aggregation is
unit-tested (3 tests). `experimental/frontier`. Artifacts: `gate_emotion_curve.csv` (128 rows),
`gate_emotion_summary.json`, `gate_emotion_cost.png`.
