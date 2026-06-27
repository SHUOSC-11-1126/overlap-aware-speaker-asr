# RQ59: Cascade with Youden's J Calibration

> **Label: `experimental/frontier`** — Builds on RQ43 (PR #959, 3-tier KL
> cascade), RQ44 (PR #963, OOB bootstrap), RQ46 (PR #966, original-rule CI
> anchor), RQ48 (PR #965, Youden's J calibration rule + `count_modes`), and
> RQ54 (PR #971, F1 cascade comparison baseline). Reanalysis only (no Whisper /
> no ASR / no LLM run); reuses RQ43's per-window KL/cpWER data, RQ48's
> `calibrate_youdens_j` / `count_modes` verbatim, and RQ44/RQ54's OOB bootstrap
> + BCa protocol. Does NOT overwrite any verified reference / gold table.

## Executive Summary

RQ54 (PR #971) found that F1 calibration of RQ43's KL gate collapses the
bootstrap threshold distribution to a **single mode** (KL = 0.01, 96.3%) but is
**too aggressive**: it escalates **83.1%** of windows to whisper-base (cascade
compute 1.773× vs RQ43's ~1.4×). RQ48 (PR #965) found Youden's J (TPR − FPR)
gives 3 modes on the lang-id-entropy detector (vs F1's 2, vs the original
rule's 6). RQ59 asked whether Youden's J — which balances sensitivity and
specificity rather than maximising precision × recall on the hallucinated
class — gives a **less aggressive** cascade operating point than F1 while
maintaining robustness.

**The answer is no: Youden's J collapses to the SAME aggressive operating point
as F1.** Two of three pre-registered hypotheses are killed:

| Hypothesis | Verdict | Test statistic | Kill threshold |
|---|---|---:|---|
| H59a: Youden's J escalates < 83% of windows | **KILLED** | 83.1% (= F1) | ≥ 83% |
| H59b: OOB cpWER ≤ 0.889 (matches RQ43) | **SUPPORTED** | 0.7824 | > 0.889 |
| H59c: BCa CI width ≤ 0.2489 (maintains robustness) | **KILLED** | 0.2827 | > 0.2489 |

The headline finding is that **Youden's J and F1 pick the byte-identical
in-sample operating point** on the KL detector: threshold KL = 0.01, sensitivity
= 1.0, specificity = 0.325, escalation = 83.1%, cascade cpWER = 0.7775. This is
not a coincidence — it is a property of the KL detector's ROC curve on this
data. All 37 hallucinated windows have KL ∈ [2.98, 6.58], while clean windows
span the full KL range [0.0, 8.53] (13 clean windows have KL = 0 exactly). The
KL ROC is therefore **flat-topped**: once the threshold is raised above 0.01
all 37 hallucinated windows are flagged (sensitivity = 1.0) and 13 clean
windows are excluded (specificity = 0.325), and raising the threshold further
(over the empty KL band (0.01, 2.98)) changes nothing. Above 2.98,
hallucinated windows drop out (sensitivity falls) while clean high-KL windows
stay flagged (specificity barely rises), so J *decreases*. J is thus maximised
at 0.325 across [0.01, 2.98]; the lowest-threshold tie-break picks 0.01 — the
same point F1 picks (F1 maximises recall at 1.0 with precision 0.578).

Because Youden's J lands on the same aggressive operating point as F1, H59a
(less aggressive than F1) is killed by construction: the escalation fraction is
identical (0.831169). H59b (OOB cpWER ≤ 0.889) is supported — the OOB median
cpWER is 0.7824, a 11.9% improvement over RQ43's 0.8889, but this is the **same
mechanical cpWER gain F1 achieves** by escalating 83% of windows to the cheaper
base tier, not a calibration-rule quality gain.

H59c (BCa width ≤ 0.2489) is killed: the BCa width is **0.2827**, *wider* than
RQ46's original-rule width (0.2489) and RQ54's F1 width (0.2481). Although
Youden's J and F1 share the same in-sample operating point, Youden's J is
**less stable under bootstrap**: 91.6% of resamples pick 0.01 (vs F1's 96.3%),
and the 8.4% off-mode resamples spread across 6 distinct thresholds up to KL =
4.44 (vs F1's 3.7% off-mode over 2 thresholds up to 3.31). The off-mode
resamples correspond to bootstrap draws where the clean high-KL tail is
under-sampled, which lets J improve specificity by raising the threshold —
producing higher-threshold operating points with higher cpWER. This greater
off-mode dispersion inflates the OOB cpWER spread, widening the BCa CI beyond
both RQ46's original-rule width and RQ54's F1 width.

## Pre-registered Hypotheses

| ID | Statement | Kill condition | Verdict |
|---|---|---|---|
| H59a | Youden's J cascade escalates < 83% of windows to base (less aggressive than F1's 83.1%) | escalation fraction ≥ 0.83 | **KILLED** (0.831169) |
| H59b | Youden's J cascade OOB cpWER ≤ 0.889 (matches RQ43's original-rule cpWER 0.888947) | OOB median cpWER > 0.889 | **SUPPORTED** (0.782394) |
| H59c | Youden's J cascade BCa CI width ≤ 0.2489 (maintains robustness vs RQ46's original-rule width) | BCa width > 0.2489 | **KILLED** (0.282660) |

## Method (controlled comparison)

The ONLY independent variable vs RQ54 is the calibration rule (Youden's J
instead of F1). The cascade simulation is held fixed at RQ43's actual
implementation so the comparison to RQ43's 0.888947 anchor (H59b) and RQ54's
83.1% F1 escalation (H59a) is apples-to-apples:

- **Tier 1 (whisper-tiny)** cpWER per window = RQ43's `tiny_sep_cpwer` (the
  real whisper-tiny separated-audio cpWER).
- **Tier 3 (whisper-base)** cpWER per window = RQ43's `base_sep_cpwer` =
  `tiny_sep_cpwer × 0.428031` (the model_scale separated base/tiny CER ratio,
  constant across overlap).
- **Tier 2 (KL gate)**: escalate to base when the character-bigram asymmetric
  KL divergence of the tiny transcript (RQ43's `kl_sep`) ≥ the calibrated
  threshold.

The hallucination label used to calibrate Youden's J is `tiny_sep_cpwer > 1.0`
(37 hallucinated / 40 clean), matching RQ44/RQ48/RQ54's label rule. High KL
flags a window as hallucinated and escalates it to base.

**Youden's J calibration rule** (RQ48's `calibrate_youdens_j`, reused verbatim
via `import`): J = sensitivity + specificity − 1 = TPR − FPR. The KL threshold
is swept over a 0.01-step grid spanning the observed KL range [0.00, 8.55]; the
grid point maximising J is chosen, with the lowest threshold breaking ties
(RQ48's `_select_threshold` convention, `≥ − EPS` flagging). Unlike F1 (which
collapses to the lowest grid point because recall dominates), J trades
sensitivity against specificity continuously — but on this KL detector the ROC
is flat-topped, so J lands on the same point as F1.

**Bootstrap** (B=10000, seed=42): for each resample, draw n=77 indices with
replacement, calibrate the J-optimal KL threshold on the in-bag windows, and
evaluate the cascade cpWER on the out-of-bag (OOB) windows (RQ44's OOB
protocol). Records the per-resample threshold (for mode counting) and OOB cpWER
(for the BCa CI). Mean OOB size = 28.22 (expected 28.14 = n·(1−1/n)^n).

**BCa 95% CI** on the OOB cpWER distribution: bias-correction z₀ from the
in-sample point estimate θ̂ (in-sample cascade cpWER at the in-sample Youden's J
threshold); acceleration from a delete-1 jackknife (77 fits); Acklam inverse-
normal (no scipy).

**Mode count** via RQ48's `count_modes` (≥ 5% frequency = a mode).

## Results

### In-sample Youden's J calibration (all 77 windows)

| Quantity | Value |
|---|---:|
| KL threshold | **0.01** |
| Youden's J | 0.3250 |
| Sensitivity (TPR) | 1.0000 |
| Specificity (1 − FPR) | 0.3250 |
| TP / FP / TN / FN | 37 / 27 / 13 / 0 |
| In-sample cascade cpWER | 0.777525 |
| Cascade compute | 1.772987× |
| Escalation fraction | **0.831169** (83.1%) |

This is the **byte-identical operating point RQ54's F1 picks** (threshold 0.01,
sensitivity 1.0, specificity 0.325, escalation 0.831169, cpWER 0.777525).

### Bootstrap threshold distribution (B=10000, seed=42)

| Quantity | Value |
|---|---:|
| Median threshold | 0.01 |
| Mean threshold | 0.284275 |
| Std | 0.904199 |
| Min / Max | 0.01 / 4.44 |
| Unique thresholds | 6 |
| Modes (≥ 5%) | **1** |
| Mode: KL=0.01 | count=9157, fraction=0.9157 |

Youden's J is **less concentrated than F1** (91.6% at 0.01 vs F1's 96.3%) and
**more dispersed** (6 unique thresholds up to 4.44 vs F1's 3 up to 3.31). The
8.4% off-mode resamples are bootstrap draws where the clean high-KL tail is
under-sampled, letting J improve specificity by raising the threshold.

### Bootstrap OOB cpWER distribution

| Quantity | Value |
|---|---:|
| n valid | 10000 |
| Median | **0.782394** |
| Mean | 0.790792 |
| Min / Max | 0.591034 / 1.532393 |
| Percentile 2.5% / 97.5% | 0.681818 / 0.981644 |

### BCa 95% CI

| Quantity | Value |
|---|---:|
| CI low | 0.675166 |
| CI high | 0.957827 |
| **Width** | **0.282660** |
| Median | 0.782394 |
| z₀ (bias correction) | −0.088851 |
| a (acceleration) | 0.012479 |
| α₁ / α₂ | 0.018463 / 0.966150 |
| Method | bca |
| θ̂ (point estimate) | 0.777525 |
| n valid | 10000 |

### Jackknife (delete-1, 77 fits)

| Quantity | Value |
|---|---:|
| Acceleration a | 0.012479 |
| θ̄_loo (mean) | 0.777525 |
| θ_loo min / max | 0.763350 / 0.782124 |

## Comparison to RQ54 (F1) and RQ43/RQ46 (original rule)

| Metric | RQ59 Youden's J | RQ54 F1 | RQ43 original | RQ46 original-rule CI |
|---|---:|---:|---:|---:|
| KL threshold | 0.01 | 0.01 | 3.30 | 3.30 (fixed) |
| Escalation fraction | 0.831 | 0.831 | ~0.43 | ~0.43 |
| Cascade compute | 1.773× | 1.773× | ~1.40× | ~1.40× |
| In-sample cpWER | 0.7775 | 0.7775 | 0.8889 | 0.8889 |
| OOB median cpWER | 0.7824 | 0.7799 | — | — |
| BCa / CI width | **0.2827** | 0.2481 | — | 0.2489 |
| Bootstrap modes (≥5%) | 1 | 1 | — | — |
| Off-mode fraction | 8.4% | 3.7% | — | — |
| Off-mode threshold range | up to 4.44 | up to 3.31 | — | — |

**Key contrasts:**

1. **Youden's J does NOT give a less aggressive operating point than F1.** Both
   collapse to KL=0.01, 83.1% escalation. H59a is killed by construction.
2. **The OOB cpWER gain (0.7824 vs RQ43's 0.8889) is mechanical**, not a
   calibration-rule quality gain: it comes from escalating 83% of windows to the
   cheaper base tier (cpWER × 0.428031). F1 achieves the same gain (0.7799).
3. **Youden's J is LESS robust than F1** under bootstrap (H59c killed): the BCa
   width (0.2827) exceeds both RQ46's original-rule width (0.2489) and RQ54's F1
   width (0.2481). Youden's J has more off-mode dispersion (8.4% over 6
   thresholds vs F1's 3.7% over 3), which inflates the OOB cpWER spread.

## Why Youden's J collapses to the same point as F1

The KL detector's ROC on this data is **flat-topped**:

- All 37 hallucinated windows have KL ∈ [2.98, 6.58] (floor ≈ 2.98).
- Clean windows span the full KL range [0.0, 8.53] (13 clean windows have KL = 0
  exactly; the clean high-KL tail extends above the hallucinated floor).
- There is an **empty KL band (0.01, 2.98)** with no windows at all.

Raising the threshold from 0.01 to 2.98 therefore changes nothing: all 37
hallucinated windows stay flagged (sensitivity = 1.0) and the same 13 clean
windows (KL = 0) stay excluded (specificity = 0.325). Both F1 and J are
maximised across this whole plateau. Above 2.98, hallucinated windows drop out
(sensitivity falls) faster than clean high-KL windows are excluded (specificity
barely rises), so both F1 and J *decrease*. The lowest-threshold tie-break then
picks 0.01 for both rules — the byte-identical operating point.

This is a **detector-geometry property**, not a calibration-rule property: any
threshold-maximising rule that is monotone in (sensitivity, specificity) will
land on the same plateau. RQ48's finding that Youden's J gives 3 modes on the
lang-id-entropy detector does NOT transfer to the KL detector, because the KL
detector's class-conditional KL distributions have a clean separation gap
(0.01, 2.98) that lang-id-entropy lacks.

## Methodological caveat on H59c

RQ46's 0.2489 anchor is a **percentile CI** evaluated **in-bag** at a **fixed**
threshold (3.30). RQ59's BCa CI is **bias-corrected + accelerated** and
evaluated **OOB** at a **re-calibrated** threshold. The H59c comparison is
therefore **directional** (does Youden's J + BCa + OOB keep the interval within
the original-rule width) rather than a pure like-for-like CI-method swap. This
mirrors RQ54's H54b caveat. The conclusion (Youden's J is less robust than F1
under bootstrap) holds regardless: RQ59 and RQ54 use the *same* BCa + OOB
protocol, and Youden's J's BCa width (0.2827) exceeds F1's (0.2481) by 13.9%.

## Reproducibility

- **Data**: RQ43's 77 per-window `three_tier_cascade_results.json` (n=77,
  baseline 1.590909, base ratio 0.428031, KL range [0.0, 8.5255]).
- **Calibration rule**: RQ48's `calibrate_youdens_j` / `count_modes`, imported
  verbatim (`results/frontier/calibration_rule_comparison/`).
- **Bootstrap**: B=10000, seed=42, OOB protocol per RQ44.
- **CI**: BCa 95% (z₀ from θ̂, acceleration from delete-1 jackknife, Acklam
  inverse-normal, no scipy).
- **RQ43 anchor reproduction**: cascade @ KL=3.30 = 0.888947 (verified in tests
  and at runtime).
- **No LLM / no ollama / no Whisper calls.** Pure reanalysis (numpy + stdlib).

## Files

- `cascade_youdens_j_analysis.py` — main analysis script.
- `cascade_youdens_j_results.json` — machine-readable results (full summary +
  per-bootstrap arrays).
- `cascade_youdens_j_results.csv` — per-resample bootstrap table (threshold,
  OOB cpWER, n_oob, n_escalated_oob).
- `FINDINGS.md` — this document.
- `tests/test_cascade_youdens_j.py` — 67 unit tests (constants, Acklam inverse
  normal, Youden's J calibration on KL, cascade simulation, OOB cpWER,
  vectorised bootstrap, jackknife, BCa CI, mode count, end-to-end, CSV output).
