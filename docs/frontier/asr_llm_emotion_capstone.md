# Capstone: the ASR × LLM + Emotion + Speaker Frontier

**Label:** `experimental/frontier` — a synthesis of five `experimental/frontier` results (all merged, all
verified through the harness with repo-guard review + green CI). Hero figure:
`results/frontier/asr_llm_frontier_capstone.png`. No gold tables are touched by this consolidation.

This is the one-page map of what a *local, offline* LLM (`deepseek-r1` via ollama) and cheap
reference-free signals can and cannot do for overlap-aware speaker ASR, built on this repo's controlled
overlap × separation × noise grid with silver references.

## Reproducibility

Each of the five results can be reproduced independently:

```bash
# Semantic Emotion Tax (#831)
python -m src.semantic_emotion_tax

# Emotion-anchored Repair (#833)
python -m src.emotion_anchored_repair

# Tri-modal Fusion (#835)
python -m src.emotion_modality_fusion

# Noise-robust Router (#814)
python -m src.noise_robust_router

# LLM Speaker Attribution (#838)
python -m src.llm_speaker_attribution
```

All outputs are written to `results/frontier/<experiment_name>/` as CSV + PNG + FINDINGS.md.
Unit tests: `python -m pytest tests/test_<module>.py` for each module.

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

## Failure Analysis

### Why Emotion-Anchored Repair Fails (#833)

The hypothesis was natural: if the LLM over-corrects because it doesn't know the speaker's emotional
state, providing that state as context should constrain its edits. The result was the opposite:
anchored repair (CER 1.122) was *worse* than naive repair (1.082), which was worse than no repair
(0.924).

**Mechanism:** The anchor text ("the speaker sounds angry") gives the LLM *permission* to rewrite
more aggressively — it interprets the emotional context as license to paraphrase, not as a constraint
on edit distance. This is consistent with the general finding that LLMs in this small-model regime
(7B parameters) have weak instruction-following for edit-minimal tasks.

**Implication:** Don't blind-repair in this setting. The 0.200 CER floor (Thread 2) is not fixable by
contextual understanding alone.

### Why LLM Speaker Attribution Sign Is Unknowable (#838)

The LLM can detect that speaker A is more positive/negative than speaker B (AUC 0.78 for role
strength), but it cannot determine *which* speaker is the pro side and *which* is the con side
without labeled examples. The sign mapping is dataset-specific: positive valence → pro speaker in one
debate, → con speaker in another.

**Mechanism:** The LLM reads *relative* affect (who is more positive), not *absolute* stance (who
supports the proposition). Without a few ground-truth labels to calibrate the sign, the attribution
is a coin flip (naive AUC 0.08).

**Implication:** Affect-based speaker attribution requires a small calibration set — a few labeled
examples per debate to establish the sign mapping. This is a realistic deployment constraint, not a
fundamental failure.

## Connection to Broader Literature

This capstone connects to three research lines:

1. **ASR × LLM (GenSEC-LLM, R3, VoxEmo):** Prior work showed LLMs can process ASR output for
   downstream tasks. Our contribution: the LLM's value is *coverage* of implicit semantic emotion
   (7× vs lexicon), not free repair or attribution rules. This is a scope clarification, not a
   contradiction.

2. **Whisper hallucination (Koenecke, Baranski, Aparin, Waldendorf):** The confident-attractor
   mechanism explains why the compression-ratio signal works — it detects the loop *after* it starts.
   Our noise-robust router (#814) shows this signal survives noise, extending the hallucination
   detection line into realistic conditions.

3. **Emotion in speech (Russell, Scherer):** The Emotional Separation Tax (#14) is a new finding in
   the dimensional emotion tradition: separation helps emotion (opposite of ASR tax), making the
   routing decision objective-dependent. This has not been reported in prior work.

## Honesty note

Two of five are clean negatives/nuanced and one is a strong positive — that ratio is the point. The
frontier's value is *boundaries revealed, not claimed*: we now know the cheap decoder signal is the
deployable lever, the LLM's gift is coverage of implicit semantics, and its tempting decision-rules
(repair, attribution sign) don't come for free. All results are Whisper-`tiny` + silver references +
local `deepseek-r1`; small-n, synthetic oracle separation — `experimental/frontier`, not gold.
