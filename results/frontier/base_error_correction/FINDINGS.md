# Base Error Pattern Analysis — Findings

## Label: experimental/frontier (Issue #867)

## Research Question
Can pattern-based post-processing reduce base's CER from 0.200 toward 0.100?

## Results (26 clean snippets, Whisper-base vs Whisper-small reference)

### Error Type Distribution

| Type | Count | Share |
|------|-------|-------|
| Substitution | 72 | **75.0%** |
| Insertion | 12 | 12.5% |
| Deletion | 12 | 12.5% |

Base's errors are overwhelmingly substitution (75%), not hallucination (insertion).

### H1 REJECTED: Errors Are NOT Predictable ❌

- 64 unique substitution patterns across 26 snippets
- Only 6 patterns (9.4%) recur ≥ 2 times
- H1 (recurring > 50%): **REJECTED**

### Traditional/Simplified Chinese Confusion

The top recurring patterns are T/S conversions:
- 个→個, 点→點, 间→間, 让→讓, 时→時, 里→裡, 拥→擁

But T/S normalization (OpenCC t2s) only reduces CER by **5.9%** (0.316 → 0.298).
Only 5/26 samples improved. T/S is a minor factor, not the main issue.

### Interpretation

Base's 0.200 CER reflects genuine acoustic ambiguity, not predictable patterns.
The errors are:
- Diverse (64 unique patterns in 26 samples)
- Mostly substitution (homophone confusion, similar-sounding characters)
- Not correctable by simple lookup tables

This means the 0.200 CER is a **hard floor** for pattern-based post-processing.
Improving beyond this requires either:
1. A language model rescoring pass (LLM-based correction)
2. Better training data or fine-tuning
3. Multi-model consensus (if multiple models are available)

## Files
- substitution_table.csv — all 64 substitution patterns ranked by frequency
- error_log.csv — full character-level error log
- analysis_summary.json — quantitative summary
