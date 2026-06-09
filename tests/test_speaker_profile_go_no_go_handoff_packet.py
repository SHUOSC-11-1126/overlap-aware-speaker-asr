from __future__ import annotations

import unittest

from src.speaker_profile_go_no_go_handoff_packet import build_packet_rows


class SpeakerProfileGoNoGoHandoffPacketTest(unittest.TestCase):
    def test_build_packet_rows_include_go_no_go_stack(self) -> None:
        rows = build_packet_rows(
            {
                "handoff_status": "speaker_profile_go_handoff_ready",
                "case_scope": "NoOverlap",
                "queue_status": "queue_complete",
            }
        )

        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["section_name"], "go_no_go_board")
        self.assertEqual(rows[6]["section_name"], "go_no_go_handoff_completion_bridge_checklist")
        self.assertIn("speaker_profile_go_handoff_ready", rows[0]["packet_note"])


if __name__ == "__main__":
    unittest.main()
