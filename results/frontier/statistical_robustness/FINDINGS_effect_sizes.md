# Effect Size and Post-Hoc Power Analysis — RQ11

> **Label: `experimental/frontier`**
>
> Reanalysis only. No new data was collected, no new models were run, and no
> verified references or gold result tables were modified. This document
> re-examines the 21 numbered findings from RQ3 (`bh_correction.py`,
> `correction_table.csv`) under an effect-size and post-hoc power lens. All
> statistics are computed by `effect_size_analysis.py` in this directory.

This work addresses GitHub issue #897 (RQ11) and tests three research
questions about the practical significance of the BH-surviving findings and
the power status of the non-surviving findings.

---

## 1. Headline result

| Quantity | Value |
|---|---|
| Total findings audited | 21 |
| Findings with insufficient data (excluded) | 3 (F04, F08, F09) |
| Directional findings in the BH family | 17 |
| BH-surviving directional findings | 6 |
| Non-surviving directional findings | 11 |
| Null finding (F15, reported separately) | 1 |
| **Practically significant** (\|d\|>0.5 AND power>0.80) | **5** |
| **Underpowered** (\|d\|>0.5 AND power<0.80) | **2** |
| **Genuinely small** (\|d\|≤0.5) | **10** |
| Insufficient data | 3 |
| Null finding | 1 |

**The 6 BH-surviving findings are NOT all practically significant.** Five of
the six (F10, F14, F18, F19, F21) have medium-to-large standardized effect
sizes (|d| = 0.55–1.47) and post-hoc power > 0.80. The sixth survivor, F01
(separation tax at low overlap), has a genuinely small effect size
(d = −0.26) — it survives BH correction because of its large sample (n=80)
and low variance, not because the effect is large.

**The 11 non-surviving findings are NOT predominantly underpowered.** Only 2
of 11 (F02 with n=3, F07 with n=5) have |d| > 0.5 but insufficient power. The
remaining 9 have genuinely small standardized effects (|d| = 0.09–0.36),
meaning their BH failure reflects a real absence of a medium-to-large effect,
not merely a lack of statistical power.

---

## 2. Methods

### 2.1 Effect sizes

* **Cohen's d** — standardized mean difference. For one-sample/paired t-tests,
  d = mean_diff / sd_diff. For two-sample t-tests, d = (mean₁−mean₂) / pooled_sd.
  For Pearson correlations, d = 2r / √(1−r²).
* **Hedges' g** — small-sample corrected d via the correction factor
  J = 1 − 3/(4·df − 1), where df = n−1 (one-sample/paired), n₁+n₂−2
  (two-sample), or n−2 (correlation). g = d × J.
* **95% CI for d** — analytical standard error (Hedges & Olkin 1985) for
  t-tests: SE_d = √(1/n + d²/(2n)) for one-sample/paired,
  SE_d = √((n₁+n₂)/(n₁n₂) + d²/(2(n₁+n₂−2))) for two-sample. For correlations,
  the Fisher-z transform is used: z = atanh(r), SE_z = 1/√(n−3), CI converted
  back to d via d = 2r/√(1−r²).

### 2.2 Post-hoc power

Post-hoc power is computed at two-sided α = 0.05 given the observed d and n.

* **t-tests (one-sample, paired, two-sample):** The noncentral t CDF is
  evaluated via Gauss-Laguerre quadrature over the chi-squared mixing
  distribution. The noncentral t representation T = (Z + δ) / √(V/df) where
  Z ~ N(0,1) and V ~ χ²(df) gives:

  F(t; df, δ) = E_V[Φ(t·√(V/df) − δ)]

  evaluated by 100-point Gauss-Laguerre quadrature in log-space (to avoid
  overflow for large df). This is **critical for small samples**: at n=3
  (df=2), the normal approximation overestimates power by ~2× (0.92 vs the
  correct 0.45 for F02), because the t-distribution with 2 df has very heavy
  tails and a critical value of 4.303 (vs 1.96 for the normal).

* **Correlations:** The Fisher-z normal approximation is used
  (δ = atanh(r)·√(n−3)), which is standard and accurate for n ≥ 20.

### 2.3 MDE (minimum detectable effect)

The MDE at 80% power is computed in standardized d units by inverting the
two-sided t-test using the t-distribution quantiles (consistent with
`bh_correction.py` but expressed in d rather than raw units):

* one-sample/paired: MDE_d = (t_{0.975,df} + t_{0.80,df}) / √n
* two-sample: MDE_d = (t_{0.975,df} + t_{0.80,df}) · √(1/n₁ + 1/n₂)
* correlation: MDE_r = tanh((z_{0.975} + z_{0.80}) / √(n−3)), converted to d

### 2.4 Classification

Each finding is classified as:

| Classification | Criterion |
|---|---|
| **practically_significant** | \|d\| > 0.5 AND power > 0.80 |
| **underpowered** | \|d\| > 0.5 AND power < 0.80 |
| **genuinely_small** | \|d\| ≤ 0.5 |
| **insufficient_data** | no inferential test possible (F04, F08, F09) |
| **null_finding** | F15 (consistent with H0, reported separately) |

The |d| > 0.5 threshold corresponds to Cohen's "medium" effect size convention.

### 2.5 Data sources

All effect sizes are recomputed from the **existing per-track CSVs** already in
the repository — no new runs. The raw data extraction mirrors
`bh_correction.py`'s finding functions but captures the intermediate mean and
SD needed for Cohen's d. BH survival status is loaded from the existing
`correction_table.csv`.

---

## 3. Effect size table

Ordered by finding ID. `d` = Cohen's d, `g` = Hedges' g, `CI` = 95% CI for d,
`power` = post-hoc power at α=0.05, `MDE_d` = minimum detectable d at 80% power.

| ID | short_name | n | d | g | CI_low | CI_high | power | MDE_d | classification | BH survives |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|:---:|
| F01 | separation_tax_low_overlap | 80 | −0.261 | −0.258 | −0.487 | −0.034 | 0.634 | 0.317 | genuinely_small | **yes** |
| F02 | gold_benefit_separation | 3 | 1.942 | 1.110 | −2.278 | 6.163 | 0.453 | 3.097 | underpowered | no |
| F03 | repetition_hallucination_mechanism | 80 | 0.160 | 0.158 | −0.064 | 0.384 | 0.293 | 0.317 | genuinely_small | no |
| F04 | speaker_swap_not_dominant | 0 | — | — | — | — | — | — | insufficient_data | — |
| F05 | router_v1_fails_synthetic | 25 | 0.261 | 0.252 | −0.159 | 0.680 | 0.240 | 0.584 | genuinely_small | no |
| F06 | router_v2_improves_synthetic | 25 | 0.177 | 0.171 | −0.239 | 0.592 | 0.135 | 0.584 | genuinely_small | no |
| F07 | risk_aware_not_best_cer | 5 | 0.730 | 0.584 | −0.667 | 2.128 | 0.243 | 1.662 | underpowered | no |
| F08 | synthetic_silver_label | 0 | — | — | — | — | — | — | insufficient_data | — |
| F09 | llm_rag_optional | 0 | — | — | — | — | — | — | insufficient_data | — |
| F10 | compute_cascade_base_better | 25 | 1.373 | 1.330 | 0.798 | 1.949 | 1.000 | 0.584 | **practically_significant** | **yes** |
| F11 | noise_robust_gate_cure | 192 | 0.132 | 0.131 | −0.011 | 0.275 | 0.442 | 0.203 | genuinely_small | no |
| F12 | speaker_gate_moderate_babble | 32 | 0.237 | 0.232 | −0.128 | 0.603 | 0.256 | 0.511 | genuinely_small | no |
| F13 | gate_selector_falsified | 288 | 0.091 | 0.090 | −0.026 | 0.207 | 0.335 | 0.166 | genuinely_small | no |
| F14 | emotion_no_separation_tax | 16 | 0.856 | 0.812 | 0.233 | 1.479 | 0.892 | 0.749 | **practically_significant** | **yes** |
| F15 | arousal_null_predictor | 120 | 0.003 | 0.003 | −0.361 | 0.368 | 0.050 | 0.524 | null_finding | yes* |
| F16 | lexical_tax_cer_reproduction | 16 | −0.356 | −0.338 | −0.905 | 0.194 | 0.266 | 0.749 | genuinely_small | no |
| F17 | llm_repair_net_harm | 16 | 0.133 | 0.127 | −0.402 | 0.669 | 0.079 | 0.749 | genuinely_small | no |
| F18 | objective_aware_decoupling | 40 | 0.547 | 0.536 | 0.204 | 0.890 | 0.921 | 0.454 | **practically_significant** | **yes** |
| F19 | emotion_fidelity_meter_corr | 192 | −1.199 | −1.195 | −1.545 | −0.878 | 1.000 | 0.410 | **practically_significant** | **yes** |
| F20 | gate_emotion_cost_speaker_least | 32 | 0.289 | 0.281 | −0.079 | 0.656 | 0.353 | 0.511 | genuinely_small | no |
| F21 | causal_confident_attractor | 66 | 1.469 | 1.452 | 0.903 | 2.035 | 1.000 | 0.717 | **practically_significant** | **yes** |

\* F15 is a null finding; "BH survives" means *not refuted* (p > 0.05).

The machine-readable version is `effect_size_table.csv` / `effect_size_results.json`.

---

## 4. Research question verdicts

### RQ1: Are all 6 BH-surviving findings practically significant (|d| > 0.5)?

**Verdict: NOT FULLY SUPPORTED.**

Five of the six BH-surviving findings are practically significant (|d| > 0.5
AND power > 0.80):

| Survivor | d | power | classification |
|---|---:|---:|---|
| F10 (compute cascade) | 1.373 | 1.000 | practically_significant |
| F14 (emotion no tax) | 0.856 | 0.892 | practically_significant |
| F18 (objective-aware decoupling) | 0.547 | 0.921 | practically_significant |
| F19 (emotion fidelity meter) | −1.199 | 1.000 | practically_significant |
| F21 (causal confident attractor) | 1.469 | 1.000 | practically_significant |
| **F01 (separation tax low overlap)** | **−0.261** | **0.634** | **genuinely_small** |

F01 survives BH correction (BH-adjusted p = 0.032) but its standardized effect
size is small (d = −0.26, below the |d| > 0.5 medium-effect threshold) and its
post-hoc power is only 0.63. The raw mean difference (ΔCER = −0.615) appears
substantial, but the within-condition variability (SD = 2.36) is large relative
to the mean, producing a small standardized effect. F01's BH survival is driven
by the large sample (n=80) rather than by a large effect.

**Implication:** The frontier's BH-surviving backbone is 5/6 practically
significant, not 6/6. F01 should be reported as "statistically significant but
small effect size" rather than "practically significant."

### RQ2: Are >50% of the 11 non-surviving findings underpowered (|d| > 0.5 but power < 0.80)?

**Verdict: NOT SUPPORTED.**

Only **2 of 11** non-surviving findings are underpowered:

| Non-survivor | d | power | classification |
|---|---:|---:|---|
| F02 (gold benefit separation) | 1.942 | 0.453 | underpowered |
| F07 (risk-aware not best CER) | 0.730 | 0.243 | underpowered |
| F03 | 0.160 | 0.293 | genuinely_small |
| F05 | 0.261 | 0.240 | genuinely_small |
| F06 | 0.177 | 0.135 | genuinely_small |
| F11 | 0.132 | 0.442 | genuinely_small |
| F12 | 0.237 | 0.256 | genuinely_small |
| F13 | 0.091 | 0.335 | genuinely_small |
| F16 | −0.356 | 0.266 | genuinely_small |
| F17 | 0.133 | 0.079 | genuinely_small |
| F20 | 0.289 | 0.353 | genuinely_small |

The remaining **9 of 11** non-surviving findings have genuinely small
standardized effect sizes (|d| = 0.09–0.36, all below the 0.5 medium threshold).
Their BH failure is not ambiguous — it reflects a real absence of a
medium-to-large effect, not merely insufficient power.

**Implication:** This is a **more pessimistic** conclusion than RQ3 suggested.
RQ3 classified 9–10 of the 11 non-survivors as "underpowered" (observed
|effect| < MDE in raw units), implying their BH failure was ambiguous and
could be resolved with larger samples. The effect-size analysis shows that
most non-survivors have genuinely small effects: even with infinite sample
size, a |d| of 0.09–0.36 would not cross the |d| > 0.5 practical-significance
threshold. Only F02 (n=3, d=1.94) and F07 (n=5, d=0.73) are genuinely
underpowered — their effects are medium-to-large but the samples are too small
to detect them reliably.

### RQ3: Do the 9 underpowered findings from RQ3 match the underpowered group from this power analysis?

**Verdict: NO — the sets do not match.**

| Set | Findings |
|---|---|
| RQ3 "underpowered" (raw-unit MDE criterion) | F02, F03, F05, F06, F07, F11, F12, F16, F17, F20 |
| RQ11 "underpowered" (standardized d + power criterion) | F02, F07 |
| Intersection | F02, F07 |
| Only in RQ3 | F03, F05, F06, F11, F12, F16, F17, F20 |
| Only in RQ11 | (none) |

The RQ11 underpowered set is a **strict subset** of the RQ3 underpowered set.
The 8 findings that RQ3 classified as underpowered but RQ11 does not (F03,
F05, F06, F11, F12, F16, F17, F20) all have |d| < 0.5 — they are genuinely
small effects, not underpowered medium effects.

**Why the discrepancy?** RQ3 used the criterion |observed effect| < MDE in
**raw units** (e.g., ΔCER < MDE_dCER). This criterion conflates two cases:
1. The effect is medium-to-large but the sample is too small to detect it
   (true underpowered).
2. The effect is genuinely small in raw units AND the MDE happens to be larger
   (because the SD is large, inflating the MDE).

The standardized criterion (|d| > 0.5 AND power < 0.80) separates these two
cases. Findings with large SD but small mean difference have small d values
regardless of the raw-unit MDE, correctly identifying them as genuinely small
rather than underpowered.

**Note on the "9" count:** RQ3's FINDINGS.md lists 10 finding IDs (F02, F03,
F05, F06, F07, F11, F12, F16, F17, F20) but states "9 are underpowered." This
appears to be a minor counting discrepancy in the original document. The RQ11
analysis uses the standardized criterion and identifies 2 underpowered
findings (F02, F07), which is a strict subset of the RQ3 list.

---

## 5. Honest interpretation

### What the effect-size analysis confirms

The frontier's quantitative backbone is real and practically significant for
5 of 6 BH-surviving findings. F10 (compute cascade, d=1.37), F19 (emotion
fidelity meter, d=−1.20), F21 (causal confident attractor, d=1.47), F14
(emotion no tax, d=0.86), and F18 (objective-aware decoupling, d=0.55) all
have medium-to-large standardized effects with post-hoc power ≥ 0.89. These
are the findings the project should foreground.

### What the effect-size analysis revises

1. **F01 is not practically significant.** Its BH survival (p_adj = 0.032) is
   real but the effect is small (d = −0.26). The project should present F01
   as "statistically significant under BH, small effect size" rather than
   "practically significant."

2. **Most non-survivors are genuinely small, not underpowered.** RQ3's
   raw-unit MDE criterion classified 9–10 of 11 non-survivors as
   "underpowered," suggesting their BH failure was ambiguous. The standardized
   analysis shows that 9 of 11 have |d| < 0.5 — their effects are genuinely
   small, and larger samples would not make them practically significant.
   Only F02 (n=3) and F07 (n=5) are truly underpowered medium-to-large
   effects trapped by tiny gold-sample sizes.

3. **The noncentral t matters for small n.** The normal approximation
   overestimates power by ~2× at n=3 (F02: 0.92 vs correct 0.45) because the
   t-distribution with 2 df has very heavy tails (t_crit = 4.303 vs z = 1.96).
   The Gauss-Laguerre noncentral t CDF used here gives accurate power even
   for the smallest samples in the study.

### What this means for the project

The frontier should be presented as:

- **5 practically significant findings** (F10, F14, F18, F19, F21) —
  medium-to-large effects, well-powered, BH-surviving.
- **1 statistically significant but small-effect finding** (F01) —
  BH-surviving but |d| < 0.5.
- **2 underpowered findings** (F02, F07) — medium-to-large effects trapped
  by tiny gold samples (n=3, n=5); their BH failure is genuinely ambiguous.
- **9 genuinely small findings** (F03, F05, F06, F11, F12, F13, F16, F17, F20)
  — small standardized effects; BH failure reflects real absence of a
  medium-to-large effect, not insufficient power.
- **1 null finding** (F15) — consistent with H0.
- **3 insufficient-data findings** (F04, F08, F09) — no inferential test.

---

## 6. Reproducibility

```bash
cd <repo root>
python3 results/frontier/statistical_robustness/effect_size_analysis.py
# writes effect_size_table.csv and effect_size_results.json in this directory
```

Inputs (all pre-existing, unmodified): the `results/tables/*.csv` gold and
synthetic tables, the `results/frontier/*/{*_curve,probe_rows}.csv` per-track
files, and `results/frontier/statistical_robustness/correction_table.csv`
(for BH survival status). No verified references or gold tables were
overwritten. The original `bh_correction.py` and `correction_table.csv` are
not modified.
