from __future__ import annotations

import unittest

from src.speaker_profile_spectral_embedding_baseline import build_baseline_row


class SpeakerProfileSpectralEmbeddingBaselineTest(unittest.TestCase):
    def test_build_baseline_row_marks_signal_agreement(self) -> None:
        text_row = {
            "best_alignment": "swapped",
            "profile_confidence_gap": "0.42",
            "direct_profile_score": "0.39",
            "swapped_profile_score": "0.81",
        }
        spectral_row = {
            "best_audio_alignment": "swapped",
            "audio_confidence_gap": "0.01",
            "direct_audio_score": "0.50",
            "swapped_audio_score": "0.51",
        }
        row = build_baseline_row("NoOverlap", text_row, spectral_row)
        self.assertEqual(row["trial_status"], "executed_baseline")
        self.assertEqual(row["signals_agree"], "True")
        self.assertEqual(row["result_label"], "experimental/frontier")

    def test_build_baseline_row_detects_disagreement(self) -> None:
        text_row = {"best_alignment": "direct", "profile_confidence_gap": "0.2"}
        spectral_row = {"best_audio_alignment": "swapped", "audio_confidence_gap": "0.05"}
        row = build_baseline_row("NoOverlap", text_row, spectral_row)
        self.assertEqual(row["signals_agree"], "False")


if __name__ == "__main__":
    unittest.main()
