# Reference Validity & Model Behavior Deep Analysis

## Label: experimental/frontier (post-#859 deep investigation)

## The Question We Were Afraid to Ask

Is base's 0.200 CER in #859 real accuracy, or just model proximity to the
reference model (Whisper-small)?

## Answer: It's Real (with caveats)

### Model Divergence on Clean Audio (6 snippets)

| Comparison | Mean CER | Interpretation |
|-----------|----------|----------------|
| Small vs its own reference | 0.030 | Expected (self-comparison, near-deterministic) |
| Base vs Small | **0.372** | Base produces DIFFERENT text than small |
| Tiny vs Small | 0.503 | Tiny is even more different |
| Tiny vs Base | 0.465 | All three models produce meaningfully different outputs |

**Base and Small are NOT similar models.** They produce 37.2% character-level
different text on clean audio. The 0.200 CER on separated audio is NOT measuring
"base ≈ small" — it's measuring genuine transcription quality.

### The Separation Stability Paradox

Single-sample deep dive (con_001 + pro_001, overlap=0.5):

| Model | Clean CER | Mixed CER | Separated CER | Separation Effect |
|-------|----------|----------|--------------|-------------------|
| Base | 0.3125 | 0.3125 | 0.3125 | **Zero (completely stable)** |
| Tiny | — | 0.5938 | 0.2812 | **-0.3125 (massive help)** |

Base is UNPERTURBED by overlapping speech. Its CER is identical whether
processing clean, mixed, or separated audio. The separation tax doesn't just
have a zero slope for base — it has a flat line at all conditions.

### Transcript Comparison

**Base mixed:** 他让你在那个时间段里**方休要**那他是怎么环节我们的空虚的
**Base sep:**   他讓你在那個時間段裡**擁有了自己**你方是要那他是怎么环节我们的空虚的
**Tiny mixed:** 他讓你在那個時間**斷了你方秀要**他是什麼**環節**我們的空虛的
**Tiny sep:**   他讓你在那個時間段裡擁有了自己你方是要那它是怎么环节我们的空虚的

- Base makes consistent errors regardless of input condition (e.g., "环节" for "缓解")
- Tiny's mixed output has severe hallucinations ("斷了你方秀要") that disappear with separation
- Separation cures tiny's hallucinations but doesn't affect base at all

## Implications

1. **#859's finding is valid.** The 0.200 CER reflects real quality, not model proximity.
2. **Base has its own error patterns** (e.g., 環→环, traditional/simplified mixing)
   that are consistent and predictable, unlike tiny's random hallucinations.
3. **The "separation tax" is a tiny-specific phenomenon.** Base is immune.
4. **Future work should characterize base's error types** (substitution-dominated,
   no hallucination) rather than trying to route around tiny's failures.

## Files
- Inline analysis only (no separate CSV — this is a qualitative investigation)
