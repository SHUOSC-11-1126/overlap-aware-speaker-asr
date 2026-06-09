from __future__ import annotations

import unittest

from src.meeteval_tokenization_adaptation_handoff_packet import build_packet_rows


class MeetEvalTokenizationAdaptationHandoffPacketTest(unittest.TestCase):
    def test_build_packet_rows_include_tokenization_adaptation_stack(self) -> None:
        rows = build_packet_rows(
            {
                "handoff_status": "tokenization_adaptation_handoff_ready",
                "aligned_count": "5",
                "total_count": "5",
                "queue_status": "queue_complete",
            }
        )

        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["section_name"], "tokenization_diagnostic")
        self.assertEqual(rows[1]["section_name"], "character_level_official_execution")
        self.assertEqual(rows[2]["section_name"], "reconciliation_audit")
        self.assertEqual(rows[3]["section_name"], "tokenization_gain_scorecard")
        self.assertEqual(rows[4]["section_name"], "tokenization_gain_scorecard_bridge_checklist")
        self.assertEqual(rows[5]["section_name"], "tokenization_gain_scorecard_handoff")
        self.assertEqual(rows[6]["section_name"], "tokenization_adaptation_completion_summary")
        self.assertEqual(rows[7]["section_name"], "tokenization_adaptation_handoff")
        self.assertEqual(rows[8]["section_name"], "tokenization_adaptation_handoff_bridge_checklist")
        self.assertEqual(rows[9]["section_name"], "tokenization_adaptation_handoff_completion_summary")
        self.assertIn("tokenization_adaptation_handoff_ready", rows[0]["packet_note"])


if __name__ == "__main__":
    unittest.main()
