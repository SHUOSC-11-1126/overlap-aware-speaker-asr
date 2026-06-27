# RQ63: Cost-aware Cascade Pareto

> **Label: `experimental/frontier`** — Builds on RQ43 (PR #959, 3-tier KL
> cascade), RQ44 (PR #963, OOB bootstrap), RQ46 (PR #966, Pareto CI +
> `pareto_dominates`), RQ54 (PR #971, F1 cascade comparison), and RQ59 (PR #974,
> Youden's J cascade framework reuse). Reanalysis only (no Whisper / no ASR /
> no LLM run); reuses RQ43's per-window KL/cpWER data, RQ59's cascade simulation
> + BCa machinery verbatim, and RQ46's strict 2D Pareto dominance. Does NOT
> overwrite any verified reference / gold table.

## Executive Summary

RQ54 (PR #971) and RQ59 (PR #974) both found that detection-metric calibration
rules (F1, Youden's J) collapse the KL gate cascade to an aggressive operating
point: KL = 0.01, escalating **83.1%** of windows to whisper-base. Both rules
maximise a detection metric (precision × recall, or TPR − FPR) without
considering the compute cost of escalation. RQ43's original rule (KL = 3.30,
74.0% escalation) is less aggressive but does not explicitly trade cpWER against
compute. RQ63 asked whether a **cost-aware** threshold — selected to maximise
cpWER efficiency per compute unit — yields a better Pareto operating point than
RQ43 / RQ54 / RQ59.

**The answer is no: the cost-aware objective collapses to the SAME operating
point as RQ54 / RQ59.** Two of three pre-registered hypotheses are killed:

| Hypothesis | Verdict | Test statistic | Kill threshold |
|---|---|---:|---|
| H63a: Cost-aware escalation < 83.1% | **KILLED** | 83.1% (= RQ54) | ≥ 83.1% |
| H63b: Cost-aware OOB cpWER ≤ 0.889 | **SUPPORTED** | 0.7780 | > 0.889 |
| H63c: Cost-aware ratio strictly better than RQ43 & RQ54 | **KILLED** | ratio = RQ54 | not strictly lower |

The headline finding is that the cost-aware (min cpWER/compute) threshold is
**byte-identical to RQ54's F1 point**: KL = 0.01, escalation = 83.1%, cascade
cpWER = 0.7775, compute = 1.356×. This is not a coincidence — it is a property
of the cascade frontier's geometry. The cpWER/compute ratio is **monotonic in
escalation**: escalating a hallucinated window from tiny (high cpWER) to base
(low cpWER = tiny × 0.428) reduces cpWER by far more than the 0.428× compute
surcharge, so the ratio cpWER/compute *decreases* as more windows are escalated.
The minimum-ratio point is therefore the most aggressive escalation (KL = 0.01),
and the maximum-ratio point is the least aggressive (all-tiny corner, KL = 8.53,
no escalation, degenerate). There is **no interior Pareto knee** on this cascade
frontier.

All three cost-aware objectives confirm this:

1. **Primary (min cpWER/compute)**: KL = 0.01 (= RQ54's point). ratio = 0.5735.
2. **Secondary (max cpWER/compute, literal task METHOD)**: KL = 8.53 (all-tiny
   corner). ratio = 1.5909. Degenerate — fails H63b trivially.
3. **Secondary (max marginal efficiency / bang-for-buck)**: KL = 0.01 (= RQ54's
   point). marginal efficiency = 2.286 (cpWER reduction per compute unit).

The bootstrap is **degenerate**: all 10,000 resamples pick threshold 0.01
(n_unique = 1, std = 0.0). The cost-aware threshold has zero selection variance
— the min-ratio point is always KL = 0.01 regardless of resample composition.
The BCa CI width (0.196) is narrower than RQ46's (0.249) and RQ54's (0.248),
but this is a mechanical artifact of the zero-variance threshold selection: all
OOB cpWER variance comes from window composition, not threshold instability.

H63c (strictly better Pareto ratio than both RQ43 and RQ54) is killed because
the cost-aware point **is** RQ54's point: the ratio (0.5735) is strictly below
RQ43's (0.6751) but **equal** to RQ54's (0.5735), not strictly lower. The
cost-aware point is not Pareto-dominated by either RQ43 or RQ54 (it has lower
cpWER than RQ43 but higher compute; it is identical to RQ54), but the "strictly
better ratio" condition fails by equality.

## Pre-registered Hypotheses

| ID | Statement | Kill condition | Verdict |
|---|---|---|---|
| H63a | Cost-aware cascade escalates < 83.1% of windows to base (less aggressive than F1/J's 83.1%) | escalation fraction ≥ 0.831 | **KILLED** (0.831169) |
| H63b | Cost-aware cascade OOB cpWER ≤ 0.889 (matches RQ43's original-rule cpWER 0.888947) | OOB median cpWER > 0.889 | **SUPPORTED** (0.777961) |
| H63c | Cost-aware cpWER/compute ratio strictly better (lower) than both RQ43 and RQ54, and not Pareto-dominated by either | dominated by RQ43 or RQ54, OR ratio not strictly below both | **KILLED** (ratio = RQ54's ratio, not strictly lower) |

## Method (controlled comparison)

The ONLY independent variable vs RQ54 / RQ59 is the threshold-selection
objective (cost-aware min cpWER/compute instead of F1 or Youden's J). The
cascade simulation is held fixed at RQ43's actual implementation so the
comparison to RQ43's 0.888947 anchor (H63b) and RQ54's 83.1% escalation (H63a)
is apples-to-apples:

- **Tier 1** (whisper-tiny) cpWER per window = RQ43's `tiny_sep_cpwer` (the real
  whisper-tiny separated-audio cpWER).
- **Tier 3** (whisper-base) cpWER per window = RQ43's `base_sep_cpwer` =
  `tiny_sep_cpwer × 0.428031` (the model_scale separated base/tiny CER ratio,
  constant across overlap). This is RQ43's actual base-cpWER estimate.
- **Tier 2** (KL gate): escalate to base when `kl_sep ≥ threshold` (RQ59's
  `≥ threshold − EPS` convention, matching RQ48's flagging direction).

### Cost model (task METHOD, differs from RQ54/RQ59)

Per the task METHOD: `cascade compute = 1.0 + fraction_escalated × 0.428031`,
i.e. tiny = 1.0× and escalating a window to base adds 0.428031× (the RQ43
model_scale separated base/tiny CER ratio 0.428031, reused as the compute
surcharge). So `COMPUTE_TINY = 1.0`, `COMPUTE_BASE = 1.428031`. This is a
different cost model from RQ54/RQ59 (which used `COMPUTE_BASE = 1.93` from
`runtime_cascade`); only the compute axis changes, so the cpWER anchors
(RQ43 0.888947, RQ54 0.777525) reproduce exactly.

### Pareto efficiency operationalisation

The task METHOD writes "Pareto efficiency = cpWER/compute; select maximising".
cpWER is a **loss** (lower is better), so the raw ratio cpWER/compute is
maximised at the all-tiny corner (no escalation, compute 1.0×) — a degenerate
point that fails H63b trivially — and minimised at the most-aggressive
escalation. H63c's reference points (RQ43 0.889/1.4 = 0.635, RQ54 0.780/1.77 =
0.441) show the **better** cascade (RQ54, lower cpWER) has the **lower** ratio,
so "strictly better ratio" means **lower** cpWER/compute. RQ63 therefore
operationalises the cost-aware objective as **minimising** cpWER/compute (=
maximising compute/cpWER efficiency). The literal maximise-cpWER/compute point
(all-tiny) and the marginal-efficiency max are reported as secondary objectives
for full transparency.

### Protocol

1. Load RQ43's 77 per-window (tiny_sep_cpwer, base_sep_cpwer, kl_sep). Verify
   n = 77, baseline 1.590909, RQ43 @ KL = 3.30 reproduces 0.888947, label
   counts 37 hall / 40 clean.
2. For each KL threshold on the 0.01-step grid [0.01, 8.53] (853 points):
   compute cascade cpWER, cascade compute, cpWER/compute ratio, and marginal
   efficiency.
3. Cost-aware operating point = threshold minimising cpWER/compute (primary).
   Secondary: threshold maximising cpWER/compute (literal) and threshold
   maximising marginal efficiency.
4. Bootstrap B = 10000, seed = 42: per resample re-select the min-ratio
   threshold on in-bag windows, evaluate cascade cpWER and compute on OOB
   windows (RQ44 OOB protocol).
5. Delete-1 jackknife (77 fits) for the BCa acceleration.
6. BCa 95% CI on the OOB cpWER distribution (Acklam inverse-normal, no scipy).
7. Pre-registered hypothesis verdicts H63a/b/c.

## Results

### In-sample cost-aware operating points

| Objective | KL threshold | Cascade cpWER | Cascade compute | Escalation | cpWER/compute | Marginal eff |
|---|---:|---:|---:|---:|---:|---:|
| **Primary (min ratio)** | 0.01 | 0.777525 | 1.355766× | 83.1% | 0.573495 | 2.286289 |
| Secondary (max ratio) | 8.53 | 1.590909 | 1.000000× | 0.0% | 1.590909 | — |
| Secondary (max marg eff) | 0.01 | 0.777525 | 1.355766× | 83.1% | 0.573495 | 2.286289 |

All three objectives collapse to corners: min-ratio and max-marg-eff both pick
KL = 0.01 (= RQ54's point); max-ratio picks KL = 8.53 (all-tiny, degenerate).

### Reference points (recomputed under RQ63's cost model)

| Rule | KL threshold | Cascade cpWER | Cascade compute | Escalation | cpWER/compute |
|---|---:|---:|---:|---:|---:|
| RQ43 (original rule) | 3.30 | 0.888947 | 1.316854× | 74.0% | 0.675054 |
| RQ54 (F1) | 0.01 | 0.777525 | 1.355766× | 83.1% | 0.573495 |
| RQ59 (Youden's J) | 0.01 | 0.777525 | 1.355766× | 83.1% | 0.573495 |
| **RQ63 (cost-aware min-ratio)** | **0.01** | **0.777525** | **1.355766×** | **83.1%** | **0.573495** |

### Bootstrap (B = 10000, seed = 42, OOB protocol)

The bootstrap threshold distribution is **degenerate**: all 10,000 resamples
pick threshold 0.01 (n_unique = 1, std = 0.0). The cost-aware min-ratio
threshold has zero selection variance.

| Statistic | Value |
|---|---:|
| OOB cpWER median | 0.777961 |
| OOB cpWER mean | 0.777889 |
| OOB cpWER percentile CI [2.5%, 97.5%] | [0.679427, 0.876004] |
| BCa CI [lo, hi] | [0.681451, 0.877525] |
| BCa width | 0.196074 |
| BCa z0 (bias correction) | −0.008523 |
| BCa acceleration (jackknife) | 0.012479 |
| OOB compute median | 1.356693× |

The BCa width (0.196) is narrower than RQ46's original-rule width (0.249) and
RQ54's F1 width (0.248). This is a mechanical artifact of the zero-variance
threshold selection: since every resample picks the same threshold, all OOB
cpWER variance comes from window composition alone, with no contribution from
threshold instability. The narrower CI does not indicate a "better" cascade —
it indicates a degenerate selector.

### H63c Pareto check

| Point | cpWER | compute | cpWER/compute |
|---|---:|---:|---:|
| Cost-aware (min ratio) | 0.777525 | 1.355766× | 0.573495 |
| RQ43 | 0.888947 | 1.316854× | 0.675054 |
| RQ54 | 0.777525 | 1.355766× | 0.573495 |

- Cost-aware **not** dominated by RQ43 (cost-aware has lower cpWER but higher
  compute — neither dominates).
- Cost-aware **not** dominated by RQ54 (they are the same point).
- Cost-aware ratio **strictly below** RQ43's (0.5735 < 0.6751). ✓
- Cost-aware ratio **NOT strictly below** RQ54's (0.5735 = 0.5735, equal). ✗

H63c is killed by the equality with RQ54: the cost-aware point does not achieve
a strictly better ratio than RQ54 because it **is** RQ54's point.

## Why the cost-aware objective collapses to RQ54's point

The cascade frontier on this data is **monotonic** — there is no interior
Pareto knee. The mechanism:

1. **Hallucinated windows** (tiny cpWER > 1.0, 37 windows) all have KL ∈
   [2.98, 6.58]. Escalating them to base (cpWER = tiny × 0.428) replaces a high
   cpWER with a low one, reducing the cascade mean substantially.
2. **Clean windows** (tiny cpWER ≤ 1.0, 40 windows) span the full KL range
   [0.0, 8.53] (13 have KL = 0 exactly). Escalating a clean window to base
   *increases* its cpWER (base = tiny × 0.428 > tiny when tiny < 1.0... wait,
   actually base = tiny × 0.428 < tiny always, since 0.428 < 1.0). So
   escalating any window reduces its individual cpWER.
3. Because base cpWER = tiny × 0.428 < tiny for **every** window, escalating
   more windows always reduces the cascade cpWER. The compute surcharge
   (0.428× per escalated window) is small relative to the cpWER reduction
   (0.572× per escalated window). So cpWER/compute **decreases monotonically**
   as escalation increases — the min-ratio point is the most aggressive
   escalation (KL = 0.01), and the max-ratio point is the least aggressive
   (all-tiny, KL = 8.53).

The cost-aware objective therefore provides **no new information** beyond what
F1 and Youden's J already showed: the best cascade cpWER per compute unit is
achieved by escalating as many windows as possible, which means the lowest KL
threshold (0.01). The 13 clean windows with KL = 0 are the only windows not
escalated at KL = 0.01; they are also the only windows where escalation would
*increase* cpWER (their tiny cpWER is already low, and base = tiny × 0.428 is
even lower — so escalating them would *further reduce* cpWER, but they have
KL = 0 so no threshold > 0 can flag them).

This reveals a structural property of the RQ43 cascade: because base cpWER is
a constant fraction (0.428) of tiny cpWER, escalating **always** reduces cpWER.
The only reason not to escalate everything is compute cost — but the cost-aware
objective (min cpWER/compute) finds that the cpWER reduction per compute unit is
positive for every escalation, so the optimum is to escalate as much as
possible. The cascade frontier has no interior knee because the cost/benefit
ratio is uniform across windows.

## Comparison to RQ54 / RQ59

| Property | RQ54 (F1) | RQ59 (Youden's J) | RQ63 (cost-aware) |
|---|---|---|---|
| In-sample KL threshold | 0.01 | 0.01 | 0.01 |
| Escalation fraction | 83.1% | 83.1% | 83.1% |
| Cascade cpWER | 0.7775 | 0.7775 | 0.7775 |
| Bootstrap threshold n_unique | 2 | 7 | **1** |
| OOB median cpWER | 0.7799 | 0.7824 | 0.7780 |
| BCa width | 0.2481 | 0.2827 | **0.1961** |

RQ63's cost-aware selector is the **most stable** (n_unique = 1, zero variance)
and has the **narrowest BCa CI** (0.196), but this is because the selector is
degenerate: the monotonic frontier means the min-ratio point is always KL = 0.01
regardless of resample composition. RQ54 and RQ59 have non-degenerate threshold
distributions because their selection rules (F1, Youden's J) depend on the
label distribution, which varies across resamples; the cost-aware ratio depends
only on the cpWER/compute trade-off, which is monotonic and thus always picks
the same corner.

## Limitations

1. **Cost model is a proxy.** The task METHOD specifies compute = 1.0 + 0.428 ×
   frac, using the base/tiny CER ratio as the compute surcharge. This is a
   modeling choice, not a measured runtime cost. A real runtime cost model
   (e.g. from `runtime_cascade` with COMPUTE_BASE = 1.93) would change the
   absolute compute values but not the monotonicity: base cpWER < tiny cpWER
   always, so escalating always reduces cpWER, and the min-ratio point remains
   the most aggressive escalation.

2. **No interior Pareto knee.** The cascade frontier is monotonic because base
   cpWER = tiny × 0.428 < tiny for every window. A non-monotonic frontier
   (where escalating some windows *increases* cpWER) would be needed for the
   cost-aware objective to find an interior operating point. This would require
   a base model that is *worse* than tiny on some windows (e.g. a base model
   that hallucinates on different inputs than tiny).

3. **77 windows is small.** The bootstrap OOB protocol mitigates this, but the
   degenerate threshold distribution (n_unique = 1) means the cost-aware
   selector's stability cannot be challenged by resampling — it is trivially
   stable because the frontier is monotonic.

4. **Pareto frontier plot omitted.** matplotlib is not installed in this
   environment. The full frontier (cpwer, compute, cpwer_per_compute,
   marginal_efficiency per threshold) is in the JSON `pareto_frontier` array
   and is plottable downstream.

## Reproducibility

```bash
/opt/homebrew/bin/python3 results/frontier/cost_aware_cascade/cost_aware_cascade_analysis.py
/opt/homebrew/bin/python3 -m unittest tests.test_cost_aware_cascade -v
```

Outputs:
- `results/frontier/cost_aware_cascade/cost_aware_cascade_results.json` — full
  results (frontier, bootstrap, BCa, hypothesis verdicts).
- `results/frontier/cost_aware_cascade/cost_aware_cascade_results.csv` — per-
  resample bootstrap table (B = 10000 rows).

Data: `results/frontier/three_tier_cascade/three_tier_cascade_results.json`
(RQ43, label `experimental/frontier`, 77 AISHELL-4 windows, no modification).
