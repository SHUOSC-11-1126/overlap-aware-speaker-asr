from __future__ import annotations

import unittest

from src.speaker_profile_embedding_trial_execution_receipt_handoff_packet import build_packet_rows


class SpeakerProfileEmbeddingTrialExecutionReceiptHandoffPacketTest(unittest.TestCase):
    def test_build_packet_rows_include_four_sections(self) -> None:
        rows = build_packet_rows(
            {
                "case_id": "NoOverlap",
                "readiness_status": "receipt_ready_to_fill",
                "receipt_template_status": "template_only",
            }
        )

        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["section_name"], "receipt_readiness")
        self.assertEqual(rows[-1]["section_name"], "receipt_open_card_bridge_checklist")


if __name__ == "__main__":
    unittest.main()
