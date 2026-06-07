from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_status import build_status_row


class SpeakerProfileEmbeddingTrialExecutionStatusTest(unittest.TestCase):
    def test_build_status_row_marks_chain_ready(self) -> None:
        row = build_status_row(
            {"case_id": "NoOverlap", "preflight_pass": True, "swapped_bias_detected": True},
            {"scaffold_status": "receipt_scaffold_only"},
            "template_only",
        )

        self.assertEqual(row["execution_chain_status"], "execution_chain_ready")
        self.assertEqual(row["swapped_bias_detected"], "True")


if __name__ == "__main__":
    unittest.main()
