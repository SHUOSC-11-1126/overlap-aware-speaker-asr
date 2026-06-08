from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_handoff_packet_bridge_checklist import (
    build_bridge_checklist_rows,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptHandoffPacketBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_targets_readiness_rollup(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "case_id": "NoOverlap",
                "readiness_status": "receipt_ready_to_fill",
                "receipt_template_status": "template_only",
            }
        )

        self.assertEqual(rows[0]["case_id"], "NoOverlap")
        self.assertEqual(rows[0]["readiness_status"], "receipt_ready_to_fill")
        self.assertIn("receipt_readiness.md", rows[0]["receipt_target"])


if __name__ == "__main__":
    unittest.main()
