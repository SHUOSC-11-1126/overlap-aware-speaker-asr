from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_readiness import build_readiness_row


class SpeakerProfileEmbeddingTrialExecutionReceiptReadinessTest(unittest.TestCase):
    def test_build_readiness_row_marks_ready_when_chain_and_template_pass(self) -> None:
        row = build_readiness_row(
            {
                "case_id": "NoOverlap",
                "execution_chain_status": "execution_chain_ready",
                "swapped_bias_detected": "True",
                "combined_signal_status": "text_swapped_audio_weak",
            },
            {
                "execution_status": "template_only",
                "preflight_pass": "True",
                "swapped_bias_detected": "True",
                "combined_signal_status": "text_swapped_audio_weak",
            },
        )

        self.assertEqual(row["readiness_status"], "receipt_ready_to_fill")
        self.assertEqual(row["swapped_bias_detected"], "True")
        self.assertEqual(row["combined_signal_status"], "text_swapped_audio_weak")

    def test_build_readiness_row_marks_not_ready_when_template_missing(self) -> None:
        row = build_readiness_row(
            {"execution_chain_status": "execution_chain_ready"},
            {"execution_status": "missing"},
        )

        self.assertEqual(row["readiness_status"], "receipt_not_ready")


if __name__ == "__main__":
    unittest.main()
