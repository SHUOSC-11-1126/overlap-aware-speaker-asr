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

## Frontier extensions: lexical emotion + LLM × ASR (added 2026-06)

6. **Lexical Emotion Separation Tax + tri-modal agreement (DONE).** A deterministic, offline
   regex/lexicon **valence + arousal** reader (`src/lexical_emotion.py`, the "用正则辅助情感分析"
   direction) measures whether ASR errors corrupt a speaker's *textual* emotion, and unifies three
   views of "should we separate?" — CER, acoustic arousal, lexical valence — on identical conditions
   (`src/lexical_emotion_tax.py`). *Finding:* the three respond differently (CER tax; acoustic no-tax;
   lexical ~flat) and weakly correlate; but the lexical arm is **underpowered** here — the seed lexicon
   fires on only 2/16 casual debate snippets — which **motivates a generative LLM** emotion reader.
   See `results/frontier/lexical_emotion_tax/FINDINGS.md`.
7. **Prosody-grounded LLM × ASR critic (DONE — bounding negative).** A dependency-injected critic
   (`src/llm_asr_critic.py`) with an offline default (regex/lexicon) and a real local LLM backend
   (deepseek-r1 via ollama). Following the 2025/26 SER + GER frontier (below), it **injects explicit
   prosodic + lexical cues** into the LLM (speech-LLMs have documented weak prosody perception) and
   **separates the repair role from the judge role** (the code-tape *generation-evaluation separation*
   principle). *Finding:* the critic adds cost without winning — the LLM judge (QE r=−0.41) is
   dominated by the free compression-ratio signal (r=+0.74), and GER repair net-harms CER
   (over-corrects clean text); no reference-free gate rescues it. Same "simple beats fancy" motif as
   #13. See `results/frontier/llm_asr_critic/FINDINGS.md`. Demo: `python -m src.llm_asr_critic --pairs 8`
   (requires `ollama serve` with `deepseek-r1:7b`).

## References / Frontier reading (2025–2026)

This frontier is grounded in current work; every paper consulted is listed here (per project policy
to cite all reading). Treated as background — no text reproduced.

- *Prompt-Based ASR with Speech LLMs* (review, Jan 2026), emergentmind.com — names over-correction in
  ill-posed regions and highly-overlapping scenarios as open problems (motivates our over-correction
  guard and the overlap setting). https://www.emergentmind.com/topics/prompt-based-asr-with-speech-llms
- *VoxEmo: Benchmarking Speech Emotion Recognition with Speech LLMs* (arXiv 2603.08936, 2026).
  https://arxiv.org/pdf/2603.08936
- *EmotionThinker: Prosody-Aware Reinforcement Learning for Explainable Speech Emotion Reasoning*
  (OpenReview, 2026) — explainable, acoustic-cue-grounded SER; speech-LLMs have weak prosody perception.
  https://openreview.net/forum?id=wbttgzp7MT
- *ProsodyLM: Uncovering the Emerging Prosody Processing Capabilities in Speech Language Models*
  (OpenReview, 2026). https://openreview.net/forum?id=uBg8PClMUu
- *EmoSRE: Emotion-prediction-based speech synthesis and refined speech recognition using LLM and
  prosody encoding* (Current Psychology, Springer, 2025).
  https://link.springer.com/content/pdf/10.1007/s12144-025-07705-2.pdf
- *Steering Language Model to Stable Speech Emotion Recognition via Contextual Perception and Chain of
  Thought* (arXiv 2502.18186, 2025). https://arxiv.org/pdf/2502.18186
- *LLM-based Generative Error Correction for Rare Words with Synthetic Data and Phonetic Context*
  (arXiv 2505.17410, 2025). https://arxiv.org/pdf/2505.17410
- *LLM-Based GER: A Challenge and Baselines for Speech Recognition, Speaker Tagging, and Emotion
  Recognition* (arXiv 2409.09785, 2024) — GER + emotion jointly. https://arxiv.org/html/2409.09785v3
- *HyPoradise: Open Baseline for Generative Speech Recognition with LLMs* (arXiv 2309.15701, 2023) —
  the GER paradigm. https://arxiv.org/pdf/2309.15701

## Lineage / acknowledgements

The development harness (git hooks, GitNexus knowledge-base contract, repo-guard CR loop, TDD, SDD)
this frontier runs under is adapted from **[ceilf6/code-tape](https://github.com/ceilf6/code-tape)**
(`ref/code-tape`). The LLM × ASR critic (experiment 7) deliberately borrows code-tape's
**generation-evaluation separation** principle — the transcript *repairer* and the quality *judge* are
distinct roles, not one self-grading pass — to reduce the model's bias in scoring its own corrections.

