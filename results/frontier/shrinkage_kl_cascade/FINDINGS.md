# RQ69: Cascade with Shrinkage-Calibrated KL Gate

> **Label: `experimental/frontier`** — Builds on RQ43 (PR #959, 3-tier KL
> cascade), RQ44 (PR #963, OOB bootstrap), RQ48 (PR #965, `count_modes`), RQ59
> (PR #980, BCa CI + jackknife framework), RQ61 (PR #991, shrinkage
> calibration), and RQ62 (PR #992, ensemble cascade comparison). Reanalysis
> only (no Whisper / no ASR / no LLM run); reuses RQ43's per-window KL/cpWER
> data, RQ59's `norm_cdf` / `norm_ppf` / `bca_ci` / jackknife structure
> verbatim, RQ48's `count_modes` verbatim, and RQ44's OOB bootstrap protocol.
> Does NOT overwrite any verified reference / gold table.

## Executive Summary

RQ59 (PR #980) showed both Youden's J and F1 collapse the KL gate to the same
aggressive operating point (threshold 0.01, escalation 83.1%, OOB cpWER 0.782)
because the KL ROC is flat-topped. RQ61 (PR #991) showed that shrinkage
calibration (`sensitivity − λ·|t − prior_mean|` at ≥ 90% specificity)
eliminates the pathological 0.01 mode on the lang-id detector. RQ62 (PR #992)
showed the KL+lang-id ensemble gate gives 55.8% escalation but OOB cpWER 0.942
> 0.889. RQ69 asked whether replacing the raw KL gate with a **shrinkage-
calibrated KL gate** — using RQ61's shrinkage with a **Beta(2,2) posterior-mode
prior** (rather than RQ61's data-derived lang-id median) — improves the
cascade's OOB cpWER.

**The answer is no: shrinkage calibration kills cpWER.** Two of three
pre-registered hypotheses are killed:

| Hypothesis | Verdict | Test statistic | Kill threshold |
|---|---|---:|---|
| H69a: OOB cpWER < 0.889 (RQ43 baseline) | **KILLED** | 1.5405 | ≥ 0.889 |
| H69b: escalation rate < 83.1% (RQ59 baseline) | **SUPPORTED** | 6.49% | ≥ 83.1% |
| H69c: BCa width < 0.283 (RQ59 baseline) | **KILLED** | 0.5313 | ≥ 0.283 |

The headline finding is that the **≥ 90% specificity floor is binding on the
KL detector**, and once it binds, the shrinkage penalty has nothing to act on.
At λ = 0 (no shrinkage, pure max-sensitivity-at-90%-specificity, the RQ44
rule) the in-sample threshold is already 4.87 — the lowest grid point at
which exactly 4 of 40 clean windows are flagged (specificity = 36/40 = 0.900).
At KL ≥ 4.87 only **5 of 77 windows escalate** (1 true positive + 4 false
positives), leaving **36 of 37 hallucinations on the tiny tier** where their
mean cpWER is well above 1.0. The cascade cpWER collapses to **1.5501** —
**74.3% worse than RQ43's 0.8889** and only 2.6% better than the always-tiny
baseline (1.5909). H69a is killed by construction.

Shrinkage at λ > 0 does **not move the in-sample threshold**: it stays at
4.87 across {0.0, 0.01, 0.1, 0.5, 1.0} because the feasible set at ≥ 90%
specificity contains only the 4.87 grid point (every higher threshold has
lower sensitivity; every lower threshold violates the spec floor). The
shrinkage penalty cannot break the floor, so it cannot move the in-sample
choice. The only place shrinkage acts is in the **bootstrap**: at λ = 0 the
threshold distribution has 5 modes (51.9% at the degenerate 8.55 "escalate
nothing" fallback), while at λ = 0.01 it has 7 modes with the fallback
dropping to 8.7% and the median moving from 8.53 down to 4.87. This
redistribution slightly lowers the OOB cpWER median (1.5536 → 1.5405) but
**increases the mode count** (5 → 7), which broadens the OOB cpWER
distribution and inflates the BCa width from 0.5257 to 0.5313. Both are far
above RQ59's 0.283 anchor (H69c killed).

H69b (escalation < 83.1%) is trivially supported — escalation collapses to
6.5%, an **order of magnitude below** RQ59's 83.1%. But this is the **same
trade-off RQ58 and RQ62 faced**: high-specificity calibration gives low
escalation but high cpWER, because the KL detector cannot separate the
hallucinated class at high specificity without giving up almost all
sensitivity. The KL ROC is the wrong shape for a high-specificity gate: the
37 hallucinated windows span KL ∈ [2.98, 6.58] (heavily overlapping the clean
windows' KL ∈ [0.0, 8.53]), so any threshold that protects 90% of clean
windows (≥ 4.87) catches only 1 of 37 hallucinations.

**Implication for the frontier:** Shrinkage calibration is not a free lunch.
RQ61 showed it stabilises the lang-id detector (where the prior mean 0.38 was
*inside* the feasible set), but on the KL detector the ≥ 90% specificity
floor is *outside* the informative threshold range, so shrinkage's prior-pull
is blocked by the constraint. The cascade needs a detector whose ROC has
genuine operating-point diversity at ≥ 90% specificity — not a different
calibration rule on a detector whose ROC does not.

## Pre-registered Hypotheses

| ID | Statement | Kill condition | Verdict |
|---|---|---|---|
| H69a | Shrinkage KL cascade OOB cpWER < 0.889 (RQ43 baseline 0.888947) | OOB cpWER ≥ 0.889 | **KILLED** (1.540544) |
| H69b | Shrinkage KL cascade escalation rate < 83.1% (RQ59 baseline 0.831169) | escalation ≥ 0.831 | **SUPPORTED** (0.064935) |
| H69c | Shrinkage KL cascade BCa width < 0.283 (RQ59 baseline 0.282660) | BCa width ≥ 0.283 | **KILLED** (0.531324) |

All three verdicts are evaluated at the best λ, selected by the pre-
registered criterion: lowest OOB cpWER median (H69a primary), then narrowest
BCa width (H69c), then fewest modes, then smallest λ. The best λ is **0.01**.

## Method (controlled comparison)

The ONLY independent variable vs RQ59 (Youden's J) and RQ62 (ensemble OR) is
the calibration rule. The cascade simulation is held fixed at RQ43's actual
implementation so the comparisons to RQ43's 0.888947 anchor (H69a), RQ59's
83.1% escalation (H69b), and RQ59's 0.2827 BCa width (H69c) are apples-to-
apples:

- **Tier 1 (whisper-tiny)** cpWER per window = RQ43's `tiny_sep_cpwer` (the
  real whisper-tiny separated-audio cpWER; == `always_separated_cpwer` in
  AISHELL-4, verified in tests).
- **Tier 3 (whisper-base)** cpWER per window = RQ43's `base_sep_cpwer` =
  `tiny_sep_cpwer × 0.428031` (the model_scale separated base/tiny CER
  ratio, constant across overlap). This is RQ43's actual base-cpWER estimate.
- **Tier 2 (KL gate)**: escalate to base when RQ43's character-bigram
  asymmetric KL divergence of the tiny transcript (`kl_sep`, range
  [0.0, 8.5255]) ≥ the **shrinkage-calibrated** threshold.

The hallucination label used to calibrate the threshold is
`tiny_sep_cpwer > 1.0` (37 hallucinated / 40 clean), matching
RQ44/RQ48/RQ54/RQ59/RQ62's label rule. High KL flags a window as
hallucinated and escalates it to base — the same direction as RQ43's cascade.

### Shrinkage calibration rule (RQ61's `shrinkage_objective` on KL)

RQ61's shrinkage objective is:

    objective(t) = sensitivity(t) − λ · |t_norm − prior_mean_norm|

maximised subject to `specificity(t) ≥ 0.90` over the 0.01-step KL grid
[0.00, 8.55]. At λ = 0 this reduces to RQ44's max-sensitivity-at-90%-
specificity rule (the no-shrinkage baseline). At λ > 0 the penalty pulls the
threshold toward `prior_mean_norm` (the shrinkage target on the normalised
[0, 1] KL scale: `t_norm = t / kl_max`).

### Beta(2,2) posterior-mode prior

RQ61 used `prior_mean = 0.38` (the lang-id bootstrap median, data-derived).
RQ69 replaces this with a Bayesian Beta(2,2) prior on the hallucination
rate, updated by the observed class counts:

| Step | Distribution | Mode |
|---|---|---:|
| Prior | Beta(α=2, β=2) | 0.5 |
| Likelihood | Binomial(n=77, p) observing k=37 hallucinated | — |
| Posterior | Beta(α'=39, β'=42) | 38/79 ≈ 0.481013 |

The posterior mode **0.481013** is the shrinkage target on the normalised KL
threshold scale (`t_norm = t / 8.5255`). On the KL scale this is
**0.481013 × 8.5255 ≈ 4.10**. The prior is data-informed (it incorporates
the 37/40 class balance) but regularised toward 0.5 by the Beta(2,2) prior,
unlike RQ61's pure data-derived 0.38. The shrinkage penalty operates on the
normalised scale so λ is comparable to RQ61 (penalty in [0, ~0.5],
comparable to sensitivity in [0, 1]).

The posterior mode is computed analytically by `beta_posterior_mode` and
verified by an assertion in `main()`: `abs(prior_mean_norm − 38/79) < 1e-12`.

### Bootstrap and BCa protocol

- **B = 10000** resamples (≥ the task's B = 1000 minimum; BCa requires the
  full bootstrap distribution, so B = 10000 is used for both OOB cpWER and
  BCa, consistent with RQ59/RQ62).
- **Seed = 42** (task-specified).
- **OOB protocol** (RQ44): for each resample, draw n = 77 indices with
  replacement, re-calibrate the shrinkage KL threshold on the in-bag windows,
  evaluate the cascade cpWER on the out-of-bag windows. Records the per-
  resample threshold (for mode counting) and OOB cpWER (for the BCa CI).
- **Jackknife acceleration** (RQ59/RQ62 structure): delete-1 (77 fits) on the
  in-sample shrinkage-KL cascade cpWER.
- **BCa 95% CI** (RQ59's `bca_ci`, verbatim): bias-correction z0 from the
  in-sample point estimate θ̂; acceleration from the jackknife; Acklam
  inverse-normal, no scipy.
- **Mode count** (RQ48's `count_modes`, verbatim): distinct thresholds with
  ≥ 5% frequency in the bootstrap threshold distribution.

### Best-λ selection (pre-registered)

The best λ is selected by the lexicographic criterion:

1. Lowest OOB cpWER median (H69a is the primary hypothesis).
2. Narrowest BCa width (H69c).
3. Fewest modes (`n_modes_5pct`).
4. Smallest λ (least regularisation, most faithful to data).

The best λ is **0.01** (OOB cpWER median 1.540544 < 1.553571 at λ = 0; the
other λ values tie on OOB cpWER but λ = 0.01 is the smallest).

## Results

### KL detector geometry (RQ43's corpus, n = 77)

| Statistic | Value |
|---|---:|
| KL range | [0.0000, 8.5255] |
| KL mean | 3.3735 |
| KL median | 3.6511 |
| Hallucinated windows (KL ∈ [2.98, 6.58]) | 37 |
| Clean windows (KL ∈ [0.0, 8.53]) | 40 |
| Clean windows with KL = 0 exactly | 13 |
| Clean windows with KL ≥ 4.87 | 4 |
| Hallucinated windows with KL ≥ 4.87 | 1 |

### In-sample calibration (full 77 windows, per λ)

| λ | threshold | sensitivity | specificity | escalation | cascade cpWER | compute |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00 | 4.87 | 0.027 | 0.900 | 0.0649 | 1.5501 | 1.0604 |
| 0.01 | 4.87 | 0.027 | 0.900 | 0.0649 | 1.5501 | 1.0604 |
| 0.10 | 4.87 | 0.027 | 0.900 | 0.0649 | 1.5501 | 1.0604 |
| 0.50 | 4.87 | 0.027 | 0.900 | 0.0649 | 1.5501 | 1.0604 |
| 1.00 | 4.87 | 0.027 | 0.900 | 0.0649 | 1.5501 | 1.0604 |

**The shrinkage penalty does not move the in-sample threshold.** The feasible
set at ≥ 90% specificity contains only the 4.87 grid point: every higher
threshold has lower sensitivity (1 TP drops to 0 at KL > 5.0), every lower
threshold violates the spec floor (4.86 flags 5 clean windows → spec = 0.875
< 0.90). The penalty cannot break the floor, so it cannot move the choice.
The cascade cpWER is 1.5501 across all λ — **74.3% worse than RQ43's
0.8889** and only 2.6% better than the always-tiny baseline (1.5909).

### Bootstrap distribution (B = 10000, seed = 42, OOB)

| λ | thr median | n_modes ≥ 5% | OOB cpWER median | OOB cpWER mean | BCa CI | BCa width |
|---:|---:|---:|---:|---:|---|---:|
| 0.00 | 8.53 | 5 | 1.5536 | 1.5520 | [1.2784, 1.8040] | 0.5257 |
| **0.01** | **4.87** | **7** | **1.5405** | **1.5393** | **[1.2987, 1.8300]** | **0.5313** |
| 0.10 | 4.87 | 7 | 1.5405 | 1.5393 | [1.2987, 1.8300] | 0.5313 |
| 0.50 | 4.87 | 7 | 1.5405 | 1.5393 | [1.2987, 1.8300] | 0.5313 |
| 1.00 | 4.87 | 7 | 1.5405 | 1.5393 | [1.2987, 1.8300] | 0.5313 |

**Shrinkage acts only in the bootstrap.** At λ = 0 the threshold distribution
is dominated by the 8.53 "escalate nothing" fallback (51.9% of resamples pick
the highest grid point because the in-bag clean tail is under-sampled,
pushing specificity-90% above the in-sample 4.87 anchor). At λ > 0 the
penalty pulls the threshold toward 4.10, redistributing mass away from 8.53
(down to 8.7%) and into a wider spread of modes around 4.10–7.63. This
redistribution slightly lowers the OOB cpWER median (1.5536 → 1.5405) but
increases the mode count (5 → 7), which broadens the OOB cpWER distribution
and inflates the BCa width (0.5257 → 0.5313). Both widths are far above
RQ59's 0.283 anchor.

### Best-λ operating point (λ = 0.01)

| Quantity | Value | Reference |
|---|---:|---|
| In-sample threshold | 4.87 | RQ43: 3.30, RQ59: 0.01, RQ62 OR: 5.42/0.38 |
| In-sample escalation | 6.49% | RQ43: 74%, RQ59: 83.1%, RQ62 OR: 55.8% |
| In-sample cascade cpWER | 1.5501 | RQ43: 0.8889, RQ59: 0.7775, RQ62 OR: 0.9423 |
| In-sample compute | 1.0604× | RQ43: ~1.4×, RQ59: 1.77×, RQ62 OR: 1.54× |
| OOB cpWER median | 1.5405 | RQ59: 0.7824, RQ62 OR: 0.9423 |
| OOB cpWER range | [0.981, 2.030] | — |
| BCa 95% CI | [1.2987, 1.8300] | RQ59: [0.66, 0.94] |
| BCa width | 0.5313 | RQ59: 0.2827, RQ62 OR: 0.2391 |
| Bootstrap threshold modes (≥ 5%) | 7 | RQ59: 1, RQ48 lang-id: 3 |

## Why shrinkage kills cpWER on the KL detector

The KL detector's ROC is the wrong shape for a high-specificity gate. The 37
hallucinated windows span KL ∈ [2.98, 6.58] (heavily overlapping the clean
windows' KL ∈ [0.0, 8.53]), so any threshold that protects 90% of clean
windows (≥ 4.87) catches only 1 of 37 hallucinations. The shrinkage prior
(0.481 on the normalised scale = 4.10 on the KL scale) is *inside* the
informative threshold range, but the ≥ 90% specificity floor *blocks* the
penalty from pulling the threshold toward it: the feasible set at ≥ 90%
specificity contains only 4.87, which is above the prior, so the penalty
would *increase* the objective at lower thresholds — but those thresholds
are infeasible.

This is the opposite of RQ61's lang-id result. On the lang-id detector
the prior mean 0.38 was *inside* the feasible set at ≥ 90% specificity, so
the penalty could pull the threshold toward 0.38 and break the pathological
0.01 mode. On the KL detector the prior mean 4.10 is *below* the spec-floor
threshold 4.87, so the penalty is blocked. Shrinkage calibration is not a
free lunch: it requires a detector whose ROC has genuine operating-point
diversity at the target specificity, not a detector whose ROC forces a
single feasible point.

The resulting cascade is the **mirror image of RQ59**: RQ59 collapsed to
threshold 0.01 (sensitivity = 1.0, specificity = 0.325, escalation = 83.1%,
cpWER = 0.78); RQ69 collapses to threshold 4.87 (sensitivity = 0.027,
specificity = 0.900, escalation = 6.5%, cpWER = 1.55). Both collapses are
mechanical properties of the KL ROC, not calibration-rule quality. The KL
detector cannot give a useful cascade operating point at either extreme of
the specificity spectrum — it needs a different detector or a different
cascade structure (e.g. RQ62's ensemble, which trades some cpWER for
operating-point diversity).

## Controlled comparison to RQ59 / RQ62

| Metric | RQ59 (Youden's J) | RQ62 (ensemble OR) | RQ69 (shrinkage KL) |
|---|---:|---:|---:|
| Calibration rule | J = TPR − FPR | KL ∨ lang-id | sens − λ·\|t−prior\| @ 90% spec |
| In-sample threshold | 0.01 | 5.42 / 0.38 | 4.87 |
| In-sample escalation | 83.1% | 55.8% | 6.5% |
| In-sample cascade cpWER | 0.7775 | — | 1.5501 |
| OOB cpWER median | 0.7824 | 0.9423 | 1.5405 |
| BCa 95% CI | [0.66, 0.94] | — | [1.30, 1.83] |
| BCa width | 0.2827 | 0.2391 | 0.5313 |
| Bootstrap modes (≥ 5%) | 1 | — | 7 |

RQ59's Youden's J wins on cpWER (0.78 vs 1.55) but at the cost of escalating
83% of windows. RQ62's ensemble OR is the Pareto middle ground (55.8%
escalation, 0.94 cpWER, 0.24 BCa width). RQ69's shrinkage KL is **dominated
by both**: it has the lowest escalation (6.5%) but the highest cpWER (1.55)
and the widest BCa (0.53). The shrinkage calibration does not improve the
Pareto frontier — it shifts the operating point to a worse corner.

## Reproducibility

- **Source data:** `results/frontier/three_tier_cascade/three_tier_cascade_results.json`
  (RQ43's per-window `tiny_sep_cpwer` / `base_sep_cpwer` / `kl_sep`,
  labelled `experimental/frontier`).
- **Code:** `results/frontier/shrinkage_kl_cascade/analysis.py`
  (pure reanalysis; numpy + stdlib only; scipy / sklearn / Whisper NOT
  required).
- **Outputs:**
  - `results/frontier/shrinkage_kl_cascade/shrinkage_kl_cascade_results.json`
    (full results, including per-resample bootstrap thresholds and OOB
    cpWER at the best λ).
  - `results/frontier/shrinkage_kl_cascade/shrinkage_kl_cascade_results.csv`
    (per-resample bootstrap table at the best λ: resample, threshold,
    oob_cpwer, n_oob, n_escalated_oob, oob_fraction,
    escalation_fraction_oob).
- **Tests:** `tests/test_shrinkage_kl_cascade.py` (≥ 50 unittest tests;
  `try/except ImportError` guard for meeteval).
- **Re-run:** `SKIP_QUALITY_HOOKS=1 /opt/homebrew/bin/python3 results/frontier/shrinkage_kl_cascade/analysis.py`
  (writes both outputs; ~30 s on Apple Silicon).
- **Environment:** python 3 (numpy 2.3.2, scipy 1.18.0, meeteval 0.4.3);
  `unittest` (not pytest); `SKIP_QUALITY_HOOKS=1` for git commit and push.
- **Verifiers (assertions in `main()`):**
  - n = 77 AISHELL-4 windows, 37 hallucinated / 40 clean.
  - RQ43's original rule @ KL = 3.30 reproduces cascade cpWER 0.888947.
  - Always-tiny baseline = 1.590909.
  - base/tiny ratio is constant at 0.428031 across all 77 windows.
  - Beta(2,2) posterior mode = 38/79 to 1e-12.

## Limitations

1. **Single dataset.** RQ69 reanalyses RQ43's 77 AISHELL-4 windows. The KL
   detector's ROC shape (flat-topped at the high-specificity end) may be
   idiosyncratic to AISHELL-4's whisper-tiny separated-audio transcripts;
   generalisation to other corpora requires re-running the cascade
   simulation with new per-window KL/cpWER data (out of scope for RQ69's
   reanalysis-only label).

2. **Beta(2,2) posterior-mode prior is data-informed.** The prior
   incorporates the observed 37/40 class balance, so the posterior mode
   0.481 is close to the empirical hallucination rate 0.481. A stronger
   prior (e.g. Beta(5,5), mode 0.5 with tighter concentration) would pull
   the target slightly higher but still below the spec-floor threshold 4.87,
   so the qualitative verdict would not change. The choice of Beta(2,2)
   follows the task specification ("Beta(2,2) posterior mode").

3. **BCa CI evaluated OOB at re-calibrated thresholds.** RQ59's 0.2827
   anchor was a BCa CI evaluated OOB at re-calibrated Youden's J thresholds
   (same methodology as RQ69), so the H69c comparison is like-for-like on
   CI method. RQ46's 0.2489 anchor (referenced in RQ59's H59c) was a
   percentile CI evaluated in-bag at a fixed threshold; the H69c comparison
   to RQ59 (not RQ46) avoids this methodological mismatch.

4. **The shrinkage penalty is on the normalised KL scale.** This makes λ
   comparable to RQ61 (penalty in [0, ~0.5], comparable to sensitivity in
   [0, 1]), but it also means the penalty magnitude depends on `kl_max`
   (8.5255). A penalty on the raw KL scale would give a different λ-
   sensitivity; the qualitative verdict (shrinkage blocked by the spec
   floor) would not change because the in-sample feasible set is a single
   point regardless of scale.

5. **No LLM / no ollama.** Per the task constraint, no LLM-based correction
   or critic agent is used. The cascade is pure reanalysis of RQ43's
   simulated tiny outputs (no ASR runs).

## Label

`experimental/frontier`. Does NOT overwrite any verified reference or gold
table. The RQ43 / RQ59 / RQ62 reference values are read-only anchors; the
RQ69 outputs are written to a new directory
(`results/frontier/shrinkage_kl_cascade/`).
