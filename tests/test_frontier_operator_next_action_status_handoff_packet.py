from __future__ import annotations

import unittest

from src.frontier_operator_next_action_status_handoff_packet import build_packet_rows


class FrontierOperatorNextActionStatusHandoffPacketTest(unittest.TestCase):
    def test_build_packet_rows_include_fourteen_sections(self) -> None:
        rows = build_packet_rows(
            {
                "queue_status": "queue_complete",
                "ready_lane_count": "1",
                "blocked_lane_count": "1",
            }
        )

        self.assertEqual(len(rows), 14)
        self.assertEqual(rows[0]["section_name"], "status")
        self.assertEqual(rows[6]["section_name"], "status_handoff_operator_brief")
        self.assertEqual(rows[11]["section_name"], "status_handoff_completion_dashboard_bridge_checklist")
        self.assertEqual(rows[-1]["section_name"], "status_handoff_status_bridge_checklist")


if __name__ == "__main__":
    unittest.main()
