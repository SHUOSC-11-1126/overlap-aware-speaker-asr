# Lexical Emotion Separation Tax + tri-modal agreement — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; references synthetic/silver; lexical emotion =
the offline regex/lexicon extractor `src/lexical_emotion.py` (valence + arousal, no model/labels);
acoustic emotion = `src/prosody.py`. No gold tables touched. Outputs in
`results/frontier/lexical_emotion_tax/`. Reproduce: `python -m src.lexical_emotion_tax --pairs 8`
(8 pairs × overlap {0,0.1,0.3,0.6,0.9} at separator leakage α=0.15 = 40 conditions).

## Question

Experiment #1 measured emotion in the AUDIO (acoustic arousal). Debate emotion also lives in the WORDS
— i.e. in the ASR transcript, where it is directly exposed to ASR errors. This adds the **valence**
dimension and asks, on identical conditions, whether the three views of "should we separate?" agree:
text correctness (CER), acoustic arousal (prosody), and lexical valence (transcript sentiment).

## Result 1 — the three modalities respond differently to separation

Mean benefit of separating (>0 ⇒ separate) by overlap (α=0.15, n=8/cell):

| overlap | CER benefit | acoustic-arousal benefit | lexical-valence benefit |
|---|---:|---:|---:|
| 0.0 | −0.425 | 0.000 | −0.004 |
| 0.1 | −0.362 | +0.118 | +0.021 |
| 0.3 | −1.716 | +0.091 | +0.021 |
| 0.6 | 0.000 | +0.132 | +0.003 |
| 0.9 | +0.232 | +0.160 | +0.025 |

- **CER** shows the separation tax (hurts at low/mid overlap, helps at high).
- **Acoustic arousal** shows no tax (separation always slightly helps) — reconfirming finding #14.
- **Lexical valence** is essentially **flat near zero** at every overlap.

The three are weakly correlated (Pearson CER~lexical 0.06, CER~acoustic 0.11, acoustic~lexical −0.10)
and frequently disagree in sign (sign-agreement CER~lexical 0.40, CER~acoustic 0.42, acoustic~lexical
0.75). There is **no single separation decision optimal across all three** — extending the #14/#15
asymmetry: text correctness, acoustic emotion, and lexical emotion each react to separation differently.

## Result 2 (honest) — the lexical arm is underpowered on this data

The flat lexical signal is **not** a clean "valence is invariant to separation" result: the seed
lexicon fires on only **2 of 16** reference snippets. The debate snippets are short, casual fragments
(e.g. "他让你在那个时间段里拥有了自己") that rarely contain explicit sentiment keywords, so the lexical
separation signal sits near the extractor's floor. The extractor itself is validated (unit tests show
it correctly scores polarity, negation 不支持→negative, intensifiers, and detects a 支持↔反对 flip as a
large distortion); the limitation is the **emotional-lexical sparsity of casual debate ASR text**, not
the extractor.

This is the key methodological finding: **a fixed keyword/regex lexicon under-detects the implicit,
context-dependent emotion of casual debate speech.** It directly motivates the generative LLM critic
(`src/llm_asr_critic.py`, next experiment): an LLM can read implicit/contextual valence that no fixed
lexicon enumerates — exactly the gap measured here.

## Synthesis

- Deliverable: a tested, offline, extensible regex/lexicon **valence + arousal** reader (the "用正则辅助
  情感分析" direction), plus a tri-modal (CER / acoustic / lexical) separation-benefit framework.
- Robust claim: CER-vs-acoustic divergence persists (reconfirms #14); the three emotion/text views do
  not share one optimal separation decision.
- Honest bound: lexical valence on this corpus is underpowered (2/16 snippets fire) → motivates the LLM
  critic for implicit emotion.

## Honest limitations

Whisper-`tiny`; synthetic oracle/leaky separation; seed lexicon is debate-oriented and small (fires on
2/16 snippets here — casual fragments are lexically sparse in sentiment); n=40 with heavy CER tails
(robust claim is the per-modality direction, not magnitudes); lexical emotion is utterance-level
(both speakers combined, like CER). The extractor's pure logic is unit-tested (13 tests) and the
tri-modal summarizer (4 tests). `experimental/frontier`. Artifacts: `lexical_tax_curve.csv` (40 rows),
`lexical_tax_summary.json`, `lexical_emotion_tax.png`.
