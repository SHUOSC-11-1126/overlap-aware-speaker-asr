# RQ68 — Multi-Meeting Power Simulation for Oracle Exclusion

**Label:** experimental/frontier
**Closes issue:** #996
**Source data:** `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (external/sanity-check)
**KL source:** `results/frontier/kl_corrected_router/kl_corrected_router_results.json` (experimental/frontier)
**RQ64 source:** `results/frontier/bootstrap_power_analysis/` (experimental/frontier, PR #993)
**Meeting:** `M_R003S02C01` (AISHELL-4), 77 windows of 30 s
**Method:** Reanalysis only — no Whisper, no ASR run, no LLM, no ollama.

---

## 1. The Question

RQ64 (PR #993) reached a `sample_size_problem` verdict on the corrected router's
"reaches oracle within noise" result: the lang-id corrected router needs n=105
windows and the KL corrected router needs n=250 windows for the BCa CI to
exclude the oracle, but the meeting has only n=77 windows. RQ64 reached this
verdict via the **extrapolated bootstrap**: treat the 77 per-window cpWER
values as the empirical population `F_hat`, draw B=10000 resamples of size n,
compute **one** BCa CI per n using the population mean as `theta_hat`.

The extrapolated bootstrap answers "what would the BCa CI look like if we had
n windows?" under the assumption that `F_hat` is the true distribution and
`theta_hat` is the population mean. But a researcher who actually collected n
windows would not know `F_hat` or the population mean — they would have a
single sample of n values, and would compute the BCa CI treating that sample's
mean as `theta_hat` and that sample's skewness as the jackknife acceleration.

RQ68 asks: **does RQ64's prediction hold up under this more realistic
multi-meeting simulation?** We simulate M=200 independent "synthetic meetings"
of size n (each a resample WITH replacement from `F_hat`), and for each
meeting we compute the standard RQ39 BCa CI the way a researcher would. Power
is the fraction of M meetings whose BCa CI excludes the oracle. If power
reaches 80% well within RQ64's tractable ceiling of n=770, RQ64's
sample-size-problem verdict is confirmed under the more realistic procedure.

## 2. Pre-registered Hypotheses

| ID | Statement | Kill condition |
|----|-----------|----------------|
| H68a | Simulated n=105 lang-id BCa CI (primary meeting, seed=42, B=10000) excludes oracle. | KILL if includes oracle. |
| H68b | Simulated n=250 KL BCa CI (primary meeting, seed=42, B=10000) excludes oracle. | KILL if includes oracle. |
| H68c | Power curve reaches 80% at n ≤ 770 (RQ64's extrapolated ceiling). | KILL if n* > 770. |

H68a/H68b are *single-meeting* checks at RQ64's predicted minimum-n (using the
pre-registered seed=42, B=10000). H68c is the *power-curve* check that
averages over M=200 simulated meetings per n (B=2000 inner bootstrap) and
finds the n* where power crosses 80%.

## 3. Method

### 3.1 Population (inherited from RQ64)

The 77 per-window cpWER values for each router are treated as the empirical
distribution `F_hat`. This is the standard retrospective/empirical-bootstrap
set-up for power analysis: the observed sample is the best estimate of the
population.

* **Lang-id corrected (RQ39 word-level):** entropy threshold 0.38 (== RQ13's
  0.409 on AISHELL-4 — no window has entropy in `(0.38, 0.409]`). Decision
  counts: 38 mixed / 39 separated. Population mean `theta_hat` = 1.04329.
* **KL-corrected (RQ58):** char 2-gram KL-divergence detector, threshold
  5.418144. Population mean `theta_hat` = 1.030303.
* **Oracle point** (both routers): mean of `oracle_best_cpwer` over 77
  windows = 1.017316.

### 3.2 Multi-meeting simulation (NEW vs RQ64)

For each target `n` in `{77, 105, 154, 250, 308, 500, 616, 770, 1000}`:

1. **Primary headline meeting (H68a/H68b):** draw ONE meeting of size n from
   `F_hat` with `meeting_seed=42`, compute BCa CI with B=10000 inner bootstrap
   resamples (`boot_seed=42`). This is a single deterministic check at the
   pre-registered seed.
2. **Power curve (H68c):** draw M=200 independent synthetic meetings of size n
   from `F_hat`. Meeting i uses `meeting_seed = 42 + i` and
   `boot_seed = 42 + i + 200`. For each meeting, compute the standard RQ39
   BCa CI (B=2000 inner bootstrap, jackknife acceleration on the meeting's n
   values, bias-correction z0 from the inner bootstrap distribution). Power =
   fraction of M meetings whose BCa CI lower bound exceeds the oracle.

The BCa CI reuses RQ39's `bca_ci` verbatim, but with a crucial difference from
RQ64: `theta_hat` is the **meeting's sample mean** (not the population mean),
and the jackknife acceleration `a` is computed from the **meeting's n values**
(not the 77-value population). This is the standard BCa CI a researcher would
compute on a freshly collected n-window meeting.

### 3.3 Reproducibility at n=77 (integrity check)

At n=77 the baseline (standard bootstrap on the 77 values, B=10000, seed=42)
must reproduce RQ39's BCa CI `[1.012987, 1.097403]` (lang-id) and RQ58's
`[1.006494, 1.077922]` (KL) bit-for-bit. This is the load-bearing sanity
check: if the BCa framework doesn't reproduce the source RQs at n=77, the
whole multi-meeting simulation is invalid.

### 3.4 RNG

`np.random.default_rng(seed).integers(0, n, size=...)`. The primary meeting
uses `meeting_seed=42` and `boot_seed=42`. The power curve uses
`meeting_seed = 42 + i` and `boot_seed = 42 + i + 200` for meeting
`i = 0..199`. Deterministic; `B_inner=2000` for the power curve (vs `B=10000`
for the primary) keeps the M=200 × 9-grid computation tractable (~40 s) while
giving power resolution of ~3.5 percentage points (binomial SE at p=0.5,
M=200).

## 4. Results

### 4.1 Reproducibility at n=77 (integrity check)

Both routers reproduce their source RQs exactly at the baseline n=77. This is
the load-bearing sanity check.

| Router | RQ | Point cpWER | BCa CI @ n=77 | Reproduces source? |
|--------|----|-------------|---------------|--------------------|
| Lang-id corrected | RQ39 | 1.043290 | [1.012987, 1.097403] | ✓ bit-for-bit |
| KL corrected | RQ58 | 1.030303 | [1.006494, 1.077922] | ✓ bit-for-bit |

Both CIs include the oracle (1.017316) at n=77 → RQ64's H64a is reproduced
for both routers.

### 4.2 Lang-id corrected router — full power curve

| n | Primary meeting mean | Primary BCa CI | Primary excludes? | Power | Excludes / M | Median BCa excludes? |
|------:|--------:|:---------------|:-----------------:|------:|-------------:|:--------------------:|
| 77 | 1.032468 | [1.006494, 1.071429] | ✗ | 0.385 | 77/200 | ✗ |
| **105** | **1.033333** | **[1.009524, 1.071429]** | **✗** | **0.495** | **99/200** | **✗** |
| 154 | 1.038961 | [1.016234, 1.068182] | ✗ | 0.605 | 121/200 | ✓ |
| 250 | 1.034667 | [1.019333, 1.056667] | ✓ | 0.840 | 168/200 | ✓ |
| 308 | 1.034091 | [1.020022, 1.054654] | ✓ | 0.890 | 178/200 | ✓ |
| 500 | 1.040000 | [1.027333, 1.057000] | ✓ | 0.990 | 198/200 | ✓ |
| 616 | 1.035444 | [1.024351, 1.049784] | ✓ | 0.995 | 199/200 | ✓ |
| 770 | 1.034416 | [1.024892, 1.046753] | ✓ | 1.000 | 200/200 | ✓ |
| 1000 | 1.037333 | [1.028333, 1.048500] | ✓ | 1.000 | 200/200 | ✓ |

**n\* (power = 80%) = 234** (linear interpolation between n=154 power=0.605 and
n=250 power=0.840; 0.80 is crossed at n ≈ 234).

### 4.3 KL corrected router — full power curve

| n | Primary meeting mean | Primary BCa CI | Primary excludes? | Power | Excludes / M | Median BCa excludes? |
|------:|--------:|:---------------|:-----------------:|------:|-------------:|:--------------------:|
| 77 | 1.019481 | [1.000000, 1.045455] | ✗ | 0.110 | 22/200 | ✗ |
| 105 | 1.023810 | [1.004762, 1.052381] | ✗ | 0.215 | 43/200 | ✗ |
| 154 | 1.025974 | [1.009740, 1.048701] | ✗ | 0.220 | 44/200 | ✗ |
| **250** | **1.030667** | **[1.017333, 1.052000]** | **✓** | **0.410** | **82/200** | **✗** |
| 308 | 1.027597 | [1.015693, 1.044913] | ✗ | 0.425 | 85/200 | ✗ |
| 500 | 1.026000 | [1.017000, 1.038667] | ✗ | 0.625 | 125/200 | ✓ |
| 616 | 1.024080 | [1.015963, 1.035444] | ✗ | 0.755 | 151/200 | ✓ |
| 770 | 1.025325 | [1.017749, 1.035498] | ✓ | 0.865 | 173/200 | ✓ |
| 1000 | 1.024333 | [1.017833, 1.032833] | ✓ | 0.915 | 183/200 | ✓ |

**n\* (power = 80%) = 680** (linear interpolation between n=616 power=0.755 and
n=770 power=0.865; 0.80 is crossed at n ≈ 680).

### 4.4 Hypothesis verdicts

| Hypothesis | Lang-id | KL |
|------------|---------|----|
| H68a/H68b (primary meeting at RQ64's n excludes oracle) | **KILLED** (n=105: BCa [1.009524, 1.071429] includes 1.017316) | **SUPPORTED** (n=250: BCa [1.017333, 1.052] excludes 1.017316 by 0.000017) |
| H68c (power ≥ 80% at n ≤ 770) | **SUPPORTED** (n\* = 234) | **SUPPORTED** (n\* = 680) |

**Overall verdict: `sample_size_problem` confirmed under multi-meeting
simulation for both routers' H68c.** H68a is honestly KILLED: the primary
simulated meeting at n=105 (seed=42) happens to have a sample mean low enough
that its BCa CI includes the oracle, even though power at n=105 is 0.495
(essentially a coin flip) and n\* for 80% power is 234 (well under 770).

## 5. Interpretation

### 5.1 H68a KILLED — honest reporting

The pre-registered primary meeting at n=105 (lang-id, seed=42, B=10000) has
BCa CI `[1.009524, 1.071429]`, which **includes** the oracle (1.017316). The
lower bound (1.009524) is below the oracle by 0.007792. Per the pre-registered
KILL criterion, **H68a is KILLED**. We do not cherry-pick a different seed.

This is not a contradiction of RQ64. RQ64's n=105 was the minimum n where the
*extrapolated* BCa CI (using the population mean as `theta_hat`) excludes the
oracle. RQ68's H68a is a *single simulated meeting* (using the meeting's
sample mean as `theta_hat`), and the seed-42 meeting happened to land on the
"includes" side of the boundary. The power at n=105 is 0.495 — almost exactly
a coin flip — which is the expected behaviour at the boundary of a
power-curve crossing. The median simulated BCa CI at n=105 also includes the
oracle, consistent with power < 50%. At n=154 the power jumps to 0.605 and
the median BCa CI excludes the oracle; the multi-meeting simulation's
"typical-meeting" crossing is around n=154, slightly higher than RQ64's
population-mean crossing of n=105.

### 5.2 H68b SUPPORTED — remarkable coincidence with RQ64

The pre-registered primary meeting at n=250 (KL, seed=42, B=10000) has BCa CI
`[1.017333, 1.052]`, which **excludes** the oracle (1.017316) by a margin of
0.000017. This is the *same lower bound* (1.017333) and the *same margin*
(0.000017) as RQ64's extrapolated BCa CI at n=250. The KL threshold is
genuinely tight: the population effect size (0.012987) is roughly half the
lang-id effect size (0.025974), so the BCa CI barely clears the oracle at
n=250 in both methods.

However, the power at n=250 is only **0.410** — the seed-42 primary meeting
landed on the lucky side of the distribution. The median simulated BCa CI at
n=250 *includes* the oracle (median_excl=False). 80% power is not reached
until n\*=680. So H68b's SUPPORTED verdict is a single-meeting artefact; the
power-curve verdict (H68c) is the more meaningful check.

### 5.3 H68c SUPPORTED — RQ64's sample-size-problem verdict confirmed

Power reaches 80% at n\*=234 (lang-id) and n\*=680 (KL), both well under
RQ64's tractable ceiling of 770. The power curves rise monotonically with n
and approach 100% by n=770 (lang-id: 1.000; KL: 0.865). This confirms RQ64's
core prediction: the "includes oracle" verdict at n=77 is a sample-size
problem, not a real ceiling. A researcher collecting ~234 windows (lang-id)
or ~680 windows (KL) would have 80% power to conclude "corrected router's
BCa CI excludes the oracle."

### 5.4 Multi-meeting n\* vs RQ64 extrapolated minimum-n

| Router | RQ64 extrapolated minimum-n | RQ68 multi-meeting n\* (80% power) | Ratio |
|--------|------:|------:|------:|
| Lang-id corrected | 105 | 234 | 2.23× |
| KL corrected | 250 | 680 | 2.72× |

The multi-meeting n\* is consistently **2-3× higher** than RQ64's
extrapolated minimum-n. This is expected: RQ64's minimum-n is the n where the
*expected* BCa CI (using the population mean) excludes the oracle; RQ68's n\*
is the n where *80% of simulated meetings* (using each meeting's sample
mean) exclude the oracle. The latter is a stricter criterion — it requires
not just that the CI excludes on average, but that it excludes 80% of the
time across meetings. The 2-3× ratio is the price of accounting for
meeting-to-meeting sampling variability in addition to within-meeting
bootstrap variability.

### 5.5 What this confirms (and does not)

* **Confirms RQ64's sample-size-problem verdict.** The "corrected router
  reaches oracle within noise" result at n=77 is a power artifact: more
  meetings (or a longer meeting) would shrink the BCa CI enough to exclude
  the oracle with high probability. RQ64's n=105 / n=250 predictions are the
  *minimum* n for exclusion; RQ68's n\*=234 / n\*=680 are the n for *80%
  power* — both well under the 770 tractable ceiling.
* **Does not upgrade the claim to "corrected router beats oracle."** The
  corrected router's cpWER (1.0433 lang-id, 1.0303 KL) is still above the
  oracle (1.0173) by construction (`corrected >= oracle` per window, since
  the oracle picks the better of mixed/separated and the corrected router
  picks one of them). Excluding the oracle from the CI means the regret is
  *statistically detectable*, not that it is *practically zero*.
* **Does not model cross-meeting variance.** RQ68 simulates "what would
  happen if we collected n windows from the *same* meeting distribution
  F_hat." It does not model the case where a different meeting has a
  different F_hat. Cross-meeting generalisation would require actually
  collecting more meetings, not just resampling the one we have.

## 6. Methodological Notes

### 6.1 Why multi-meeting simulation, not just extrapolated bootstrap

RQ64's extrapolated bootstrap computes ONE BCa CI per n using the population
mean as `theta_hat`. This is the *expected* BCa CI under F_hat — it tells you
where the CI would centre, but not how variable it would be across
realisations. A researcher who actually collects n windows gets a single
sample, computes a single BCa CI, and either concludes "excludes" or
"includes." The probability of concluding "excludes" is the *power*, which
requires simulating many meetings — exactly what RQ68 does.

The two methods agree at the boundary: RQ64's n=105 (lang-id) is the n where
the expected BCa CI excludes; RQ68's power at n=105 is 0.495 (essentially 50%,
the boundary). RQ64's n=250 (KL) is the n where the expected BCa CI excludes;
RQ68's power at n=250 is 0.410 (slightly below 50%, reflecting the tighter
margin). The small asymmetry for KL is because the BCa CI's bias correction
can push the lower bound below the oracle on left-skewed meetings, even when
the expected (extrapolated) lower bound is just above.

### 6.2 Why B=2000 for the power curve (vs B=10000 for the primary)

The power curve requires M=200 meetings × 9 grid points × 2 routers = 3600
inner bootstraps. At B=10000 each, this would be ~36000 inner bootstraps of
size up to n=1000 — about 6 minutes. At B=2000 each, it's ~80 seconds. BCa
CI is stable to ±0.001 at B=2000 for these distributions (verified by
re-running the primary meeting at B=2000 vs B=10000: lower bounds agree to
4 decimal places). The primary meeting keeps B=10000 to match RQ64's spec
exactly for the H68a/H68b single-meeting check.

### 6.3 Why the primary meeting at n=105 fails but RQ64's extrapolated CI succeeds

RQ64's extrapolated BCa CI at n=105 uses `theta_hat = 1.043290` (the
population mean of the 77 values). The seed-42 primary meeting at n=105 has
`theta_hat = 1.033333` (the meeting's sample mean), which is 0.009957 lower
than the population mean. This shifts the entire BCa CI down by ~0.01,
pushing the lower bound from 1.019048 (RQ64, excludes) to 1.009524 (RQ68
primary, includes). The meeting's sample mean is lower because the seed-42
resample happened to draw more low-cpWER windows than the population
average. This is the meeting-to-meeting variability that RQ64's
extrapolated-bootstrap method does not capture but RQ68's multi-meeting
simulation does.

### 6.4 Determinism

`seed=42`, `B_primary=10000`, `B_power=2000`, `M=200`, `alpha=0.05`. The
primary meeting uses `meeting_seed=42` and `boot_seed=42`. The power curve
uses `meeting_seed = 42 + i` and `boot_seed = 42 + i + 200` for meeting
`i = 0..199`. All results are bit-for-bit reproducible.

## 7. Deliverables

* `analysis.py` — standalone analysis script (stdlib + numpy + scipy only).
* `multi_meeting_power_results.json` — full machine-readable results
  (per-window data, power curve, hypothesis verdicts, reproducibility checks).
* `multi_meeting_power_results.csv` — 18 rows (2 routers × 9 grid points),
  one row per (router, n) with primary-meeting BCa CI, power, and
  median/mean BCa CI summaries.
* `FINDINGS.md` — this file.
* `tests/test_multi_meeting_power.py` — unittest suite covering helpers,
  integration, reproducibility, and hypothesis verdicts.

## 8. Reproducing

```bash
/opt/homebrew/bin/python3 results/frontier/multi_meeting_power_simulation/analysis.py
/opt/homebrew/bin/python3 -m unittest tests.test_multi_meeting_power -v
```

Both commands are deterministic. The analysis re-runs in ~80 s on a laptop
(M=200 meetings × 9 grid points × 2 routers × B=2000 inner bootstrap). The
test suite runs in <5 s (uses reduced M and B for the integration tests).
