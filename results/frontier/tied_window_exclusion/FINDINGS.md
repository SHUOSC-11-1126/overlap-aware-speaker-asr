# RQ50: Tied-Window Exclusion Corrected-Router on AISHELL-4

> **Label: `experimental/frontier`** — a reanalysis-only investigation of whether
> excluding the 35 "tied" AISHELL-4 windows changes RQ39's conclusion that the
> corrected router's BCa CI includes the oracle cpWER. Reads the existing
> external-validation JSON (label `external/sanity-check`, PR #890) read-only.
> No Whisper / no ASR / no MeetEval / no scipy / no sklearn; the bootstrap and
> BCa CI are implemented from scratch (numpy + stdlib only). Closes the RQ50 issue.
>
> Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
> (77 windows of 30 s from meeting `M_R003S02C01`).

## Executive Summary

RQ39 (PR #960) found the corrected router's word-level BCa CI [1.012987, 1.097403]
*includes* the oracle cpWER (1.017316): the corrected router is statistically
indistinguishable from oracle on the 77-window set (H39b NOT SUPPORTED). RQ47
(PR #967) showed 35 of those 77 windows are "tied" — `abs(always_mixed_cpwer -
always_separated_cpwer) < 1e-6` — silence / single-speaker no-ops where both ASR
routes give identical cpWER and routing cannot help by construction. RQ50 asks
the natural follow-up: **does excluding the 35 tied no-op windows change the
"reaches oracle" verdict?**

**No — but the picture sharpens.** On the 42 non-tied (actionable) windows:

- The corrected router's cpWER **rises** from 1.043 to 1.071 (tied windows were
  mostly at cpWER 1.0, pulling the all-windows mean down).
- The BCa CI **widens** from [1.0130, 1.0974] (width 0.0844) to
  [1.0119, 1.1548] (width 0.1429) — the tied windows were variance-reducing
  anchors, not noise.
- The CI still **includes** the non-tied oracle (1.0238): BCa lower 1.0119 ≤
  1.0238. The "reaches oracle" verdict survives the exclusion.
- The corrected router's **improvement over always-mixed roughly doubles**
  (0.130 → 0.238): the router's advantage is concentrated on the actionable
  windows, exactly as the lang-id-driven RQ16 design intended.

**Headline results:**

| Hypothesis | Verdict | Statistic | Kill condition |
|---|:---:|---:|---|
| **H50a** BCa lower > non-tied oracle (beats oracle on actionable) | **NOT SUPPORTED (killed)** | BCa lower=1.0119 vs oracle=1.0238 | CI includes oracle |
| **H50b** non-tied BCa width < RQ39 width 0.0844 | **NOT SUPPORTED (killed)** | non-tied width=0.1429 | width ≥ 0.0844 |
| **H50c** non-tied improvement > all-windows improvement | **SUPPORTED** | 0.2381 vs 0.1299 | non-tied ≤ all |

The single cleanest takeaway: **the tied windows are not inflating the corrected
router's apparent accuracy — they are stabilising its CI.** Removing them does
not turn the corrected router into a statistically detectable winner over oracle
(H50a killed); it reveals that the router's actionable improvement is real and
concentrated (H50c supported), at the cost of a wider, less certain CI (H50b
killed).

## Method

### Tie definition (RQ47, verbatim)

A window is **tied** iff `abs(always_mixed_cpwer - always_separated_cpwer) < 1e-6`.
On a tie the corrected router — constrained to {mixed, separated} — gets the same
cpWER either way, so no routing decision can improve over always-mixed on that
window. This is the precise definition RQ47 used to identify the 35 tied windows.

### Corrected router (RQ16, threshold 0.38)

Per window, compute the language-id entropy detector (RQ13): Shannon entropy
over Unicode script categories, max across per-speaker separated tracks. Route
**MIXED** if `max_across_speakers(separated, language_id_entropy) >= 0.38`, else
**SEPARATED**. The corrected router's per-window cpWER is then the cpWER of the
chosen route.

On this AISHELL-4 file the threshold-0.38 decisions coincide bit-for-bit with
RQ16's threshold-0.409 decisions (no window has entropy in [0.38, 0.409)), so
the corrected-router point estimate reproduces RQ16's 1.043290 and RQ39's
word-level 1.043290 exactly. This is verified by the all-windows sanity check
below.

### Bootstrap and BCa CI

- **B = 10,000** resamples, **seed = 42** (deterministic).
- Resampling convention: `rng.integers(0, n, size=n)` per resample (RQ16 verbatim).
- **Percentile CI**: [2.5%, 97.5%] quantiles of the bootstrap distribution.
- **BCa CI**: bias-corrected + accelerated. Bias correction `z0 =
  Φ⁻¹(#{T* < T̂}/B)`. Acceleration `a = Σ(T̄₍ᵢ₎ − T̂₍₋ᵢ₎)³ / [6 (Σ(T̄₍ᵢ₎ −
  T̂₍₋ᵢ₎)²)^{3/2}]` via leave-one-out jackknife. Both `z0` and `a` are lifted
  verbatim from RQ39's `bca_ci` and `_jackknife_means`.
- **Paired delta CI**: bootstrap distribution of `mean(corrected − mixed)` per
  resample, [2.5%, 97.5%] percentiles. Negative values mean the corrected router
  beats always-mixed.

All per-window cpWER values are at the **word level** (no MeetEval re-run). The
analysis reads the existing `always_mixed_cpwer`, `always_separated_cpwer`, and
`oracle_best_cpwer` fields directly from the source JSON.

## Results

### All-windows sanity check (must reproduce RQ39)

| Quantity | RQ50 (this run) | RQ39 (PR #960) |
|---|---:|---:|
| n windows | 77 | 77 |
| corrected router cpWER | 1.043290 | 1.043290 |
| always-mixed cpWER | 1.173160 | 1.173160 |
| oracle cpWER | 1.017316 | 1.017316 |
| percentile CI 95% | [1.008658, 1.088745] | [1.008658, 1.088745] |
| BCa CI 95% | [1.012987, 1.097403] | [1.012987, 1.097403] |
| BCa width | 0.084416 | 0.084416 |
| improvement (mixed − corrected) | 0.129870 | 0.129870 |

The all-windows numbers reproduce RQ39 exactly, confirming the helper lift and
threshold-0.38 ≡ threshold-0.409 on this dataset.

### Non-tied windows (the actionable subset, n = 42)

| Quantity | Non-tied (n=42) | All-windows (n=77) |
|---|---:|---:|
| corrected router cpWER | 1.071429 | 1.043290 |
| always-mixed cpWER | 1.309524 | 1.173160 |
| always-separated cpWER | 2.075397 | 1.590909 |
| oracle cpWER | 1.023810 | 1.017316 |
| improvement (mixed − corrected) | **0.238095** | 0.129870 |
| percentile CI 95% | [1.011905, 1.154762] | [1.008658, 1.088745] |
| BCa CI 95% | [1.011905, 1.154762] | [1.012987, 1.097403] |
| BCa width | **0.142857** | 0.084416 |
| paired delta CI (corrected − mixed) | [-0.571429, 0.000000] | [-0.311688, 0.000000] |

**Decision counts:**

| Subset | MIXED | SEPARATED |
|---|---:|---:|
| all-windows | 38 | 39 |
| non-tied | 34 | 8 |

The non-tied subset is heavily MIXED-skewed (34/42 = 81%): the lang-id detector
fires on almost every actionable window, routing it to the (cheaper, here better)
mixed pass. The 8 SEPARATED decisions on non-tied windows are the low-entropy
cases where separation genuinely helps. The 39 all-windows SEPARATED decisions
include 31 tied windows where the choice is irrelevant.

### Hypothesis verdicts

**H50a — NOT SUPPORTED (killed).** The non-tied BCa lower bound is 1.0119; the
non-tied oracle is 1.0238. The CI [1.0119, 1.1548] includes the oracle, so the
corrected router does *not* statistically beat oracle on the actionable subset.
The kill condition (CI includes oracle) is met. RQ39's "reaches oracle" verdict
survives the tied-window exclusion.

**H50b — NOT SUPPORTED (killed).** The non-tied BCa width is 0.1429; RQ39's
all-windows width is 0.0844. The CI *widened* by 69%, not narrowed. The kill
condition (width ≥ 0.0844) is met. The tied windows were variance-reducing
anchors — 34 of them sit at cpWER = 1.0, a tight cluster that shrinks the
bootstrap distribution's spread. Removing them exposes the genuine variability
of the actionable windows.

**H50c — SUPPORTED.** The corrected router's improvement over always-mixed is
0.2381 on non-tied vs 0.1299 on all-windows. The advantage nearly doubles on
the actionable subset (1.83×). This confirms the pre-registered intuition: the
router's value is concentrated on the windows where routing can actually change
the outcome. On tied windows the "improvement" is mechanically 0 (both routes
give the same cpWER), so the all-windows improvement is diluted by the 35
no-op windows.

## What this changes for the project

1. **RQ39's "reaches oracle" verdict is robust to the tied-window exclusion
   (H50a killed).** The headline RQ39 finding — corrected router BCa CI
   includes oracle — is not an artifact of the tied no-op windows inflating
   agreement. On the 42 windows where routing can actually matter, the CI still
   includes oracle. The corrected router remains statistically indistinguishable
   from oracle, just with a higher point estimate (1.071 vs 1.043) and a wider
   interval.

2. **The tied windows were stabilising the CI, not inflating accuracy (H50b
   killed).** This is the counterintuitive finding. The pre-registered intuition
   was that excluding tied windows would *tighten* the CI by removing
   uninformative no-ops. The opposite happened: the CI widened by 69%. The
   reason is that 34/35 tied windows sit at exactly cpWER = 1.0, a tight
   zero-variance cluster that anchors the bootstrap distribution. Removing them
   leaves 42 heterogeneous actionable windows (cpWER ranges from 1.0 to 4.0+),
   which spread the bootstrap resamples wider. The all-windows CI was
   *optimistically narrow*, not the non-tied CI being pessimistically wide.

3. **The corrected router's actionable advantage is real and concentrated
   (H50c supported).** The improvement over always-mixed nearly doubles on
   non-tied windows (0.130 → 0.238). This is the cleanest signal in the study:
   the lang-id-driven RQ16 router is doing exactly what it was designed to do —
   concentrating its MIXED-route decisions on the multilingual-hallucination
   windows where the mixed pass wins, and leaving the low-entropy windows alone.
   The all-windows improvement understates the router's value because 35
   no-op windows mechanically contribute 0 improvement.

4. **No support for "exclude tied windows to get a cleaner comparison".** A
   naive reading of RQ47 might suggest excluding tied windows to get a "fairer"
   evaluation of the router. RQ50 shows this does not help: the CI widens, the
   point estimate rises, and the verdict (CI includes oracle) is unchanged. The
   tied windows are not a confound to remove — they are part of the real
   workload distribution, and the router's all-windows numbers are the
   deployable ones.

5. **Implication for the frontier.** The non-tied subset (n=42) is where the
   router's *learnable* signal lives: 34 MIXED decisions vs 8 SEPARATED, with
   the corrected router beating always-separated by 1.004 cpWER (2.075 → 1.071)
   but losing to oracle by 0.048 (1.071 vs 1.024). Closing that 0.048 gap on
   the actionable subset — via a stronger detector, a third route, or a critic
   loop — is the concrete next step suggested by this analysis. The tied
   windows are a separable class (RQ47 AUC 0.873) but excluding them does not
   move the verdict.

## Honest Limitations

1. **Single meeting, 77 windows (inherited from RQ16/RQ39/RQ47).** The 35/42
   tied / non-tied split and the BCa CIs characterise within-meeting structure
   only. The non-tied n=42 is small for a BCa CI; the 0.1429 width is partly a
   small-sample artifact. Cross-meeting replication would require running the
   corrected router on additional AISHELL-4 meetings (out of scope for this
   reanalysis-only RQ).

2. **BCa acceleration on a discrete, lumpy distribution.** The per-window cpWER
   values are discrete rationals (1.0, 1.333, 1.5, 2.0, 3.0, 4.0, ...), so the
   jackknife acceleration `a` is computed on a non-smooth statistic. On the
   non-tied subset the percentile and BCa CIs coincide ([1.0119, 1.1548] for
   both), which is a symptom of the discrete distribution — BCa's correction
   has little to bite on. The CI should be read as "the bootstrap distribution's
   central 95%", not as a precise confidence statement.

3. **Threshold 0.38 ≡ 0.409 on this file, not in general.** The task directive
   specifies threshold 0.38; we verified the decisions coincide with RQ16's
   0.409 on this AISHELL-4 file because no window has entropy in [0.38, 0.409).
   On other meetings the two thresholds could diverge. The all-windows sanity
   check reproducing RQ39 exactly confirms the equivalence *here*, not as a
   general claim.

4. **No MeetEval re-run.** The per-window cpWER values are read from the
   existing RQ1 external-validation JSON (word-level WER via the original
   MeetEval pass). RQ50 does not recompute cpWER; it reanalyses the existing
   values. Any error in the source cpWER propagates unchanged.

5. **The "5 tied windows" in any inherited brief narrative is inconsistent with
   the data.** RQ47 already documented this: the stated operational definition
   (`abs(mixed - sep) < 1e-6`) yields **35** tied windows (34 at exactly 1.0),
   not 5. RQ50 uses RQ47's verified 35-window list directly; the discrepancy is
   documented in RQ47's FINDINGS.md and is not re-litigated here.

## Reproducibility

- Script: `results/frontier/tied_window_exclusion/tied_window_exclusion_analysis.py`
  (deterministic; numpy + stdlib only — no scipy, no sklearn, no MeetEval, no
  Whisper, no audio).
- Tests: `tests/test_tied_window_exclusion.py` (65 tests; pure-helper pins for
  `is_tied_window`, `identify_tied_windows`, `identify_nontied_windows`,
  `per_window_corrected_cpwer`, `build_per_window_rows`, `corrected_router_decision`,
  `bootstrap_indices`, `bootstrap_distribution`, `percentile_ci`, `_jackknife_means`,
  `bca_ci`, `paired_delta_distribution`, `paired_delta_ci` plus the lang-id
  helpers; smoke tests load the real AISHELL-4 JSON to pin tied_count=35,
  nontied_count=42, and the all-windows reproduction of RQ39's
  [1.012987, 1.097403] BCa CI).
- Per-window data: `results/frontier/tied_window_exclusion/tied_window_exclusion_results.csv`
  (77 rows; per-window cpWER + `is_tied` flag + corrected decision + lang-id entropy).
- Summary + hypothesis verdicts: `results/frontier/tied_window_exclusion/tied_window_exclusion_results.json`.
- Source data: `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
  (read-only — not modified).
- Run: `/opt/homebrew/bin/python3 results/frontier/tied_window_exclusion/tied_window_exclusion_analysis.py`
- Tests: `/opt/homebrew/bin/python3 -m unittest tests.test_tied_window_exclusion -v`
- Seed: 42 (bootstrap RNG).
