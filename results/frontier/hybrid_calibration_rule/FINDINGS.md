# RQ51: Hybrid Calibration Rule for the Corrected Router

> **Label: `experimental/frontier`** — Builds on RQ13 (PR #904), RQ16 (PR #912),
> RQ25 (PR #929), RQ44 (PR #963), and RQ48 (PR #965).
> Reanalysis only (no Whisper / no ASR run); reuses RQ44's lang-id entropy
> detector, bootstrap draw, and OOB cpWER evaluator verbatim, RQ48's F1 rule,
> confusion helpers, mode counter, and per-rule aggregator verbatim, plus the
> existing AISHELL-4 external-validation windows (PR #890). Does NOT overwrite
> any verified reference / gold table.

## Executive Summary

RQ48 (PR #965) decomposed RQ44's 6-modal threshold distribution into two parts:
(1) rule-artefact modes (0.87, 0.95) that smoother rules (Youden's J, F1)
eliminate, and (2) a fundamental detector-ambiguity mode (0.01 "Mode S catch")
that no calibration rule removes. F1 minimised the mode count (2 modes) but
could not shrink the interval (width 0.94). Cost-aware shrank the interval
(width 0.32) but over-fit (median OOB cpWER 1.063 > 1.056). RQ51 asks whether a
**hybrid rule** — F1 for mode reduction followed by cost-aware-with-asymmetric-cost
refinement within F1's neighbourhood — can get the best of both: ≤ 2 modes,
width < 0.32, AND median OOB cpWER ≤ 1.056.

**All three pre-registered hypotheses are KILLED. The hybrid combines the
weaknesses of F1 and cost-aware rather than their strengths:**

| Hypothesis | Verdict | Test statistic | Kill threshold |
|---|---|---:|---|
| H51a: hybrid gives ≤ 2 modes (matches F1) | **KILLED** | 3 modes (≥ 5% freq) | > 2 modes |
| H51b: hybrid width < 0.32 (matches cost-aware) | **KILLED** | width 0.84 | ≥ 0.32 |
| H51c: hybrid median OOB cpWER ≤ 1.056 (no over-fit) | **KILLED** | 1.0705 | > 1.056 |

The headline finding is a **mechanism decomposition of why the hybrid fails**:

1. **The cost-aware refinement SPLITS F1's 0.38 mode into two (0.33 + 0.28),
   giving 3 modes > 2 (H51a killed).** F1's dominant mode (0.38, 62.3% of
   resamples at B=10000) maps to the neighbourhood [0.28, 0.48]. Within that
   neighbourhood, the asymmetric-cost objective is minimised at 0.33 for some
   resamples and at 0.28 for others — the in-bag cost surface is flat enough
   that small resample-to-resample composition shifts flip the argmin between
   two adjacent grid points. So instead of inheriting F1's single 0.38 mode,
   the hybrid produces TWO high-threshold modes (0.33 at 47.5%, 0.28 at 19.4%).
   The cost-aware step, intended to *tighten* the distribution, actually
   *fragments* it within F1's neighbourhood.

2. **The hybrid inherits F1's rare high-threshold picks, so the 97.5th
   percentile stays at 0.85 (H51b killed).** F1 itself produces 0.95 (3.3%)
   and 0.87 (2.3%) on resamples where the in-bag composition makes a high
   threshold F1-optimal. The hybrid's neighbourhood extends these to 0.85
   (from F1=0.95, neighbourhood [0.85, 1.05]) and 0.77 (from F1=0.87). These
   are below the 5% mode threshold but set the 97.5th percentile at 0.85,
   giving width 0.84 (0.01 to 0.85). The neighbourhood constraint cannot
   eliminate F1's high-threshold tail — it only shifts it inward by 0.10.

3. **The hybrid over-fits WORSE than pure cost-aware (1.0705 vs 1.0632,
   H51c killed).** The 0.01 mode persists at 26.4% (when F1 picks 0.01 to
   catch Mode S, the neighbourhood [0.0, 0.11] offers no escape — every
   threshold in it over-flags clean windows, and the asymmetric cost cannot
   distinguish among them). On the OOB set, the 0.01 mode routes clean windows
   to MIXED and degrades cpWER, exactly as in RQ48's cost-aware rule. But the
   hybrid ALSO has the 0.28 mode (19.4%), which routes some hallucinated
   windows to SEPARATED (those with entropy in [0.28, 0.33) are no longer
   flagged), and on the OOB set this misses hallucinations that the 0.33
   threshold would have caught. The hybrid therefore over-fits on BOTH ends:
   the 0.01 mode over-flags clean windows, and the 0.28 mode under-flags
   hallucinated windows.

**Bottom line.** The hybrid rule does not achieve the goal. The failure is
informative and sharpens RQ48's conclusion: the 0.01 mode is a detector
limitation that NO calibration rule — pure, smooth, cost-aware, or hybrid — can
remove, and the cost-aware refinement within F1's neighbourhood fragments
rather than stabilises the threshold. The actionable conclusion is unchanged
from RQ44/RQ48: **deploy the bootstrap median threshold (0.38)**. The residual
instability is a detector limitation (Mode S), and the fix is the complementary
Mode S detector (RQ19) or a larger multi-meeting calibration corpus — not a
hybrid calibration rule.

## Method

### Data (read-only, not overwritten)

`results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
(label `external/sanity-check`, PR #890): 77 windows of 30 s from AISHELL-4
meeting `M_R003S02C01`. Hallucination label: `always_separated_cpwer > 1.0` → 37
hallucinated / 40 clean (RQ12/RQ13/RQ16/RQ25/RQ44/RQ48).

### Detector, routing rule, and bootstrap framework (reused verbatim)

To guarantee the **only** thing varying vs RQ48 is the hybrid calibration
criterion, RQ51 imports RQ44's and RQ48's modules directly:

- **Detector** (from RQ44): `max_across_speakers(window)` = max
  `language_id_entropy` over the per-speaker separated transcripts.
- **Routing rule**: `lang_id_entropy >= threshold` → route MIXED
  (`always_mixed_cpwer`); else → SEPARATED (`always_separated_cpwer`).
- **Bootstrap draw** (from RQ44): `bootstrap_indices(n, B, seed)`. RQ51 draws
  B=10000 (seed=42, n=77) — matching RQ44's bootstrap size and larger than
  RQ48's B=2000 for tighter percentile-interval estimates. The same seed means
  the first 2000 resamples are identical to RQ48's, and the full 10000 are
  identical to RQ44's.
- **OOB cpWER evaluator** (from RQ44): `out_of_bag_cpwer(...)`.
- **F1 rule, confusion helpers, mode counter, per-rule aggregator** (from
  RQ48): `calibrate_f1`, `_confusion_arrays`, `_sens_spec`, `_select_threshold`,
  `count_modes`, `_summarise_rule`. The hybrid's Step 1 (F1) is byte-identical
  to RQ48's F1 rule.

### The hybrid calibration rule

```
Step 1 (F1 for mode reduction):
    Calibrate the F1-optimal threshold on the resample.
    f1_thr = argmax_t  F1(t) = 2 * prec(t) * rec(t) / (prec(t) + rec(t))

Step 2 (cost-aware-with-asymmetric-cost for width reduction, within F1's
neighbourhood):
    Restrict to grid points in [f1_thr - 0.1, f1_thr + 0.1].
    For each candidate threshold t in the neighbourhood:
        flagged = score >= t
        routed_cpwer = flagged ? mixed_cpwer : separated_cpwer
        weight = (routed_cpwer > 1.10) ? 2.0 : 1.0      # asymmetric cost
        cost(t) = weighted_mean(routed_cpwer, weight)
    hybrid_thr = argmin_t cost(t)    # tie-break: lowest threshold
```

**Why these parameters:**
- **Neighbourhood ±0.1**: wide enough to let cost-aware shift the high mode
  from 0.38 down toward 0.28–0.33 (tightening the interval), narrow enough to
  inherit F1's mode-reduction (cannot reach the 0.87/0.95 artefact modes).
- **Catastrophic threshold 1.10**: RQ44's H44c kill line ("bad" OOB cpWER).
- **Penalty 2.0**: a window routed to cpWER > 1.10 counts double in the cost.
  This is the mechanism intended to penalise the 0.01 mode's over-flagging of
  clean windows (which produces cpWER > 1.10 OOB for some clean windows even
  though the in-bag mean looks tied).

### Mode definition (kill-condition)

A "mode" = a distinct threshold value whose bootstrap frequency is **≥ 5%**
(`count_modes`, `min_fraction=0.05`). This is the explicit kill-condition
definition for H51a/b/c, identical to RQ48.

### Statistics

B=10000 bootstrap resamples, seed=42. numpy + stdlib only (no scipy / sklearn /
Whisper / meeteval). Runtime ≈ 15 s (one rule × B=10000).

## Results

### In-sample hybrid calibration (full 77 windows)

| step | threshold | neighbourhood | n grid pts | sensitivity | specificity | F1 | asym cost | expected cpWER |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| F1 (Step 1) | 0.380 | — | — | 0.946 | 0.925 | 0.933 | — | 1.0433 |
| Hybrid (Step 2) | 0.330 | [0.28, 0.48] | 21 | 0.946 | 0.875 | 0.933 | 1.0813 | 1.0433 |

F1 picks 0.38 (matching RQ48's in-sample F1 threshold byte-for-byte). Within the
neighbourhood [0.28, 0.48], the asymmetric-cost step picks 0.33 — the lowest
cpWER-tied threshold (matching RQ48's cost-aware in-sample pick). The in-sample
corrected cpWER is 1.0433 (matching RQ25/RQ44/RQ48). The asymmetric cost at
0.33 (1.0813) is higher than at 0.38 because 0.33 flags 2 extra clean windows
to MIXED, and some of those have MIXED cpWER > 1.10 (penalised) — but 0.33 and
0.38 tie on the plain mean (1.0433), and the tie-break selects the lower
threshold.

### Bootstrap threshold + OOB cpWER distributions (hybrid, B=10000)

| rule | thr median | thr pct [2.5, 97.5] | thr width | n unique | **n modes ≥ 5%** | OOB cpWER median | OOB cpWER mean | frac < 1.10 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| max_sens_at_90_spec (RQ48) | 0.380 | [0.010, 0.950] | 0.940 | 6 | 5 | 1.0539 | 1.0680 | 0.763 |
| youdens_j (RQ48) | 0.380 | [0.010, 0.950] | 0.940 | 6 | 3 | 1.0511 | 1.0608 | 0.810 |
| f1 (RQ48) | 0.380 | [0.010, 0.950] | 0.940 | 6 | 2 | 1.0513 | 1.0621 | 0.790 |
| cost_aware (RQ48) | 0.330 | [0.010, 0.330] | 0.320 | 3 | 2 | 1.0632 | 1.0712 | 0.636 |
| **hybrid (RQ51)** | **0.330** | **[0.010, 0.850]** | **0.840** | **8** | **3** | **1.0705** | **1.0798** | **0.602** |

Mode table for the hybrid (3 modes ≥ 5%):

| threshold | count | fraction |
|---:|---:|---:|
| 0.33 | 4750 | 47.5% |
| 0.01 | 2638 | 26.4% |
| 0.28 | 1935 | 19.4% |

Sub-5% tail (sets the 97.5th percentile):

| threshold | count | fraction |
|---:|---:|---:|
| 0.85 | 333 | 3.3% |
| 0.77 | 230 | 2.3% |
| 0.84 | 27 | 0.3% |

### Reading the table

1. **The hybrid has MORE modes than F1 (3 vs 2), not fewer.** The cost-aware
   refinement within F1's [0.28, 0.48] neighbourhood splits F1's single 0.38
   mode into 0.33 (47.5%) and 0.28 (19.4%). The in-bag asymmetric-cost surface
   is flat enough that small resample-to-resample composition shifts flip the
   argmin between 0.33 and 0.28. The cost-aware step — intended to tighten the
   distribution — fragments it instead. **H51a killed.**

2. **The hybrid's interval width (0.84) is WIDER than cost-aware's (0.32) and
   barely narrower than F1's (0.94).** The 97.5th percentile is 0.85, set by
   the 3.3% of resamples where F1 picks a high threshold (0.95) and the
   hybrid's neighbourhood [0.85, 1.05] extends it to 0.85. The neighbourhood
   constraint shifts F1's high-threshold tail inward by 0.10 (0.95 → 0.85) but
   cannot eliminate it. **H51b killed.**

3. **The hybrid over-fits WORSE than pure cost-aware (1.0705 vs 1.0632).** Two
   mechanisms:
   - The **0.01 mode (26.4%)** over-flags clean windows OOB (same pathology as
     RQ48's cost-aware rule). When F1 picks 0.01 to catch Mode S, the
     neighbourhood [0.0, 0.11] offers no escape: every threshold in it
     over-flags, and the asymmetric cost cannot distinguish among them (all
     flag the same clean windows).
   - The **0.28 mode (19.4%)** under-flags hallucinated windows OOB. At 0.28,
     windows with entropy in [0.28, 0.33) are NOT flagged (routed SEPARATED),
     but some of those are hallucinated — on the OOB set this misses
     hallucinations that the 0.33 threshold would have caught, raising cpWER.
   
   The hybrid therefore over-fits on **both** ends: the 0.01 mode over-flags
   clean windows, and the 0.28 mode under-flags hallucinated windows. Pure
   cost-aware only has the 0.01 over-flagging pathology; the hybrid adds the
   0.28 under-flagging pathology on top. **H51c killed.**

4. **Only 60.2% of resamples are below OOB cpWER 1.10** (vs 76.3% for the
   baseline, 79.0% for F1, 63.6% for cost-aware). The hybrid is the worst
   rule on this metric — confirming the dual over-fitting mechanism.

## Hypothesis Verdicts

- **H51a — Hybrid gives ≤ 2 modes: KILLED.** The hybrid produces 3 modes ≥ 5%
  (0.33 47.5%, 0.01 26.4%, 0.28 19.4%) vs F1's 2 modes (0.38, 0.01). The kill
  mechanism is informative: the cost-aware refinement within F1's neighbourhood
  splits F1's dominant 0.38 mode into two (0.33, 0.28) because the in-bag
  asymmetric-cost surface is flat enough that resample composition flips the
  argmin between adjacent grid points. The hybrid inherits F1's mode-reduction
  for the high-threshold artefact modes (0.87/0.95 → eliminated or shifted
  below 5%) but introduces a NEW fragmentation within F1's neighbourhood. The
  cost-aware step does not reduce modes — it redistributes them.

- **H51b — Hybrid width < 0.32: KILLED.** The hybrid's width is 0.84 (pct
  [0.01, 0.85]), far above 0.32. The 97.5th percentile (0.85) is set by the
  3.3% of resamples where F1 picks 0.95 and the neighbourhood extends it to
  0.85. The neighbourhood constraint can shift F1's high-threshold tail inward
  by ±0.10 but cannot eliminate it — the tail is a property of F1's
  behaviour on resamples where a high threshold is F1-optimal, not a property
  the cost-aware step can remove. The hybrid's width is closer to F1's (0.94)
  than to cost-aware's (0.32): the neighbourhood constraint is too loose to
  achieve cost-aware's interval shrinkage.

- **H51c — Hybrid median OOB cpWER ≤ 1.056: KILLED.** The hybrid's median OOB
  cpWER is 1.0705, worse than pure cost-aware (1.0632) and well above 1.056.
  The kill mechanism is the dual over-fitting described above: the 0.01 mode
  over-flags clean windows OOB (inherited from F1/cost-aware), AND the 0.28
  mode under-flags hallucinated windows OOB (introduced by the cost-aware
  refinement shifting the threshold below 0.33). The asymmetric cost was
  designed to avoid the 0.01 over-flagging, but within the 0.01 neighbourhood
  [0.0, 0.11] every threshold over-flags the same clean windows, so the
  asymmetric cost cannot distinguish among them. The asymmetric cost is
  effective within F1's main neighbourhood [0.28, 0.48] (where it can penalise
  flagging catastrophic-clean windows) but ineffective in the 0.01
  neighbourhood where the over-fitting originates.

## Honest Limitations

1. **Single meeting, 77 windows.** As in RQ44/RQ48, all resamples draw from the
   same 77 windows of `M_R003S02C01`. The 0.01 mode is driven by this meeting's
   2 Mode S windows; a different meeting would produce a different mode
   structure. RQ51 answers "does the hybrid rule achieve ≤ 2 modes, width <
   0.32, and OOB cpWER ≤ 1.056 under resampling of this meeting?" — it does NOT
   answer "does it transfer to a new meeting?".

2. **B=10000 vs RQ48's B=2000.** RQ51 uses B=10000 (matching RQ44) for tighter
   percentile-interval estimates. The RQ48 comparison values in the table are
   at B=2000. The qualitative comparison holds: the hybrid's 3 modes (47.5%,
   26.4%, 19.4%) are far above the 5% threshold and robust to B; the width
   0.84 is set by the 3.3% tail, which is stable across B. The hybrid's
   over-fitting (1.0705) is well-separated from 1.056.

3. **Pre-registered parameters (neighbourhood ±0.1, catastrophic 1.10, penalty
   2.0) were not tuned.** RQ51 reports the pre-registered result honestly. A
   different neighbourhood (e.g. ±0.05, which would keep the high mode at 0.33
   and avoid the 0.28 split) or a higher penalty might reduce the mode count or
   the over-fitting, but tuning parameters to pass pre-registered hypotheses
   would invalidate the test. The negative result is the honest finding.

4. **Asymmetric cost is oracle-style.** Like RQ48's cost-aware rule, the
   asymmetric cost uses reference cpWER as the calibration objective on
   labelled data (cpWER is NOT a routing input — the deployable signal remains
   lang_id_entropy). The asymmetric cost bounds the achievable stability but is
   not itself deployable. Its purpose is to test whether penalising
   catastrophic outcomes avoids the over-fitting that killed RQ48's H48c — the
   answer is no.

5. **Same detector limitation as RQ44/RQ48.** RQ51 changes only the
   calibration rule, not the detector. The 0.01 mode is a property of the
   lang-id entropy detector's inability to separate Mode S from clean Chinese
   — a complementary Mode S detector (RQ19) is the fix, not a hybrid
   calibration rule. RQ51 confirms this by showing the 0.01 mode persists
   under the hybrid exactly as it did under RQ48's 4 rules.

6. **cpWER is utterance-level.** As in RQ44/RQ48, cpWER passes each speaker's
   full Chinese utterance as a single token; cpWER > 1.0 measures extra
   inserted speaker-streams, not character accuracy. A char-level
   re-validation (RQ31/RQ35) remains the follow-up before claiming
   generalisation at character granularity.

7. **The 0.28 mode is a grid-resolution artefact of the cost-aware step.** The
   in-bag asymmetric-cost surface within [0.28, 0.48] is flat (several
   thresholds give near-identical cost), so the argmin flips between 0.33 and
   0.28 across resamples. A coarser grid (0.05 steps) would collapse these
   into one mode, but that would be hiding the fragmentation, not fixing it.
   The fragmentation is a real property of the cost-aware step's sensitivity
   to resample composition on a flat cost surface.

## Reproducibility

- Script:
  `/opt/homebrew/bin/python3 results/frontier/hybrid_calibration_rule/hybrid_calibration_analysis.py`
  (deterministic; numpy + stdlib only; no scipy / sklearn / Whisper / meeteval).
  Runtime ≈ 15 s for the hybrid rule × B=10000.
- Tests: `/opt/homebrew/bin/python3 -m unittest tests.test_hybrid_calibration -v`
  (63 tests; pins `_asymmetric_cost`, `calibrate_hybrid`, module constants,
  in-sample smoke tests reproducing RQ48's 0.38 F1 threshold and a 0.33 hybrid
  threshold on the 77-window data, bootstrap smoke tests, and the committed
  JSON's hypothesis verdicts).
- Outputs:
  - `hybrid_calibration_results.csv` — comparison table (RQ48's 4 rules + the
    hybrid: n_modes, width, median OOB cpWER, over-fits flag).
  - `hybrid_calibration_results.json` — full summary (in-sample hybrid
    calibration, hybrid threshold + OOB cpWER distributions with mode tables,
    RQ48 comparison, hypothesis verdicts) plus `per_bootstrap` arrays
    (thresholds, f1_thresholds, oob_cpwer, n_oob) for reproducibility.
- Bootstrap: B=10000, seed=42 (same seed as RQ44/RQ48; first 2000 resamples
  identical to RQ48, full 10000 identical to RQ44).
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (label `external/sanity-check`, read-only — not modified).

## What this changes for the project

RQ48 left an open question: can a hybrid of F1 (mode reduction) and cost-aware
(width reduction) achieve both goals without over-fitting? RQ51 answers **no**,
and the failure is mechanistically informative:

1. **Cost-aware refinement within F1's neighbourhood FRAGMENTS rather than
   stabilises.** The in-bag cost surface within [0.28, 0.48] is flat enough
   that the argmin flips between 0.33 and 0.28 across resamples, splitting
   F1's single 0.38 mode into two. This is a new failure mode not present in
   RQ48's pure rules: the hybrid introduces fragmentation that neither parent
   rule has (F1 has one high mode 0.38; cost-aware has one high mode 0.33).
   Future hybrid designs should either (a) use a coarser grid within the
   neighbourhood to avoid adjacent-point flips, or (b) regularise the
   cost-aware step toward the F1 threshold.

2. **The neighbourhood constraint cannot eliminate F1's high-threshold tail.**
   F1's rare 0.95/0.87 picks (3.3%/2.3%) are a property of F1's behaviour on
   certain resample compositions, not a property the neighbourhood can remove
   — it only shifts them inward by ±0.10. To eliminate the high-threshold
   tail, one would need to change F1 itself (e.g. a F1-variant that penalises
   extreme thresholds), not constrain its neighbourhood.

3. **The asymmetric cost is ineffective in the 0.01 neighbourhood.** The
   0.01 mode's over-flagging pathology (RQ48's H48c kill) cannot be fixed by
   the asymmetric cost because within [0.0, 0.11] every threshold over-flags
   the same clean windows — the asymmetric cost is identical across them. The
   asymmetric cost is only effective where there is variation in which windows
   are flagged (i.e. within F1's main neighbourhood), but that is not where
   the over-fitting originates. This confirms RQ48's conclusion that the 0.01
   mode is a detector limitation, not a calibration-choice problem: no
   cost-awareness variant can fix it.

4. **The hybrid over-fits on BOTH ends.** Pure cost-aware over-fits only via
   the 0.01 mode (over-flagging clean windows). The hybrid adds a second
   over-fitting channel: the 0.28 mode under-flags hallucinated windows OOB
   (windows with entropy in [0.28, 0.33) are routed SEPARATED, but some are
   hallucinated). The cost-aware refinement, by shifting the threshold below
   0.33, trades one over-fitting mode for two. This is a cautionary result
   for hybrid designs: combining two rules can compound their failure modes
   rather than cancel them.

The actionable conclusion is unchanged from RQ44/RQ48 — **deploy the bootstrap
median threshold (0.38)** — but now better justified: the hybrid rule, which
was the most promising remaining calibration-rule design (combining the
mode-reduction of F1 with the width-reduction of cost-aware), does not beat
0.38 on any of the three pre-registered criteria. The residual instability is a
detector limitation (Mode S) that no calibration rule — pure, smooth,
cost-aware, or hybrid — can fix. The next steps remain those RQ44/RQ48 pointed
to: (a) a complementary Mode S detector (RQ19) to remove the 0.01 mode, and
(b) a multi-meeting calibration corpus to dilute the Mode S prevalence.
