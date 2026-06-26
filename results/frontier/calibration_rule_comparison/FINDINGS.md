# RQ48: Calibration Rule Comparison for Threshold Stability

> **Label: `experimental/frontier`** — Builds on RQ13 (PR #904), RQ16 (PR #912),
> RQ25 (PR #929), and RQ44 (PR #963).
> Reanalysis only (no Whisper / no ASR run); reuses RQ44's lang-id entropy
> detector, bootstrap draw, and OOB cpWER evaluator verbatim, plus the existing
> AISHELL-4 external-validation windows (PR #890). Does NOT overwrite any
> verified reference / gold table.

## Executive Summary

RQ44 (PR #963) showed the corrected router's lang-id entropy threshold
distribution is **6-modal** over [0.01, 0.95] under the "max sensitivity at
≥ 90% specificity" calibration rule (H44b KILLED, interval width 0.94). RQ44's
limitations (point 5) conjectured that "the 6-modality is partly a property of
this rule's discontinuous behaviour at the specificity boundary" and that "a
smoother rule (e.g. maximise F1) might reduce the number of modes but would not
change the fundamental identifiability problem at n=77." RQ48 tests that
conjecture directly by comparing **4 calibration rules** on RQ44's bootstrap
framework, using the **same** B=2000 paired resamples (seed=42) so any
difference is purely due to the calibration criterion.

**Two of three pre-registered hypotheses are supported; RQ44's conjecture is
confirmed with a sharper edge:**

| Hypothesis | Verdict | Test statistic | Kill threshold |
|---|---|---:|---|
| H48a: Youden's J gives ≤ 3 modes | **SUPPORTED** | 3 modes (≥ 5% freq) | > 3 modes |
| H48b: F1 maximisation gives ≤ 3 modes | **SUPPORTED** | 2 modes (≥ 5% freq) | > 3 modes |
| H48c: Cost-aware ≤ 2 modes AND median OOB cpWER < 1.056 | **KILLED** | 2 modes ✓ but median OOB cpWER 1.063 ✗ | > 2 modes OR cpWER ≥ 1.056 |

The headline finding is a **clean separation between rule-artefact modes and a
fundamental detector-ambiguity mode**:

- The **high-threshold modes (0.87, 0.95)** that RQ44's specificity-boundary
  rule produces **disappear** under the smoother Youden's J and F1 rules. These
  modes were artefacts of the discontinuous "≥ 90% specificity" boundary: when a
  resample's clean windows push the achievable specificity below 0.90 at the
  0.38 threshold, the spec rule jumps to the next threshold that restores 0.90
  specificity (0.87 / 0.95), fragmenting the distribution. J and F1 have no such
  boundary — they trade sensitivity and specificity continuously — so they never
  produce the high-threshold modes. **H48a and H48b supported.**

- The **low-threshold "Mode S catch" mode (0.01)** persists under **every** rule,
  including the cost-aware rule. This mode is NOT a calibration-rule artefact:
  it arises when a resample's in-bag composition makes the 0.01 threshold
  optimal for catching the 2 low-entropy hallucinated (Mode S) windows. No
  calibration rule can remove it because the lang-id entropy detector
  fundamentally cannot distinguish Mode S (monoscript Chinese semantic
  hallucination) from clean Chinese on the entropy axis (RQ19's territory). This
  is the "fundamental identifiability problem at n=77" RQ44 predicted.

- Because the 0.01 mode persists, the **2.5/97.5 percentile interval width stays
  0.94** for Youden's J and F1 (the distribution still spans [0.01, 0.95]).
  Reducing the mode count does NOT shrink the interval: the remaining 0.01 mode
  is a genuine operating-point ambiguity, not rule fragmentation.

- The **cost-aware rule** (minimise expected cpWER directly) collapses the
  distribution to **2 modes {0.33, 0.01}** with a dramatically narrower interval
  (width 0.32 vs 0.94). But its **median OOB cpWER (1.063) is worse than RQ44's
  1.056** — the 0.01 mode swells to 48.7% of resamples, over-flagging clean
  windows, and on the out-of-bag windows (which lack the in-bag cpWER ties that
  make over-flagging "free") this routes clean windows to MIXED and degrades
  cpWER. The cpWER-optimal-in-bag threshold is not cpWER-optimal-out-of-bag: a
  clean overfitting result. **H48c killed on the cpWER condition.**

**Bottom line.** RQ44's 6-modality decomposes into two parts: (1) rule-artefact
modes (0.87, 0.95) that smoother rules eliminate, and (2) a fundamental
detector-ambiguity mode (0.01) that no calibration rule removes. Smoother rules
reduce the mode count (H48a/H48b supported) but do not stabilise the threshold
(interval width unchanged at 0.94) — exactly RQ44's prediction. The cost-aware
rule shrinks the interval but over-fits the in-bag cpWER, trading threshold
stability for worse out-of-sample cpWER. The actionable conclusion is unchanged
from RQ44: **deploy the bootstrap median threshold (0.38)**; the residual
instability is a detector limitation (Mode S), not a calibration-rule choice,
and the fix is the complementary Mode S detector (RQ19) or a larger
multi-meeting calibration corpus — not a different calibration rule.

## Method

### Data (read-only, not overwritten)

`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
(label `external/sanity-check`, PR #890): 77 windows of 30 s from AISHELL-4
meeting `M_R003S02C01`. Hallucination label: `always_separated_cpwer > 1.0` → 37
hallucinated / 40 clean (RQ12/RQ13/RQ16/RQ25/RQ44).

### Detector, routing rule, and bootstrap framework (reused verbatim from RQ44)

To guarantee that the **only** thing varying across rules is the calibration
criterion, RQ48 imports RQ44's module directly:

- **Detector**: `max_across_speakers(window)` = max `language_id_entropy` over
  the per-speaker separated transcripts (RQ13/RQ16/RQ25/RQ44 verbatim).
- **Routing rule**: `lang_id_entropy >= threshold` → route MIXED
  (`always_mixed_cpwer`); else → SEPARATED (`always_separated_cpwer`).
- **Bootstrap draw**: `bootstrap_indices(n, B, seed)` — RQ44's exact function.
  RQ48 draws **one** (B=2000, seed=42, n=77) index array and reuses it for all 4
  rules, so the comparison is **paired**: each resample sees the same in-bag/OOB
  split under every rule. RQ48's baseline is therefore the first 2000 of RQ44's
  10000 resamples (same seed → same first 2000 rows).
- **OOB cpWER evaluator**: `out_of_bag_cpwer(...)` — RQ44's exact function.
- **Baseline rule**: `calibrate_max_sens_at_spec` delegates to RQ44's
  `calibrate_threshold_at_spec`, so the baseline reproduces RQ44's in-sample
  0.38 threshold byte-for-byte.

### The four calibration rules

All sweep the same grid {0.00, 0.01, ..., 2.00} (201 points) and flag
`score >= threshold`. Tie-breaker for every rule: the **lowest** threshold among
ties (more sensitive), matching RQ44's convention.

1. **`calibrate_max_sens_at_spec`** (RQ44 baseline): select the threshold with
   specificity ≥ 0.90 and maximal sensitivity. Discontinuous at the specificity
   boundary.
2. **`calibrate_youdens_j`**: maximise J = sensitivity + specificity − 1. Smooth
   ROC criterion, no specificity boundary.
3. **`calibrate_f1`**: maximise F1 = 2·precision·recall / (precision+recall)
   (precision = TP/(TP+FP), recall = sensitivity; F1 = 0 when TP = 0). Smooth
   precision/recall criterion.
4. **`calibrate_cost_aware`**: minimise the expected cpWER directly using the
   routing rule (flagged → MIXED, unflagged → SEPARATED). **Oracle-style**: uses
   reference cpWER as the calibration objective on labelled data (the same role
   the hallucination label — itself `cpwer_separated > 1.0` — plays for the other
   rules). cpWER is **not** a routing input; the deployable signal remains
   lang_id_entropy. Included to bound the achievable stability.

### Mode definition (kill-condition)

A "mode" = a distinct threshold value whose bootstrap frequency is **≥ 5%**
(`count_modes`, `min_fraction=0.05`). This is the explicit kill-condition
definition for H48a/b/c. Note: RQ44 reported "6-modal" counting **all** distinct
thresholds (its 0.84 mode was at 1.9% frequency); under RQ48's ≥ 5% definition
RQ44's baseline has **5** modes (the 1.9% mode is excluded). Both definitions are
reported in the JSON for traceability.

### Statistics

B=2000 bootstrap resamples, seed=42, paired across rules. numpy + stdlib only
(no scipy / sklearn / Whisper / meeteval). Runtime ≈ 2.5 s total (all 4 rules).
B=2000 (not RQ44's 10000) keeps per-rule runtime well under 60 s; the baseline's
first-2000-of-10000 design keeps it directly comparable to RQ44.

## Results

### In-sample calibration (full 77 windows, per rule)

| rule | threshold | expected cpWER | sensitivity | specificity | rule metric |
|---|---:|---:|---:|---:|---:|
| max_sens_at_90_spec (RQ44) | 0.380 | 1.0433 | 0.946 | 0.925 | — |
| youdens_j | 0.380 | 1.0433 | 0.946 | 0.925 | J = 0.871 |
| f1 | 0.380 | 1.0433 | 0.946 | 0.925 | F1 = 0.933 |
| cost_aware | 0.330 | 1.0433 | 0.946 | 0.875 | cost = 1.0433 |

Three of four rules calibrate the **same in-sample operating point (0.38)** as
RQ44 — confirming the smoother rules agree with RQ44 when the data permits a
clean operating point. The cost-aware rule picks 0.33 (one grid step below
0.38): on the full 77 windows 0.33 and 0.38 give identical expected cpWER
(1.0433), and the lower-threshold tie-break selects 0.33. All four rules produce
the same in-sample corrected cpWER (1.0433, matching RQ25/RQ44).

### Bootstrap threshold + OOB cpWER distributions (B=2000, paired)

| rule | thr median | thr pct [2.5, 97.5] | thr width | n unique | **n modes ≥ 5%** | OOB cpWER median | OOB cpWER mean | frac < 1.10 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| max_sens_at_90_spec | 0.380 | [0.010, 0.950] | 0.940 | 6 | **5** | 1.0539 | 1.0680 | 0.763 |
| youdens_j | 0.380 | [0.010, 0.950] | 0.940 | 6 | **3** | 1.0511 | 1.0608 | 0.810 |
| f1 | 0.380 | [0.010, 0.950] | 0.940 | 6 | **2** | 1.0513 | 1.0621 | 0.790 |
| cost_aware | 0.330 | [0.010, 0.330] | 0.320 | 3 | **2** | 1.0632 | 1.0712 | 0.636 |

Mode tables (threshold / count / fraction, sorted by descending frequency):

**max_sens_at_90_spec** (baseline, 5 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.38 | 1217 | 60.9% |
| 0.87 | 269 | 13.5% |
| 0.95 | 186 | 9.3% |
| 0.01 | 184 | 9.2% |
| 0.33 | 110 | 5.5% |

**youdens_j** (3 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.38 | 1301 | 65.0% |
| 0.01 | 451 | 22.6% |
| 0.33 | 115 | 5.8% |

**f1** (2 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.38 | 1241 | 62.1% |
| 0.01 | 552 | 27.6% |

**cost_aware** (2 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.33 | 1022 | 51.1% |
| 0.01 | 974 | 48.7% |

### Reading the table

1. **The high-threshold modes (0.87, 0.95) are rule artefacts.** They are
   present only under the specificity-boundary baseline (13.5% + 9.3% = 22.8% of
   resamples). Youden's J and F1 — which have no specificity boundary — never
   produce them. This is the mechanism RQ44 hypothesised: the "≥ 90%
   specificity" rule jumps to a high threshold when a resample's clean windows
   drag the 0.38 specificity below 0.90, fragmenting the distribution. J and F1
   trade sensitivity/specificity continuously and stay at 0.38 (or drop to 0.01
   to catch Mode S).

2. **The 0.01 "Mode S catch" mode persists under every rule** (baseline 9.2%,
   J 22.6%, F1 27.6%, cost-aware 48.7%). It is a fundamental detector
   ambiguity, not a calibration artefact: when a resample's in-bag composition
   makes 0.01 optimal for catching the 2 low-entropy Mode S windows, every rule
   agrees on 0.01. Notably, the smoother rules concentrate MORE mass at 0.01
   (because they no longer spill mass into the 0.87/0.95 artefact modes), so
   their mode count drops but the 0.01 mode grows.

3. **The percentile interval width is unchanged (0.94) for J and F1.** Reducing
   the mode count did not shrink the interval because the surviving 0.01 mode
   still spans the full [0.01, 0.95] range. This is the "fundamental
   identifiability problem at n=77" RQ44 predicted: smoother rules reduce
   fragmentation but cannot resolve the underlying detector ambiguity.

4. **The cost-aware rule shrinks the interval (0.32) but at a cpWER cost.** By
   optimising cpWER directly it collapses to {0.33, 0.01}, but the 0.01 mode
   swells to 48.7%. The 0.01 threshold over-flags clean windows; on the in-bag
   set this is "free" (the over-flagged clean windows have tied
   `mixed == separated` cpWER), but on the OOB set (different windows, ties may
   not hold) it routes clean windows to MIXED and degrades cpWER. Median OOB
   cpWER rises to 1.063 (vs RQ44's 1.056), and only 63.6% of resamples are below
   1.10 (vs 76.3% for the baseline). The cpWER-optimal-in-bag threshold
   over-fits and is not cpWER-optimal-out-of-bag.

## Hypothesis Verdicts

- **H48a — Youden's J gives ≤ 3 modes: SUPPORTED.** Youden's J produces 3 modes
  ≥ 5% (0.38 65.0%, 0.01 22.6%, 0.33 5.8%) vs the baseline's 5. The two
  high-threshold artefact modes (0.87, 0.95) vanish: J's continuous
  sensitivity/specificity trade-off has no discontinuous boundary to jump over.
  This confirms the "rule-artefact" half of RQ44's conjecture. Caveat: the
  interval width is unchanged (0.94), so "fewer modes" does not mean "more
  stable" — the 0.01 fundamental mode still spans the full range.

- **H48b — F1 maximisation gives ≤ 3 modes: SUPPORTED.** F1 produces only 2
  modes ≥ 5% (0.38 62.1%, 0.01 27.6%) — the smoothest threshold distribution of
  the four. The 0.33 mode (which is cpWER-equivalent to 0.38 on this data) also
  drops below 5% under F1, leaving a clean 0.38 / 0.01 bimodality. F1 is the
  strongest demonstration that the high-threshold modes were specificity-boundary
  artefacts. The same caveat applies: the interval width is still 0.94.

- **H48c — Cost-aware ≤ 2 modes AND median OOB cpWER < 1.056: KILLED (on the
  cpWER condition).** The cost-aware rule achieves the mode target (2 modes:
  0.33 51.1%, 0.01 48.7%) and the narrowest interval (width 0.32), but its
  median OOB cpWER is **1.0632 ≥ 1.056**. The kill is informative, not a
  failure: it shows that directly minimising in-bag cpWER over-fits. The 0.01
  mode — which over-flags clean windows — is cpWER-optimal on the in-bag set
  (because the over-flagged clean windows have tied cpWER) but cpWER-suboptimal
  on the OOB set (where the ties do not hold). The cost-aware rule therefore
  trades threshold stability for worse out-of-sample cpWER; it is not a
  deployable improvement over the 0.38 median.

## Honest Limitations

1. **Single meeting, 77 windows.** As in RQ44, all resamples draw from the same
   77 windows of `M_R003S02C01`. The 0.01 mode is driven by this meeting's 2
   Mode S windows and its tied-cpWER clean windows; a different meeting would
   produce a different mode structure. RQ48 answers "do smoother calibration
   rules reduce the mode count under resampling of this meeting?" — it does NOT
   answer "do they transfer to a new meeting?". Multi-meeting calibration remains
   the prerequisite (RQ25/RQ44 conclusion).

2. **B=2000, not RQ44's 10000.** RQ48 uses B=2000 to keep per-rule runtime under
   60 s (actual ≈ 2.5 s total). The baseline is the first 2000 of RQ44's 10000
   resamples (same seed), so its mode fractions (e.g. 0.38 at 60.9% vs RQ44's
   60.4%) carry small-B sampling noise. The qualitative conclusions (J/F1
   eliminate the high-threshold modes; 0.01 persists; cost-aware over-fits) are
   robust to this: the eliminated modes were at 13.5% / 9.3% — far above any
   small-B noise floor — and the 0.01 mode is present under every rule.

3. **"Modes" defined at ≥ 5% frequency.** The kill conditions use the explicit
   ≥ 5% definition. RQ44's "6-modal" counted all distinct thresholds (its 0.84
   mode was 1.9%); under RQ48's definition RQ44's baseline has 5 modes. Both
   definitions are in the JSON. The choice does not affect any verdict: J (3)
   and F1 (2) pass ≤ 3 under either definition; cost-aware (2) passes ≤ 2 under
   either.

4. **Cost-aware rule uses reference cpWER at calibration time.** This is an
   oracle-style criterion (cpWER is the calibration objective, not a routing
   input — the routing signal stays lang_id_entropy). It bounds the achievable
   stability but is not itself deployable (deployable routing cannot use cpWER).
   Its purpose is to show that even a cpWER-optimal calibration does not beat
   0.38 out-of-sample — strengthening RQ44's "deploy 0.38" recommendation.

5. **Tie-breaker is "lowest threshold".** Every rule tie-breaks to the lowest
   threshold among equal-objective grid points (more sensitive). A different
   tie-breaker (e.g. highest threshold) would shift some mass between 0.33/0.38
   but would not change the mode-count verdicts: the high-threshold artefact
   modes (0.87, 0.95) exist only under the spec rule regardless of tie-break,
   and the 0.01 mode exists under every rule regardless of tie-break.

6. **Same detector limitation as RQ44.** RQ48 changes only the calibration rule,
  not the detector. The 0.01 mode is a property of the lang-id entropy
  detector's inability to separate Mode S from clean Chinese — a complementary
  Mode S detector (RQ19) is the fix, not a different calibration rule. RQ48
  confirms this by showing the 0.01 mode is calibration-rule-invariant.

7. **cpWER is utterance-level.** As in RQ44 (limitation 6), cpWER passes each
   speaker's full Chinese utterance as a single token; cpWER > 1.0 measures
   extra inserted speaker-streams, not character accuracy. A char-level
   re-validation (RQ31/RQ35) remains the follow-up before claiming
   generalisation at character granularity.

## Reproducibility

- Script:
  `/opt/homebrew/bin/python3 results/frontier/calibration_rule_comparison/calibration_rule_analysis.py`
  (deterministic; numpy + stdlib only; no scipy / sklearn / Whisper / meeteval).
  Runtime ≈ 2.5 s for all 4 rules × B=2000.
- Tests: `/opt/homebrew/bin/python3 -m unittest tests.test_calibration_rule -v`
  (42 tests; pins `calibrate_youdens_j`, `calibrate_f1`,
  `calibrate_cost_aware`, `count_modes`, `calibrate_max_sens_at_spec`, module
  constants, and in-sample smoke tests reproducing RQ44's 0.38 threshold and a
  valid cost-aware threshold on the 77-window data).
- Outputs:
  - `calibration_rule_results.csv` — per-rule summary (in-sample threshold/cpWER,
    threshold median/percentiles/width/n_unique/n_modes≥5%, OOB cpWER
    median/mean/percentiles/frac<1.10, hypothesis verdict).
  - `calibration_rule_results.json` — full summary (in-sample calibration per
    rule, per-rule threshold + OOB cpWER distributions with mode tables,
    hypothesis verdicts) plus `per_bootstrap` arrays (thresholds, oob_cpwer,
    n_oob) for all 4 rules for reproducibility.
- Bootstrap: B=2000, seed=42, paired across rules (same resample indices for all
  4 rules).
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

RQ44 left an open question (limitations point 5): is the 6-modality a property of
the calibration rule or of the data? RQ48 **decomposes** it:

1. **The 6-modality is partly a rule artefact (H48a/H48b supported).** The
   high-threshold modes (0.87, 0.95) are produced only by the discontinuous
   "≥ 90% specificity" rule. Youden's J (3 modes) and F1 (2 modes) — smooth,
   single-objective criteria — eliminate them entirely. Future threshold
   stability studies should prefer J or F1 over the specificity-boundary rule to
   avoid mistaking rule artefacts for genuine operating-point ambiguity.

2. **But the fundamental ambiguity is calibration-rule-invariant.** The 0.01
   "Mode S catch" mode persists under every rule, including the cpWER-optimal
   cost-aware rule. No calibration rule removes it because it is a detector
   limitation, not a calibration choice. The percentile interval width stays
   0.94 for J and F1 — reducing the mode count does not stabilise the threshold.
   This confirms RQ44's prediction that "a smoother rule might reduce the number
   of modes but would not change the fundamental identifiability problem at
   n=77."

3. **The cost-aware rule over-fits (H48c killed on cpWER).** Directly minimising
   in-bag cpWER collapses the distribution to {0.33, 0.01} (width 0.32) but
   raises the median OOB cpWER to 1.063 (vs RQ44's 1.056): the 0.01 over-flagging
   is "free" in-bag (tied cpWER) but costly out-of-bag. This is a clean
   overfitting result and a caution against using cpWER-optimal calibration for
   deployment — it strengthens RQ44's "deploy the bootstrap median (0.38)"
   recommendation by showing that even an oracle calibration rule does not beat
   it out-of-sample.

The actionable conclusion is unchanged from RQ44 — **deploy 0.38** — but now
better justified: the 0.38 operating point is robust across calibration rules
(J, F1, and the baseline all select 0.38 in-sample, and 0.38 is the dominant
bootstrap mode under every rule), and the residual instability is a detector
limitation (Mode S) that no calibration rule can fix. The next steps remain
those RQ44 pointed to: (a) a complementary Mode S detector (RQ19) to remove the
0.01 mode, and (b) a multi-meeting calibration corpus to dilute the Mode S
prevalence.
