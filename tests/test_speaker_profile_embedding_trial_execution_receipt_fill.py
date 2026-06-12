from __future__ import annotations

import unittest
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_receipt_fill import (
    build_fill_row,
    build_filled_receipt_row,
    fill_execution_receipt,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptFillTest(unittest.TestCase):
    def test_build_filled_receipt_row_marks_diagnostic_complete(self) -> None:
        row = build_filled_receipt_row(
            {"case_id": "NoOverlap", "preflight_pass": "True", "swapped_bias_detected": "True"},
            {
                "case_id": "NoOverlap",
                "text_best_alignment": "direct",
                "spectral_best_alignment": "swapped",
                "signals_agree": "False",
                "spectral_confidence_gap": "0.12",
            },
        )
        self.assertEqual(row["execution_status"], "embedding_diagnostic_complete")

    def test_build_fill_row_records_alignment_signals(self) -> None:
        row = build_fill_row(
            {"case_id": "NoOverlap"},
            {"text_best_alignment": "direct", "spectral_best_alignment": "direct", "signals_agree": "True"},
        )
        self.assertEqual(row["signals_agree"], "True")
        self.assertEqual(row["blocker"], "none_documented")

    def test_fill_execution_receipt_requires_readiness(self) -> None:
        with patch(
            "src.speaker_profile_embedding_trial_execution_receipt_fill.load_readiness",
            return_value={"readiness_status": "receipt_not_ready"},
        ):
            with self.assertRaises(RuntimeError):
                fill_execution_receipt()


if __name__ == "__main__":
    unittest.main()
