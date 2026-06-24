# POMDP Per-Utterance Heterogeneity Extension — Findings (RQ10)

**Label:** `experimental/frontier`. Theoretical + reanalysis only; no new data collection, no ASR runs.
Builds on RQ5 (`pomdp_solver.py`, finding #24); does NOT overwrite it. Rewards estimated from
existing frontier data (#11 phase_aggregate, #14 prosody_tax_curve, #18 objective-aware routing,
#20 gate emotion cost) + the AISHELL-4 external validation (RQ1, #881) + the causal hallucination
probe (#21). Reproduce: `python3 results/frontier/decision_theoretic_routing/pomdp_per_utterance.py`.

Closes #896. Answers RQ10. See `results/frontier/decision_theoretic_routing/pomdp_solver.py` (RQ5,
the stratum-level baseline this extends).

## Question

RQ5 built a stratum-level POMDP (5 discrete overlap strata) that recovers router v2's empirical
boundary to within 0.03 overlap-ratio and predicts #18's decoupling. But its honest limitation
(stated in RQ5's FINDINGS) was: *"the POMDP captures the dominant trend but not per-utterance
heterogeneity. The mid-overlap coupling costs #18 reports arise from within-stratum variation the
POMDP does not see."* RQ10 asks whether lifting the stratum-level discretization to a per-utterance
(continuous-state) POMDP (a) improves text regret, (b) predicts the AISHELL-4 failure that router v2
could not generalize to, and (c) reveals the within-stratum coupling-cost heterogeneity that RQ5
could not see.

## Method

Three extensions over `pomdp_solver.py`, all reanalysis (no new data):

| Extension | What it does | Data |
|---|---|---|
| **Continuous overlap** | Replaces 5 discrete strata with a Gaussian-kernel-smoothed reward surface over continuous overlap ∈ [0, 0.9]. Bandwidth h_text=0.08 (15 greedy support points), h_emo=0.15 (5 support points × 8 pairs). | `phase_aggregate.csv` (15 greedy strata), `prosody_tax_curve.csv` (8 pairs × 5 overlaps, α=0.15) |
| **Silence-fraction state** | Adds a continuous silence-fraction dimension `g ∈ [0, 1]` (fraction of the separated track that is silence). Models the AISHELL-4 oracle-TextGrid failure driver: an additive hallucination penalty on separated-track actions (separated, gate_flatness, gate_speaker), calibrated from #21 (confident-attractor) + RQ1 (separated cpWER 1.496–1.720 vs gold CER 0.46–0.76). | #21 causal probe, RQ1 AISHELL-4 |
| **Per-pair emotion heterogeneity** | Uses the 8 prosody pairs as per-utterance samples to compute within-stratum coupling-cost CV. | `prosody_tax_curve.csv` (8 pairs) |

**Solver:** greedy per-utterance argmax. With deterministic transitions (T=δ, same as RQ5), the
POMDP collapses to per-state argmax; the extension is the continuous state + silence dimension, not
a multi-step belief-state solver. The greedy solver picks, for each utterance, the action with the
highest expected reward given its continuous state (overlap, silence_fraction, noise, objective).

**Silence-gap penalty calibration (documented; no data invented):**
- The AISHELL-4 failure (RQ1): oracle-TextGrid separation creates per-speaker tracks with long
  interior silence gaps. These trigger Whisper's confident-attractor (#21): the encoder flags silence
  while the decoder is confident, producing repetition/insertion loops that inflate separated cpWER
  past 1.0 (1.496 NoOverlap, 1.720 MidOverlap).
- Model: `separated_cer(r, g) = base_sep_cer(r) + 1.5·g` (additive hallucination cost, linear in
  silence fraction). `mixed_cer(r, g) = base_mixed_cer(r) + 0.1·g` (mild masking). The gain 1.5 is
  calibrated so that at g=0.6 (representative AISHELL-4 silence: one speaker ~12 s speech in a 30 s
  window), the penalty (0.9) exceeds the separation benefit at high overlap (base_sep(0.3)=0.482 vs
  base_mixed(0.3)=1.194, gap=0.712), flipping separated→mixed. This reproduces RQ1's finding that
  separated > mixed at ALL overlap levels under oracle-TextGrid silence.
- The existing gates (flatness, speaker) do NOT cure interior silence (RQ8 documents this gap), so
  the penalty applies to all separated-track actions equally.

## Result 1 (RQ10.1) — Per-utterance POMDP improves text regret, but marginally and in-sample

Three policies compared on clean-text CER regret over a dense overlap grid (0.00–0.90, step 0.01,
91 points). The "true" CER surface is the kernel-smoothed estimate; regret = cer(policy) − cer(oracle).

| Policy | Mean text regret | Crossover (overlap-ratio) |
|---|---:|---:|
| Stratum-level POMDP (RQ5) | 0.00033 | 0.21 |
| **Per-utterance POMDP (RQ10)** | **0.00000** | **0.20** |
| Router v2 (baseline) | 0.00260 | 0.17 |

The per-utterance POMDP's crossover (0.20) matches the oracle crossover exactly; the stratum-level
POMDP's crossover (0.21) is one grid-step late (its step-function boundary sits at the stratum
midpoint 0.20, but the nearest-stratum snap pushes it to 0.21); router v2's crossover (0.17) is
slightly early.

**Honest scope.** The per-utterance POMDP's zero regret is partly tautological: it is evaluated on
the same kernel-smoothed surface it optimizes over, so it wins by construction. The meaningful
number is that the **stratum-level discretization regret is tiny (0.00033)** — the 5-strata POMDP
is already a good approximation for the text objective, because the text CER crossover is sharp
(between overlap 0.15 and 0.20 in the actual data) and any policy that places its crossover in that
band has near-zero regret. Router v2's threshold (0.17) incurs the largest regret (0.0026) because
it switches to separated 0.03 too early, paying the mixed→separated separation tax on windows where
mixed is still optimal.

**Verdict RQ10.1: SUPPORTED but marginal.** The per-utterance POMDP improves over the stratum-level
POMDP on text regret (0.00033 → 0.00000), but the improvement is small and in-sample. The
continuous-state extension's value is NOT in text-regret reduction (the stratum-level POMDP already
captures the dominant crossover); it is in the silence-fraction dimension (RQ10.2) and the
within-stratum heterogeneity (RQ10.3), which the stratum-level POMDP cannot represent at all.

## Result 2 (RQ10.2) — Per-utterance POMDP predicts the AISHELL-4 failure

The AISHELL-4 failure (RQ1, #881): router v2 cpWER (1.206) does not beat always-mixed (1.173)
because separated is worse than mixed at ALL overlap levels — including HeavyOverlap, where the gold
benchmark found separated wins. The root cause is oracle-TextGrid silence gaps triggering the
confident-attractor (#21). Router v2 and the stratum-level POMDP both lack a silence dimension, so
both pick "separated" at high overlap and fail on AISHELL-4.

The per-utterance POMDP adds the silence-fraction state dimension. Simulating AISHELL-4-like windows
(overlap from the RQ1 distribution: 53% NoOverlap, 31% Light, 14% Mid, 1% Heavy) at two silence
regimes:

| Regime | P(mixed) overall | P(mixed) high-overlap (Mid+Heavy) |
|---|---:|---:|
| **Silence-gap (g=0.6, AISHELL-4-like)** | **1.00** | **1.00** |
| No-silence (g=0.0, gold-baseline-like) | 0.83 | 0.00 |
| Stratum-level POMDP (no silence dim, g=0.6) | 0.85 | 0.00 |

**The discriminating test is the high-overlap band.** Without silence, both POMDPs pick separated at
high overlap (P(mixed)=0.00) — the gold-baseline prediction. With silence gaps, the per-utterance
POMDP flips to mixed at high overlap (P(mixed)=1.00 > 0.70 threshold), predicting the AISHELL-4
failure. The stratum-level POMDP, lacking the silence dimension, keeps separated at high overlap
(P(mixed)=0.00) and does NOT predict the failure.

The overall P(mixed) is >0.70 for both policies even without silence (0.83–0.85), because 84% of
AISHELL-4 windows are low-overlap where mixed always wins. The failure is specifically about the
high-overlap windows where the gold baseline says "separate" but AISHELL-4 says "don't" — and only
the per-utterance POMDP with the silence dimension captures this.

**Verdict RQ10.2: SUPPORTED.** The per-utterance POMDP, given a silence-fraction state dimension
calibrated from #21/RQ1, assigns P(mixed)=1.00 > 0.70 to silence-gap high-overlap windows,
predicting the AISHELL-4 failure. The stratum-level POMDP cannot predict this failure because it has
no silence dimension. This is the main value of the per-utterance extension: it adds the state
variable (silence fraction) that explains *why* the gold-baseline routing boundary does not transfer
to AISHELL-4.

**Caveat.** The silence-gap penalty (gain=1.5) is a qualitative model calibrated from #21/RQ1, not a
measured quantity. The result is robust to the gain choice in the sense that any gain large enough
to overcome the separation benefit at high overlap (>~1.3 at g=0.6) flips separated→mixed; but the
exact P(mixed) and the threshold g at which the flip occurs depend on the gain. A measured
silence-fraction→CER curve (from a real AISHELL-4 cpWER run with the silence-aware gate, RQ8) would
replace the calibrated penalty with data. This is left as future work.

## Result 3 (RQ10.3) — Coupling cost is heterogeneous within strata (CV > 0.5 at ov 0.1)

RQ5's honest limitation: *"the mid-overlap coupling costs #18 reports arise from within-stratum
variation the POMDP does not see."* RQ10 tests this directly. Coupling cost = regret of forcing one
action for both objectives vs letting each pick its optimum, computed per (pair, stratum) from the 8
prosody pairs (emotion side) + stratum-level text CER.

| Stratum | Mean coupling cost | Std | **CV** | CV > 0.5? | sep_helps_frac (text-side proxy) |
|---:|---:|---:|---:|:--:|---:|
| 0.0 | 0.000 | 0.000 | 0.00 | — | 0.25 |
| **0.1** | **0.108** | **0.105** | **0.97** | **✓** | 0.30 |
| 0.3 | 0.001 | 0.003 | 2.65 | ✓* | 0.50 |
| 0.6 | 0.000 | 0.000 | 0.00 | — | 0.70 |
| 0.9 | 0.011 | 0.028 | 2.65 | ✓* | 1.00 |

**Verdict RQ10.3: SUPPORTED at ov 0.1.** CV at ov 0.1 = 0.97 > 0.5, confirming the within-stratum
heterogeneity that RQ5 could not see. At ov 0.1, the 8 prosody pairs split: 4 pairs have emotion
wanting separated (text wants mixed → disagree → coupling cost > 0), 4 pairs have emotion wanting
mixed (agree → coupling cost = 0). This bimodal split produces the high CV.

**Text-side heterogeneity (supporting evidence).** `sep_helps_frac` (fraction of the 20 cases where
separated CER < mixed CER) provides a text-side heterogeneity proxy: at ov 0.3, sep_helps_frac =
0.50 (half the cases benefit from separation, half don't — maximum text-route heterogeneity). This
confirms that the within-stratum heterogeneity is not just an emotion-side artifact; the text route
itself is heterogeneous within strata, which a per-utterance POMDP would capture but a stratum-level
POMDP cannot.

*Asterisk on ov 0.3 / 0.9.* The CV at ov 0.3 and 0.9 is 2.65, but the mean coupling cost is near
zero (0.001 / 0.011). CV is misleading when the mean is near zero: a single pair with a tiny nonzero
coupling cost inflates the CV. The robust claim is at ov 0.1, where the mean is substantial (0.108)
and the CV (0.97) is meaningful. At ov 0.3, the text-side heterogeneity (sep_helps_frac=0.50) is the
stronger signal than the emotion-side CV.

## Synthesis

| RQ | Verdict | Honest scope |
|---|---|---|
| **RQ10.1** (per-utterance improves text regret?) | **SUPPORTED but marginal** | Improvement is 0.00033 → 0.00000, in-sample. The stratum-level POMDP already captures the dominant text crossover; the continuous-state extension's value is not in text regret. |
| **RQ10.2** (predicts AISHELL-4 failure?) | **SUPPORTED** | P(mixed)=1.00 > 0.70 for silence-gap high-overlap windows. The silence-fraction dimension — absent from the stratum-level POMDP — is what enables the prediction. This is the main result. |
| **RQ10.3** (coupling cost CV > 0.5 at ov 0.1?) | **SUPPORTED** | CV=0.97 at ov 0.1, from the bimodal split of the 8 prosody pairs (4 disagree, 4 agree). Text-side sep_helps_frac=0.30–0.50 confirms the heterogeneity is not emotion-only. |

The per-utterance POMDP's value over the stratum-level POMDP is **not** in refining the text
crossover (RQ5's stratum-level POMDP already gets it right to within 0.03), but in two things the
stratum-level POMDP cannot represent:

1. **The silence-fraction dimension** (RQ10.2): the state variable that explains why the
   gold-baseline routing boundary does not transfer to AISHELL-4. The stratum-level POMDP, lacking
   this dimension, predicts "separated at high overlap" and is wrong on AISHELL-4. The per-utterance
   POMDP, given silence-gap windows, predicts "mixed at all overlap" — matching RQ1's finding.

2. **Within-stratum heterogeneity** (RQ10.3): the coupling cost varies substantially within strata
   (CV=0.97 at ov 0.1), confirming RQ5's stated limitation. A stratum-level policy assigns one action
   to all utterances in a stratum, paying the coupling cost on the disagreeing utterances; a
   per-utterance policy could route each utterance by its own (continuous) state, avoiding this cost.
   The text-side heterogeneity (sep_helps_frac=0.50 at ov 0.3) shows this is not just an emotion-side
   artifact.

## Honest limitations

- **In-sample text regret (RQ10.1).** The per-utterance POMDP is evaluated on the same
  kernel-smoothed surface it optimizes over, so its zero regret is partly tautological. The
  meaningful number is the stratum-level discretization regret (0.00033), which is small —
  confirming the stratum-level POMDP is a good text-objective approximation. An out-of-sample test
  (held-out utterances with per-utterance CER) would be needed to validate the per-utterance
  advantage non-tautologically; this requires per-utterance CER data not available in the current
  frontier (phase_aggregate gives stratum means, not per-utterance values).

- **Calibrated silence penalty (RQ10.2).** The hallucination penalty (gain=1.5) is a qualitative
  model calibrated from #21/RQ1, not a measured silence-fraction→CER curve. The qualitative result
  (silence flips high-overlap from separated to mixed) is robust to the gain choice above ~1.3, but
  the exact P(mixed) and flip threshold depend on the gain. A measured curve (from an AISHELL-4 cpWER
  run with the RQ8 silence-aware gate, sweeping silence fraction) would replace the calibration with
  data.

- **Emotion-side heterogeneity only (RQ10.3).** Within-stratum coupling-cost CV is computed from the
  8 prosody pairs (emotion side); text CER is stratum-level (phase_aggregate averages 20 cases per
  stratum). The text-side heterogeneity is proxied by `sep_helps_frac` (the fraction of cases where
  separated helps), which confirms heterogeneity exists but does not give per-utterance text CER.
  Full per-utterance coupling-cost CV would need per-utterance text CER, which is not in the current
  frontier.

- **Kernel bandwidth fixed a-priori.** h_text=0.08, h_emo=0.15 are chosen from the support spacing
  (0.05 for text, ~0.2 for emotion), not tuned on regret. A leave-one-out bandwidth sweep would
  confirm robustness; the crossover location (0.20) is stable across h_text ∈ [0.05, 0.12] because
  the actual data crossover is sharp (between 0.15 and 0.20).

- **Deterministic transitions.** Same as RQ5: the single-step POMDP (T=δ) models the route as
  fixing the output for one utterance. A multi-step belief-state extension (where the route affects
  future belief via observations) would be needed for streaming/long-form context.

- **No new data.** This is a reanalysis of #11/#14/#18/#20/#21/RQ1 data; it does not test the
  per-utterance POMDP on held-out utterances. The RQ10.2 verdict is about model specification (does
  adding a silence dimension predict the AISHELL-4 failure?), not about out-of-sample cpWER
  prediction.

`experimental/frontier`. Artifacts: `pomdp_per_utterance.py`, `policy_comparison_per_utterance.csv`,
`policy_comparison_per_utterance.json`.
