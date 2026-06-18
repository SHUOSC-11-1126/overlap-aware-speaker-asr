# Objective-aware decoupled routing: recover both text and emotion — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; references synthetic/silver; emotion =
gain-invariant prosody distance to the clean source (`src/prosody.py`, label-free); separation =
cross-talk leakage α=0.15. No gold tables touched. Outputs in
`results/frontier/objective_aware_routing/`. Reproduce: `python -m src.objective_aware_routing --pairs 8`
(8 pairs × overlap {0,0.1,0.3,0.6,0.9} = 40 utterances).

## Question

The capstone of findings #14–#17. If a system must output BOTH an accurate transcript AND each
speaker's emotion, can a single separate-or-not switch serve both? #14 said no in principle (separation
helps emotion at every overlap but hurts ASR at low/mid overlap). This quantifies the cost and tests
the fix: **objective-aware decoupling** — route the TEXT objective by the ASR-optimal decision, but
always read EMOTION from the separated track.

## Result — decoupling Pareto-dominates the single switch, near-oracle on both axes

Mean over 40 utterances (text route = ASR-optimal argmin-CER; see scope note):

| strategy | mean CER | mean emotion distortion | joint regret (↓) |
|---|---:|---:|---:|
| always-mixed | 0.596 | 0.180 | 0.078 |
| always-separated | 1.050 | 0.079 | 0.025 |
| coupled (one switch) | 0.528 | 0.139 | 0.046 |
| **decoupled (this work)** | **0.528** | **0.079** | **0.003** |
| oracle (best per axis) | 0.528 | 0.075 | 0.000 |

- **Same text, half the emotion distortion.** Decoupled matches the coupled router's CER (0.528) but
  cuts mean emotion distortion 0.139 → 0.079 — essentially the oracle's 0.075 — by reading emotion from
  the separated track even when the text route stays mixed.
- **Joint regret cut ~14×** (0.046 → 0.003), placing decoupled almost exactly on the two-objective
  oracle. Neither fixed strategy is good on both axes: always-mixed is decent text / worst emotion;
  always-separated is oracle emotion / ruinous text (1.05).
- **The coupling cost is real and localized.** Mean 0.060, concentrated in the low/mid-overlap band
  the #14 divergence predicted: +0.119 (ov 0.1), +0.085 (ov 0.3), +0.096 (ov 0.6), and **0.000** at ov
  0.0 and 0.9 (where the text route already picks separated, so coupling is free).

## Synthesis — the deployable emotion-aware ASR answer

The emotion frontier resolves to a concrete, deployable design: **keep the proven reference-free ASR
router for the transcript, and always recover per-speaker emotion from the separated track.** This
costs nothing in text quality and recovers almost all of the emotion fidelity a single ASR-tuned switch
would silently forfeit — precisely in the light/mid-overlap regime where the two objectives disagree.
It directly answers the project's grand question for the multi-objective setting: *when should we
separate?* — for text, by the ASR router; for emotion, always.

## Honest scope and limitations

The text route here is the **oracle** ASR route (argmin-CER), used to isolate the decoupling benefit.
A real reference-free router (router_v2 / compression-ratio) would raise the absolute CER of coupled
AND decoupled equally, but cannot change the emotion-axis argument: decoupled always reads emotion from
the separated track, so its emotion advantage (and the coupling cost) is independent of text-router
quality. Whisper-`tiny`; synthetic oracle/leaky separation (α=0.15); emotion is arousal-side prosody
*preservation* vs the clean source (not classified emotion, no human labels — see #14); n=40 with heavy
CER tails (the robust claims are the *ordering* and the overlap-localized coupling cost, not exact
magnitudes). Pure routing logic is unit-tested (8 tests). `experimental/frontier`. Artifacts:
`routing_curve.csv` (40 rows), `routing_summary.json`, `objective_aware_routing.png`.
