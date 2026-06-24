"""Silence-aware gate: a reference-free cure for the interior-silence confident-attractor (frontier).

Pre-registered research question (issue #892; extends the separation-tax / confident-attractor arc
opened by findings #11/#21 and the AISHELL-4 external validation #881):
  Iteration 1's RQ1 (AISHELL-4 external validation, PR #890) found that router v2 does NOT
  generalize to AISHELL-4: cpWER 1.206 vs always-mixed 1.173. The root cause is structural:
  oracle-TextGrid separation creates per-speaker tracks where one speaker's speech sits at its
  original positions and the rest of the 30 s window is silence. These long INTERIOR silence
  gaps (between speaker turns) trigger Whisper's confident-attractor hallucination (finding #21,
  `causal_hallucination_probe`): the encoder flags silence while the decoder locks into a
  confident repetition/insertion loop, inflating cpWER past 1.0.

  The existing gates do not handle this artifact type:
    - `separation_tax_phase.trim_silence` (#11) and `noise_robust_gate.flatness_trim` crop only
      LEADING/TRAILING silence. Oracle-TextGrid tracks have silence BETWEEN speech segments, so
      the leading/trailing crop leaves the interior gaps intact and the hallucination returns.
    - The compression-ratio guard (#21) is an OUTPUT signal: it detects the catastrophe AFTER
      Whisper has already emitted the repetition loop. It cannot prevent the firing.
    - The noise-robust flatness gate targets broadband NOISE residual, not true silence gaps.

  RQ (this module): Can a reference-free silence-aware gate that detects and truncates INTERIOR
  silence gaps in separated tracks BEFORE ASR decoding reduce the confident-attractor firing
  rate on AISHELL-4 separated tracks, bringing router v2's cpWER below always-mixed?

  H8: Truncating silence gaps longer than 0.5 s down to a 0.3 s keep-span (preserving boundary
      transitions) removes the long-silence stimulus that drives the confident-attractor, so
      router v2 + silence-gate cpWER < always-mixed cpWER on AISHELL-4.
  Useful-either-way: if the gate does NOT fix the issue, that is a negative result bounding where
      reference-free silence cures can work -- it would argue the hallucination is driven by the
      speech/silence BOUNDARY structure (not just gap duration) and point toward a real separator
      (Gap M2) rather than an oracle-TextGrid paradigm.

Design (all reference-free; CER/cpWER is post-hoc evaluation only, never a gate/routing input):
  Frame the track (25 ms / 10 ms, matching `noise_robust_gate`), compute per-frame RMS energy,
  estimate an ADAPTIVE silence threshold from the track's own energy distribution (noise-floor-
  relative: the low percentile of frame energy times a factor, so it adapts to absolute amplitude
  differences across tracks and survives real-separator residual noise). Mark silence frames,
  find contiguous silence gaps, and truncate every gap longer than `max_gap_sec` down to
  `keep_gap_sec` (keeping half at each boundary to avoid abrupt speech-to-speech concatenation).
  The output is a shorter, gap-compressed track fed to ASR. This is the interior-gap analogue of
  the energy-based `trim_silence` -- but it crops EVERY long gap, not just the leading/trailing
  span.

Labels: experimental/frontier; references are external/sanity-check (AISHELL-4) and
synthetic/silver (unit-test fixtures). ASR = Whisper-tiny (only model cached offline). Stable/gold
tables are NOT touched; all outputs go to results/frontier/silence_aware_gate/.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from .config import PROJECT_ROOT

SR = 16000
WIN = 400   # 25 ms @ 16 kHz (matches noise_robust_gate)
HOP = 160   # 10 ms @ 16 kHz
CATASTROPHIC_CER = 1.0
OUT_DIR = PROJECT_ROOT / "results" / "frontier" / "silence_aware_gate"

# A-priori gate parameters (set from the failure-mode physics, never tuned on CER):
#   MAX_GAP_SEC   silence gaps longer than this trigger the confident-attractor and are truncated.
#                 0.5 s is the natural pause ceiling in conversational Chinese; longer pauses in a
#                 separated track are separation artifacts (the other speaker's turn), not speech.
#   KEEP_GAP_SEC  a truncated gap is shortened to at most this, split half/half across the boundary,
#                 so speech segments stay separated by a natural pause (no click/pop on concat).
#   FLOOR_PCT     percentile of frame energy used as the noise floor estimate (low = silence-like).
#   ENERGY_FACTOR a frame is silent if its energy < factor * floor (noise-floor-RELATIVE, like
#                 noise_robust_gate.relenergy_speech_mask; adapts to each track's amplitude).
#   ABS_SILENCE_DB  tracks whose peak energy is below this (relative to int16 full-scale) are
#                   treated as all-silence and returned unchanged (the AISHELL-4 driver already
#                   skips these; the guard makes the gate safe standalone).
MAX_GAP_SEC = 0.5
KEEP_GAP_SEC = 0.3
FLOOR_PCT = 20.0
ENERGY_FACTOR = 3.0
ABS_SILENCE_FLOOR = 1e-6  # ~-120 dBFS; below this the track is numerically silent


# ======================================================================================
# Pure primitives (no Whisper, no audio I/O) -- unit tested in tests/test_silence_aware_gate.py
# ======================================================================================
def frame_signal(x: np.ndarray, win: int = WIN, hop: int = HOP) -> np.ndarray:
    """Split a 1-D signal into overlapping frames -> (n_frames, win). Returns (0, win) if the
    signal is shorter than one frame. Mirrors `noise_robust_gate.frame_signal`."""
    x = np.asarray(x, dtype=np.float32)
    if x.size < win:
        return np.zeros((0, win), dtype=np.float32)
    n = 1 + (x.size - win) // hop
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]


def frame_rms_energy(frames: np.ndarray) -> np.ndarray:
    """Per-frame RMS energy (mean square). Empty input -> empty output."""
    if frames.shape[0] == 0:
        return np.zeros((0,), dtype=np.float64)
    return np.mean(np.asarray(frames, dtype=np.float64) ** 2, axis=1)


def adaptive_energy_threshold(
    energy: np.ndarray, floor_pct: float = FLOOR_PCT, factor: float = ENERGY_FACTOR
) -> float:
    """Noise-floor-RELATIVE silence threshold. The floor is the low-percentile frame energy (the
    silence-like frames); a frame is silent if its energy is below ``factor * floor``. This adapts
    to each track's absolute amplitude (unlike an absolute dB threshold) and survives real-
    separator residual noise. Returns 0.0 for an empty energy vector."""
    e = np.asarray(energy, dtype=np.float64)
    e = e[np.isfinite(e)]
    if e.size == 0:
        return 0.0
    floor = float(np.percentile(e, floor_pct)) + 1e-12
    return float(factor * floor)


def silence_mask(energy: np.ndarray, threshold: float) -> np.ndarray:
    """Boolean mask: True where the frame is silent (energy <= threshold)."""
    return np.asarray(energy, dtype=np.float64) <= threshold


def find_silence_gaps(
    mask: np.ndarray, hop: int = HOP, win: int = WIN, sr: int = SR
) -> list[tuple[int, int, float]]:
    """Locate contiguous silence runs and return them as (start_sample, end_sample, duration_sec)
    spanning the full silent region. ``mask`` is the per-frame silence flag (True = silent). A gap
    covers from the first sample of the first silent frame to the last sample of the last silent
    frame. Returns [] when there are no silent frames."""
    m = np.asarray(mask, dtype=bool)
    if m.size == 0 or not m.any():
        return []
    gaps: list[tuple[int, int, float]] = []
    # find run boundaries: indices where the mask transitions
    diff = np.diff(m.astype(np.int8), prepend=0, append=0)
    starts = np.nonzero(diff == 1)[0]
    ends = np.nonzero(diff == -1)[0]  # exclusive frame index
    for sf, ef in zip(starts, ends):
        if ef <= sf:
            continue
        # frame sf..ef-1 are silent; map to sample span (frame start to frame end)
        s_sample = sf * hop
        e_sample = min((ef - 1) * hop + win, sr * 1000)  # bound by a large ceiling; caller clips
        duration = (e_sample - s_sample) / float(sr)
        gaps.append((int(s_sample), int(e_sample), float(duration)))
    return gaps


def truncate_gaps(
    x: np.ndarray,
    gaps: list[tuple[int, int, float]],
    sr: int = SR,
    max_gap_sec: float = MAX_GAP_SEC,
    keep_gap_sec: float = KEEP_GAP_SEC,
) -> np.ndarray:
    """Return a copy of ``x`` with every silence gap longer than ``max_gap_sec`` shortened to at
    most ``keep_gap_sec``. The keep-span is split half/half across the gap boundary so speech
    segments stay separated by a natural pause (no abrupt speech-to-speech concatenation). Gaps
    shorter than ``max_gap_sec`` are left intact. The output may be shorter than the input.

    A gap that starts at sample 0 (leading silence) or ends at the track end (trailing silence) is
    truncated symmetrically: the keep-span is anchored at the outer edge so the inner speech
    boundary keeps its natural pause. This matches how `trim_silence` handles edges but applies
    the same logic to interior gaps."""
    x = np.asarray(x, dtype=np.float32)
    if x.size == 0 or not gaps:
        return x
    n = x.size
    keep_samples = int(round(keep_gap_sec * sr))
    max_samples = int(round(max_gap_sec * sr))
    # build the list of (keep_start, keep_end) sample spans to PRESERVE within each long gap
    edits: list[tuple[int, int, int, int]] = []  # (gap_start, gap_end, keep_start, keep_end)
    for gs, ge, _dur in gaps:
        gap_len = ge - gs
        if gap_len <= max_samples or gap_len <= keep_samples:
            continue
        half = keep_samples // 2
        if gs == 0:
            # leading gap: anchor keep at the speech-facing edge (end of gap)
            ks, ke = ge - keep_samples, ge
        elif ge >= n:
            # trailing gap: anchor keep at the speech-facing edge (start of gap)
            ks, ke = gs, gs + keep_samples
        else:
            # interior gap: split half/half across the boundary
            ks, ke = gs, gs + half
            # second keep-span at the end of the gap is handled by emitting two edits
            edits.append((gs, ge, ks, ke))
            edits.append((gs, ge, ge - half, ge))
            continue
        edits.append((gs, ge, ks, ke))
    if not edits:
        return x
    # Build the output by concatenating: for each long gap, drop the samples between the two
    # keep-spans. We process gaps in order and accumulate the kept regions.
    # Collect (start, end) sample ranges to KEEP, then concatenate.
    keep_ranges: list[tuple[int, int]] = [(0, n)]
    for gs, ge, ks, ke in edits:
        # within gap [gs, ge), keep [ks, ke); drop [gs, ks) and [ke, ge)
        new_ranges: list[tuple[int, int]] = []
        for rs, re_ in keep_ranges:
            # drop the portions of this keep-range that fall inside the gap's drop zones
            if re_ <= gs or rs >= ge:
                new_ranges.append((rs, re_))
                continue
            # split the keep-range around the gap
            if rs < gs:
                new_ranges.append((rs, min(gs, re_)))
            if re_ > ge:
                new_ranges.append((max(ge, rs), re_))
            # inside the gap, keep only [ks, ke)
            if ks < ke and ks < re_ and ke > rs:
                new_ranges.append((max(ks, rs), min(ke, re_)))
        # merge contiguous ranges
        keep_ranges = _merge_ranges(new_ranges)
    if not keep_ranges:
        return x
    parts = [x[s:e] for s, e in keep_ranges if e > s]
    if not parts:
        return x
    return np.concatenate(parts).astype(np.float32)


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping/contiguous (start, end) sample ranges into a sorted, disjoint list."""
    if not ranges:
        return []
    rs = sorted((s, e) for s, e in ranges if e > s)
    out = [rs[0]]
    for s, e in rs[1:]:
        ls, le = out[-1]
        if s <= le:
            out[-1] = (ls, max(le, e))
        else:
            out.append((s, e))
    return out


def silence_aware_gate(
    track: np.ndarray,
    sr: int = SR,
    win: int = WIN,
    hop: int = HOP,
    max_gap_sec: float = MAX_GAP_SEC,
    keep_gap_sec: float = KEEP_GAP_SEC,
    floor_pct: float = FLOOR_PCT,
    energy_factor: float = ENERGY_FACTOR,
) -> np.ndarray:
    """Top-level reference-free silence-aware gate. Detects interior (and leading/trailing)
    silence gaps via noise-floor-relative RMS energy VAD and truncates every gap longer than
    ``max_gap_sec`` down to ``keep_gap_sec``. Returns the gap-compressed track (may be shorter
    than the input). Falls back to the unchanged track when there is nothing to crop (all-speech,
    all-silence, or no long gaps)."""
    x = np.asarray(track, dtype=np.float32)
    if x.size < win:
        return x
    # all-silence guard: no speech to preserve, return unchanged (driver skips these anyway)
    peak = float(np.max(np.abs(x)))
    if peak < ABS_SILENCE_FLOOR:
        return x
    frames = frame_signal(x, win, hop)
    energy = frame_rms_energy(frames)
    if energy.size == 0:
        return x
    threshold = adaptive_energy_threshold(energy, floor_pct, energy_factor)
    # if the threshold is at/above the peak energy, the whole track reads as silent -> return as-is
    if threshold >= float(np.max(energy)):
        return x
    mask = silence_mask(energy, threshold)
    if not mask.any():
        return x  # no silence -> nothing to truncate
    gaps = find_silence_gaps(mask, hop, win, sr)
    # clip gap end-samples to the actual signal length
    n = x.size
    gaps = [(gs, min(ge, n), dur) for gs, ge, dur in gaps]
    return truncate_gaps(x, gaps, sr, max_gap_sec, keep_gap_sec)


# ======================================================================================
# Diagnostics + aggregation (pure; reference-free signals, CER only scores outcomes post-hoc)
# ======================================================================================
def gate_diagnostics(
    track: np.ndarray,
    sr: int = SR,
    win: int = WIN,
    hop: int = HOP,
    max_gap_sec: float = MAX_GAP_SEC,
    keep_gap_sec: float = KEEP_GAP_SEC,
    floor_pct: float = FLOOR_PCT,
    energy_factor: float = ENERGY_FACTOR,
) -> dict[str, Any]:
    """Reference-free per-track diagnostics: how many silence gaps were found, how many were
    truncated, the longest gap, and the total silence removed. ``fired`` is True iff the gate
    would modify the track (at least one gap exceeds ``max_gap_sec``). No CER / no reference."""
    x = np.asarray(track, dtype=np.float32)
    n = x.size
    if n < win:
        return {"n_gaps": 0, "n_truncated": 0, "max_gap_sec": 0.0,
                "total_silence_removed_sec": 0.0, "fired": False, "threshold": 0.0}
    peak = float(np.max(np.abs(x)))
    if peak < ABS_SILENCE_FLOOR:
        return {"n_gaps": 0, "n_truncated": 0, "max_gap_sec": 0.0,
                "total_silence_removed_sec": 0.0, "fired": False, "threshold": 0.0}
    frames = frame_signal(x, win, hop)
    energy = frame_rms_energy(frames)
    threshold = adaptive_energy_threshold(energy, floor_pct, energy_factor)
    if threshold >= float(np.max(energy)):
        return {"n_gaps": 0, "n_truncated": 0, "max_gap_sec": 0.0,
                "total_silence_removed_sec": 0.0, "fired": False, "threshold": threshold}
    mask = silence_mask(energy, threshold)
    gaps = find_silence_gaps(mask, hop, win, sr)
    gaps = [(gs, min(ge, n), dur) for gs, ge, dur in gaps]
    if not gaps:
        return {"n_gaps": 0, "n_truncated": 0, "max_gap_sec": 0.0,
                "total_silence_removed_sec": 0.0, "fired": False, "threshold": threshold}
    max_samples = int(round(max_gap_sec * sr))
    keep_samples = int(round(keep_gap_sec * sr))
    n_trunc = 0
    removed = 0.0
    max_gap = 0.0
    for gs, ge, dur in gaps:
        gap_len = ge - gs
        max_gap = max(max_gap, dur)
        if gap_len > max_samples and gap_len > keep_samples:
            n_trunc += 1
            removed += (gap_len - keep_samples) / float(sr)
    return {
        "n_gaps": len(gaps),
        "n_truncated": n_trunc,
        "max_gap_sec": round(max_gap, 6),
        "total_silence_removed_sec": round(removed, 6),
        "fired": n_trunc > 0,
        "threshold": round(threshold, 10),
    }


def selective_silence_policy(
    rows: list[dict[str, Any]],
    threshold: float = 2.4,
) -> dict[str, Any]:
    """Reference-free SELECTIVE gating, mirroring `noise_robust_gate.selective_gate_policy`. The
    silence gate helps separated tracks with long interior gaps but is a no-op on clean tracks, so
    apply it only when the raw separated tracks look degenerate: max(compression_ratio) > threshold.
    Compares always_sep / always_silence_gate / guard_gated / oracle(min). Routing uses ONLY the
    reference-free CR signal; CER scores the outcome and is never a routing input."""
    sep, gate, guard, oracle = [], [], [], []
    fired = 0
    for r in rows:
        if r.get("cer_sep") in (None, "") or r.get("cer_silence_gate") in (None, ""):
            continue
        cs, cg = float(r["cer_sep"]), float(r["cer_silence_gate"])
        cr = max(float(r.get("cr_sep1", 0.0)), float(r.get("cr_sep2", 0.0)))
        use_gate = cr > threshold
        fired += int(use_gate)
        sep.append(cs)
        gate.append(cg)
        guard.append(cg if use_gate else cs)
        oracle.append(min(cs, cg))
    n = len(sep)

    def m(x: list[float]) -> float:
        return round(sum(x) / len(x), 6) if x else 0.0

    def tail(x: list[float]) -> float:
        return round(sum(1 for c in x if c > CATASTROPHIC_CER) / len(x), 6) if x else 0.0

    means = {"always_sep": m(sep), "always_silence_gate": m(gate),
             "guard_gated": m(guard), "oracle": m(oracle)}
    return {
        "n": n,
        "threshold": threshold,
        "guard_fired_frac": round(fired / n, 6) if n else 0.0,
        "mean_cer": means,
        "tail_rate": {"always_sep": tail(sep), "always_silence_gate": tail(gate),
                      "guard_gated": tail(guard), "oracle": tail(oracle)},
        "regret_vs_oracle": {k: round(v - means["oracle"], 6) for k, v in means.items() if k != "oracle"},
    }


# ======================================================================================
# Synthetic fixture (pure; for the unit test and the no-data expected-impact illustration)
# ======================================================================================
def make_synthetic_separated_track(
    sr: int = SR,
    speech_durations: list[float] | None = None,
    silence_durations: list[float] | None = None,
    speech_freq: float = 220.0,
    speech_amp: float = 0.3,
) -> np.ndarray:
    """Build a synthetic oracle-TextGrid-style separated track: alternating speech bursts (tone)
    and silence gaps. Defaults model the AISHELL-4 failure mode: 3 short speech segments separated
    by long interior silence gaps (the other speakers' turns). Deterministic, pure-numpy."""
    if speech_durations is None:
        speech_durations = [2.0, 1.5, 2.5]
    if silence_durations is None:
        silence_durations = [0.2, 8.0, 6.0, 0.3]
    parts: list[np.ndarray] = []
    t = np.arange(int(silence_durations[0] * sr)) / float(sr)
    parts.append(np.zeros_like(t, dtype=np.float32))
    for i, sd in enumerate(speech_durations):
        n = int(sd * sr)
        tt = np.arange(n) / float(sr)
        # voiced-like tone + slight AM to look speech-like in energy
        wave = speech_amp * np.sin(2 * np.pi * speech_freq * tt) * (0.7 + 0.3 * np.sin(2 * np.pi * 4 * tt))
        parts.append(wave.astype(np.float32))
        if i + 1 < len(silence_durations):
            ns = int(silence_durations[i + 1] * sr)
            parts.append(np.zeros(ns, dtype=np.float32))
    return np.concatenate(parts).astype(np.float32)


# ======================================================================================
# Whisper-dependent driver (optional; only runs when whisper + AISHELL-4 data are available)
# ======================================================================================
def run_aishell4_validation(
    out_dir: Path,
    textgrid_path: Path,
    wav_path: Path,
    window_sec: float = 30.0,
    num_windows: int = 77,
    whisper_model: str = "tiny",
    language: str = "zh",
) -> dict[str, Any]:
    """Re-run the AISHELL-4 validation with the silence-aware gate applied to separated tracks.
    Mirrors `results/external_sanity_check/aishell4/rq1_aishell4_validation.py` but adds a
    ``silence_gate`` arm: each separated speaker track is passed through `silence_aware_gate`
    before Whisper decoding. Reports cpWER for always-mixed / always-separated /
    always-silence-gate / router-v2 / router-v2+silence-gate. Reference-free; cpWER is post-hoc."""
    import whisper

    out_dir.mkdir(parents=True, exist_ok=True)
    # Reuse the RQ1 validation helpers (parse_textgrid, create_speaker_track, compute_cpwer, etc.)
    import sys
    rq1_path = PROJECT_ROOT / "results" / "external_sanity_check" / "aishell4"
    if str(rq1_path) not in sys.path:
        sys.path.insert(0, str(rq1_path))
    from rq1_aishell4_validation import (  # type: ignore[import-not-found]
        parse_textgrid, read_wav, extract_window, create_speaker_track,
        compute_overlap_ratio, overlap_ratio_to_level, choose_method_v2,
        compute_cpwer, compute_orcwer, write_wav,
    )

    sr = 16000
    model = whisper.load_model(whisper_model)
    tiers = parse_textgrid(textgrid_path)
    full_audio, framerate = read_wav(wav_path)
    print(f"[silence-gate] meeting audio {len(full_audio)/framerate:.1f}s, "
          f"speakers={list(tiers.keys())}", flush=True)

    def transcribe(audio: np.ndarray) -> dict[str, Any]:
        import time
        tmp = out_dir / "_tmp_asr_input.wav"
        write_wav(tmp, audio, framerate)
        t0 = time.time()
        result = model.transcribe(str(tmp), language=language, verbose=False)
        segs = [{"start": s["start"], "end": s["end"], "text": s["text"].strip()}
                for s in result.get("segments", [])]
        cr_vals = [float(s.get("compression_ratio", 0.0) or 0.0) for s in result.get("segments", [])]
        return {"text": result["text"].strip(), "segments": segs,
                "runtime_sec": round(time.time() - t0, 3),
                "max_compression_ratio": max(cr_vals) if cr_vals else 0.0}

    rows: list[dict[str, Any]] = []
    for i in range(num_windows):
        ws = i * window_sec
        we = ws + window_sec
        if we > len(full_audio) / framerate:
            break
        active: dict[str, list[tuple[float, float, str]]] = {}
        for spk, intervals in tiers.items():
            wi = [(s, e, t) for s, e, t in intervals if s < we and e > ws]
            if wi:
                active[spk] = wi
        if not active:
            continue
        overlap_ratio = compute_overlap_ratio(ws, window_sec, active)
        overlap_level = overlap_ratio_to_level(overlap_ratio)
        ref_speakers = {spk: "".join(t for s, e, t in iv if s < we and e > ws)
                        for spk, iv in active.items()}
        mixed_audio = extract_window(full_audio, framerate, ws, window_sec)
        tracks = {spk: create_speaker_track(full_audio, framerate, ws, window_sec, iv)
                  for spk, iv in active.items()}

        mixed_res = transcribe(mixed_audio)
        mixed_text = mixed_res["text"]
        mixed_len = len(mixed_text)
        mixed_segs = len(mixed_res["segments"])
        mixed_runtime = mixed_res["runtime_sec"]

        sep_texts: dict[str, str] = {}
        sep_runtime = 0.0
        sep_len = 0
        cr_sep: list[float] = []
        for spk, tr in tracks.items():
            if np.max(np.abs(tr)) < 100:
                continue
            r = transcribe(tr)
            sep_texts[spk] = r["text"]
            sep_runtime += r["runtime_sec"]
            sep_len += len(r["text"])
            cr_sep.append(r["max_compression_ratio"])

        gate_texts: dict[str, str] = {}
        gate_runtime = 0.0
        gate_len = 0
        gate_diag: list[dict[str, Any]] = []
        for spk, tr in tracks.items():
            if np.max(np.abs(tr)) < 100:
                continue
            dg = gate_diagnostics(tr, sr=sr)
            gate_diag.append(dg)
            gtr = silence_aware_gate(tr, sr=sr)
            r = transcribe(gtr)
            gate_texts[spk] = r["text"]
            gate_runtime += r["runtime_sec"]
            gate_len += len(r["text"])

        cpwer_sep = compute_cpwer(ref_speakers, sep_texts)
        cpwer_gate = compute_cpwer(ref_speakers, gate_texts)
        orcwer_mixed = compute_orcwer(ref_speakers, mixed_text)
        runtime_ratio = round(sep_runtime / mixed_runtime, 3) if mixed_runtime > 0 else 0.0

        router_method, router_rule = choose_method_v2(
            overlap_level=overlap_level, mixed_len=mixed_len, separated_len=sep_len,
            cleaned_len=0, duplicate_removed_count=0, runtime_ratio=runtime_ratio,
            cleaned_exists=False, mixed_segments_count=mixed_segs,
        )
        # router v2 + silence gate: same routing rule, but the separated arm uses the gated track
        router_gate_cpwer = cpwer_gate["error_rate"] if router_method == "separated" else orcwer_mixed["error_rate"]
        router_cpwer = cpwer_sep["error_rate"] if router_method == "separated" else orcwer_mixed["error_rate"]

        row = {
            "window_id": i, "overlap_ratio": round(overlap_ratio, 4),
            "overlap_level": overlap_level,
            "always_mixed_cpwer": orcwer_mixed["error_rate"],
            "always_separated_cpwer": cpwer_sep["error_rate"],
            "always_silence_gate_cpwer": cpwer_gate["error_rate"],
            "router_v2_cpwer": router_cpwer,
            "router_v2_silence_gate_cpwer": router_gate_cpwer,
            "oracle_best_cpwer": min(orcwer_mixed["error_rate"], cpwer_sep["error_rate"]),
            "cr_sep_max": max(cr_sep) if cr_sep else 0.0,
            "gate_fired": int(any(d["fired"] for d in gate_diag)),
            "gate_n_truncated": sum(d["n_truncated"] for d in gate_diag),
            "gate_total_removed_sec": round(sum(d["total_silence_removed_sec"] for d in gate_diag), 4),
            "router_v2_method": router_method,
        }
        rows.append(row)
        print(f"  [w{i:02d}] ov={overlap_ratio:.3f} mixed={orcwer_mixed['error_rate']:.3f} "
              f"sep={cpwer_sep['error_rate']:.3f} gate={cpwer_gate['error_rate']:.3f} "
              f"router={router_cpwer:.3f} router+gate={router_gate_cpwer:.3f} "
              f"fired={row['gate_fired']} removed={row['gate_total_removed_sec']}s", flush=True)

    n = len(rows)
    summary = {
        "label": "experimental/frontier",
        "n_windows": n,
        "always_mixed_cpwer": round(sum(r["always_mixed_cpwer"] for r in rows) / n, 6) if n else 0.0,
        "always_separated_cpwer": round(sum(r["always_separated_cpwer"] for r in rows) / n, 6) if n else 0.0,
        "always_silence_gate_cpwer": round(sum(r["always_silence_gate_cpwer"] for r in rows) / n, 6) if n else 0.0,
        "router_v2_cpwer": round(sum(r["router_v2_cpwer"] for r in rows) / n, 6) if n else 0.0,
        "router_v2_silence_gate_cpwer": round(sum(r["router_v2_silence_gate_cpwer"] for r in rows) / n, 6) if n else 0.0,
        "oracle_best_cpwer": round(sum(r["oracle_best_cpwer"] for r in rows) / n, 6) if n else 0.0,
        "gate_fire_rate": round(sum(r["gate_fired"] for r in rows) / n, 6) if n else 0.0,
        "windows": rows,
    }
    (out_dir / "aishell4_silence_gate_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[silence-gate] wrote aishell4_silence_gate_results.json (n={n})", flush=True)
    if n:
        print(f"[silence-gate] always_mixed={summary['always_mixed_cpwer']} "
              f"router_v2={summary['router_v2_cpwer']} "
              f"router_v2+gate={summary['router_v2_silence_gate_cpwer']}", flush=True)
    return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Silence-aware gate experiment (frontier, issue #892).")
    p.add_argument("--aishell4", action="store_true",
                   help="Run the AISHELL-4 validation with the silence gate (needs whisper + data).")
    p.add_argument("--textgrid", type=str, default="/tmp/M_R003S02C01.TextGrid")
    p.add_argument("--wav", type=str, default="/tmp/wt-rq1/M_R003S02C01.wav")
    p.add_argument("--windows", type=int, default=77)
    p.add_argument("--out-dir", type=str, default=str(OUT_DIR))
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if args.aishell4:
        run_aishell4_validation(out_dir, Path(args.textgrid), Path(args.wav), num_windows=args.windows)
    else:
        # smoke: run the gate on the synthetic fixture and print diagnostics
        track = make_synthetic_separated_track()
        gated = silence_aware_gate(track)
        diag = gate_diagnostics(track)
        print(f"[smoke] synthetic track: {len(track)/SR:.1f}s -> gated {len(gated)/SR:.1f}s")
        print(f"[smoke] diagnostics: {diag}")


if __name__ == "__main__":
    main()
