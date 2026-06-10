from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from src.speaker_profile_audio_proxy_trial import (
    average_profile_vector,
    build_audio_proxy_row,
    cosine_similarity,
    extract_audio_profile_vector,
)


class SpeakerProfileAudioProxyTrialTest(unittest.TestCase):
    def test_cosine_similarity_is_high_for_matching_vectors(self) -> None:
        score = cosine_similarity(np.array([1.0, 0.0]), np.array([1.0, 0.0]))
        self.assertAlmostEqual(score, 1.0, places=6)

    def test_extract_audio_profile_vector_returns_stable_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "tone.wav"
            sample_rate = 16000
            seconds = 1.0
            t = np.linspace(0.0, seconds, int(sample_rate * seconds), endpoint=False)
            waveform = 0.5 * np.sin(2 * np.pi * 440.0 * t)
            wavfile.write(audio_path, sample_rate, np.int16(waveform * 32767))

            vector = extract_audio_profile_vector(audio_path)

        self.assertEqual(vector.shape, (9,))
        self.assertTrue(np.isfinite(vector).all())

    def test_extract_audio_profile_vector_returns_nine_dims_for_empty_waveform(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "empty.wav"
            wavfile.write(audio_path, 16000, np.array([], dtype=np.int16))
            vector = extract_audio_profile_vector(audio_path)
        self.assertEqual(vector.shape, (9,))

    def test_average_profile_vector_returns_nine_dims_for_missing_paths(self) -> None:
        vector = average_profile_vector([Path("/tmp/__missing_audio_profile__.wav")])
        self.assertEqual(vector.shape, (9,))

    def test_build_audio_proxy_row_prefers_direct_alignment_for_matching_profiles(self) -> None:
        row = build_audio_proxy_row(
            case_id="DemoCase",
            hypothesis_source="separated_whisper",
            con_vector=np.array([1.0, 0.0, 0.0]),
            pro_vector=np.array([0.0, 1.0, 0.0]),
            speaker_1_vector=np.array([0.9, 0.1, 0.0]),
            speaker_2_vector=np.array([0.1, 0.9, 0.0]),
        )

        self.assertEqual(row["best_audio_alignment"], "direct")
        self.assertGreater(float(row["direct_audio_score"]), float(row["swapped_audio_score"]))
        self.assertEqual(row["result_label"], "experimental/frontier")


if __name__ == "__main__":
    unittest.main()
