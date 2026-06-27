# RQ64 — Retrospective Bootstrap Power Analysis

**Label:** experimental/frontier
**Closes issue:** #988
**Source data:** `results/external_sanity_check/aishell4/rq1_aishell4_validation_results.json` (external/sanity-check)
**KL source:** `results/frontier/kl_corrected_router/kl_corrected_router_results.json` (experimental/frontier)
**Meeting:** `M_R003S02C01` (AISHELL-4), 77 windows of 30 s
**Method:** Reanalysis only — no Whisper, no ASR run, no LLM.

---

## 1. The Question

RQ39 (word-level), RQ55 (char-level), and RQ58 (KL-corrected) all reported that the
corrected router's BCa 95% CI **includes** the oracle point (1.017316). Three readings
are possible:

1. **Sample-size problem.** The CI is too wide because n=77 is small; more data would
   shrink the CI and exclude the oracle, confirming a real (non-zero) regret.
2. **Real ceiling.** The gap (corrected − oracle) is effectively zero, so the CI will
   always include the oracle no matter how large n grows.
3. **Something in between.** A real but practically negligible gap.

RQ64 distinguishes (1) from (2)/(3) via an **extrapolated bootstrap**: treat the 77
per-window cpWER values as the empirical population `F_hat` and resample at sizes
`n > 77`. The BCa CI shrinks at rate `1/√n`, so if the gap is real and non-zero the CI
will eventually exclude the oracle. We then read off the minimum `n` at which exclusion
occurs and compare it to the pre-registered thresholds.

## 2. Pre-registered Hypotheses

| ID | Statement | Kill condition |
|----|-----------|----------------|
| H64a | At n=77 the BCa CI includes the oracle (baseline confirmation). | KILLED if n=77 already excludes. |
| H64b | Required n to exclude oracle > 770 (10× current). | KILLED if ≤ 770. |
| H64c | Effect size (corrected − oracle) < 0.01 (practically negligible). | KILLED if ≥ 0.01. |

## 3. Method

* **Population.** The 77 per-window cpWER values for each router are treated as the
  empirical distribution `F_hat`. This is the standard retrospective/empirical-bootstrap
  set-up for power analysis: the observed sample is the best estimate of the population.
* **Resampling.** For each target `n` in the coarse grid `{77, 154, 308, 616, 1232, 2464}`
  and a finer grid
  `{77, 80, 85, 90, 95, 100, 105, 110, 120, 130, 140, 154, 175, 200, 225, 250, 275, 308, 350, 400, 500, 616, 770, 1000, 1232, 2464}`,
  draw `B=10000` resamples of size `n` with replacement from `F_hat` and record the mean
  of each resample.
* **CI.** Compute the BCa 95% CI (RQ39 framework, jackknife acceleration `a` from the
  77-value population — fixed across `n`; bias-correction `z0` recomputed per `n` from
  the extrapolated bootstrap distribution). At `n=77` this reproduces RQ39 / RQ58 bit
  for bit, which is the integrity check.
* **RNG.** `np.random.default_rng(seed=42).integers(0, n_pop, size=n_target)` per
  resample, chunked at 500 to bound memory — the chunked stream is identical to the
  one-shot stream, verified by the n=77 reproducibility tests.
* **Effect size.** `theta_hat − oracle`, where `theta_hat` is the mean of the 77
  per-window values (the population mean of `F_hat`).
* **Routers.**
  * **Lang-id corrected (RQ39 word-level):** entropy threshold 0.38 (== RQ13's 0.409 on
    AISHELL-4 — no window has entropy in `(0.38, 0.409]`). Decision counts: 38 mixed / 39
    separated.
  * **KL-corrected (RQ58):** char 2-gram KL-divergence detector, threshold 5.418144.

## 4. Results

### 4.1 Reproducibility at n=77 (H64a integrity check)

Both routers reproduce their source RQs exactly at the baseline n=77. This is the
load-bearing sanity check: if the extrapolated bootstrap framework doesn't reproduce the
published BCa CIs at n=77, the whole extrapolation is invalid.

| Router | RQ | Point cpWER | BCa CI @ n=77 | Reproduces source? |
|--------|----|-------------|---------------|--------------------|
| Lang-id corrected | RQ39 | 1.043290 | [1.012987, 1.097403] | ✓ bit-for-bit |
| KL corrected | RQ58 | 1.030303 | [1.006494, 1.077922] | ✓ bit-for-bit |

Both CIs include the oracle (1.017316) at n=77 → **H64a SUPPORTED** for both routers.

### 4.2 Coarse extrapolation grid

| n | Lang-id BCa CI | Lang-id excludes? | KL BCa CI | KL excludes? |
|------:|----------------|:-----------------:|-----------|:------------:|
| 77 | [1.012987, 1.097403] | ✗ | [1.006494, 1.077922] | ✗ |
| 154 | [1.021645, 1.083074] | ✓ | [1.014069, 1.063853] | ✗ |
| 308 | [1.027056, 1.070346] | ✓ | [1.018398, 1.052489] | ✓ |
| 616 | [1.031656, 1.061959] | ✓ | [1.021645, 1.045996] | ✓ |
| 1232 | [1.034767, 1.056006] | ✓ | [1.024080, 1.041036] | ✓ |
| 2464 | [1.037202, 1.052083] | ✓ | [1.025771, 1.037844] | ✓ |

CI width shrinks at roughly `1/√n` for both routers, as expected.

### 4.3 Minimum n to exclude the oracle (fine grid)

| Router | min n | Baseline n | Multiple of baseline | Effect size |
|--------|------:|-----------:|:--------------------:|------------:|
| Lang-id corrected (RQ39) | **105** | 77 | 1.36× | 0.025974 |
| KL corrected (RQ58) | **250** | 77 | 3.25× | 0.012987 |

The lang-id router needs only ~28 more windows than we have; the KL router needs ~173
more. KL needs more windows precisely because its gap to oracle is roughly half the
lang-id gap — a smaller effect needs more data to clear the CI.

The KL threshold is genuinely tight: at n=225 the BCa lower bound is 1.016296 (oracle
1.017316 still inside); at n=250 the lower bound is 1.017333, excluding the oracle by a
margin of 0.000017. The lang-id exclusion at n=105 is more comfortable (lower bound
1.019048 vs oracle 1.017316, margin 0.001732).

### 4.4 Hypothesis verdicts

| Hypothesis | Lang-id | KL |
|------------|---------|----|
| H64a (baseline includes oracle) | **SUPPORTED** | **SUPPORTED** |
| H64b (required n > 770) | **KILLED** (n=105) | **KILLED** (n=250) |
| H64c (effect < 0.01) | **KILLED** (0.026) | **KILLED** (0.013) |

**Overall verdict (both routers): `sample_size_problem`.**

The corrected router's CI including the oracle at n=77 is **not** a real ceiling. The
gap to oracle is real and non-negligible (0.013–0.026), and a modestly larger sample
(105 windows for lang-id, 250 for KL — both well under the 770 tractability threshold)
would shrink the BCa CI enough to exclude the oracle.

## 5. Interpretation

* **The "includes oracle" verdict in RQ39 / RQ55 / RQ58 is a power artifact.** It cannot
  be read as "the corrected router matches the oracle." The corrected router has a real,
  detectable regret of 0.026 (lang-id, word-level) or 0.013 (KL, char-level).
* **The KL router is closer to the oracle but harder to certify.** Its smaller effect
  size (0.013 vs 0.026) is why it needs more windows (250 vs 105) to reach statistical
  separation. This is the usual small-effect / large-n trade-off.
* **Practical implications for AISHELL-4 evaluation.** A single 30-minute meeting
  (60 windows) is under-powered for certifying corrected-router regret at the 5% level.
  A 90-minute meeting (~180 windows) would suffice for the lang-id router; the KL router
  needs ~2 hours of meeting audio (~250 windows). Future external benchmarks should
  budget meeting length accordingly.
* **What this does *not* show.** RQ64 is an extrapolation under the assumption that the
  77 observed windows are representative of `F_hat`. It is a statement about statistical
  power, not about the corrected router's deployment accuracy. The effect sizes are
  point estimates from one meeting; cross-meeting variance is not modelled here.

## 6. Methodological Notes

* **Why extrapolated bootstrap, not a t-test.** The per-window cpWER distribution is
  right-skewed and bounded below by 0; BCa (not a normal approximation) is what RQ39 /
  RQ58 reported. Reusing the same BCa framework at larger `n` keeps the integrity check
  load-bearing: at n=77 the extrapolated BCa CI *is* RQ39's BCa CI, by construction.
* **Why the jackknife acceleration `a` is fixed across `n`.** `a` is a property of the
  population's skewness under the smooth functional `theta = mean`. Under the
  empirical-population extrapolation `F_hat` is fixed, so `a` is fixed. Only `z0`
  (which depends on how often the bootstrap mean falls below `theta_hat`) changes with
  `n`, because the bootstrap distribution tightens around `theta_hat` as `n` grows.
  This is the standard formulation for retrospective power analysis under the
  empirical-bootstrap.
* **Why chunk=500.** At n=2464 and B=10000 the index array is ~200 MB. Chunking at 500
  keeps peak memory to ~10 MB per chunk while preserving the exact RNG stream
  (`default_rng(42).integers(0, n_pop, size=(n_boot, n))` chunked along axis 0 is
  bit-identical to the one-shot draw — asserted in the test suite).
* **Determinism.** `seed=42`, `n_boot=10000`, `alpha=0.05` match RQ39 / RQ58 exactly.

## 7. Deliverables

* `bootstrap_power_analysis.py` — standalone analysis script (stdlib + numpy only).
* `bootstrap_power_results.json` — full machine-readable results (per-window data,
  grids, hypothesis verdicts, reproducibility checks).
* `bootstrap_power_results.csv` — 52 rows (2 routers × 26 fine-grid points), one row
  per (router, n) with BCa/percentile CI bounds and exclusion flags.
* `FINDINGS.md` — this file.
* `tests/test_bootstrap_power.py` — 105 tests (helpers, integration, reproducibility,
  hypothesis verdicts).

## 8. Reproducing

```bash
/opt/homebrew/bin/python3 results/frontier/bootstrap_power_analysis/bootstrap_power_analysis.py
/opt/homebrew/bin/python3 -m unittest tests.test_bootstrap_power -v
```

Both commands are deterministic and re-run the analysis in <2 s on a laptop. The JSON
and CSV in this directory are regenerated verbatim by the script.
