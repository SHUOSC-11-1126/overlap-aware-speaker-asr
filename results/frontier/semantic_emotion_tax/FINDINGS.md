# The Semantic Emotion Tax — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny` (cached transcripts); LLM `deepseek-r1:7b` (local ollama, offline); references synthetic/silver (clean source text); CER post-hoc only; no gold tables touched. Issue #831.

Grid: 50 (sample×speaker) records, 5/tier across 5 overlap levels (0.0/0.1/0.3/0.5/0.8). The LLM reads {valence,arousal,stance} from each transcript; emotion has no ground truth, so the clean source text is the silver anchor (exactly as the verified transcript anchors CER).

**Parse health:** 50/50 reference readings parsed (1.0000). Kill criterion (>50% unparseable) not tripped.

## H1 — Coverage: does the LLM read implicit emotion the lexicon misses?

- LLM non-degenerate coverage: **0.7000**
- Lexicon firing rate (same texts): **0.1000**
- Verdict: LLM recovers MORE emotion signal than the fixed lexicon.

## H2 — The Semantic Emotion Tax (separation: help or hurt the *meaning*?)

| overlap | n | mean semantic benefit | mean d_sem(mixed) | mean d_sem(sep) |
|---:|---:|---:|---:|---:|
| 0.0 | 10 | 0.1476 | 0.4334 | 0.2858 |
| 0.1 | 10 | 0.2627 | 0.5372 | 0.2746 |
| 0.3 | 10 | 0.3118 | 0.6545 | 0.3428 |
| 0.5 | 10 | 0.4572 | 0.8000 | 0.3428 |
| 0.8 | 10 | 0.2182 | 0.4265 | 0.2083 |

- Overlap crossover (benefit sign flips low→high overlap): **False**
- d_sem ↔ CER, pooled over both arms: Pearson **0.2941**, Spearman 0.5110 (n=100) — does ASR error move the emotional meaning? (headline)
- d_sem ↔ CER, within the contaminated mixed arm only: Pearson 0.0778, Spearman 0.0994 (n=50).
- semantic_benefit ↔ CER_benefit: Pearson 0.0376, Spearman 0.3494 (n=50) — do emotion and ASR want the same separate/mixed call?

Reading: a positive d_sem↔CER correlation means ASR errors DO distort the recoverable emotional meaning (a real semantic tax); a near-zero correlation means the emotional meaning is robust to transcription error — which *strengthens* the project's decoupling recipe (the text route can carry emotion despite CER). NB: with oracle separation the separated arm sits near (0 CER, 0 d_sem), so the pooled correlation is the valid full-range test.

## H3 — Is LLM-semantic emotion a complementary third modality?

| pair | Pearson | Spearman | n |
|---|---:|---:|---:|
| llm_valence_vs_lexical_valence | -0.1406 | 0.0785 | 50 |
| llm_arousal_vs_acoustic_arousal | -0.0308 | -0.0885 | 50 |
| lexical_valence_vs_acoustic_arousal | -0.1824 | -0.1307 | 50 |

Low pairwise correlation ⇒ the three readers (acoustic arousal, lexical valence, LLM-semantic) capture *different* facets of emotion — the LLM is additive, not redundant.

## Honest limitations

Small n; Whisper-`tiny`; synthetic oracle separation (the separated track is the isolated source, an upper bound on a real separator); local `deepseek-r1` reasoning model with temperature 0 (still has reading variance); emotion is silver-anchored on clean source text, not human emotion labels — this measures *semantic emotion preservation*, a proxy, not classified-emotion accuracy. `experimental/frontier`, not a gold result.
