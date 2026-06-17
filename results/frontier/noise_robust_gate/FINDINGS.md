# A separation-hallucination cure that survives noise — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny` (offline); references synthetic/silver
(Whisper-`small` on clean snippets); CER is post-hoc only, never a routing/gate input. No
gold tables touched; all outputs in `results/frontier/noise_robust_gate/`. Main grid: 12
speaker pairs × 4 overlap ratios × 5 SNR levels = 240 conditions, 48 separated-track samples
per SNR. Reproduce: `python -m src.noise_robust_gate --pairs 12` (synthetic oracle mixtures)
and `python -m src.noise_robust_gate --gold-noisy` (real-separator transfer on the 5 gold cases).

## Question (closes the loose end from the noise-robustness map, #806)

The frontier had reached a clean dead end. The chain of prior findings:

1. **Separation tax** (`separation_tax_phase.py`): separation helps Whisper at no/heavy/opposite
   overlap but hurts at light/mid overlap, via a heavy-tailed hallucination — a separated track
   left with a long low-information region drives Whisper into a catastrophic CER > 1 loop.
2. **Cure in clean audio** (`hallucination_cure_eval.py`): an energy-based leading/trailing
   silence trim eliminates that tail (catastrophic-group CER 19.84 → 0.54).
3. **Noise defeats the cure** (`noise_robustness.py`, #806): at every noisy SNR the trimmed and
   untrimmed separated CERs were *identical* (`trim_gain_vs_sep == 0.0`). Left open: **why, and
   is there a cure that survives noise?**

**RQ:** the energy trim dies because amplitude is not noise-robust — additive noise fills the
"silent" residual above the amplitude threshold, so the trimmer stops cropping. Spectral
**flatness** *is* noise-robust: broadband noise is spectrally flat, voiced speech is peaky.
Can a flatness-gated trim re-fire under noise where the energy trim cannot, and recover the cure?

## Grounding (measured before building)

A direct probe on the real snippets confirmed both halves of the mechanism:

- **Energy trim is inert under noise.** Fraction of a separated track it keeps: **54% clean →
  100% at 20/10/5/0 dB.** It removes nothing once noise is present — exactly the `trim_gain == 0`
  of #806.
- **Flatness separates speech from noise-residual across SNR.** Mean per-frame flatness, speech
  vs residual: `0.058 vs 0.994` (clean) → `0.461 vs 0.563` (0 dB); ranking AUC `0.999 → 0.765`.
  The contrast narrows as noise rises but never inverts, so an *adaptive* threshold keeps working.

## Method (reference-free; a priori, not CER-tuned)

Frame the track (25 ms / 10 ms), compute per-frame spectral flatness, put an **adaptive**
threshold in the valley of the (speech-low, noise-high) flatness distribution, and crop to the
contiguous low-flatness span — a drop-in replacement for the energy `trim_silence`. The
`flatness_relenergy` variant additionally keeps frames whose energy exceeds the *estimated noise
floor* (noise-floor-relative, unlike absolute amplitude). All thresholds fixed a priori
(`min_gap=0.15`, `gate_frac=0.5`, `factor=3.0`); none tuned on CER.

## Result: the cure is recovered under noise — concentrated where it's needed

Mean separated CER (lower is better), 48 samples/SNR:

| input SNR | mixed | raw sep | energy_trim (#806) | flatness_gate | **flatness+rel-energy** | tail sep | tail flat+E | fire% energy | fire% flat+E |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| clean | 0.522 | 1.010 | 0.455 | 0.446 | **0.442** | 0.062 | 0.000 | 100% | 100% |
| 20 dB | 0.752 | 0.621 | 0.621 | 0.597 | **0.467** | 0.021 | 0.000 | 0% | 100% |
| 10 dB | 0.655 | 1.030 | 1.030 | 0.628 | **0.621** | 0.104 | 0.021 | 0% | 100% |
| 5 dB  | 1.729 | 1.082 | 1.082 | 1.404 | 1.203 | 0.062 | 0.042 | 0% | 100% |
| 0 dB  | 1.212 | 1.874 | 1.874 | 1.880 | **1.041** | 0.250 | 0.146 | 0% | 100% |

Findings, all falsifiable:

1. **The energy trim is exactly inert under noise.** At every noisy SNR `energy_trim == raw sep`
   to six decimals; pooled-noisy paired ΔCER vs raw sep is `+0.000`, 95% CI `[0, 0]`, 0% of 192
   tracks changed. This reproduces #806 mechanistically: fire rate 0%.

2. **The flatness+rel-energy gate fires 100% under noise and recovers the cure.** Pooled over all
   noisy SNRs it cuts mean separated CER **1.152 → 0.833** (−28%) and roughly **halves the
   catastrophic tail, 0.109 → 0.052**, where the energy trim does nothing.

3. **The win is concentrated on the catastrophic minority — which is the point.** On the 21/192
   noisy tracks where raw separation hallucinates (CER > 1), the gate cuts mean CER
   **5.305 → 1.045** while the energy trim stays stuck at 5.305. This is a *tail* cure, so the
   pooled-mean 95% CI marginally includes zero (`[−0.667, +0.033]`): the gate is a catastrophe
   firewall, not a uniform CER reducer.

4. **Honest cost: blind gating slightly hurts the healthy majority.** On the 171 non-catastrophic
   noisy tracks the gate raises CER `0.642 → 0.807` (+0.165) by occasionally over-cropping speech
   onsets. In clean audio it is safe (ties/beats the energy trim: 0.442 vs 0.455, both ≪ raw sep
   1.010). The pure-flatness variant is unreliable under noise (fires 48–100%, sometimes hurts);
   the rel-energy union is what makes it robust.

## Deployment: gate selectively via the existing reference-free guard

Because the cure helps the catastrophic minority but taxes the healthy majority, apply it
*selectively* — exactly the project's reference-free-router thesis. Reusing Whisper's own
compression-ratio degeneracy signal (`GUARD_THRESHOLD = 2.4`, the same a-priori guard as
`separation_tax_phase`), the **guard-gated** policy uses the gate only when the raw separated
tracks look degenerate, else keeps raw separation (`selective_policy.json`):

<!-- SELECTIVE_POLICY_BLOCK -->
| policy (pooled noisy, n=192) | mean CER | tail (CER>1) | regret vs oracle |
|---|---:|---:|---:|
| always raw separation | 1.152 | 0.109 | +0.499 |
| always gate (flat+rel-energy) | 0.833 | 0.052 | +0.181 |
| **guard-gated (gate only when CR > 2.4; fires 6.8%)** | **0.690** | 0.057 | **+0.037** |
| oracle (per-track min) | 0.653 | 0.036 | — |

By gating only the **6.8%** of tracks the reference-free guard flags as degenerate, the
guard-gated policy reaches **mean CER 0.690** — better than always-gating (0.833, which taxes the
healthy majority) and far better than raw separation (1.152), within **+0.037** of the per-track
oracle. The guard signal is Whisper's own compression ratio, chosen a priori; no reference/CER
enters the routing. This is the deployable form of the cure.

## Transfer to a real separator (noise-stressed gold cases)

The grid above uses oracle (synthetic) separation. The same arms on the 5 verified gold cases'
**real** separated tracks, noise-injected (`gold_noisy_summary.json`):

<!-- GOLD_NOISY_BLOCK -->
| policy (pooled noisy, n=20: 5 gold cases × 4 SNR) | mean CER |
|---|---:|
| always raw separation | 0.888 |
| energy_trim (#806) | 0.888 (inert — identical to raw sep, as on synthetic) |
| always gate (flat+rel-energy) | 0.910 (blind gating slightly *hurts*) |
| guard-gated | **0.865** (small net gain) |
| oracle (per-track min) | 0.847 |

This is the honest boundary of the result. On a *real* separator's output the long contiguous
silence-residual that the gate exploits is largely absent (the separator spreads leakage through
the track), so **blind gating does not transfer** — it slightly hurts (0.910 vs 0.888). Only the
**selective guard-gated** policy stays net-positive (0.865 < 0.888). The energy trim is again
exactly inert (0.888), confirming #806's mechanism on real audio too. n=20 is small; treat as a
directional sanity check, not a benchmark.

## Noise type decides everything: robust to broadband, not to babble

The grid above used white noise. White is the *easy* case for spectral flatness. Stress test
across noise types (8 pairs × 2 low overlaps × 3 SNR = 48 separated tracks/type;
`python -m src.noise_robust_gate --noise-types`):

| noise type | raw sep | flat+rel-energy gate | gain | tail sep → gate | gate fire rate |
|---|---:|---:|---:|---:|---:|
| white (broadband) | 0.974 | 0.944 | **+0.030** | 0.062 → 0.042 | ~100% |
| pink (1/f) | 1.245 | 1.240 | +0.005 | 0.042 → 0.042 | ~23% (abstains) |
| babble (speech-like) | 2.394 | 2.243 | +0.152 | 0.604 → 0.542 | ~95% |

Measured frame-level flatness contrast (residual − speech) at 5 dB: **white +0.162, pink +0.028,
babble −0.004** (it *inverts*). Consequences, all falsifiable:

- **White:** residual is flatter than speech → gate fires and helps (the main result).
- **Pink:** 1/f noise is itself low-flatness (energy at low frequency), so the adaptive threshold
  finds no clean valley and the gate **safely abstains** (~23% fire) — inert, neither helping nor
  hurting. Pink defeats the cure but *fails safe*.
- **Babble:** the residual is speech-like and spectrally **indistinguishable** from the target, so
  flatness carries no signal; the gate fires on the rel-energy term but crops unreliably and the
  catastrophic tail stays high (0.54). The cure **largely fails** — and babble is the real-meeting
  condition.

**Synthesis (the direction this opens).** Reference-free *spectral* gating cures
separation-hallucination only when the interference is spectrally distinct from speech.
Speech-like babble cannot be separated from a target's silence-residual by spectral statistics
alone — it requires **speaker identity**. The principled next step is a *voiceprint-conditioned*
gate (keep frames whose embedding matches the track's dominant speaker), which is exactly where
the project's dormant speaker-profile / voiceprint frontier becomes load-bearing rather than
diagnostic. This experiment turns "try voiceprints" from a vague backlog item into a specific,
motivated question: *can a speaker-embedding gate crop babble residual where flatness cannot?*

## Honest limitations

Whisper-`tiny`; silver references; synthetic oracle separation for the main grid; additive
synthetic noise (real meeting noise is non-stationary). The white-noise result does **not**
generalize to colored/babble noise (see above) — the gate is a broadband-noise cure. The 5 dB
column of the white grid is anomalous (raw sep already low, mixed unusually high): per-cell point
estimates are high-variance at n=48 with a heavy tail, so the *pooled* and *tail-conditional*
numbers are the trustworthy ones. The gate's benefit is tail control, not uniform reduction, and
it costs ~+0.16 CER on healthy tracks if applied blindly — hence the guard-gated policy. Frontier
evidence, not a gold result. Artifacts: `gate_curve.csv` (240 rows), `gate_summary.json`,
`selective_policy.json`, `gold_noisy_curve.csv`, `gold_noisy_summary.json`,
`noise_types_curve.csv` (144 rows), `noise_types_summary.json`, `noise_robust_gate.png`.
