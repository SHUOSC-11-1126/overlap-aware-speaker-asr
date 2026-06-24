"""Tests for the silence-aware gate (experimental/frontier, issue #892).

Pin the PURE helpers: frame RMS energy, noise-floor-relative adaptive threshold, silence mask,
contiguous-gap finding, gap truncation (interior + leading + trailing), the top-level gate on a
synthetic oracle-TextGrid-style separated track, and the reference-free diagnostics. No Whisper /
no audio I/O needed (the synthetic fixture is built from pure numpy).
"""
from __future__ import annotations

import unittest

import numpy as np

from src.silence_aware_gate import (
    ABS_SILENCE_FLOOR,
    KEEP_GAP_SEC,
    MAX_GAP_SEC,
    SR,
    adaptive_energy_threshold,
    find_silence_gaps,
    frame_rms_energy,
    frame_signal,
    gate_diagnostics,
    make_synthetic_separated_track,
    silence_aware_gate,
    silence_mask,
    truncate_gaps,
)


def _speech_burst(sr: int, dur_sec: float, freq: float = 220.0, amp: float = 0.3,
                  am: bool = True) -> np.ndarray:
    """A voiced-like tone burst. ``am=True`` adds slight amplitude modulation (looks speech-like
    in RMS energy); ``am=False`` is a pure tone (use when testing that continuous speech produces
    NO silence gaps -- the AM dips can fall below the relative threshold)."""
    n = int(dur_sec * sr)
    t = np.arange(n) / float(sr)
    env = (0.7 + 0.3 * np.sin(2 * np.pi * 4 * t)) if am else np.ones(n, dtype=np.float64)
    return (amp * np.sin(2 * np.pi * freq * t) * env).astype(np.float32)


def _track(parts: list[np.ndarray]) -> np.ndarray:
    return np.concatenate(parts).astype(np.float32) if parts else np.zeros(0, dtype=np.float32)


class TestFrameEnergy(unittest.TestCase):
    def test_empty_signal_returns_empty_frames(self) -> None:
        self.assertEqual(frame_signal(np.zeros(0, dtype=np.float32)).shape[0], 0)

    def test_short_signal_returns_empty_frames(self) -> None:
        # shorter than one frame -> (0, win)
        self.assertEqual(frame_signal(np.zeros(100, dtype=np.float32)).shape[0], 0)

    def test_rms_energy_silent_frames_near_zero(self) -> None:
        frames = frame_signal(np.zeros(SR, dtype=np.float32))
        e = frame_rms_energy(frames)
        self.assertTrue(np.all(e <= 1e-12))

    def test_rms_energy_speech_frames_above_silence(self) -> None:
        x = _speech_burst(SR, 1.0)
        frames = frame_signal(x)
        e = frame_rms_energy(frames)
        self.assertGreater(float(np.max(e)), 1e-4)
        self.assertGreater(float(np.mean(e)), float(np.percentile(e, 5)))


class TestAdaptiveThreshold(unittest.TestCase):
    def test_threshold_separates_speech_from_silence(self) -> None:
        # speech bursts + silence: floor (low pct) is silence energy, threshold = factor*floor
        x = _track([_speech_burst(SR, 1.0), np.zeros(int(2 * SR), dtype=np.float32),
                    _speech_burst(SR, 1.0)])
        frames = frame_signal(x)
        e = frame_rms_energy(frames)
        thr = adaptive_energy_threshold(e, floor_pct=20.0, factor=3.0)
        # speech energy well above threshold, silence energy well below
        speech_e = float(np.max(e))
        silence_e = float(np.min(e))
        self.assertGreater(thr, silence_e)
        self.assertLess(thr, speech_e)

    def test_threshold_empty_returns_zero(self) -> None:
        self.assertEqual(adaptive_energy_threshold(np.zeros(0)), 0.0)

    def test_threshold_adapts_to_amplitude(self) -> None:
        # same shape, 10x amplitude -> threshold scales ~10x (relative, not absolute).
        # Use a low-amplitude NOISE FLOOR (not true zeros) so the floor tracks the noise level:
        # the relative threshold adapts to the noise floor, not the speech peak.
        rng = np.random.default_rng(0)
        floor_base = (rng.standard_normal(int(SR)) * 0.01).astype(np.float32)
        floor_loud = (rng.standard_normal(int(SR)) * 0.10).astype(np.float32)
        base = _track([_speech_burst(SR, 0.5, amp=0.1), floor_base])
        loud = _track([_speech_burst(SR, 0.5, amp=1.0), floor_loud])
        thr_base = adaptive_energy_threshold(frame_rms_energy(frame_signal(base)))
        thr_loud = adaptive_energy_threshold(frame_rms_energy(frame_signal(loud)))
        self.assertGreater(thr_loud, thr_base * 5)  # roughly scales with the noise floor


class TestSilenceMaskAndGaps(unittest.TestCase):
    def test_mask_marks_silence_true(self) -> None:
        e = np.array([0.0, 0.0, 1.0, 1.0, 0.0], dtype=np.float64)
        m = silence_mask(e, threshold=0.5)
        self.assertTrue(m[0] and m[1] and m[4])
        self.assertFalse(m[2] or m[3])

    def test_find_gaps_no_silence(self) -> None:
        # a continuous PURE-TONE speech burst (no AM dips) padded with short silence to establish
        # a low noise floor. The relative threshold sits below the tone energy, so the speech
        # region has NO interior silence gaps (only the leading/trailing padding gaps).
        x = _track([np.zeros(int(0.2 * SR), dtype=np.float32),
                    _speech_burst(SR, 1.0, am=False),
                    np.zeros(int(0.2 * SR), dtype=np.float32)])
        frames = frame_signal(x)
        e = frame_rms_energy(frames)
        thr = adaptive_energy_threshold(e)
        m = silence_mask(e, thr)
        gaps = find_silence_gaps(m, sr=SR)
        # the speech region spans samples [0.2s, 1.2s); no gap should fall strictly inside it
        speech_start = int(0.2 * SR)
        speech_end = int(1.2 * SR)
        for gs, ge, dur in gaps:
            interior_start = max(gs, speech_start)
            interior_end = min(ge, speech_end)
            interior = max(0, interior_end - interior_start) / float(SR)
            self.assertLess(interior, 0.1, f"interior gap of {interior:.3f}s within speech")

    def test_find_gaps_interior_silence(self) -> None:
        # 1s speech, 3s silence, 1s speech -> one interior gap ~3s
        x = _track([_speech_burst(SR, 1.0), np.zeros(int(3 * SR), dtype=np.float32),
                    _speech_burst(SR, 1.0)])
        frames = frame_signal(x)
        e = frame_rms_energy(frames)
        thr = adaptive_energy_threshold(e)
        m = silence_mask(e, thr)
        gaps = find_silence_gaps(m, sr=SR)
        # at least one gap near 3s (interior); the leading/trailing edges may also be flagged
        self.assertGreaterEqual(len(gaps), 1)
        max_gap = max(dur for _, _, dur in gaps)
        self.assertGreater(max_gap, 2.5)  # the 3s interior gap

    def test_find_gaps_empty_mask(self) -> None:
        self.assertEqual(find_silence_gaps(np.zeros(0, dtype=bool), sr=SR), [])
        self.assertEqual(find_silence_gaps(np.array([False, False, False]), sr=SR), [])


class TestTruncateGaps(unittest.TestCase):
    def test_long_interior_gap_truncated(self) -> None:
        # 1s speech, 5s silence, 1s speech; truncate gaps > 0.5s to 0.3s
        sr = SR
        x = _track([_speech_burst(sr, 1.0), np.zeros(int(5 * sr), dtype=np.float32),
                    _speech_burst(sr, 1.0)])
        frames = frame_signal(x)
        e = frame_rms_energy(frames)
        thr = adaptive_energy_threshold(e)
        m = silence_mask(e, thr)
        gaps = find_silence_gaps(m, sr=sr)
        gated = truncate_gaps(x, gaps, sr=sr, max_gap_sec=0.5, keep_gap_sec=0.3)
        # original 7s; removed ~4.7s of the 5s gap -> ~2.3s
        self.assertLess(len(gated), len(x))
        self.assertGreater(len(gated), int(1.8 * sr))  # at least the 2s of speech + 0.3s keep
        self.assertLess(len(gated), int(3.0 * sr))     # well below the original 7s

    def test_short_gap_preserved(self) -> None:
        # 1s speech, 0.2s silence (below max_gap), 1s speech -> unchanged
        sr = SR
        x = _track([_speech_burst(sr, 1.0), np.zeros(int(0.2 * sr), dtype=np.float32),
                    _speech_burst(sr, 1.0)])
        frames = frame_signal(x)
        e = frame_rms_energy(frames)
        thr = adaptive_energy_threshold(e)
        m = silence_mask(e, thr)
        gaps = find_silence_gaps(m, sr=sr)
        gated = truncate_gaps(x, gaps, sr=sr, max_gap_sec=0.5, keep_gap_sec=0.3)
        self.assertEqual(len(gated), len(x))

    def test_speech_content_preserved(self) -> None:
        # the speech bursts must survive truncation intact (same samples)
        sr = SR
        s1 = _speech_burst(sr, 1.0)
        s2 = _speech_burst(sr, 1.0, freq=330.0)
        x = _track([s1, np.zeros(int(5 * sr), dtype=np.float32), s2])
        frames = frame_signal(x)
        e = frame_rms_energy(frames)
        thr = adaptive_energy_threshold(e)
        m = silence_mask(e, thr)
        gaps = find_silence_gaps(m, sr=sr)
        gated = truncate_gaps(x, gaps, sr=sr, max_gap_sec=0.5, keep_gap_sec=0.3)
        # the first speech burst is at the start (unchanged); the second is somewhere after
        self.assertTrue(np.array_equal(gated[:len(s1)], s1))
        # the second burst should appear near the end (after the shortened gap)
        self.assertTrue(np.array_equal(gated[-len(s2):], s2))

    def test_no_gaps_returns_unchanged(self) -> None:
        x = _speech_burst(SR, 1.0)
        self.assertIs(truncate_gaps(x, [], sr=SR), x)

    def test_leading_gap_anchored_at_speech_edge(self) -> None:
        # 5s silence, 1s speech: leading gap truncated, keep anchored at speech-facing edge
        sr = SR
        x = _track([np.zeros(int(5 * sr), dtype=np.float32), _speech_burst(sr, 1.0)])
        frames = frame_signal(x)
        e = frame_rms_energy(frames)
        thr = adaptive_energy_threshold(e)
        m = silence_mask(e, thr)
        gaps = find_silence_gaps(m, sr=sr)
        gated = truncate_gaps(x, gaps, sr=sr, max_gap_sec=0.5, keep_gap_sec=0.3)
        # the speech burst (last 1s) must be preserved at the tail
        s = _speech_burst(sr, 1.0)
        self.assertTrue(np.array_equal(gated[-len(s):], s))
        # and the leading silence is shortened to ~0.3s
        self.assertLess(len(gated), int(2 * sr))


class TestSilenceAwareGate(unittest.TestCase):
    def test_gate_shortens_track_with_long_gaps(self) -> None:
        x = make_synthetic_separated_track()  # has 8s + 6s interior gaps
        gated = silence_aware_gate(x)
        self.assertLess(len(gated), len(x))
        # should remove a substantial fraction (the 8s + 6s gaps -> ~0.3s each)
        removed_sec = (len(x) - len(gated)) / float(SR)
        self.assertGreater(removed_sec, 10.0)  # at least 10s of silence removed

    def test_gate_noop_on_all_speech(self) -> None:
        x = _speech_burst(SR, 2.0)
        gated = silence_aware_gate(x)
        self.assertEqual(len(gated), len(x))

    def test_gate_noop_on_all_silence(self) -> None:
        x = np.zeros(int(5 * SR), dtype=np.float32)
        gated = silence_aware_gate(x)
        self.assertEqual(len(gated), len(x))

    def test_gate_noop_on_short_track(self) -> None:
        x = _speech_burst(SR, 0.01)  # shorter than one frame
        gated = silence_aware_gate(x)
        self.assertIs(gated, x)

    def test_gate_preserves_speech_segments(self) -> None:
        # build a track with 3 distinct speech bursts; after gating all 3 must be present
        sr = SR
        s1 = _speech_burst(sr, 0.5, freq=200.0)
        s2 = _speech_burst(sr, 0.5, freq=300.0)
        s3 = _speech_burst(sr, 0.5, freq=400.0)
        x = _track([s1, np.zeros(int(4 * sr), dtype=np.float32),
                    s2, np.zeros(int(3 * sr), dtype=np.float32), s3])
        gated = silence_aware_gate(x, sr=sr, max_gap_sec=0.5, keep_gap_sec=0.3)
        # each burst's first sample pattern should appear in the gated output
        for burst in (s1, s2, s3):
            # find the burst in the gated signal (cross-correlation peak)
            corr = np.correlate(gated, burst, mode="valid")
            self.assertGreater(float(np.max(corr)), 0.5 * float(np.sum(burst ** 2)),
                               "a speech burst was lost in gating")

    def test_gate_reference_free(self) -> None:
        # the gate must not require any reference text / CER -- it operates on audio alone
        x = make_synthetic_separated_track()
        gated = silence_aware_gate(x)  # no reference argument accepted
        self.assertIsInstance(gated, np.ndarray)


class TestGateDiagnostics(unittest.TestCase):
    def test_fired_true_for_long_gaps(self) -> None:
        x = make_synthetic_separated_track()
        d = gate_diagnostics(x)
        self.assertTrue(d["fired"])
        self.assertGreater(d["n_truncated"], 0)
        self.assertGreater(d["total_silence_removed_sec"], 5.0)
        self.assertGreater(d["max_gap_sec"], 5.0)

    def test_fired_false_for_all_speech(self) -> None:
        x = _speech_burst(SR, 2.0)
        d = gate_diagnostics(x)
        self.assertFalse(d["fired"])
        self.assertEqual(d["n_truncated"], 0)

    def test_fired_false_for_all_silence(self) -> None:
        x = np.zeros(int(5 * SR), dtype=np.float32)
        d = gate_diagnostics(x)
        self.assertFalse(d["fired"])

    def test_fired_false_when_gaps_below_max(self) -> None:
        # 1s speech, 0.2s silence, 1s speech -> gap below max_gap_sec -> not fired
        sr = SR
        x = _track([_speech_burst(sr, 1.0), np.zeros(int(0.2 * sr), dtype=np.float32),
                    _speech_burst(sr, 1.0)])
        d = gate_diagnostics(x, max_gap_sec=0.5)
        self.assertFalse(d["fired"])

    def test_diagnostics_reference_free(self) -> None:
        x = make_synthetic_separated_track()
        d = gate_diagnostics(x)  # no reference argument
        self.assertIsInstance(d, dict)
        self.assertIn("fired", d)


class TestSyntheticFixture(unittest.TestCase):
    def test_fixture_has_long_interior_gaps(self) -> None:
        x = make_synthetic_separated_track()
        d = gate_diagnostics(x)
        # the default fixture models the AISHELL-4 failure: 8s + 6s interior gaps
        self.assertGreater(d["max_gap_sec"], 5.0)
        self.assertGreaterEqual(d["n_truncated"], 2)

    def test_fixture_is_deterministic(self) -> None:
        a = make_synthetic_separated_track()
        b = make_synthetic_separated_track()
        self.assertTrue(np.array_equal(a, b))


if __name__ == "__main__":
    unittest.main()
