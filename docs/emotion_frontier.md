# Emotion Frontier: Emotion-aware, Overlap-aware, Speaker-level ASR Analysis

**Label:** `experimental/frontier`. Status: opened with the Emotional Separation Tax experiment
(`src/emotion_separation_tax.py`, `src/prosody.py`); see
`results/frontier/emotion_separation_tax/FINDINGS.md`.

## Goal

Extend the project's central question — *"when should we separate?"* — from the ASR-CER objective into
the **emotion** dimension of speech. Concretely: in overlapping multi-speaker (con/pro debate) audio,
quantify whether speech separation **preserves or distorts** each speaker's emotional prosody, whether
that decision **agrees with the ASR-optimal decision**, and whether acoustic emotion/arousal is a
usable **reference-free signal** for routing — all with offline, falsifiable, label-free experiments
that reuse the existing mixture / separation / ASR scaffolding.

## Why this is tractable offline (assumptions)

- **No pretrained SER model, no emotion labels.** `transformers`/`torchaudio`/`funasr` are not
  installed and weights cannot be downloaded. So emotion is operationalized as **acoustic prosody**
  (`src/prosody.py`): pitch, energy *dynamics*, spectral shape, voicing — the **arousal** dimension,
  which is acoustically robust. **Valence is explicitly not claimed.**
- **Label-free reference.** Emotional change is always a **distance to a reference signal** (the clean
  source's own prosody), never to a class label — mirroring how CER scores against the verified
  transcript. This measures *emotion preservation*, a proxy for SER accuracy, not classified emotion.
- **Gain invariance is the load-bearing control.** `prosody_distance(..., energy_invariant=True)` is
  built only from gain-invariant cues and reports loudness change separately, so a measured "emotional
  distortion" can never be just a volume/SNR artifact.
- **No real separator offline** → separation quality is a cross-talk **leakage knob**
  `separated_k(α) = track_k + α·track_other` (α=0 oracle … α=1 raw mixture; realistic ≈ 0.1–0.3).

## Ranked experiment plan

1. **The Emotional Separation Tax (DONE — this PR).** Does separation help/hurt per-speaker prosody
   recovery vs the raw mixture, across overlap × separator-quality, and does it agree with ASR? →
   *Finding:* emotion has **no** separation tax (separation always helps, more at higher overlap), and
   **diverges from ASR** at low/mid overlap (where ASR is hurt). Modules: `src/prosody.py`,
   `src/emotion_separation_tax.py`.
2. **Arousal as a reference-free ASR-difficulty predictor (DONE — bounding negative).** Does acoustic
   arousal predict per-track CER / hallucination, controlling for overlap and beyond the
   compression-ratio guard? → *Finding:* **no** — Pearson(arousal, CER)=0.002, partial-controlling-
   overlap=0.002, orthogonal to compression ratio (−0.04); the pre-registered kill criterion is met.
   So emotion is a downstream consequence to **preserve**, not an upstream feature for **routing**.
   The emotion↔ASR relationship is asymmetric (separation affects emotion; emotion doesn't predict
   ASR). Module: `src/arousal_asr_probe.py`; see `results/frontier/arousal_asr_probe/FINDINGS.md`.
3. **Objective-aware routing.** Fold the divergence into a router that decodes text from the
   conservative route but estimates emotion from the separated track, specifically in the identifiable
   low/mid-overlap disagreement band. Builds on the noise-robust router (issue #814). *Metric: joint
   (CER, prosody-preservation) regret vs a two-objective oracle.*
4. **Prosody-preservation as a reference-free separator-quality score.** At deploy there is no clean
   reference; test whether separated-track prosody **self-consistency** (or speaker-embedding stability)
   tracks the leakage α, giving a label-free separation-quality meter. *Label frontier/oracle-analysis.*
5. **Emotion-conditioned gate (stretch).** Does an arousal-aware variant of the speaker-conditioned
   gate (finding #12/#13) preserve prosody better than the CER-tuned gate? Ties the gate frontier to
   emotion.

## Metrics (all offline)

- `prosodic_features` → pitch (median/IQR), energy dynamics (dB), spectral centroid/rolloff/bandwidth,
  zcr, voicing fraction.
- `arousal_index` → documented relative arousal proxy.
- `prosody_distance` → `emotional_distortion` (gain-invariant), `arousal_distance`, `gain_component_db`.
- emotion-recovery benefit, ASR CER benefit, sign-disagreement flag, Pearson/Spearman cross-correlation.

## Example commands / demo workflow

```bash
# 1. Emotional separation tax phase diagram (offline, ~3 min, no Whisper):
python -m src.emotion_separation_tax --pairs 8

# 2. ASR x emotion cross-link at oracle and realistic separator quality (Whisper-tiny):
python -m src.emotion_separation_tax --crosslink --crosslink-alpha 0.0  --pairs 8
python -m src.emotion_separation_tax --crosslink --crosslink-alpha 0.15 --pairs 8

# 3. Render both figures from existing summaries:
python -m src.emotion_separation_tax --figure

# 4. Arousal -> ASR-difficulty probe (experiment #2, Whisper-tiny):
python -m src.arousal_asr_probe --pairs 8

# Smoke check (fast):
python -m unittest tests.test_prosody tests.test_emotion_separation_tax tests.test_arousal_asr_probe
```

## Limitations

Whisper-`tiny`; synthetic oracle/leaky separation (no real separator offline); arousal-only prosody
(no valence, no human labels — measures *preservation*, not classified emotion); small n with heavy
CER tails (robust claims are sign/direction, not exact magnitudes); the α=0 emotion benefit is partly
structural (oracle separated = clean truth in-region — the α>0 rows are the honest evidence).

## Next steps

- Run experiment 2 (arousal → ASR-difficulty partial correlation) to test whether emotion adds routing
  signal beyond overlap.
- Prototype objective-aware routing (experiment 3) on the identified low/mid-overlap disagreement band.
- If a real separator or a SER model becomes available offline, re-validate the divergence with true
  separation artifacts and (for valence) a labeled probe set.

## Kill criteria

Abandon the emotion frontier if, with a realistic separator (α≈0.15–0.3): the emotion benefit is flat
in overlap AND uncorrelated with CER AND dominated by `gain_component_db` — i.e. prosody preservation
is orthogonal to the separation decision and adds no objective. (Current evidence rejects this: there
is a clear, gain-invariant, overlap-dependent divergence.)
