from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_packet import build_packet_rows


class FrontierOperatorNextActionStatusHandoffPacketTest(unittest.TestCase):
    def test_build_packet_rows_include_eight_sections(self) -> None:
        rows = build_packet_rows(
            {
                "queue_status": "queue_complete",
                "ready_lane_count": "1",
                "blocked_lane_count": "1",
            }
        )

        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[0]["section_name"], "status")
        self.assertEqual(rows[-1]["section_name"], "status_handoff_status_bridge_checklist")


if __name__ == "__main__":
    unittest.main()
