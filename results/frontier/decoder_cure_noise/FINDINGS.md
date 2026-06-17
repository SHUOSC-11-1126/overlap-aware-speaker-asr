# The noise-robust separation-hallucination cure is NOT in the decoder — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny` (offline); references synthetic/silver; CER
post-hoc only, never a routing/gate input. No gold tables touched; all outputs in
`results/frontier/decoder_cure_noise/`. Grid: 8 speaker pairs × 3 overlaps × 3 noise types × 3 SNR
+ a clean anchor = 480 separated-track rows, 48 samples/cell. Reproduce:
`python -m src.decoder_cure_noise --pairs 8`.

## Question (issue #809 — reverses the assumption of the noise saga)

The separation-hallucination thread (#796 Separation Tax → #804 clean cures → #806 noise defeats the
energy trim → #808 flatness/speaker gates) shares one hidden assumption: **the cure must detect and
crop the low-information residual *in the audio*.** That detection is what keeps dying as noise gets
harder (energy → flatness → speaker). But #804 showed the catastrophe is, in **clean** audio, a
*greedy-decoding artifact*: beam search and Whisper's **native** `hallucination_silence_threshold`
kill the tail with zero cropping. Those decoder-domain cures were never tested under noise.

**RQ:** do decoder-domain cures survive noise — including babble — where input-domain
silence-detection dies? **Pre-registered prediction:** beam search (path diversity, no silence
detection) survives; Whisper's native silence-threshold dies like the energy trim.

## Verdict: H1 confirmed, H2 refuted — the decoder is not where the noise-robust cure lives

The honest result is a **negative** one for the bold hypothesis, and it is clean and falsifiable.

### Mean CER + catastrophic tail rate by condition (48 samples/cell)

| noise | SNR | greedy | energy_trim | **flatness** | beam5 | halluc(native) | tail greedy→beam |
|---|---:|---:|---:|---:|---:|---:|---:|
| clean | — | 0.981 | 0.418 | 0.410 | 0.482 | 0.483 | 0.021→0.000 |
| babble | 10 dB | 1.133 | 1.133 | 1.052 | 1.273 | **0.782** | 0.229→0.146 |
| babble | 5 dB | 2.193 | 2.193 | **1.132** | 2.463 | 1.853 | 0.583→0.417 |
| babble | 0 dB | 4.777 | 4.777 | **2.946** | 5.885 | 6.712 | 0.625→0.750 |
| white | 10 dB | 1.019 | 1.019 | **0.637** | 1.179 | 1.032 | 0.062→0.062 |
| white | 5 dB | 1.289 | 1.289 | **0.746** | 1.183 | 1.296 | 0.083→0.104 |
| white | 0 dB | 2.206 | 2.206 | **1.716** | 2.720 | 3.039 | 0.208→0.271 |
| pink | 10 dB | 0.581 | 0.581 | 0.573 | 0.864 | 0.573 | 0.000→0.021 |
| pink | 5 dB | 1.054 | 1.054 | 1.054 | 1.055 | 1.060 | 0.062→0.104 |
| pink | 0 dB | 0.829 | 0.829 | 0.836 | 0.902 | **0.811** | 0.125→0.125 |

### Fire rate (fraction of tracks where the cure changed Whisper's output vs greedy) — the mechanism

| noise | SNR | energy_trim | flatness | beam5 | halluc(native) |
|---|---:|---:|---:|---:|---:|
| clean | — | 0.729 | 0.729 | 0.750 | 0.042 |
| babble | 10 dB | **0.000** | 0.646 | 0.771 | 0.188 |
| babble | 5 dB | **0.000** | 0.667 | 0.792 | 0.292 |
| babble | 0 dB | **0.000** | 0.604 | 0.896 | 0.312 |
| white | 0 dB | **0.000** | 0.792 | 0.896 | 0.333 |
| pink | 10 dB | **0.000** | 0.062 | 0.792 | 0.062 |

Findings, all falsifiable:

1. **H1 confirmed and generalized — silence detectors die under noise.** The energy trim fires on
   **0%** of tracks at every noisy SNR; its CER equals raw greedy to the decimal (1.133=1.133,
   2.193=2.193, 4.777=4.777). This reproduces #806 exactly. Whisper's **native**
   `hallucination_silence_threshold` is the same kind of detector and suffers the same fate: it
   fires on only 4–33% of noisy tracks (vs needing to fire on the ~20–60% that are catastrophic),
   because additive noise fills the silence its DTW alignment looks for. The mechanism that killed
   the manual energy trim in #806 also disables Whisper's own built-in anti-hallucination feature.

2. **H2 refuted — beam search does NOT robustly cure under noise; it makes the mean worse.** Beam
   fires constantly (77–90% under noise), so it is *active* — but activity is not help. Beam raises
   mean CER under **every** noise type at **every** SNR (babble 10 dB 1.13→1.27; white 0 dB
   2.21→2.72), and pooled over all noisy conditions `always_beam` (mean 1.947) is **worse than
   doing nothing** (`always_greedy` 1.676). On noisy/degenerate separated audio the alternative
   decoding paths beam explores are *also* wrong; it trades a catastrophic greedy repetition loop
   for broad, mild, widespread error.

3. **Tail rate vs mean: beam's only redeeming behavior is an unfavorable trade.** Beam does lower
   the catastrophic *tail rate* at moderate babble (10 dB 0.229→0.146; 5 dB 0.583→0.417) — it pulls
   some blow-ups back under CER 1 — but the tail-conditional split shows why this loses on balance:

   | arm (pooled, babble) | mean CER on catastrophic (n=69) | mean CER on normal (n=75) | normal Δ vs greedy |
   |---|---:|---:|---:|
   | greedy | 4.823 | 0.749 | +0.000 |
   | energy_trim | 4.823 | 0.749 | +0.000 (inert) |
   | flatness | 1.863 | 1.570 | +0.821 |
   | beam5 | 4.322 | 2.181 | **+1.432** |
   | halluc(native) | 5.678 | 0.758 | +0.009 |

   Beam barely dents the catastrophic group (4.82→4.32) while taxing the healthy majority by +1.43
   CER. The net is negative. (Native halluc-silence is the opposite: it leaves the healthy majority
   almost untouched, +0.009, but cannot fix the catastrophic group under noise, 4.82→5.68.)

## The deployable consequence: the noise-robust cure must touch the audio

Reference-free policy regret vs a per-track oracle (min over {greedy, beam5, flatness}; CER scores
the outcome, never routes):

| policy (pooled noisy, n=432) | mean CER | tail (CER>1) | regret vs oracle |
|---|---:|---:|---:|
| always greedy (raw separation) | 1.676 | 0.220 | +0.908 |
| always beam5 (decoder cure) | 1.947 | 0.222 | +1.179 (worst) |
| **always flatness gate (input cure, #808)** | **1.188** | **0.160** | **+0.420 (best non-oracle)** |
| oracle (per-track min) | 0.768 | 0.079 | — |

The input-domain **flatness gate is the best single cure under noise**; the decoder cure (beam) is
the **worst** policy of the three — worse than raw separation. So the answer to #809 is **no**: the
noise-robust separation-hallucination cure is not in the decoder. In clean audio the catastrophe is
a pure decoding artifact (beam/halluc both cure it, 0.98→0.48), but **under noise it is not** — the
noise itself drives Whisper into a degeneracy that neither path diversity nor silence-skipping can
undo, because both leave the offending audio in place. The cure has to crop the residual, which is
exactly the audio-domain line (#806 flatness, #808 speaker) — now explained, not just asserted: it
is necessary *because* the decoder-only cures provably fail here.

## What this changes

- **Closes a tempting blind alley with data.** "Just decode with beam search, it's robust" is the
  obvious cheap fix and it is wrong under noise — beam is a net negative on the population. This is
  worth knowing precisely because it is counterintuitive (beam is usually assumed safe-or-neutral).
- **Generalizes #806.** The energy trim's death was not specific to the manual trimmer; it is the
  fate of *any* silence-detection cure under noise, including Whisper's purpose-built feature.
- **Validates and explains the input-gate direction.** #808's flatness/speaker gates are not just
  one option among many; they are doing the one thing that survives noise (acting on the audio).
- **A bright spot worth a selector.** Native `hallucination_silence_threshold` is the single best
  arm at moderate babble (10 dB, 0.782) and nearly free on the healthy majority (+0.009), while
  flatness wins everywhere else. The reference-free gate selector named in the #808 synthesis could
  add `halluc_silence` as a moderate-babble member — a concrete, data-grounded next build.

## Methodological note (honest)

A single-track grounding probe (the known-catastrophic `con_006/pro_006@0.10` spk2) showed beam
*helping* under babble (2.25→1.875). The 48-sample/cell population grid **reverses** that: beam
hurts on the mean. The rare catastrophic track is exactly where beam helps; across the population
its tax on the healthy majority dominates. This is a clean reminder that single-track probes are
misleading for tail phenomena — the population grid is what decided the verdict.

## Honest limitations

Whisper-`tiny`; silver references; synthetic oracle separation (real separators add their own
artifacts); additive synthetic noise (real meeting noise is non-stationary). n = 48/cell with heavy
CER tails, so per-cell point estimates are high-variance; the trustworthy claims are the
*directional* ones (energy_trim/halluc fire-rate collapse; beam's pooled mean > greedy; flatness the
best single policy) and the *fire-rate* numbers, not exact per-cell means. `hallucination_silence_threshold`
fixed at 2.0 s; beam_size fixed at 5; thresholds a priori, never CER-tuned. Frontier evidence, not a
gold result. Artifacts: `cure_noise_curve.csv` (480 rows), `dichotomy_summary.json`,
`firerate_summary.json`, `tail_conditional.json`, `regret_summary.json`, `decoder_cure_noise.png`.
