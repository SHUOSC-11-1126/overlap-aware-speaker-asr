# LLM Rescoring for Base — Findings

## Label: experimental/frontier (Issue #869)

## CATASTROPHIC NEGATIVE RESULT

| Metric | Value |
|--------|-------|
| Mean CER (raw base) | 0.316 |
| Mean CER (LLM corrected) | **0.798** |
| Samples helped | **0/26** |
| Samples hurt | **19/26** |
| Mean LLM time | 7.4s per snippet |

## The Problem

deepseek-r1:7b does NOT make targeted corrections — it REWRITES the entire
text based on its own understanding. Even with the explicit instruction "只修正
你确定是错误的字符，不要改变正确的部分", the LLM produces completely different
text with CER = 1.0 for most samples.

This is WORSE than the #833 over-correction finding (which was on tiny model).
For base, the LLM doesn't over-correct — it replaces entirely.

## Implication

**LLM post-processing is not viable for ASR correction with deepseek-r1:7b.**
The model lacks the precision to make character-level corrections. It treats
the task as "paraphrase this text" rather than "fix specific errors."

The 0.200 CER floor is confirmed across ALL correction approaches tested:
- Pattern-based: 0.200 (H1 rejected, #867)
- T/S normalization: 0.200 (only 5.9% reduction)
- LLM rescoring: 0.798 (catastrophically worse)

## What Might Work Instead

1. **Character-level confusion model**: Train a small classifier on
   (context, wrong_char) → correct_char pairs, not generative LLM
2. **Multiple hypothesis rescoring**: Run base N times with different seeds,
   use agreement to select characters (but #858 showed this doesn't help)
3. **Accept the 0.200 floor**: For practical deployment, 80% character accuracy
   on Chinese speech may be sufficient, especially with human-in-the-loop
   review for critical content
