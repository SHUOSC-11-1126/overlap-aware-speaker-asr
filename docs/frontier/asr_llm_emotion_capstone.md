# Capstone: the ASR × LLM + Emotion + Speaker Frontier

**Label:** `qualitative/demo` — a synthesis of five `experimental/frontier` results (all merged, all
verified through the harness with repo-guard review + green CI). Hero figure:
`results/frontier/asr_llm_frontier_capstone.png`. No gold tables are touched by this consolidation.

This is the one-page map of what a *local, offline* LLM (`deepseek-r1` via ollama) and cheap
reference-free signals can and cannot do for overlap-aware speaker ASR, built on this repo's controlled
overlap × separation × noise grid with silver references.

## The five results

| # | Question | Outcome | Headline |
|---|---|---|---|
| [#831](../../results/frontier/semantic_emotion_tax/FINDINGS.md) | Can a local LLM read *implicit* emotion the lexicon misses? | ✅ positive | LLM emotion coverage **0.70 vs lexicon 0.10** (≈7×); it is an **orthogonal** 3rd modality vs acoustic-arousal & lexical-valence. |
| [#833](../../results/frontier/emotion_anchored_repair/FINDINGS.md) | Does anchoring LLM repair to the detected stance cure over-correction? | ❌ negative | No: **no-repair 0.924 < naive 1.082 < anchored 1.122**. Anchoring slightly *worsens* it; #822's over-correction tax is robust to the natural fix. |
| [#835](../../results/frontier/emotion_modality_fusion/FINDINGS.md) | Do the orthogonal emotion modalities *fuse* to predict emotion damage? | ◐ nuanced | Only partly: fusion helps the **semantic** target (CV R² 0.10→0.16) but **hurts** the acoustic one; **acoustic-arousal is the single best** reference-free emotion-damage signal. |
| [#814](../../results/frontier/noise_robust_router/FINDINGS.md) | Can a reference-free router beat fixed separate-vs-mixed under noise? | ✅✅ strong | Yes: router **0.778 vs mixed 1.214 / gate 1.531**, recovers **~92%** of the per-utterance oracle gap; **Pearson(compression-ratio, separation-tax) = 0.82**. |
| [#838](../../results/frontier/llm_speaker_attribution/FINDINGS.md) | Can LLM affect repair who-said-what? | ◐ nuanced | Valence **strongly encodes** speaker role (AUC strength 0.78) but in a **sign that isn't knowable reference-free**: naive 0.08, sign-calibrated 0.92. |

## The unifying thread: which reference-free signal wins which decision

The project's spine is *reference-free routing* — deciding without the transcript you're trying to
produce. Across these five studies one ordering is consistent:

- **The cheap Whisper decoder signal wins where accuracy is decided.** Compression-ratio /
  repetition of the candidate output is the single most useful reference-free signal for the
  separate-vs-mixed decision (#814, Pearson 0.82) — it realizes the per-utterance gain that #811
  proved no *fixed* strategy could take. This echoes #822 (compression-ratio beat the LLM-judge for QE).
- **Acoustic prosody wins for the acoustic emotion it protects** (#835). Text-emotion readers
  (LLM-semantic, lexical) are *orthogonal* to acoustic emotion damage and do not proxy it.
- **The local LLM is the right reader for *implicit, semantic* emotion** (#831) — the one thing the
  sparse lexicon and arousal-only prosody miss — but its **mappings are not free**: emotion→repair
  over-corrects (#833) and emotion→speaker-role has an unknowable sign (#838). The LLM gives you
  *coverage*, not a free-lunch decision rule.

## Deployable recipe (reference-free, fully offline)

1. **Separate-vs-mixed:** route per utterance by the candidate (separated+speaker-gated) output's
   decoder degeneracy — take separation unless compression-ratio > 2.4 or repetition is high, else fall
   back to mixed (#814). This is the deployable win.
2. **Gate choice:** settled — speaker-conditioned gate as the default post-separation cure (#811).
3. **Emotion route:** read emotion from the separated track *acoustically* (arousal/prosody); use the
   acoustic signal — not text-emotion — to gate emotion-risk (#835). For *implicit/semantic* emotion or
   stance labelling, add the local LLM as a complementary reader (#831).
4. **Do NOT** run blind LLM transcript repair in this small-model overlapping-speech setting — it
   over-corrects, anchored or not (#833).
5. **Speaker attribution:** affect alone can't fix who-said-what reference-free (the sign is
   dataset-specific, #838); a few labels — or a full LLM role-classification call reading context, not
   just valence — would unlock it.

## Honesty note

Two of five are clean negatives/nuanced and one is a strong positive — that ratio is the point. The
frontier's value is *boundaries revealed, not claimed*: we now know the cheap decoder signal is the
deployable lever, the LLM's gift is coverage of implicit semantics, and its tempting decision-rules
(repair, attribution sign) don't come for free. All results are Whisper-`tiny` + silver references +
local `deepseek-r1`; small-n, synthetic oracle separation — `experimental/frontier`, not gold.
