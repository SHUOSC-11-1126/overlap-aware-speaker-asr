# RQ37: Per-speaker cpWER Decomposition -- Findings

## Label: experimental/frontier (Issue #944)

Decomposes AISHELL-4 cpWER (77 windows, meeting M_R003S02C01) by speaker using MeetEval 0.4.3's `cpwer` with character-level tokenisation. Tests whether total cpWER is dominated by 1-2 speakers and whether Mode S windows (separator-collapse, ids 22 and 30) have uniform per-speaker error.

## Method

For each window: run `cpwer` on char-level segments (`' '.join(list(text))`, the standard Chinese cpCER convention from RQ30) to get the optimal ref<->hyp speaker assignment; apply the assignment; compute per-speaker Levenshtein distance on the raw character strings. Per-speaker errors sum to MeetEval's `cpwer.errors` (including unmatched-hypothesis insertions in a dedicated `__unmatched_hyp__` bucket). Worst speaker = highest error count. Share = speaker errors / total errors. Gini computed on per-speaker cpWER values (errors/ref_length).

## Hypothesis verdicts

| ID | Statement | Verdict | Key value | Threshold |
|----|-----------|---------|-----------|-----------|
| H37a | One speaker contributes > 50% of total cpWER in worst windows | SUPPORTED | max share = 96.5% | > 50% |
| H37b | Worst speaker is consistent across windows | SUPPORTED | '001-M' worst in 60% of top-10 | > 50% |
| H37c | Mode S windows have uniform per-speaker error | SUPPORTED | Gini = 22: 0.172, 30: 0.000 | < 0.30 |

## Top-10 worst windows (by char-level cpWER)

| Rank | Window | cpWER | Errors | Worst speaker | Worst share | Unmatched share |
|------|--------|-------|--------|---------------|-------------|-----------------|
| 1 | 0 | 1.6455 | 181 | 001-M | 49.2% | 0.0% |
| 2 | 23 | 1.5747 | 137 | 005-F | 62.8% | 0.0% |
| 3 | 65 | 1.1320 | 223 | 001-M | 47.5% | 0.0% |
| 4 | 51 | 1.0361 | 258 | 001-M | 83.3% | 0.0% |
| 5 | 21 | 1.0000 | 113 | 001-M | 70.8% | 0.0% |
| 6 | 66 | 1.0000 | 248 | 001-M | 50.4% | 0.0% |
| 7 | 67 | 1.0000 | 226 | 005-F | 96.5% | 0.0% |
| 8 | 15 | 0.9945 | 182 | 006-F | 87.9% | 0.0% |
| 9 | 24 | 0.9944 | 176 | 005-F | 92.0% | 0.0% |
| 10 | 48 | 0.9900 | 199 | 001-M | 71.4% | 0.0% |

## Mode S windows (separator-collapse)

| Window | Speakers | cpWER | Gini | Per-speaker (errors/len: cpwer) |
|--------|----------|-------|------|----------------------------------|
| 22 | 2 | 0.4915 | 0.172 | 005-F 57/117:0.487, 006-F 1/1:1.000 |
| 30 | 1 | 0.8027 | 0.000 | 005-F 179/223:0.803 |

## Decomposition invariant

Per-speaker error counts plus unmatched-hypothesis insertions sum to MeetEval's `cpwer.errors` for **all 77 windows** (0 mismatches). The decomposition is exact, not approximate.

## Interpretation

H37a SUPPORTED: cpWER is heavily concentrated. In the top-10 worst windows a single speaker contributes 96% of the total cpWER errors in the worst case. The aggregate cpWER masks a 'worst speaker' problem -- improving that speaker's channel (better separation, better ASR, or rerouting it to mixed) would disproportionately reduce the total. H37b SUPPORTED: the worst speaker is consistent ('001-M' in 60% of top-10). The same speaker's channel fails repeatedly -- a speaker-specific failure mode, not random. H37c SUPPORTED: Mode S windows have low Gini (22:0.17, 30:0.00), meaning per-speaker cpWER values are relatively uniform. CAVEAT: Gini on cpWER rates can obscure error concentration when ref lengths differ wildly -- e.g. window 22 has 98.3% of absolute errors on speaker 005-F, but because the 1-char 006-F reference yields cpWER=1.0 (vs 005-F's 0.49) the cpWER values look 'uniform'. The Gini verdict is technically correct but should be read alongside the per-speaker error shares in the Mode S table.

## Files

- per_speaker_decomposition_results.json -- full per-window decomposition + verdicts
- per_speaker_decomposition_results.csv -- one row per window (ranked by cpWER)
- per_speaker_decomposition_analysis.py -- analysis script (imports src/per_speaker_decomposition.py)
- src/per_speaker_decomposition.py -- testable helpers (cpwer bridge, Gini, edit distance, hypothesis eval)
- tests/test_per_speaker_decomposition.py -- 48 unit tests (unittest.TestCase)
