from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_preflight import build_receipt_rows, run_preflight


class SpeakerProfileEmbeddingTrialExecutionPreflightTest(unittest.TestCase):
    def test_run_preflight_detects_swapped_bias(self) -> None:
        row = run_preflight(
            "NoOverlap",
            {"handoff_status": "execution_handoff_ready", "method_direction": "embedding_or_voiceprint_baseline"},
            {
                "best_profile_alignment": "swapped",
                "profile_confidence_gap": "0.42",
            },
            {
                "combined_signal_status": "text_swapped_audio_weak",
                "recommended_next_step": "Advance only to a narrow embedding baseline; attribution claims remain blocked.",
            },
        )

        self.assertTrue(row["preflight_pass"])
        self.assertTrue(row["swapped_bias_detected"])
        self.assertEqual(row["combined_signal_status"], "text_swapped_audio_weak")
        self.assertIn("narrow embedding baseline", row["preflight_recommendation"])

    def test_build_receipt_rows_marks_preflight_failed_when_data_missing(self) -> None:
        rows = build_receipt_rows(
            {
                "case_id": "NoOverlap",
                "preflight_pass": False,
                "method_direction": "test",
                "combined_signal_status": "signals_missing",
            }
        )

        self.assertEqual(rows[0]["execution_status"], "preflight_failed")
        self.assertEqual(rows[0]["combined_signal_status"], "signals_missing")


if __name__ == "__main__":
    unittest.main()
