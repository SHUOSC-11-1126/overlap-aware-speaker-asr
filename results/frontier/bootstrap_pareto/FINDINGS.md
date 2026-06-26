# RQ46 — Bootstrap Pareto Frontier Confidence Intervals (RQ43 Cascade)

**Label:** experimental/frontier
**Closes:** #957
**Branch:** `research/rq46-bootstrap-pareto`
**Mode:** C — Frontier Exploration (Direction 2: compute-aware cascaded recognition; robustness extension of RQ43)
**Builds on:** RQ43 (PR #959, `results/frontier/three_tier_cascade/`)

---

## Executive Summary

RQ43 produced a 3-tier compute-aware cascade (tiny → KL gate → base) and reported
a Pareto curve of (compute, cpWER) trade-offs on **a single AISHELL-4 meeting
(77 windows)**: cascade cpWER 0.8889 vs always-tiny 1.5909 at compute 1.6884×.
Those were point estimates. RQ46 asks: **is the Pareto frontier robust to window
composition?** We bootstrap-resample the 77 windows (B=2000, with replacement,
seed=42) and re-compute the 14-point KL-threshold Pareto curve on each resample
to obtain 95% confidence intervals on the frontier.

**Result: the frontier's cpWER advantage is robust in the high-escalation region
but not in the low-escalation tail.** Two of three hypotheses are killed:

- **H46a — KILLED.** The cascade cpWER 95% bootstrap CI excludes the always-tiny
  baseline (1.5909) at only 9 of 14 Pareto points. At the 5 highest-threshold
  points (KL ≥ 4.0, escalation fraction ≤ 24.7%) the CI overlaps 1.5909 — the
  cascade is not statistically separable from always-tiny there because it
  escalates so few windows that its cpWER approaches the baseline.
- **H46b — SUPPORTED.** The cascade compute 95% CI is entirely below 1.93×
  (always-base) at all 14 Pareto points. The compute savings are robust across
  the whole frontier.
- **H46c — KILLED.** The cascade beats the baseline on cpWER in ≥ 95% of
  resamples at only 10 of 14 points. The same 4 high-threshold points (KL ≥ 4.5)
  fall below 95% (as low as 68.9%).

**Crucially, RQ43's reported operating point (KL=3.30) is robust.** Its cpWER
95% CI is [0.7674, 1.0163] — entirely below the 1.5909 baseline — and it beats
the baseline in 100% of resamples. The entire high-escalation region
(KL ∈ [0.0, 3.5], escalation ≥ 59.7%, cpWER ≤ 1.0629) is statistically robust.
The kills occur only in the low-escalation tail where the cascade barely
differs from always-tiny. This is a simulation (no Whisper run); base cpWER is
inherited from RQ43's model_scale estimate.

---

## Method

### Source data (no new ASR runs)

1. **RQ43 per-window results** —
   `results/frontier/three_tier_cascade/three_tier_cascade_results.csv`
   (label `experimental/frontier`, PR #959). Provides the 77 windows'
   `tiny_sep_cpwer`, `base_sep_cpwer` (estimated via the model_scale base/tiny
   CER ratio), and `kl_sep` (character-bigram asymmetric KL). Loading RQ43's
   processed per-window data (rather than re-running the KL gate / base-cpWER
   estimation) guarantees the in-sample curve reproduces RQ43 exactly.
2. **AISHELL-4 raw source** —
   `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json`
   (label `external/sanity-check`, PR #890). Loaded to confirm n_windows=77 and
   the baseline cpWER.

### Pipeline

1. Load RQ43's 77 per-window `(tiny_sep_cpwer, base_sep_cpwer, kl_sep)`.
2. Reproduce RQ43's in-sample 14-point KL-threshold Pareto curve. Smoke check:
   cascade @ KL=3.30 reproduces cpWER 0.888947, compute 1.688442×, frac 0.74026
   (RQ43's reported operating point).
3. For each of B=2000 bootstrap resamples (seed=42, with replacement over the 77
   windows):
   a. Re-compute the 14-point Pareto curve on the resampled windows. Per point
      (KL threshold): cascade cpWER = `mean(tiny_cpwer if KL≤thr else base_cpwer)`;
      cascade compute = `1.0*(1-f) + 1.93*f` where `f` is the escalation
      fraction (fraction of resampled windows with KL > threshold, strict);
      escalation fraction `f`.
4. For each of the 14 Pareto points report: median cpWER + 2.5/97.5 percentile
   CI; median compute + 2.5/97.5 percentile CI; median escalation fraction;
   fraction of resamples where the cascade beats the baseline on cpWER
   (`cascade cpWER < 1.5909`); fraction where the cascade strictly 2D-Pareto-
   dominates the baseline (reported for transparency).

### Baseline and naming clarification

The cpWER baseline is **1.590909 = always_tiny_separated** in RQ43's data
(whisper-tiny on separated audio, no escalation) — the value the RQ43 cascade
(separated audio) improves on. The task brief labels this value "always-mixed";
in RQ43's data 1.590909 is `always_tiny_separated` (the mixed-route baseline is
1.17316, a different number). **The value 1.5909 is unambiguous and is the
baseline used for H46a/H46c.** The naming discrepancy is documented in the
results JSON and does not affect any numeric result.

### H46c operationalisation

Strict 2D Pareto dominance of the cascade over the baseline
(`cpWER ≤ 1.5909 AND compute ≤ 1.0×`, one strict) is **structurally impossible**
at low-KL-threshold points because cascade compute (≥ 1.0×) exceeds the
baseline compute (1.0×). H46c therefore operationalises "dominance" as the
cascade beating the baseline on the **cpWER (quality) axis** (`cascade cpWER <
1.5909`), which is equivalent to the baseline *not* Pareto-dominating the
cascade. The 2D strict-dominance fraction is also reported per point (it is
~0% everywhere except a negligible 0.3% at KL ≥ 5.0, where a resample
occasionally escalates zero windows and ties compute at 1.0×).

---

## Results

### Pareto frontier with 95% bootstrap CIs (n=77, B=2000, seed=42)

`cpw_med`/`cpw_CI` = cascade cpWER median / 2.5–97.5 percentile;
`cmp_med`/`cmp_CI` = cascade compute median / 2.5–97.5 percentile;
`dom%` = % of resamples where cascade cpWER < baseline (1.5909);
`2D%` = % where cascade strictly 2D-Pareto-dominates the baseline.
H46a/H46b/H46c = whether the point passes each hypothesis's per-point criterion.

| KL ≥ | frac | in-sample cpw | cpw_med | cpw_CI (95%) | cmp_med | cmp_CI (95%) | dom% | 2D% | H46a | H46b | H46c |
|---:|---:|---:|---:|---|---:|---|---:|---:|:---:|:---:|:---:|
| 0.00 | 83.1% | 0.7775 | 0.7761 | [0.7056, 0.8532] | 1.7730× | [1.6884, 1.8455] | 100.0 | 0.0 | ✓ | ✓ | ✓ |
| 0.50 | 83.1% | 0.7775 | 0.7761 | [0.7056, 0.8532] | 1.7730× | [1.6884, 1.8455] | 100.0 | 0.0 | ✓ | ✓ | ✓ |
| 1.00 | 83.1% | 0.7775 | 0.7761 | [0.7056, 0.8532] | 1.7730× | [1.6884, 1.8455] | 100.0 | 0.0 | ✓ | ✓ | ✓ |
| 1.50 | 83.1% | 0.7775 | 0.7761 | [0.7056, 0.8532] | 1.7730× | [1.6884, 1.8455] | 100.0 | 0.0 | ✓ | ✓ | ✓ |
| 2.00 | 83.1% | 0.7775 | 0.7761 | [0.7056, 0.8532] | 1.7730× | [1.6884, 1.8455] | 100.0 | 0.0 | ✓ | ✓ | ✓ |
| 2.50 | 83.1% | 0.7775 | 0.7761 | [0.7056, 0.8532] | 1.7730× | [1.6884, 1.8455] | 100.0 | 0.0 | ✓ | ✓ | ✓ |
| 3.00 | 81.8% | 0.7949 | 0.7934 | [0.7122, 0.8779] | 1.7609× | [1.6764, 1.8334] | 100.0 | 0.0 | ✓ | ✓ | ✓ |
| **3.30** | **74.0%** | **0.8889** | **0.8878** | **[0.7674, 1.0163]** | **1.6884×** | **[1.5918, 1.7730]** | **100.0** | **0.0** | **✓** | **✓** | **✓** |
| 3.50 | 59.7% | 1.0629 | 1.0579 | [0.9015, 1.2327] | 1.5556× | [1.4590, 1.6522] | 100.0 | 0.0 | ✓ | ✓ | ✓ |
| 4.00 | 24.7% | 1.3941 | 1.3928 | [1.2101, 1.5974] | 1.2295× | [1.1449, 1.3261] | 96.9 | 0.0 | ✗ | ✓ | ✓ |
| 4.50 | 11.7% | 1.5055 | 1.5021 | [1.3278, 1.7066] | 1.1087× | [1.0483, 1.1812] | 82.5 | 0.0 | ✗ | ✓ | ✗ |
| 5.00 | 6.5% | 1.5501 | 1.5486 | [1.3724, 1.7426] | 1.0604× | [1.0121, 1.1208] | 68.9 | 0.3 | ✗ | ✓ | ✗ |
| 5.50 | 6.5% | 1.5501 | 1.5486 | [1.3724, 1.7426] | 1.0604× | [1.0121, 1.1208] | 68.9 | 0.3 | ✗ | ✓ | ✗ |
| 6.00 | 6.5% | 1.5501 | 1.5486 | [1.3724, 1.7426] | 1.0604× | [1.0121, 1.1208] | 68.9 | 0.3 | ✗ | ✓ | ✗ |

- **RQ43's operating point (KL=3.30) is robust:** cpWER CI [0.7674, 1.0163] is
  entirely below the 1.5909 baseline; the CI upper (1.0163) is also below the
  RQ16 corrected-router cpWER (1.04329, a different axis). Compute CI
  [1.5918, 1.7730] is entirely below 1.93×. The cascade beats the baseline in
  100% of resamples.
- **Robust region (KL ∈ [0.0, 3.5], escalation ≥ 59.7%):** cpWER CI entirely
  below 1.5909 at all 9 points; dominance 100%.
- **Borderline point (KL=4.0, escalation 24.7%):** cpWER CI upper 1.5974 just
  exceeds 1.5909 → H46a killed here, but dominance 96.9% ≥ 95% → H46c holds.
- **Non-robust tail (KL ∈ [4.5, 6.0], escalation ≤ 11.7%):** cpWER CI overlaps
  the baseline; dominance 68.9–82.5%. The cascade escalates so few windows that
  its cpWER (≈1.55) is statistically indistinguishable from always-tiny (1.59).
- **Compute savings (H46b) are robust everywhere:** every compute CI is entirely
  below 1.93×, including the lowest-escalation points (compute CI upper
  ≤ 1.8455×).

### Number of Pareto points

RQ43's FINDINGS reports "16 frontier points" (counting always_tiny +
always_base + the oracle cascade + 13 frontier cascade sweep points). This
bootstrap operates on the **14 KL-threshold cascade operating points** (the
sweep values 0.0–6.0 including 3.30) — the points at which a cascade policy
exists and cascade cpWER / compute / escalation-fraction are defined. The
single-tier endpoints and the oracle are not cascades and have no KL threshold,
so they are excluded from the bootstrap (their cpWER CIs would be the bootstrap
CI of the always-tiny / always-base mean, and including always-tiny would
trivially kill H46a since its cpWER IS the 1.5909 baseline). This is documented
in the results JSON.

---

## Hypothesis Verdicts

### H46a — Cascade cpWER 95% CI excludes the baseline (1.5909) at all 14 points
**KILLED.** 9 of 14 points pass; 5 fail (KL ≥ 4.0). Killers:

| KL ≥ | cpw_CI (95%) | baseline |
|---:|---|---:|
| 4.00 | [1.2101, 1.5974] | 1.5909 |
| 4.50 | [1.3278, 1.7066] | 1.5909 |
| 5.00 | [1.3724, 1.7426] | 1.5909 |
| 5.50 | [1.3724, 1.7426] | 1.5909 |
| 6.00 | [1.3724, 1.7426] | 1.5909 |

The KL=4.0 point fails by a hair (CI upper 1.5974 vs baseline 1.5909); the
KL ≥ 4.5 points fail clearly. In the low-escalation tail the cascade escalates
≤ 11.7% of windows, so its cpWER (≈1.55) sits too close to the 1.5909 baseline
for the n=77 bootstrap to separate them. The high-escalation region
(KL ≤ 3.5, the practically useful part of the frontier) is fully robust.

### H46b — Cascade compute 95% CI entirely below 1.93× at all 14 points
**SUPPORTED.** 14 of 14 points pass; 0 killers. The highest compute CI upper is
1.8455× (KL=0.0, escalation 83.1%); the lowest-escalation points have compute
CI upper ≤ 1.1208×. The compute savings are robust across the entire frontier.

### H46c — Cascade cpWER advantage (cascade cpWER < baseline) in ≥ 95% of resamples at all 14 points
**KILLED.** 10 of 14 points pass; 4 fail (KL ≥ 4.5). Killers:

| KL ≥ | dom% | criterion |
|---:|---:|---:|
| 4.50 | 82.5% | 95% |
| 5.00 | 68.9% | 95% |
| 5.50 | 68.9% | 95% |
| 6.00 | 68.9% | 95% |

This is consistent with H46a: the same high-threshold tail where the cpWER CI
overlaps the baseline is where the point-wise dominance falls below 95%. The
borderline KL=4.0 point passes H46c (96.9%) but fails H46a (CI just overlaps).
RQ43's operating point (KL=3.30) passes with 100% dominance.

---

## Honest Limitations

1. **Simulation, not measurement (inherited from RQ43).** whisper-base was NOT
   run on AISHELL-4; `base_sep_cpwer` is RQ43's estimate via the model_scale
   base/tiny CER ratio (constant 0.4283 for separated audio). The bootstrap
   quantifies robustness to *window composition*, not to the base-cpWER
   estimation error. If the true base cpWER differs from the estimate, every
   bootstrap CI shifts accordingly. A follow-up running whisper-base on
   AISHELL-4 would convert these CIs from projected to measured.

2. **n=77 is small, and the bootstrap cannot create information that is not
   there.** The 77 AISHELL-4 windows are a sanity-check corpus from a single
   meeting family. The bootstrap resamples *within* this corpus, so it captures
   window-composition variance but NOT cross-meeting variance. The
   non-robustness of the high-threshold tail is partly an n=77 effect: with more
   windows the cpWER CI would tighten and the borderline KL=4.0 point might
   separate. The genuinely useful region (KL ≤ 3.5) is robust even at n=77.

3. **H46c operationalisation is 1D cpWER-dominance, not strict 2D Pareto
   dominance.** Strict 2D Pareto dominance of the cascade over the baseline
   (cpWER ≤ 1.5909 AND compute ≤ 1.0×) is structurally impossible whenever the
   cascade escalates any window (compute > 1.0×). H46c therefore tests cpWER
   dominance (cascade cpWER < baseline), equivalent to "the baseline does not
   Pareto-dominate the cascade." The 2D fraction is ~0% everywhere and is
   reported but not used for the verdict. A reader who insists on strict 2D
   dominance would find H46c trivially killed at all points — we judge that
   uninformative and use the quality-axis operationalisation, documented
   transparently.

4. **Baseline naming discrepancy.** The task brief calls the 1.5909 baseline
   "always-mixed"; in RQ43's data 1.590909 is `always_tiny_separated` (the
   mixed-route baseline is 1.17316). We use the value 1.5909
   (`always_tiny_separated`), which is the cpWER baseline RQ43's separated-audio
   cascade improves on and the value the 44.1% reduction is computed against.
   The discrepancy is a label, not a number; all results use 1.5909.

5. **The 14-vs-16 point count.** RQ43 reports "16 frontier points" (including
   the two single-tier endpoints and the oracle). This bootstrap operates on the
   14 KL-threshold cascade operating points (the sweep 0.0–6.0). The endpoints
   are excluded because they are not cascades (no KL threshold, no escalation
   fraction) and including always-tiny would trivially kill H46a (its cpWER IS
   the baseline). The 14-point set is the faithful object over which cascade
   cpWER/compute CIs are defined.

6. **Bootstrap assumes windows are i.i.d.** Resampling treats the 77 windows as
   independent draws from a common distribution. They come from AISHELL-4
   meetings with structure (overlap-ratio buckets, speaker counts), so there is
   mild dependence; the i.i.d. bootstrap is the standard first-order
   approximation and matches RQ43's own bootstrap CI methodology (which used the
   same assumption at B=10000 for the single KL=3.30 point).

---

## Reproducibility

### Inputs (existing, labeled)
- `results/frontier/three_tier_cascade/three_tier_cascade_results.csv` — `experimental/frontier`, PR #959 (RQ43 per-window data)
- `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` — `external/sanity-check`, PR #890 (raw AISHELL-4, n=77 confirmation)

### Outputs (this study, `experimental/frontier`)
- `results/frontier/bootstrap_pareto/bootstrap_pareto_analysis.py` — analysis script (numpy + stdlib only; no Whisper, no scipy, no sklearn)
- `results/frontier/bootstrap_pareto/bootstrap_pareto_results.csv` — per-Pareto-point summary with CIs (14 rows)
- `results/frontier/bootstrap_pareto/bootstrap_pareto_results.json` — full results (config, in-sample curve, per-point CIs + per-resample cpWER/compute samples, hypothesis verdicts with killers)
- `results/frontier/bootstrap_pareto/FINDINGS.md` — this document

### Tests
- `tests/test_bootstrap_pareto.py` — pins the pure helpers (`bootstrap_resample`,
  `compute_cascade_cpwer`, `compute_cascade_compute`, `pareto_dominates`,
  `escalation_mask`, `compute_escalation_fraction`, `percentile_ci`,
  `compute_pareto_point`, `compute_pareto_curve`), verifies the vectorised
  bootstrap matches the pure helpers per-resample/per-threshold, and smoke-tests
  the in-sample curve on the real RQ43 data (reproduces cpWER 0.888947,
  compute 1.688442×, frac 0.74026 at KL=3.30; baseline 1.590909). 50 tests.

```bash
# Run the analysis (writes all outputs; deterministic, ~1s)
/opt/homebrew/bin/python3 results/frontier/bootstrap_pareto/bootstrap_pareto_analysis.py

# Run the tests
/opt/homebrew/bin/python3 -m unittest tests.test_bootstrap_pareto -v
```

### Determinism
All randomness is seeded with `SEED = 42` via `np.random.default_rng(42)`.
B=2000 resamples, 14 thresholds, 77 windows. Outputs are byte-reproducible.

### Result label
`experimental/frontier` — this is a simulation (no whisper-base run on
AISHELL-4; base cpWER inherited from RQ43's model_scale estimate). It does NOT
modify any stable/gold output or verified reference; it consumes RQ43's
`experimental/frontier` per-window data and produces new bootstrap-CI outputs in
a new directory.
