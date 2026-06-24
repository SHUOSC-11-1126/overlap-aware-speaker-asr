# Statistical Robustness Audit — BH Correction + Post-Hoc Power (RQ3)

> **Label: `experimental/frontier`**
>
> Reanalysis only. No new data was collected, no new models were run, and no
> verified references or gold result tables were modified. This document
> re-examines the 21 numbered findings recorded in `docs/project_state.md`
> under a multiple-comparison and power lens. All statistics are computed by
> `bh_correction.py` in this directory (pure Python + numpy/pandas; `scipy`
> is unavailable in the environment, so the Student-t CDF/SF/PPF and the
> inverse normal are implemented from first principles — see *Methods*).

This work closes GitHub issue #882 and tests hypothesis **H3**:

> **H3** — Under Benjamini-Hochberg correction at q=0.05, ≥15 of the 21
> frontier findings' core directional claims remain statistically supported.

---

## 1. Headline result

| Quantity | Value |
|---|---|
| Total findings audited | 21 |
| Findings with insufficient data for a p-value (excluded from BH family) | 3 (F04, F08, F09) |
| Directional findings in the BH family | 17 |
| Null finding (F15, excluded from BH rejection family, reported separately) | 1 |
| **Directional findings surviving BH at q=0.05** | **6** |
| Total "supported" including the F15 null (consistent with H0) | 7 |
| **H3 threshold** | **≥15** |
| **H3 verdict** | **NOT SUPPORTED** |

Only **6 of 17** directional findings survive BH correction at q=0.05
(F01, F10, F14, F18, F19, F21). Including the F15 null result, which is
*consistent with* its null hypothesis, the total is 7 — far below the 15
required by H3. The project's frontier claims are therefore **not**
collectively robust under multiple-comparison control: the apparent strength
of the frontier rests on a small number of highly significant, well-powered
results, while the majority are individually marginal and do not survive FDR
correction.

---

## 2. Methods

### 2.1 Statistical core (pure Python, no scipy)

`scipy`/`statsmodels` are not installed in this environment. All inferential
machinery is implemented directly in `bh_correction.py`:

- **Student-t CDF** via the regularized incomplete beta function `I_x(a,b)`,
  evaluated by the continued-fraction expansion (Lentz's method) from
  *Numerical Recipes* §6.4. `t_sf` = 1 − `t_cdf`.
- **t-distribution inverse (PPF)** by bisection on `t_cdf` (monotone, robust
  for the df range 2–500 encountered here).
- **Standard-normal inverse (PPF)** via Acklam's rational approximation
  (used only for the correlation power formula).
- **One-sample t**, **paired t**, and **Welch's two-sample t** computed from
  first principles; **Pearson r test** with the standard t approximation
  `t = r·√(n−2)/√(1−r²)`, df = n−2.
- **Benjamini-Hochberg** step-up adjusted p-values (the standard
  `p_adj[i] = min over k≥i of (m/k)·p_(k)` with monotone enforcement and
  cap at 1).
- **Post-hoc power / MDE at 80% power, two-sided α=0.05**: solved by
  inverting the two-sided test. For paired/one-sample/two-sample t-tests the
  MDE is `δ = (t_{1−α/2,ν} + t_{0.80,ν})·σ_d/√n`; for the Pearson test the
  MDE on |r| uses the Fisher-z normal approximation
  `|r|_min = tanh((z_{1−α/2}+z_{0.80})/√(n−3))`.

All p-values are **one-sided in the direction of each finding's claim**,
except F15 which is a two-sided null-correlation test (large p ⇒ consistent
with the null). This one-sided convention is the most charitable to the
claims; using two-sided values would only weaken them further.

### 2.2 BH family construction

Per the task constraints ("if data insufficient for a p-value, record
'insufficient data' and exclude from the BH family with a note"):

- **Excluded — insufficient data (3):** F04 (speaker-swap is a descriptive
  error-composition claim over 5 gold cases, no per-error-count hypothesis
  test), F08 (the silver-label statement is methodological, not inferential),
  F09 (LLM/RAG-optional is a methodology statement, not a quantitative
  hypothesis).
- **Excluded — null finding (1):** F15 asserts arousal does *not* predict ASR
  difficulty. A null result does not fit the BH rejection framework (BH
  controls the *false discovery* rate among rejections); we therefore report
  F15 separately and interpret "survives" as *p > 0.05, i.e. consistent with
  the null*. It is **not** counted toward the BH family of 17.
- **In BH family (17):** F01, F02, F03, F05, F06, F07, F10, F11, F12, F13,
  F14, F16, F17, F18, F19, F20, F21.

### 2.3 Data sources (reanalysis only)

Every p-value is recomputed from the **existing per-track CSVs** already in
the repository — no new runs. Key sources: `results/tables/cer_results.csv`
(gold CER), `results/tables/synthetic_cer_results.csv` +
`synthetic_routing_decisions.csv` / `routing_decisions_v2.csv` (per-sample
synthetic CER for F05/F06), `results/frontier/separation_tax/phase_curve.csv`
(F01/F03), `results/frontier/runtime_cascade/cascade_curve.csv` (F10), and
the per-frontier `*_curve.csv` / `probe_rows.csv` files for F11–F21.
`risk_aware_selection.csv` + `cer_results.csv` feed F07.

---

## 3. BH correction table (q = 0.05)

Ordered by finding id. `survives` = BH-adjusted p ≤ 0.05 (for F15,
`survives` = raw p > 0.05, consistent with the null).

| finding_id | short_name | n | raw_p | bh_adj_p | survives_q005 | test |
|---|---|---:|---:|---:|:---:|---|
| F01 | separation_tax_low_overlap | 80 | 0.01113 | 0.03152 | **yes** | one-sample t (ΔCER<0) |
| F02 | gold_benefit_separation | 3 | 0.03907 | 0.08302 | no | paired t (mixed−sep>0) |
| F03 | repetition_hallucination_mechanism | 80 | 0.07827 | 0.11474 | no | paired t (rep_sep−rep_mixed>0) |
| F04 | speaker_swap_not_dominant | 0 | — | — | — | insufficient data |
| F05 | router_v1_fails_synthetic | 25 | 0.10248 | 0.11615 | no | paired t (v1−oracle>0) |
| F06 | router_v2_improves_synthetic | 25 | 0.19312 | 0.20519 | no | paired t (v1−v2>0) |
| F07 | risk_aware_not_best_cer | 5 | 0.08891 | 0.11474 | no | paired t (risk−oracle>0) |
| F08 | synthetic_silver_label | 0 | — | — | — | insufficient data |
| F09 | llm_rag_optional | 0 | — | — | — | insufficient data |
| F10 | compute_cascade_base_better | 25 | 2.10e−07 | 1.79e−06 | **yes** | paired t (tiny−base>0) |
| F11 | noise_robust_gate_cure | 192 | 0.03494 | 0.08302 | no | paired t (sep−gate>0) |
| F12 | speaker_gate_moderate_babble | 32 | 0.09449 | 0.11474 | no | paired t (sep−speaker>0) |
| F13 | gate_selector_falsified | 288 | 0.06252 | 0.10629 | no | paired t (selector−speaker>0) |
| F14 | emotion_no_separation_tax | 16 | 0.00188 | 0.00641 | **yes** | one-sample t (emo_benefit>0) |
| F15 | arousal_null_predictor | 120 | 0.98512 | 0.98512 | yes* | Pearson r two-sided (null) |
| F16 | lexical_tax_cer_reproduction | 16 | 0.08748 | 0.11474 | no | one-sample t (cer_benefit<0) |
| F17 | llm_repair_net_harm | 16 | 0.30069 | 0.30069 | no | paired t (after−before>0) |
| F18 | objective_aware_decoupling | 40 | 6.62e−04 | 0.00281 | **yes** | paired t (coupled−decoupled>0) |
| F19 | emotion_fidelity_meter_corr | 192 | 1.18e−14 | 2.00e−13 | **yes** | Pearson r one-sided (r<0) |
| F20 | gate_emotion_cost_speaker_least | 32 | 0.05639 | 0.10629 | no | paired t (flat−speaker>0) |
| F21 | causal_confident_attractor | 66 | 7.92e−06 | 4.49e−05 | **yes** | Welch t (cat>clean) |

\* F15 is a null finding; "survives" means *not refuted* (p > 0.05). It is
excluded from the BH rejection family and not counted in the 6/17 survivor
tally for directional claims.

The machine-readable version is `correction_table.csv` / `.json` in this
directory.

---

## 4. Post-hoc power analysis (MDE at 80% power, two-sided α=0.05)

The MDE is the smallest true effect that this study's sample size would have
detected with 80% power. An observed effect smaller than the MDE should be
treated as underpowered — a non-rejection is ambiguous rather than evidence
of no effect.

| finding_id | n | observed effect | MDE_80pct | MDE units | powered? |
|---|---:|---|---:|---|:---:|
| F01 | 80 | mean ΔCER = −0.615 | 0.748 | dCER | borderline |
| F02 | 3 | mean ΔCER = 0.303 | 0.484 | dCER | **no (n=3)** |
| F03 | 80 | mean ΔRep = 4.89 | 9.692 | rep-count | **no** |
| F05 | 25 | mean regret = 0.269 | 0.602 | dCER | **no** |
| F06 | 25 | mean ΔCER = 0.183 | 0.607 | dCER | **no** |
| F07 | 5 | mean regret = 0.015 | 0.033 | dCER | **no (n=5)** |
| F10 | 25 | mean ΔCER = 0.267 | 0.114 | dCER | **yes** |
| F11 | 192 | mean ΔCER = 0.319 | 0.492 | dCER | **no** |
| F12 | 32 | mean ΔCER = 0.605 | 1.304 | dCER | **no** |
| F13 | 288 | mean ΔCER = 0.092 | 0.169 | dCER | borderline |
| F14 | 16 | mean emo_benefit = 0.105 | 0.092 | emo-benefit | **yes** |
| F15 | 120 | r = 0.002 | 0.253 | \|r\| | **yes** (for null) |
| F16 | 16 | mean cer_benefit = −1.039 | 2.188 | cer-benefit | **no** |
| F17 | 16 | mean ΔCER = 0.032 | 0.182 | dCER | **no** |
| F18 | 40 | mean ΔEmo = 0.060 | 0.050 | emo-distortion | **yes** |
| F19 | 192 | r = −0.514 | 0.201 | \|r\| | **yes** |
| F20 | 32 | mean ΔCost = 0.049 | 0.088 | emo-cost | **no** |
| F21 | 66 | mean ΔLogprob = 0.405 | 0.197 | avg_logprob | **yes** |

**Power reading.** Of the 6 directional survivors, 5 are also well-powered
(F10, F14, F18, F19, F21); F01 is borderline (|effect| ≈ MDE). Of the 11
directional non-survivors, **9 are underpowered** (observed |effect| < MDE):
F02, F03, F05, F06, F07, F11, F12, F16, F17, F20 — i.e. their BH failure is
*ambiguous*: a non-rejection under low power is not evidence the effect is
absent. Only F13 (borderline power, large n=288) is a comparatively
well-powered non-rejection, and it is itself a *falsification* claim (the
gate selector does **not** beat always-speaker), so its non-significance is
actually consistent with the project's stated conclusion.

This pattern — a few highly significant, well-powered results carrying the
frontier, surrounded by underpowered marginal ones — is exactly what BH
correction is designed to expose.

---

## 5. Claims to downgrade from "demonstrates" to "suggests"

The following 11 directional findings do **not** survive BH correction at
q=0.05. Per the task's labeling discipline and the AGENTS.md guidance against
overclaiming, their wording in `docs/project_state.md` and the per-frontier
`FINDINGS.md` files should be read as **"suggests"** rather than
**"demonstrates"** when cited outside this audit. (No existing files are
modified by this PR; this is a reanalysis-only recommendation.)

| finding_id | short_name | raw_p | bh_adj_p | reason |
|---|---|---:|---:|---|
| F02 | gold_benefit_separation | 0.039 | 0.083 | BH fail; n=3, underpowered |
| F03 | repetition_hallucination_mechanism | 0.078 | 0.115 | BH fail; underpowered (|eff|<MDE) |
| F05 | router_v1_fails_synthetic | 0.102 | 0.116 | BH fail; raw p>0.05; underpowered |
| F06 | router_v2_improves_synthetic | 0.193 | 0.205 | BH fail; raw p>0.05; underpowered |
| F07 | risk_aware_not_best_cer | 0.089 | 0.115 | BH fail; n=5, underpowered |
| F11 | noise_robust_gate_cure | 0.035 | 0.083 | BH fail; underpowered (|eff|<MDE) |
| F12 | speaker_gate_moderate_babble | 0.094 | 0.115 | BH fail; underpowered (|eff|<MDE) |
| F13 | gate_selector_falsified | 0.063 | 0.106 | BH fail (falsification claim; non-sig is consistent) |
| F16 | lexical_tax_cer_reproduction | 0.087 | 0.115 | BH fail; underpowered (|eff|<MDE) |
| F17 | llm_repair_net_harm | 0.301 | 0.301 | BH fail; raw p>0.05; underpowered |
| F20 | gate_emotion_cost_speaker_least | 0.056 | 0.106 | BH fail; underpowered (|eff|<MDE) |

The 6 directional survivors (F01, F10, F14, F18, F19, F21) may continue to
use "demonstrates". F15 is a null result and is reported as "consistent with
the null" rather than "demonstrates".

---

## 6. H3 verdict

**H3 is NOT SUPPORTED.**

- Required: ≥15 of 21 findings' core directional claims statistically
  supported under BH at q=0.05.
- Observed: **6** directional findings survive BH (F01, F10, F14, F18, F19,
  F21); **7** total if the F15 null (consistent with H0) is counted.
- 3 findings (F04, F08, F09) had insufficient data for any p-value and were
  excluded from the BH family with notes, per the task constraints.
- 11 directional findings fail BH; of these, 9 are additionally underpowered,
  so their failure is ambiguous rather than disconfirming.

**Interpretation.** The frontier's quantitative backbone is real but narrow:
a small set of large, well-powered effects (the compute cascade F10, the
emotion-fidelity meter F19, the confident-attractor probe F21, objective-aware
decoupling F18, the emotion separation non-tax F14, and the low-overlap
separation tax F01) survive strict multiple-comparison control. The remaining
claims are individually suggestive and would need larger n or stronger
effects to clear the FDR bar. The project should therefore present its
frontier as a mixture of *demonstrated* (6) and *suggested* (11) results,
not as 21 uniformly demonstrated findings.

---

## 7. Reproducibility

```bash
cd <repo root>
python3 results/frontier/statistical_robustness/bh_correction.py
# writes correction_table.csv and correction_table.json in this directory
```

Inputs (all pre-existing, unmodified): the `results/tables/*.csv` gold and
synthetic tables, and the `results/frontier/*/{*_curve,probe_rows}.csv`
per-track files. No verified references or gold tables were overwritten.
