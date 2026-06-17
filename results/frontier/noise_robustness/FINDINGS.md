# Noise robustness: does noise change when separation helps? — Findings

**Label:** `experimental/frontier`. ASR Whisper-`tiny`; references synthetic/silver; CER
post-hoc only, never a routing input. No gold tables touched. 10 pairs × 6 overlaps × 5 SNR
levels (clean/20/10/5/0 dB) × {mixed, sep, sep_trim}. Each ASR input is presented at the
stated SNR w.r.t. its own speech power (additive white Gaussian noise); oracle separation
removes the other talker but not the noise. Reproduce: `python -m src.noise_robustness`.

## Headline: noise defeats the energy-based silence-trim cure

| SNR | mean CER_sep | mean CER_sep_trim | trim gain (sep − sep_trim) | tail_rate sep | tail_rate sep_trim |
|---|---:|---:|---:|---:|---:|
| clean | 0.691 | 0.452 | **+0.239** | 0.017 | 0.000 |
| 20 dB | 0.503 | 0.503 | **+0.000** | 0.017 | 0.017 |
| 10 dB | 1.148 | 1.148 | +0.000 | 0.133 | 0.133 |
| 5 dB | 1.071 | 1.071 | +0.000 | 0.050 | 0.050 |
| 0 dB | 1.410 | 1.410 | +0.000 | 0.200 | 0.200 |

The silence-trim cure's large clean benefit (**+0.239** mean CER) collapses to **exactly
+0.000 at every SNR ≥ 0 dB**, and `tail_rate_sep == tail_rate_sep_trim` at every noisy level.

Mechanism (RQ-N2 confirmed): the trim is energy-based — it crops the region where
`|x| < 1e-3 · peak`. Under noise the gap the separation leaves behind is no longer silent;
the noise floor exceeds the relative threshold everywhere, so `trim_silence` finds no silence
and becomes a **no-op** (sep_trim ≡ sep). The cure that was perfect in clean conditions does
nothing once any realistic noise is present.

Two further effects:
- **Noise amplifies the hallucination tail**: sep tail rate rises from 0.017 (clean) to
  0.133–0.200 (10–0 dB) — Whisper hallucinates more on noisy audio, and trim can't remove it.
- **The separation gain erodes/reverses under noise.** Mean ΔCER(mixed − sep_trim) is
  positive when clean/lightly-noisy (+0.144 clean, +0.291 at 20 dB) but becomes negative at
  moderate noise (−0.434 at 10 dB, −0.387 at 0 dB). The per-cell overlap×SNR grid is noisy
  (n=10/cell) so individual cells are exploratory, but the per-SNR aggregate (n=60) is clear:
  separation stops reliably helping once SNR drops.

## What this changes

This qualifies the earlier deployable recommendation: **silence-trim is a clean-conditions
cure, not a universal one.** A noise-robust pipeline must not gate on raw energy. The natural
next probe is Whisper's native `hallucination_silence_threshold`, which detects silence via
no-speech-probability rather than energy and may survive noise; failing that, a trained VAD.
It also means a deployed "when to separate" decision must be SNR-aware, not overlap-only.

## Honest limitations

White Gaussian noise (not babble/real environmental noise); per-input-SNR model; oracle
separation (real separators leave residual noise differently); Whisper-`tiny`; the
overlap×SNR grid has only n=10 per cell (per-SNR aggregates n=60 are the reliable read).
Artifacts: `noise_curve.csv` (300 rows), `noise_summary.json`.
