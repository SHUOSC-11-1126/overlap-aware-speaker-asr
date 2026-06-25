# POMDP Regret Bound Analysis — Findings (RQ15)

**Label:** `experimental/frontier`. Theoretical analysis; no new data, no ASR runs.
Builds on RQ5 (`pomdp_solver.py`, #889) and RQ10 (`pomdp_per_utterance.py`, #899); does NOT
overwrite either. Reproduce: `python3 results/frontier/pomdp_regret_bounds/regret_bound_analysis.py`.

Closes #904. Answers RQ15. See `regret_bounds.md` for the full derivation with LaTeX.

## Question

RQ5 showed that a simple CR-threshold router (router v2, crossover $r=0.17$) approximates
the POMDP-optimal policy to within 0.03 overlap-ratio on gold, and RQ10 showed that this
approximation breaks on AISHELL-4 because the gold-baseline boundary ignores silence gaps.
But neither study explained *why* the simple threshold is a good approximation on gold, nor
*why* it provably fails on AISHELL-4. RQ15 asks: **can we derive theoretical regret bounds
that (a) explain the near-optimality of router v2 on gold and (b) explain the failure on
AISHELL-4, and (c) identify the condition under which the bound is restored?**

## Method

Standard POMDP / approximate dynamic programming regret technique (Bertsekas & Shreve 1978,
Rustichini 1998), applied to the ASR routing POMDP. The reward surface is RQ10's
Gaussian-kernel-smoothed CER (bandwidth 0.08, 15 greedy support points), treated as the
"ground truth" continuous reward. No new data; no ASR runs; numpy + stdlib only.

Four bounds derived (see `regret_bounds.md` for full LaTeX):

| Bound | What it bounds | Formula | Key constant |
|---|---|---|---|
| **B1** (discretization) | Stratum POMDP vs continuous optimal | $L h^2 / (2D)$ | $L = \sup\|\Delta'\|$ |
| **B2** (router threshold) | Router v2 vs optimal threshold | $L d^2 / (2D)$ | $d = \|r_{\text{router}} - r^*\|$ |
| **B3** (AISHELL-4 vacuity) | When does the bound break? | — | sign-changes of $\Delta(r, g)$ |
| **B4** (Lipschitz restoration) | Per-utterance POMDP on $(r, g)$ grid | $|\Delta_r'| h_r^2/(2D_r) + L_g h_g^2/(2D_g)$ | $L_g$ (silence Lipschitz) |

The "sharp crossover" assumption is that the reward gap
$\Delta(r) = \text{CER}_{\text{mixed}}(r) - \text{CER}_{\text{sep}}(r)$ has a single
sign-change at $r^*$ with $\Delta'(r^*) > 0$. Under this assumption the optimal policy is a
threshold at $r^*$, and both router v2 and the stratum POMDP are threshold approximations
whose regret is bounded by the Lipschitz discretization bound.

## Result 1 (H15a) — Gold: router v2 regret is bounded by $O(1/n^2)$

| Quantity | Value |
|---|---:|
| $r^*$ (optimal crossover) | $0.1944$ |
| $r_{\text{router}}$ (router v2) | $0.17$ |
| $d = |r_{\text{router}} - r^*|$ | $0.0244$ |
| $L = \sup|\Delta'|$ near $r^*$ | $5.524$ |
| **B2 bound (mean regret)** | **$0.00183$** |
| Empirical router v2 mean regret | $0.00182$ |
| **Bound dominates?** | **✓ (tight, within 0.6%)** |

**H15a verdict: SUPPORTED.** We derive the tighter $O(1/n^2)$ curvature bound (log-log
slope $= -2.000$), which implies the hypothesized $O(1/n)$. The bound is **tight** (within
0.6% of the empirical regret), confirming that router v2's near-optimality on gold is not a
coincidence: the 0.024 mis-localization in the threshold, combined with the moderate
Lipschitz constant ($L = 5.52$), produces a regret that is provably $\leq 0.00183$.

**Quadrature honesty.** The bound is so tight (~1%) that the trapezoid rule's
overestimation matters. At grid step 0.0005 the trapezoid empirical is 0.00185 (exceeds the
bound 0.00183); at step 0.0001 it converges to 0.00182 (below the bound). We use step
0.0001 (9001 points) so the bound $\geq$ empirical check holds honestly. The overestimation
is because $|\Delta|$ is convex near $r^*$ ($\Delta$ is concave, $\Delta''(r^*) = -15.9$),
and the trapezoid rule overestimates the integral of convex functions.

## Result 2 (H15b) — AISHELL-4: the bound becomes vacuous

Adding the silence-fraction dimension $g$ (RQ10's per-utterance model) breaks the
sharp-crossover assumption:

| $g$ | sign-changes | crossovers | sharp crossover? |
|---:|---:|---|:--:|
| 0.0 (gold) | 1 | $[0.194]$ | ✓ |
| 0.2 | **2** | $[0.257, 0.471]$ | ✗ (SECOND sign-change) |
| 0.4 | 0 | $[]$ | ✗ (crossover vanishes) |
| 0.6 (AISHELL-4) | 0 | $[]$ | ✗ |
| 0.8 | 0 | $[]$ | ✗ |

**H15b verdict: SUPPORTED.** Adding the silence dimension breaks the sharp-crossover
assumption in two ways: (i) at $g=0.2$ a SECOND sign-change appears — $\Delta$ goes positive
(separated wins) at mid-overlap then negative again at high overlap, so there is no single
$r^*$ to localize; (ii) at $g \geq 0.4$ the silence penalty dominates and $\Delta < 0$
everywhere (separated never wins), so the crossover vanishes entirely. In both regimes
Bounds 1–2 are vacuous: the $O(1/n^2)$ bound has no single $r^*$ to anchor its constant.

This is the theoretical explanation for RQ10's empirical finding: the gold-baseline routing
boundary does not transfer to AISHELL-4 because the silence dimension introduces a second
crossover (or eliminates the crossover entirely), making the single-threshold approximation
provably invalid.

## Result 3 (H15c) — Lipschitz restoration: per-utterance POMDP recovers $O(L/n^2)$

If the reward is $L_g$-Lipschitz in $g$, the per-utterance POMDP on the $(r, g)$ grid
restores the bound:

$$\text{Regret} \leq \frac{|\Delta_r'(r^*, g)| \, h_r^2}{2 D_r} + \frac{L_g \, h_g^2}{2 D_g} = O\!\left(\frac{L_g}{n^2}\right)$$

| Quantity | Value |
|---|---:|
| $L_g$ (model, by linearity) | $1.5$ |
| $L_g$ (empirical) | $1.5000$ |
| B4 bound ($n=5$) | $0.1269$ |
| Log-log slope vs $n$ | $-2.000$ |

**H15c verdict: SUPPORTED.** With $L_g$-Lipschitz silence reward, the per-utterance POMDP
on the $(r, g)$ grid restores an $O(L_g/n^2)$ bound (slope $= -2.000$). The per-utterance
POMDP *observes* $g$, so it can threshold on $(r, g)$ and recover the bound that the
stratum-level ($g$-blind) POMDP loses. The silence Lipschitz constant is $L_g = 1.5$ exactly
(by the affine RQ10 model: $|\partial R_{\text{sep}}/\partial g| = 1.5$,
$|\partial R_{\text{mixed}}/\partial g| = 0.1$).

## Synthesis

| Hypothesis | Verdict | Key number |
|---|---|---|
| **H15a** (gold: regret $\leq O(1/n)$) | **SUPPORTED** | B2 bound $0.00183 \geq$ empirical $0.00182$ (tight, 0.6%); slope $-2.000$ |
| **H15b** (AISHELL-4: bound vacuous) | **SUPPORTED** | $g=0.2$: 2 sign-changes; $g=0.6$: 0 sign-changes |
| **H15c** (Lipschitz restores $O(L/n^2)$) | **SUPPORTED** | $L_g = 1.5$; slope $-2.000$ |

**The bound tells a coherent story:** on gold, the reward gap has a single sharp crossover,
so the Lipschitz discretization bound applies and router v2's regret is provably $\leq 0.00183$
(tight). On AISHELL-4, the silence dimension introduces a second crossover (or eliminates
the crossover), making the single-threshold bound vacuous — this is the theoretical reason
the gold boundary does not transfer. If the per-utterance POMDP observes the silence state
and the reward is Lipschitz in $g$, the bound is restored at $O(L_g/n^2)$.

## Honest limitations

- **Tightness depends on grid resolution.** Bound 2 is tight (~0.6%), so the trapezoid
  rule's overestimation matters. We use grid step 0.0001 (9001 points) for honest
  verification. At coarser steps the trapezoid overestimates the empirical regret (because
  $|\Delta|$ is convex near $r^*$) and the bound appears to fail — this is a quadrature
  artifact, not a bound failure. Documented in `regret_bounds.md` §4.

- **Lipschitz constant from finite differences.** $L = \sup|\Delta'|$ is estimated from
  `np.gradient` (finite differences) plus a secant-slope robustness check. The true $L$ (if
  $\Delta$ were known in closed form) might differ slightly. The secant estimate
  $L_{\text{secant}} = \max|\Delta(r)|/|r - r^*|$ is a lower bound on $\sup|\Delta'|$ by the
  mean-value theorem; we take $L = \max(L_{\text{grad}}, L_{\text{secant}})$ to be safe.

- **Kernel-smoothed reward as "ground truth."** The bounds are derived on RQ10's
  Gaussian-kernel-smoothed CER surface, not on raw per-utterance CER. The smoothing
  bandwidth (0.08) affects $r^*$, $L$, and $M$. A different bandwidth would give different
  constants but the same $O(1/n^2)$ rate.

- **Two actions only.** The POMDP formalization uses $\{\text{mixed}, \text{separated}\}$;
  the gate actions (flatness, speaker) are folded into "separated" (they are
  separated-track actions). The bound extends to $k$ actions by replacing the threshold
  with the closest-decision-boundary distance, but we do not derive this.

- **B3 is qualitative.** The AISHELL-4 vacuity check (H15b) counts sign-changes but does
  not quantify *how much* the bound fails (there is no scalar "vacuity magnitude"). The
  sign-change count is a binary test: the bound either applies (1 sign-change) or is
  vacuous ($\neq 1$ sign-changes).

- **B4 is not empirically verified against a per-utterance regret.** Bound 4 is a
  theoretical restoration; we verify its $O(L_g/n^2)$ rate (slope $-2.000$) but do not
  compare it to an empirical per-utterance POMDP regret on AISHELL-4 (that would require
  per-utterance CER data with silence-fraction labels, which is not in the current
  frontier).

## What this adds over RQ5 / RQ10

RQ5 showed *empirically* that router v2 ≈ POMDP-optimal on gold (divergence 0.03).
RQ10 showed *empirically* that the per-utterance POMDP predicts the AISHELL-4 failure.
RQ15 adds the **theoretical layer**: it derives the regret bound that *explains why* the
empirical near-optimality holds on gold (Bound 2, tight to 0.6%), *explains why* it breaks
on AISHELL-4 (Bound 3, second sign-change), and *identifies the condition* under which the
bound is restored (Bound 4, Lipschitz silence reward). The tightness of Bound 2 (0.6%) is
itself a finding: router v2 is not just empirically good, it is provably near-optimal with
a nearly-tight bound.
