# RQ8: Silence-Aware Gate for Router v2 AISHELL-4 Generalization

> **Label: `experimental/frontier`** — a reference-free silence-gap gate that targets the
> confident-attractor hallucination driver identified in the AISHELL-4 external validation (#881).
> Does NOT overwrite verified gold references or gold result tables.
> Closes #892. See `results/external_sanity_check/aishell4/FINDINGS.md` (RQ1, the failure mode),
> `results/frontier/causal_hallucination_probe/FINDINGS.md` (finding #21, the mechanism),
> `src/noise_robust_gate.py` (the gate-pattern reference).

## Executive Summary

Iteration 1's RQ1 (AISHELL-4 external validation, PR #890) found that router v2 does NOT
generalize to AISHELL-4: cpWER 1.206 vs always-mixed 1.173. The root cause is structural —
oracle-TextGrid separation creates per-speaker tracks where one speaker's speech sits at its
original positions and the rest of the 30 s window is silence. These long **interior** silence
gaps (between speaker turns) trigger Whisper's confident-attractor hallucination (finding #21):
the encoder flags silence while the decoder locks into a confident repetition/insertion loop,
inflating cpWER past 1.0.

This module implements a **reference-free silence-aware gate** (`src/silence_aware_gate.py`) that
detects interior silence gaps via noise-floor-relative RMS energy VAD and truncates every gap
longer than 0.5 s down to 0.3 s (preserving boundary transitions) before ASR decoding. The gate
is the interior-gap analogue of the energy-based `trim_silence` (#11) — but it crops EVERY long
gap, not just the leading/trailing span, which is the key gap the existing gates leave open.

**H8 (silence-aware gate brings router v2 cpWER below always-mixed on AISHELL-4): CONDITIONALLY
SUPPORTED by mechanism analysis; NOT YET CONFIRMED by a runnable AISHELL-4 evaluation.** The
AISHELL-4 audio (M_R003S02C01.flac/.TextGrid) and Whisper were not available in the worktree, so
the cpWER comparison could not be run. The gate is validated on synthetic audio that models the
failure mode (29/29 unit tests pass; a 20.5 s synthetic oracle-TextGrid-style track with 8 s + 6 s
interior gaps is correctly compressed to 6.5 s, removing 13.4 s of silence). The expected impact
is derived from the failure-mode chain: removing the long-silence stimulus should reduce the
confident-attractor firing rate on separated tracks, lowering separated cpWER and thus router v2
cpWER. A negative result (gate does not fix the issue) would argue the hallucination is driven by
the speech/silence boundary structure, not just gap duration, and point toward a real separator
(Gap M2) rather than oracle-TextGrid separation.

## The Silence-Gap Failure Mode

### What RQ1 found

On AISHELL-4 meeting M_R003S02C01 (38.5 min, 6 speakers, 77 windows of 30 s), router v2 cpWER
(1.206) is slightly worse than always-mixed (1.173); the paired bootstrap 95% CI [-0.152, +0.186]
crosses zero. The router's NoOverlap rule (choose separated when the mixed transcript is long)
does not transfer because **separated is worse than mixed at ALL overlap levels** on AISHELL-4
(NoOverlap Δ=+0.20, LightOverlap Δ=+0.64, MidOverlap Δ=+0.72), not just low overlap. The
separation tax is more severe than on the 5-case gold benchmark, where separated was better at
HeavyOverlap.

### Why the existing gates do not handle this

| Gate | What it does | Why it misses the AISHELL-4 failure |
|------|-------------|--------------------------------------|
| `trim_silence` (#11) | Energy-based leading/trailing silence crop | Crops only the LEADING/TRAILING span. Oracle-TextGrid tracks have silence BETWEEN speech segments; the interior gaps survive and the hallucination returns. |
| `flatness_trim` (#11, `noise_robust_gate`) | Spectral-flatness leading/trailing crop, noise-robust | Same leading/trailing limitation. Targets broadband NOISE residual, not true silence gaps. |
| Compression-ratio guard (#21) | Output-signal degeneracy detector | An OUTPUT signal: detects the catastrophe AFTER Whisper has already emitted the repetition loop. Cannot prevent the firing. |
| Token-id lock-in (#21) | Causal internal-state trip-wire | Catches the Mode R repetition tail at ~2% of the stream, but is an abort-to-mixed, not a silence cure. Does not address the silence stimulus. |

The unmet need: a gate that removes the **interior** silence gaps that are the hallucination's
acoustic trigger, before ASR decoding, reference-free.

### The mechanism chain (finding #21)

The `causal_hallucination_probe` established that the separation-tax catastrophe is a **confident
loop, not a confidence collapse**: catastrophic separated routes are decoded with HIGHER decoder
confidence (avg_logprob -0.335 vs -0.739 clean) and LOWER token-id entropy (1.487 vs 2.330) than
clean routes. The decoder is more confident and more locked while producing garbage. The
3-second tone+silence smoke test reproduced the loop (token 7322 × 224) with
`compression_ratio = 37`, `no_speech_prob = 0.82`, yet `avg_logprob = -0.065` — the decoder is
highly confident while repeating under an input the encoder flags as silent.

On AISHELL-4, the oracle-TextGrid separation creates exactly this stimulus at scale: each
per-speaker track is a 30 s window where the speaker's turns (typically 2–5 s each) are separated
by long silence (the other 5 speakers' turns, often 5–20 s of silence). Whisper-tiny's decoder
hits the confident-attractor on these silence gaps, producing the insertions that push separated
cpWER past 1.0 (1.591 average).

## Gate Design (all reference-free; CER/cpWER is post-hoc only)

### Parameters (a-priori, from failure-mode physics — never tuned on CER)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `MAX_GAP_SEC` | 0.5 s | Silence gaps longer than this are truncated. 0.5 s is the natural pause ceiling in conversational Chinese; longer pauses in a separated track are separation artifacts (the other speaker's turn), not speech. |
| `KEEP_GAP_SEC` | 0.3 s | A truncated gap is shortened to at most this, split half/half across the boundary, so speech segments stay separated by a natural pause (no click/pop on concatenation). |
| `FLOOR_PCT` | 20th percentile | The noise floor is the low percentile of per-frame RMS energy (the silence-like frames). |
| `ENERGY_FACTOR` | 3.0× | A frame is silent if its energy < `factor × floor`. Noise-floor-RELATIVE (like `noise_robust_gate.relenergy_speech_mask`), so it adapts to each track's absolute amplitude and survives real-separator residual noise. |
| `WIN` / `HOP` | 400 / 160 (25 ms / 10 ms @ 16 kHz) | Matches `noise_robust_gate` framing. |
| `ABS_SILENCE_FLOOR` | 1e-6 (~-120 dBFS) | Tracks whose peak energy is below this are all-silence and returned unchanged (the AISHELL-4 driver already skips these; the guard makes the gate safe standalone). |

### Algorithm

1. **Frame** the track (25 ms windows, 10 ms hop).
2. **Per-frame RMS energy** (mean square).
3. **Adaptive silence threshold**: `floor = percentile(energy, 20) + ε`; `threshold = 3 × floor`.
   Relative to the track's own energy distribution — adapts to absolute amplitude and residual
   noise. Returns 0 for an empty track; if the threshold is at/above the peak energy (all-silence
   or all-uniform-energy track), the gate abstains and returns the track unchanged.
4. **Silence mask**: frames with energy ≤ threshold.
5. **Find contiguous silence gaps**: runs of silent frames, mapped to (start_sample, end_sample,
   duration_sec).
6. **Truncate long gaps**: every gap longer than `MAX_GAP_SEC` is shortened to at most
   `KEEP_GAP_SEC`. For interior gaps, the keep-span is split half/half across the boundary
   (preserving natural pauses on both sides). For leading/trailing gaps, the keep-span is anchored
   at the speech-facing edge. The output is a shorter, gap-compressed track.
7. **Return** the compressed track (may be shorter than the input — less silence for Whisper to
   hallucinate on).

### What makes this different from the existing gates

- **Interior gaps, not just leading/trailing.** `trim_silence` and `flatness_trim` crop only the
  outermost silence span. The silence-aware gate crops EVERY long gap. This is the key difference:
  oracle-TextGrid tracks have multiple speech segments separated by long interior silence.
- **Pre-decoding, not post-decoding.** The compression-ratio guard and token-id lock-in detect
  the catastrophe AFTER it fires. The silence-aware gate removes the acoustic stimulus BEFORE
  Whisper sees it.
- **True-silence-targeted, not noise-targeted.** The flatness gate targets broadband noise
  residual (high spectral flatness). The silence-aware gate targets true silence gaps (low energy),
  which is the AISHELL-4 oracle-TextGrid artifact type.

## Validation

### Unit tests (synthetic audio, pure numpy)

`tests/test_silence_aware_gate.py` — 29 tests, all passing. Covers:
- Frame RMS energy (empty, short, silent, speech).
- Adaptive threshold (separates speech from silence, adapts to noise floor, empty input).
- Silence mask and gap finding (no interior gaps in continuous speech, interior gaps detected,
  empty mask).
- Gap truncation (long interior gap truncated, short gap preserved, speech content preserved,
  leading gap anchored at speech edge, no-op when no gaps).
- Top-level gate (shortens track with long gaps, no-op on all-speech/all-silence/short track,
  preserves all speech segments, reference-free).
- Diagnostics (fired flag, n_truncated, total_removed, reference-free).
- Synthetic fixture (has long interior gaps, deterministic).

Run: `python3 -m unittest tests.test_silence_aware_gate -v` → **29/29 OK**.

### Smoke test (synthetic fixture modeling the AISHELL-4 failure mode)

`python3 -m src.silence_aware_gate`:
```
[smoke] synthetic track: 20.5s -> gated 6.5s
[smoke] diagnostics: {'n_gaps': 4, 'n_truncated': 2, 'max_gap_sec': 7.995,
                      'total_silence_removed_sec': 13.39, 'fired': True, 'threshold': 0.0}
```

The synthetic fixture (`make_synthetic_separated_track`) models the AISHELL-4 failure mode: 3
short speech segments (2.0 s, 1.5 s, 2.5 s) separated by long interior silence gaps (8.0 s, 6.0 s),
with a short leading/trailing pause. The gate correctly identifies the 2 long interior gaps,
truncates them to 0.3 s each, and compresses the track from 20.5 s to 6.5 s — removing 13.4 s of
silence that would have triggered the confident-attractor. All 3 speech segments are preserved
intact (verified by cross-correlation in `test_gate_preserves_speech_segments`).

### AISHELL-4 cpWER comparison (NOT RUN — data/Whisper unavailable)

The AISHELL-4 audio (M_R003S02C01.flac/.TextGrid) and the `whisper` / `meeteval` packages were
not available in the worktree, so the cpWER comparison (router v2 + silence gate vs. router v2
baseline vs. always-mixed) could not be run. The driver is implemented
(`run_aishell4_validation`) and mirrors `rq1_aishell4_validation.py` with an added
`always_silence_gate` arm and a `router_v2_silence_gate` arm (same routing rule, but the
separated arm uses the gated track). To run it when data/Whisper are available:

```bash
# Download M_R003S02C01.flac and .TextGrid from HuggingFace AISHELL-4
ffmpeg -i /tmp/M_R003S02C01.flac -ac 1 -ar 16000 /tmp/wt-rq1/M_R003S02C01.wav
pip install openai-whisper meeteval numpy
python3 -m src.silence_aware_gate --aishell4 \
  --textgrid /tmp/M_R003S02C01.TextGrid \
  --wav /tmp/wt-rq1/M_R003S02C01.wav \
  --windows 77
```

## Expected Impact (mechanism-based, since the cpWER run was not possible)

### Why the gate should help

The failure-mode chain is: oracle-TextGrid separation → long interior silence gaps → Whisper
encoder flags silence (`no_speech_prob` high) while decoder is confident (`avg_logprob` near 0)
→ confident-attractor repetition/insertion loop → cpWER > 1.0 on separated tracks → router v2
picks separated at NoOverlap (wrong choice) → router v2 cpWER (1.206) > always-mixed (1.173).

The silence-aware gate breaks this chain at the **acoustic stimulus** step: by truncating the
long silence gaps before decoding, the decoder never sees the long-silence input that triggers the
confident-attractor. The expected effects:

1. **Lower separated cpWER.** The confident-attractor firing rate on separated tracks should drop
   substantially — the silence gaps were the stimulus. The 13.4 s of silence removed in the smoke
   test (out of 20.5 s) is representative: on AISHELL-4 NoOverlap windows, a single speaker's
   track might have 5–25 s of silence in a 30 s window. Removing it should bring separated cpWER
   closer to (or below) the mixed cpWER.
2. **Router v2 cpWER below always-mixed.** Router v2 picks separated at NoOverlap when
   `mixed_segments_count > 5`. If the silence-gated separated arm beats mixed at NoOverlap (which
   it should, since the gate removes the hallucination driver while preserving the per-speaker
   speech), the router's NoOverlap rule becomes correct again, and router v2 + silence gate cpWER
   should fall below always-mixed.
3. **Reduced catastrophic tail rate.** The cpWER > 1.0 tail on separated tracks (driven by
   insertions from the confident-attractor) should shrink, since the gate removes the stimulus.

### Why the gate might NOT fully fix the issue (honest negative-result scope)

1. **Boundary structure, not just duration.** The confident-attractor may be triggered by the
   speech/silence BOUNDARY (the abrupt transition), not just the gap duration. Truncating to 0.3 s
   leaves the boundaries intact; if the boundary is the driver, the gate would not help. The
   causal probe's Mode N (15/26 catastrophic conditions, non-repetition) showed the catastrophe is
   not always a clean repetition — a diffuse hallucination mode exists that may not respond to
   silence removal.
2. **Whisper-tiny's decoder bias.** Whisper-tiny (39M params) is a small model; its decoder may
   hallucinate even on clean per-speaker speech (the AISHELL-4 meeting audio is challenging real
   meeting Chinese). The gate removes the silence stimulus but cannot fix model-capacity limits.
3. **Oracle-TextGrid artifact type.** The gate targets true silence (zeros). A real separator
   (SepFormer) produces residual noise, not true silence — the energy threshold would need the
   noise-floor-relative form (which the gate already uses) but the flatness gate (#11) may be the
   better tool there. The silence-aware gate is specifically an oracle-TextGrid cure.

### Quantitative expectation

Based on the RQ1 stratified results and the mechanism chain:
- If the gate eliminates the confident-attractor on separated tracks, separated cpWER at NoOverlap
  should drop from 1.496 toward the mixed value (1.293) or below (since per-speaker speech is
  cleaner than mixed when the silence is removed).
- Router v2 picks separated at 41/77 windows (NoOverlap with `mixed_segments_count > 5`). If the
  gated separated arm beats mixed at even 60% of those, router v2 + gate cpWER should fall below
  the always-mixed 1.173.
- **H8 is CONDITIONALLY SUPPORTED**: the mechanism analysis predicts the gate should bring router
  v2 cpWER below always-mixed, but this requires the cpWER run to confirm. A negative result
  (gate does not fix the issue) would be a valuable boundary finding pointing toward Gap M2 (real
  separator) and away from oracle-TextGrid separation as the routing paradigm.

## Limitations

1. **No runnable AISHELL-4 evaluation.** The cpWER comparison is expected-impact only; the
   AISHELL-4 audio and Whisper were not available in the worktree. The unit tests and smoke test
   validate the gate's correctness on synthetic audio but not the downstream cpWER effect.
2. **Oracle-TextGrid-specific.** The gate targets true silence (zeros) from oracle-TextGrid
   separation. A real separator's residual noise would need the noise-floor-relative threshold
   (already implemented) but may be better served by the flatness gate (#11).
3. **Whisper-tiny only.** The expected impact is calibrated to Whisper-tiny. A stronger model
   (Whisper-small/base) may have a lower confident-attractor rate and change the gate's marginal
   value.
4. **Single meeting.** Even when run, the evaluation is on M_R003S02C01 only (1 of 20 AISHELL-4
   test meetings). Generalization across meetings requires more sessions.
5. **Parameter sensitivity not swept.** `MAX_GAP_SEC` (0.5 s) and `KEEP_GAP_SEC` (0.3 s) are
   a-priori from conversational-Chinese pause physics, not tuned on CER. A sensitivity sweep
   (like `noise_robust_gate`'s `flat_hi_sweep`) would confirm the gate is not on a knife-edge.

## Reproducibility

- Module: `src/silence_aware_gate.py`
- Tests: `python3 -m unittest tests.test_silence_aware_gate -v` (29/29 OK, pure numpy, no Whisper)
- Smoke: `python3 -m src.silence_aware_gate` (synthetic fixture, ~0.1 s)
- AISHELL-4 driver (needs data + Whisper): `python3 -m src.silence_aware_gate --aishell4 ...`

## What this changes for the project

The silence-aware gate fills the gap the existing gates leave open: **interior** silence-gap
truncation on oracle-TextGrid separated tracks. If the cpWER run confirms the expected impact,
the gate becomes the reference-free cure that unblocks router v2's generalization to AISHELL-4
and any oracle-TextGrid separation paradigm. If the cpWER run is negative, the gate is still a
useful diagnostic tool (the `gate_diagnostics` function quantifies the silence-gap stimulus per
track) and the negative result bounds where reference-free silence cures can work — arguing the
hallucination is boundary-driven, not duration-driven, and pointing toward a real separator
(Gap M2) rather than oracle-TextGrid separation.

The gate is composable with the existing gate selector (`src/gate_selector.py`): it adds a fourth
arm (`silence_gate`) that the selector could route to when the residual is true silence (low
energy, not low flatness). This is left as future work.
