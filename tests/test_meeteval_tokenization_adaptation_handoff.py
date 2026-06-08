from __future__ import annotations

import unittest

from src.meeteval_tokenization_adaptation_handoff import build_handoff_row


class MeetEvalTokenizationAdaptationHandoffTest(unittest.TestCase):
    def test_build_handoff_row_marks_ready_when_reconciled(self) -> None:
        row = build_handoff_row(
            {
                "aligned_count": "5",
                "total_count": "5",
                "queue_status": "queue_complete",
            }
        )

        self.assertEqual(row["handoff_status"], "tokenization_adaptation_handoff_ready")
        self.assertIn("operator_brief", row["handoff_target"])


if __name__ == "__main__":
    unittest.main()
