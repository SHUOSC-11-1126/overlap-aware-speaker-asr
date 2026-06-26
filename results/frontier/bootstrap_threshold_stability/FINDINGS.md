# RQ44: Bootstrap-Aggregated Threshold for Out-of-Sample Router Stability

> **Label: `experimental/frontier`** — Closes #958. Builds on RQ13 (PR #904), RQ16
> (PR #912), and RQ25 (PR #929).
> Reanalysis only (no Whisper / no ASR run); reuses the lang-id entropy detector
> from RQ13/RQ16/RQ25 and the existing AISHELL-4 external-validation windows
> (PR #890). Does NOT overwrite any verified reference / gold table.

## Executive Summary

RQ25 (PR #929) showed that the corrected router's lang-id entropy threshold is
bimodal and unstable on small train splits: a single 50/50 split calibrated a
threshold of **0.010**, two orders of magnitude below RQ16's in-sample 0.409 and
far outside the in-sample range [0.327, 0.491]. The mechanism is that the
"max sensitivity at ≥ 90% specificity" calibration rule is sensitive to whether
a Mode S (low-entropy hallucinated) window lands in the train split. This is a
deployability blocker: a single train/test split cannot identify a stable
operating point. RQ44 asks whether **bootstrap aggregation (bagging)** over
B=10,000 resamples of the 77 AISHELL-4 windows can produce a stable threshold.

**One of three pre-registered hypotheses is killed; the deployability picture is
mixed but actionable:**

| Hypothesis | Verdict | Test statistic | Kill threshold |
|---|---|---:|---|
| H44a: median bootstrap threshold in [0.30, 0.50] | **SUPPORTED** | 0.380 | outside [0.30, 0.50] |
| H44b: 2.5/97.5 percentile interval width < 0.20 | **KILLED** | 0.940 (interval [0.010, 0.950]) | ≥ 0.20 |
| H44c: median held-out (OOB) cpWER < 1.10 | **SUPPORTED** | 1.056 (CI [1.000, 1.208]) | ≥ 1.10 |

The headline finding is a **split between a stable median and an unstable
distribution**. The bootstrap *median* threshold is 0.38 — exactly RQ25's
in-sample value and within the [0.30, 0.50] deployable band (H44a). But bagging
does **not** stabilise the threshold: the 2.5/97.5 percentile interval spans
[0.010, 0.950], a width of 0.94 (H44b killed by a factor of 4.7×). The threshold
distribution is **6-modal**, not the clean bimodality RQ25 inferred from one
split:

| threshold | count | fraction | median OOB cpWER | frac OOB < 1.10 |
|---:|---:|---:|---:|---:|
| **0.38** | 6044 | 60.4% | 1.043 | 0.971 |
| 0.87 | 1451 | 14.5% | 1.107 | 0.433 |
| 0.01 | 899 | 9.0% | 1.107 | 0.433 |
| 0.95 | 844 | 8.4% | 1.172 | 0.085 |
| 0.33 | 573 | 5.7% | 1.043 | 0.974 |
| 0.84 | 189 | 1.9% | 1.104 | 0.455 |

The crucial new insight — invisible to RQ25's single-split view — is that **each
threshold mode maps to a distinct out-of-bag cpWER outcome**. The "good" band
(thresholds 0.33–0.38, 66.1% of resamples) produces median OOB cpWER 1.043 with
97% of resamples below 1.10. The "bad" band (thresholds 0.01 and 0.84–0.95,
33.9% of resamples) produces median OOB cpWER 1.10–1.17 with only 8–46% below
1.10. The threshold and the cpWER are bimodal *together*: the calibration rule
either lands in the good operating region or it does not, and when it does not,
the OOB cpWER degrades above the 1.10 kill threshold.

This directly tests RQ25's caveat. RQ25's 50/50 split landed on threshold 0.01
and got a *lucky* test cpWER of 1.022 because that split's 5 over-flagged clean
windows all had tied cpWER. RQ44 shows that on average the 0.01 mode gives
median OOB cpWER **1.107 — above the 1.10 kill threshold**, with only 43% of
0.01-resamples below 1.10. RQ25's warning that "the cpWER recovery is partly
fortuitous" is quantified and confirmed: the 0.01 threshold is a *bad* operating
point on average, and RQ25's 1.022 was a coincidence of one split's cpWER ties.

**Bottom line.** Bagging does not cure the threshold instability — it *reveals*
it as a 6-modal distribution spanning 0.01–0.95. But bagging does identify the
**median threshold (0.38)** as the stable central operating point, and the OOB
cpWER at that mode is robust (median 1.043, 97% < 1.10). The deployable
recommendation is therefore to **deploy the bootstrap median threshold (0.38)
directly**, rather than re-calibrating on a small train split that may land on a
bad mode. This is the same value RQ16/RQ25 found in-sample, now justified as the
bootstrap median rather than as a single-pool artefact. The residual risk: 34%
of bootstrap resamples calibrate a bad threshold, so on a *new* meeting (where
the cpWER ties may not hold) re-calibration on a small split remains unsafe
without a larger calibration corpus.

## Method

### Data (read-only, not overwritten)

`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
(label `external/sanity-check`, PR #890): 77 windows of 30 s from AISHELL-4
meeting `M_R003S02C01` (6 speakers, 38.5 min). Each window already stores
`always_mixed_cpwer`, `always_separated_cpwer`, `router_v2_cpwer`,
`oracle_best_cpwer`, and the per-speaker separated transcripts. No ASR is run;
the corrected router's per-window cpWER is the chosen route's stored cpWER.

Hallucination label: `always_separated_cpwer > 1.0` (cpWER > 1.0 means insertions
dominate). This gives 37 hallucinated / 40 clean — matching RQ12/RQ13/RQ16/RQ25.

### Detector (RQ13/RQ16/RQ25 verbatim)

`lang_id_entropy(text)`: Shannon entropy (bits) over the Unicode script-category
distribution of the text, computed via `unicodedata.name`. Clean Chinese is
near-monoscript Han (entropy ~ 0); diverse multilingual gibberish mixing
Han+Latin+Katakana+Hangul has high entropy. Per-speaker scores are aggregated by
MAX across the separated tracks (worst-case speaker, the RQ12/RQ13 convention).
The primitive is lifted verbatim from RQ25 so thresholds are directly comparable.

### Routing rule (RQ13/RQ16/RQ25 convention)

HIGH lang-id entropy = diverse gibberish = hallucination. The detector flags the
separated track when `lang_id_entropy >= threshold`:

- if `lang_id_entropy >= threshold` -> flag hallucinated -> route MIXED (cpWER = `always_mixed_cpwer`)
- else -> route SEPARATED (cpWER = `always_separated_cpwer`)

### Calibration rule

Sweep threshold over the grid {0.00, 0.01, 0.02, ..., 2.00} (201 candidates).
For each candidate `t`, flag = `score >= t`; compute sensitivity = TP/(TP+FN)
and specificity = TN/(TN+FP) on the calibration set. Select the threshold with
specificity >= 0.90 and maximal sensitivity. Tie-breaker: higher specificity,
then lower threshold (more sensitive). This is RQ25's `calibrate_threshold`
exactly, re-implemented as the testable helper
`calibrate_threshold_at_spec(scores, labels, grid, target_spec)`.

### Bootstrap aggregation (RQ44)

Draw B=10,000 bootstrap resamples (seed=42) of the n=77 windows **with
replacement**. Each resample is 77 indices drawn from {0, ..., 76}. On each
resample:

1. Calibrate the lang-id entropy threshold (≥ 90% specificity, max sensitivity)
   on the resampled windows.
2. Record the calibrated threshold.
3. Identify the **out-of-bag (OOB) windows** — those NOT drawn in the resample.
   The expected OOB size is `n · (1 − 1/n)^n` = 28.14 windows (observed mean
   28.22); i.e. ~37% of windows are held out per resample.
4. Compute the corrected router's cpWER on the OOB windows at the resample's
   calibrated threshold (this is the held-out cpWER for that resample).

Aggregate across the 10,000 resamples:

- **Threshold distribution**: median, mean, std, 2.5/97.5 percentile interval,
  min, max, mode(s), and the full value-by-value count table.
- **OOB cpWER distribution**: median, mean, 2.5/97.5 percentile interval, IQR,
  min, max, fraction below 1.10, fraction below the in-sample cpWER.

The OOB evaluation is the key out-of-sample signal: each resample's threshold is
calibrated on its in-bag windows and evaluated on the windows it did NOT see,
giving 10,000 honest held-out cpWER measurements (one per resample).

### Statistics

B=10,000 bootstrap resamples, seed=42. numpy + stdlib only (no scipy / sklearn /
Whisper / meeteval). The OOB cpWER distribution is reported as percentiles; no
parametric CI is assumed.

## Results

### In-sample reproduction (calibrate + evaluate on all 77 windows)

To verify the script reproduces RQ25 before bootstrapping:

| quantity | this study | RQ25 reported |
|---|---:|---:|
| threshold | 0.380 | 0.38 |
| sensitivity | 0.9459 (35/37) | 0.946 |
| specificity | 0.9250 (37/40) | 0.925 |
| corrected cpWER | 1.043290 | 1.043 |

The in-sample threshold (0.38) and cpWER (1.043) match RQ25 exactly. This is the
value the bootstrap median is compared against.

### Bootstrap threshold distribution (B=10,000)

| quantity | value |
|---|---:|
| median | **0.380** |
| mean / std | 0.472 / 0.265 |
| 2.5 / 97.5 percentile | [0.010, 0.950] |
| interval width | **0.940** |
| min / max | [0.010, 0.950] |
| mode (most frequent) | 0.380 (6044 / 10000 = 60.4%) |
| number of distinct thresholds | 6 |

The full value-by-value table (sorted by frequency) is in the executive summary
above. The distribution is 6-modal:

- **0.38** (60.4%) — the dominant mode, equal to the in-sample threshold.
- **0.87** (14.5%) and **0.95** (8.4%) — *high* thresholds that miss
  hallucinated windows with entropy in the 0.38–0.95 band (routed to SEPARATED →
  catastrophic `always_separated_cpwer`).
- **0.01** (9.0%) — the *low* "Mode S catch" threshold RQ25's 50/50 split landed
  on; catches the low-entropy Mode S windows but over-flags clean windows.
- **0.33** (5.7%) — equivalent to 0.38 on this data (both within RQ25's H25c
  range [0.327, 0.491]); produces the same operating point.
- **0.84** (1.9%) — a rare high-threshold mode.

The mode at 0.38 captures only 60% of resamples — the calibration rule does not
converge to a single operating point. The 2.5/97.5 percentile interval
[0.010, 0.950] (width 0.940) is 4.7× the H44b kill threshold of 0.20. **Bagging
does not stabilise the threshold; it exposes the calibration rule's sensitivity
to resample composition.**

### Out-of-bag cpWER distribution (held-out per resample)

| quantity | value |
|---|---:|
| n valid resamples | 10000 / 10000 |
| mean OOB size | 28.22 windows (expected 28.14) |
| median | **1.0556** |
| mean | 1.0692 |
| 2.5 / 97.5 percentile | [1.0000, 1.2083] |
| IQR [25%, 75%] | [1.0309, 1.0968] |
| min / max | [1.0000, 1.3333] |
| fraction < 1.10 | 0.7604 |
| fraction < in-sample cpWER (1.043) | 0.3810 |

The median OOB cpWER (1.056) is below the 1.10 kill threshold (H44c supported),
but the distribution has a heavy upper tail: the 97.5th percentile is 1.208, the
max is 1.333, and **24% of resamples exceed 1.10**. The bimodality is driven by
the threshold mode (see the table in the executive summary):

- Resamples that calibrate a "good" threshold (0.33 or 0.38, 66.1% of the total)
  have median OOB cpWER 1.043 with 97% below 1.10.
- Resamples that calibrate a "bad" threshold (0.01, 0.84, 0.87, or 0.95, 33.9%)
  have median OOB cpWER 1.10–1.17 with only 8–46% below 1.10.

The 0.01 "Mode S catch" mode — the threshold RQ25's 50/50 split happened to
land on — gives median OOB cpWER **1.107** (above 1.10), with only 43% of
0.01-resamples below 1.10. RQ25's reported test cpWER of 1.022 at threshold 0.01
was therefore a lucky split (its 5 over-flagged clean windows all had tied
`mixed_cpwer == separated_cpwer == 1.0`), exactly as RQ25's limitations section
warned. RQ44 confirms this quantitatively: the 0.01 threshold is a *bad*
operating point on average over 899 bootstrap resamples.

## Hypothesis Verdicts

- **H44a — median bootstrap threshold in [0.30, 0.50]: SUPPORTED.** The
  bootstrap median threshold is 0.380, exactly RQ25's in-sample value and
  squarely in the [0.30, 0.50] deployable band. The median is stable because the
  0.38 mode dominates the distribution (60.4% of resamples). This is the
  actionable result: the bootstrap median identifies 0.38 as the central
  operating point, justifying deployment of the in-sample threshold as the
  bagged estimate rather than as a single-pool artefact.

- **H44b — 2.5/97.5 percentile interval width < 0.20: KILLED.** The interval is
  [0.010, 0.950], width 0.940 — 4.7× the kill threshold. Bagging does NOT
  stabilise the threshold. The calibration rule produces 6 distinct operating
  points across the 10,000 resamples, with the dominant mode (0.38) capturing
  only 60% of resamples. The instability is fundamental: the "max sensitivity at
  ≥ 90% specificity" rule's output is determined by which Mode S and
  high-entropy-clean windows land in each resample, and bagging averages over
  this sensitivity rather than removing it. The kill is the central negative
  finding: **a stable threshold cannot be identified from n=77 windows by any
  resampling method**; the threshold is not a single number but a distribution.

- **H44c — median held-out (OOB) cpWER < 1.10: SUPPORTED (with tail-risk
  caveat).** The median OOB cpWER is 1.056, below the 1.10 kill threshold. But
  the distribution is bimodal: 76% of resamples are below 1.10 (the "good
  threshold" resamples), 24% are above (the "bad threshold" resamples, up to
  1.333). The 97.5th percentile (1.208) exceeds 1.10. The median passes because
  the good-threshold mode (66% of resamples) has robust cpWER (median 1.043), but
  the 34% of resamples that calibrate a bad threshold would, on a new meeting
  without cpWER ties, push the router above 1.10. H44c is supported *on this
  meeting* because the good mode dominates; it should not be read as a guarantee
  that the router transfers.

## Honest Limitations

1. **Single meeting, 77 windows.** M_R003S02C01 is 1 of 20 AISHELL-4 test
   meetings. The bootstrap resamples all draw from the same 77 windows, so the
   6-modal threshold distribution is a property of *this meeting's* window
   composition (in particular its 2 Mode S windows and its high-entropy clean
   windows with tied cpWER). A different meeting would have a different
   threshold distribution. The bootstrap answers "is the threshold stable under
   resampling of this meeting?" — it does NOT answer "does the threshold
   transfer to a new meeting?". Multi-meeting calibration remains the required
   next step (as RQ25 also concluded).

2. **Bagging reveals, not cures, bimodality.** H44b is killed: the bootstrap
   percentile interval is 0.94 wide. This is not a failure of bagging as a
   technique — it is the correct diagnosis that the calibration rule is
   non-identifiable from n=77. The 6 modes correspond to genuine operating-point
   ambiguities (catch Mode S at the cost of over-flagging, or miss it; catch
   high-entropy hallucinations at 0.38 or let some through at 0.87). No
   resampling method can resolve this without more data or a complementary
   detector (RQ19, Mode S detector) that removes the low-entropy hallucination
   ambiguity.

3. **OOB cpWER bimodality is meeting-specific.** The 76% / 24% split of OOB
   cpWER below / above 1.10 is driven by this meeting's cpWER ties. RQ25 showed
   that 5 of the over-flagged clean windows have `mixed_cpwer == separated_cpwer
   == 1.0`, so over-flagging is "free" on them. On a new meeting without such
   ties, the bad-threshold resamples would degrade cpWER further. The H44c
   "support" is therefore conditional on the good-threshold mode dominating; the
   24% tail is the real deployability risk.

4. **Median threshold vs. mode threshold.** H44a tests the *median* (0.38), which
   coincides with the *mode* (0.38) here because the distribution is
   right-skewed but the dominant mode is at the low end. If the bad-threshold
   mass were larger, the median could shift out of [0.30, 0.50] while the mode
   stayed at 0.38. The deployable recommendation (use 0.38) rests on the *mode*
   being the good operating point, not merely the median landing in band; the
   two coincide here but may not on a larger corpus.

5. **Calibration rule fixed at "max sensitivity at ≥ 90% specificity".** A
   different rule (e.g. maximise Youden's J, or fix specificity at 95%) would
   produce a different threshold distribution. The 6-modality is partly a
   property of this rule's discontinuous behaviour at the specificity boundary.
   A smoother rule (e.g. maximise F1, or use a parametric ROC fit) might reduce
   the number of modes but would not change the fundamental identifiability
   problem at n=77.

6. **cpWER is utterance-level (whole Chinese string = 1 token).** RQ30
   (`results/frontier/meeteval_cpwer_validation/`, PR #935) showed the project's
   cpWER pipeline passes each speaker's full Chinese utterance as a single
   token, so cpWER > 1.0 measures *extra inserted speaker-streams* per window,
   not character-level transcription accuracy. All thresholds, OOB cpWERs, and
   the 1.10 kill threshold here are at the utterance level. A char-level
   re-validation (RQ31/RQ35) is the required follow-up before claiming the
   bagged threshold generalises at character granularity.

7. **No deployable routing input from cpWER.** Per the project's hard safety
   rules, cpWER / references are not used as routing input — the lang-id entropy
   detector is computed only from the hypothesis transcripts (the deployable
   signal surface). The hallucination label (`always_separated_cpwer > 1.0`) is
   used only for calibration and OOB evaluation, not for routing.

8. **OOB size varies per resample.** Each resample holds out a different OOB set
   (mean 28.22, but ranging from a few to ~40 windows). The OOB cpWER for a
   resample with a small OOB set is noisier. The median over 10,000 resamples
   smooths this, but individual OOB cpWER values (especially the max 1.333) come
   from small-OOB resamples and should be read as distributional tails, not
   point estimates.

## Reproducibility

- Script:
  `/opt/homebrew/bin/python3 results/frontier/bootstrap_threshold_stability/bootstrap_threshold_analysis.py`
  (deterministic; numpy + stdlib only; no scipy / sklearn / Whisper / meeteval).
  Runtime ≈ 13 s on macOS for B=10,000.
- Tests: `/opt/homebrew/bin/python3 -m unittest tests.test_bootstrap_threshold -v`
  (38 tests; pins `bootstrap_indices`, `calibrate_threshold_at_spec`,
  `percentile_interval`, `out_of_bag_cpwer`, detector primitives, module
  constants, and an in-sample reproduction of RQ25's 0.38 threshold).
- Outputs:
  - `bootstrap_threshold_results.csv` — per-bootstrap table (bootstrap_id,
    threshold, n_in_bag, n_oob, n_oob_flagged_mixed, n_oob_separated,
    oob_cpwer). 10,000 rows.
  - `bootstrap_threshold_results.json` — full summary (in-sample reproduction,
    threshold distribution with modes, OOB cpWER distribution, hypothesis
    verdicts) plus `per_bootstrap` arrays (thresholds, oob_cpwer, n_oob) for
    reproducibility.
- Bootstrap: B=10,000, seed=42.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

RQ25 closed one loop and opened another: the corrected router's cpWER recovers
under a 50/50 split (test cpWER 1.022), but the threshold does not (train
threshold 0.01 vs RQ16's 0.409). RQ25's headline caveat was that "a deployable
threshold needs a larger calibration set so that the operating point is not
determined by whether one or two Mode S windows happen to land in the train
half."

RQ44 tests whether bootstrap aggregation can substitute for a larger calibration
set. The answer is **no for stability, yes for median identification**:

1. **Bagging does not stabilise the threshold (H44b killed).** The bootstrap
   threshold distribution is 6-modal over [0.01, 0.95] (width 0.94). This
   generalises RQ25's single-split bimodality (0.38 / 0.01) to a full
   distribution: the calibration rule is non-identifiable from n=77, and no
   resampling method resolves this. The threshold is genuinely a distribution,
   not a number.

2. **But the bootstrap median (0.38) is the stable operating point (H44a
   supported).** 60.4% of resamples calibrate 0.38, and the median lands there.
   This is the same value RQ16/RQ25 found in-sample — but RQ44 justifies it as
   the *bootstrap median* rather than as a single-pool artefact. The deployable
   recommendation is to **deploy 0.38 directly** and NOT re-calibrate on a small
   train split (which has a 34% chance of landing on a bad mode).

3. **The OOB cpWER links threshold modes to cpWER outcomes (H44c supported with
   tail risk).** The new cross-tabulation (threshold mode → median OOB cpWER)
   shows the good band (0.33–0.38) gives 97% of resamples below 1.10, while the
   bad band (0.01, 0.84–0.95) gives only 8–46% below 1.10. Crucially, RQ25's
   0.01 threshold — the one its 50/50 split landed on — is a *bad* operating
   point on average (median OOB cpWER 1.107 > 1.10). RQ25's lucky 1.022 test
   cpWER was a coincidence of that split's tied-cpWER clean windows, exactly as
   RQ25's limitations warned; RQ44 quantifies this over 899 resamples.

The concrete next steps RQ44 points to:

1. **Deploy 0.38 as the lang-id entropy threshold.** The bootstrap median is the
   stable central estimate; re-calibration on a small split is riskier than
   using the bagged value. This unblocks the corrected router for deployment on
   meetings similar to M_R003S02C01, with the caveat that the OOB cpWER tail
   (24% > 1.10) reflects the threshold's irreducible uncertainty at n=77.

2. **Multi-meeting calibration corpus.** The 6-modality is driven by this
   meeting's 2 Mode S windows and its high-entropy clean windows. A corpus of
   hundreds of windows across multiple AISHELL-4 meetings would dilute the
   Mode S prevalence and let the operating point converge. The single-meeting
   external validation (PR #890) does not permit this; multi-meeting staging
   (RQ7 external-validation slice work) is the prerequisite.

3. **Mode S detector (RQ19) is the complementary fix.** The 0.01 mode exists
   solely because the lang-id detector cannot distinguish Mode S (monoscript
   Chinese semantic hallucination) from clean Chinese on the entropy axis. A
   Mode S detector that catches those 2 windows separately would let the lang-id
   threshold stay at 0.38 (where it is stable) and remove the low-threshold
   mode, collapsing the distribution toward its good band.

4. **Report thresholds as distributions, not point estimates.** RQ16 reported
   0.409 as a single number; RQ25 showed that number is split-dependent; RQ44
   shows it is resample-dependent (6 modes). Future threshold reports should
   present the bootstrap distribution (median + percentile interval + mode
   table) rather than a point estimate, so downstream readers see the
   uncertainty. The `threshold_distribution` block in the results JSON is the
   template for this.
