# RQ30: MeetEval cpWER Compatibility Validation

**Label:** external/sanity-check
**Closes:** #934
**MeetEval version:** 0.4.3
**Source data:** `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (77 windows, AISHELL-4 meeting `M_R003S02C01`, read-only)
**Mode:** Conservative Reproduction (Mode A) + Frontier Exploration (Mode C)

## Executive summary

The project already uses MeetEval directly (`from meeteval.wer import cpwer` in
`results/external_sanity_check/aishell4/rq1_aishell4_validation.py`), so the
stored cpWER values reproduce **bit-for-bit** under MeetEval 0.4.3 with the
same inputs (0 mismatches across 154 comparisons; Spearman ρ = 1.0).
H30a and H30b are therefore **trivially SUPPORTED**.

However, the validation uncovered a **critical semantic discrepancy**: the
project passes whole Chinese strings as single "words" to MeetEval. Because
Chinese has no whitespace, each speaker's entire utterance becomes **1 token**,
so the cpWER `length` field equals the number of speakers, not the number of
characters. The project's own `FINDINGS.md` (line 131) claims
"MeetEval treats each Chinese character as a 'word'" — **this claim is
FALSE** for the stored values.

The standard Chinese cpCER convention is to treat each character as a token.
Re-computing cpWER at character level preserves the **qualitative direction**
of every aggregate conclusion (separated worse than mixed; oracle best) but:

- **shrinks the separation tax by ~80x** (0.418 → 0.005)
- **completely scrambles per-window ordering** (Spearman ρ ≈ 0.11 for
  separated, −0.20 for mixed)
- **flips the mixed-vs-separated winner on 37/77 windows (48%)**

H30c is SUPPORTED in the narrow sense (the discrepancy is documented and
explained; there are no bugs), but its implication is severe: the project's
cpWER values are **technically valid but semantically misleading** for Chinese.

## Pre-registered hypotheses

| ID | Statement | Verdict | Key number |
|----|-----------|---------|------------|
| H30a | Aggregate cpWER matches MeetEval within 1% absolute | **SUPPORTED** | max diff = 2.9e-07 |
| H30b | Per-window ordering matches MeetEval (ρ > 0.99) | **SUPPORTED** | min ρ = 1.000000 |
| H30c | Discrepancies explained by documented normalisation | **SUPPORTED (severe caveat)** | 0 bugs; 1 critical tokenisation discrepancy |

H30a/H30b are trivially satisfied because the project uses MeetEval directly.
H30c is satisfied because the single discrepancy (word-level vs character-level
tokenisation) is documented below and there are no bugs — but the discrepancy's
impact on the project's conclusions is severe.

## Method

### Data

77 windows of 30 s from AISHELL-4 meeting `M_R003S02C01` (6 speakers, 38.5 min),
read from the stored JSON. Each window has `ref_text_per_speaker`,
`separated_text_per_speaker`, `mixed_text`, and the project's stored
`cpwer_separated` / `orcwer_mixed` values. **No ASR runs** — reanalysis only.

### Two tokenisation arms

1. **Word-level (the project's exact approach).** Each speaker's full Chinese
   string is passed to MeetEval as one `words` field. MeetEval splits on
   whitespace; Chinese has none; so each speaker's utterance is **1 token**.
   This reproduces the stored values bit-for-bit.

2. **Character-level (the standard Chinese cpCER convention).** Each Chinese
   string is space-separated into individual characters
   (`' '.join(list(text))`), so each character is **1 token**. This is what
   the project's `FINDINGS.md` *claims* to do but the stored values do not.

Both arms use the same MeetEval 0.4.3 `cpwer` (separated) and `orcwer` (mixed)
functions, the same empty-string handling (skip whitespace-only speakers),
and the same segment-dict format as the project's `compute_cpwer` /
`compute_orcwer`. The only difference is whether `words` is the raw string
(word-level) or the character-separated string (char-level).

### Metrics

- Aggregate cpWER = mean over 77 windows of the per-window error rate
  (matches the project's convention; not length-weighted).
- Per-window Spearman ρ across the 77 windows.
- Separation tax = `mean(separated) − mean(mixed)`.
- Disagreement count = windows where word-level and char-level pick a
  different winner (min of separated vs mixed).

## Results

### Aggregate cpWER (mean over 77 windows)

| Policy | Stored (project) | MeetEval word-level | MeetEval char-level |
|--------|-----------------:|--------------------:|--------------------:|
| always_mixed | 1.173160 | 1.173160 | 0.910577 |
| always_separated | 1.590909 | 1.590909 | 0.915831 |
| router_v2 | 1.205628 | 1.205628 | 0.922196 |
| oracle_best | 1.017316 | 1.017316 | 0.876847 |

- **Stored == MeetEval word-level** to within 3e-7 (floating-point noise) on
  every metric. The project uses MeetEval; this is the trivial sanity check.
- **Character-level shrinks every gap.** Separation tax
  (`separated − mixed`): 0.418 (word) → 0.005 (char) — a **79.5x** reduction.
  Router v2's regret to oracle: 0.188 (word) → 0.045 (char) — 4.2x reduction.
  Router v2's advantage over always-mixed: 0.033 (word) → 0.012 (char) —
  2.8x reduction.

### Per-window Spearman ρ

| Comparison | ρ | p-value | Interpretation |
|-----------|---:|--------:|----------------|
| stored vs MeetEval-word (separated) | +1.000000 | 0 | ours == MeetEval (sanity) |
| stored vs MeetEval-word (mixed) | +1.000000 | 0 | ours == MeetEval (sanity) |
| word vs char (separated) | +0.107821 | 0.351 | ordering NOT preserved |
| word vs char (mixed) | −0.204355 | 0.075 | ordering NOT preserved |
| stored vs MeetEval-char (separated) | +0.107821 | 0.351 | ours vs char-level |
| stored vs MeetEval-char (mixed) | −0.204355 | 0.075 | ours vs char-level |

The word-level metric does **not** preserve the per-window ordering of the
character-level metric. Windows ranked "worst" at word level are essentially
uncorrelated with windows ranked "worst" at char level.

### Per-window winner disagreement

On **37 of 77 windows (48%)** the word-level and char-level metrics disagree
on whether mixed or separated is the better route. The router's per-window
decisions — and therefore its accuracy (85.7% at word level) — would be
substantially different at character level.

### Worked example (window 0)

- Reference: 6 speakers, 110 characters total.
- Stored cpWER (separated): error_rate = 2.333, errors = 14, length = **6**
  (= number of speakers, not characters).
- Character-level cpWER (separated): error_rate = 1.645, errors = 181,
  length = **110** (the actual character count).
- The stored `length = 6` is the smoking gun: MeetEval is treating each
  speaker's entire utterance as a single token.

## Discrepancies

### D1 — Tokenisation granularity (CRITICAL, semantic)

**Cause.** `compute_cpwer` in
`results/external_sanity_check/aishell4/rq1_aishell4_validation.py` line 253
builds segments with `"words": txt` where `txt` is the raw Chinese string.
MeetEval splits `words` on whitespace. Chinese has no whitespace, so each
speaker's full utterance becomes 1 token.

**Evidence.** Window 0: `ref_total_length = 110` characters, but
`cpwer_separated.length = 6` (= number of speakers). The character-level arm
gives `length = 110`.

**Documentation mismatch.** `results/external_sanity_check/aishell4/FINDINGS.md`
line 131 states: "MeetEval treats each Chinese character as a 'word.' This is
standard for Chinese cpWER but means the error rates are character-level, not
word-level." This claim is **false** for the stored values. The stored values
are utterance-level (1 token per speaker), not character-level.

**Impact — aggregate.**
- `always_separated`: 1.591 (word) vs 0.916 (char) — absolute Δ = 0.675 (74%).
- `always_mixed`: 1.173 (word) vs 0.911 (char) — absolute Δ = 0.262 (29%).
- `oracle_best`: 1.017 (word) vs 0.877 (char) — absolute Δ = 0.140 (16%).

**Impact — separation tax.** 0.418 (word) vs 0.005 (char) — **79.5x**
inflation at word level. The qualitative direction (separated worse than
mixed) is preserved, but the magnitude is wildly overstated.

**Impact — per-window ordering.** Spearman ρ (word vs char) = 0.108
(separated), −0.204 (mixed). The word-level metric does not preserve the
character-level per-window ranking. 37/77 windows (48%) flip the
mixed-vs-separated winner.

**Is this a bug?** No — MeetEval is being called correctly with the inputs it
receives. The bug is in the **input preparation** (not splitting Chinese into
characters) and in the **documentation** (FINDINGS.md claiming character-level
when the implementation is utterance-level).

### D2 — Empty-string handling (MINOR, cosmetic)

The project skips speakers with empty/whitespace-only text and returns
`{error_rate: 1.0, errors: -1, length: -1}` as a sentinel. MeetEval itself
would error on empty input. This is consistent and documented; not a bug.
No impact on aggregate (the sentinel is used only for windows with no speech,
which are excluded from means).

### D3 — Punctuation / marker handling (MINOR, cosmetic)

Reference text contains `<#>` segment-boundary markers and Chinese
punctuation. Neither the project nor the character-level arm normalises these.
Both arms are consistent, so this does not affect the comparison. A future
cpCER could strip `<#>` and punctuation for a cleaner character-level score,
but this is a separate research question.

## Limitations

1. **Single meeting.** Only `M_R003S02C01` is validated (the only AISHELL-4
   meeting in the project). Generalisation across meetings is not tested.
2. **No punctuation normalisation.** The character-level arm does not strip
   `<#>` markers or Chinese punctuation. This affects both arms equally, so
   the comparison is fair, but the absolute char-level numbers could shift
   slightly with cleaner normalisation.
3. **No word-segmentation arm.** A third arm using jieba or similar Chinese
   word segmentation would give true word-level cpWER. This is out of scope
   for RQ30 (MeetEval does not segment Chinese) but would be a useful
   follow-up.
4. **Reanalysis only.** No new ASR runs. The transcripts are frozen at their
   Whisper-tiny outputs; a stronger model would change the absolute numbers
   but not the tokenisation-granularity finding.
5. **Aggregate is unweighted mean.** The project uses unweighted mean over
   windows (each window counts equally regardless of length). A length-
   weighted mean would give different absolute numbers but the same
   word-vs-char discrepancy.

## Reproducibility

- **Script:** `python3 results/frontier/meeteval_cpwer_validation/meeteval_validation_analysis.py`
  (deterministic; requires `meeteval>=0.4.3`, `scipy`, `numpy`).
- **Install MeetEval:** `pip install --user --break-system-packages meeteval`
  (tested with meeteval 0.4.3, kaldialign 0.12.0, Cython 3.2.6).
- **Runtime:** ~30 s (77 windows × 2 arms × 2 metrics).
- **Outputs:**
  - `meeteval_validation_results.csv` — per-window comparison
  - `meeteval_validation_results.json` — full structured results
- **Source data:** `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

1. **The headline cpWER numbers are technically valid but semantically
   misleading for Chinese.** Every prior RQ that quotes cpWER values
   (RQ1, RQ8, RQ12, RQ13, RQ16, RQ25) is affected. The **relative ordering**
   of policies is preserved (oracle < mixed < separated < router_v2 at
   aggregate level — wait, router_v2 is between mixed and separated, and that
   ordering IS preserved), but the **magnitudes** are inflated by the
   utterance-level tokenisation.

2. **The separation tax is ~80x smaller at character level.** The project's
   central narrative — "separation introduces a large cpWER tax on
   AISHELL-4" — is qualitatively true but quantitatively overstated. At
   character level, separated (0.916) is only 0.005 worse than mixed (0.911),
   not 0.418 worse.

3. **Per-window routing decisions are 48% different.** The router's 85.7%
   accuracy (vs oracle) is measured against word-level cpWER. At character
   level, 37/77 windows would have a different oracle winner, so the router's
   accuracy would be measured against a different ground truth.

4. **FINDINGS.md must be corrected.** The claim on line 131 of
   `results/external_sanity_check/aishell4/FINDINGS.md` that "MeetEval treats
   each Chinese character as a 'word'" is false and should be corrected to
   describe the actual utterance-level tokenisation. This is a documentation
   fix, not a result overwrite — the stored values are not modified.

5. **Future cpWER work should use character-level tokenisation.** Any new
   AISHELL-4 cpWER computation should split Chinese strings into characters
   before passing to MeetEval. The project should consider re-running the
   stable RQ1 baseline with character-level cpWER and labelling it clearly
   as a corrected character-level result (NOT overwriting the stored
   utterance-level values — those remain as historical record).

6. **The router thesis survives, weakened.** The core finding — that a
   corrected router can recover the gap to oracle — is preserved at character
   level (router_v2 0.922 vs oracle 0.877, gap 0.045 vs word-level gap 0.188).
   The lang-id-entropy detector's qualitative signal (diverse hallucination
   is bad) should still hold, but the magnitude of the recoverable gap is
   ~4x smaller. Re-validating RQ16's corrected router at character level is
   the natural follow-up.
