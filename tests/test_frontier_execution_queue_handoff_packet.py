from __future__ import annotations

import unittest

from src.frontier_execution_queue_handoff_packet import build_packet_rows


class FrontierExecutionQueueHandoffPacketTest(unittest.TestCase):
    def test_build_packet_rows_include_twenty_one_sections(self) -> None:
        rows = build_packet_rows({"queue_status": "queue_complete", "ready_chain_count": "3"})

        self.assertEqual(len(rows), 21)
        self.assertEqual(rows[0]["section_name"], "execution_queue_status")
        self.assertEqual(rows[1]["section_name"], "execution_queue_status_bridge_checklist")
        self.assertEqual(rows[3]["section_name"], "execution_queue_completion_summary_bridge_checklist")
        self.assertEqual(rows[5]["section_name"], "execution_queue_operator_brief")
        self.assertEqual(rows[6]["section_name"], "execution_queue_runbook_card")
        self.assertEqual(rows[7]["section_name"], "execution_queue_runbook_bridge_checklist")
        self.assertEqual(rows[8]["section_name"], "execution_queue_phase_checkpoint_card")
        self.assertEqual(rows[9]["section_name"], "execution_queue_phase_checkpoint_bridge_checklist")
        self.assertEqual(rows[10]["section_name"], "execution_queue_milestone_card")
        self.assertEqual(rows[11]["section_name"], "execution_queue_milestone_bridge_checklist")
        self.assertEqual(rows[12]["section_name"], "execution_queue_completion_dashboard")
        self.assertEqual(rows[13]["section_name"], "execution_queue_completion_dashboard_bridge_checklist")
        self.assertEqual(rows[14]["section_name"], "execution_queue_status_preflight_bridge_checklist")
        self.assertEqual(rows[15]["section_name"], "execution_queue_status_reentry_card")
        self.assertEqual(rows[16]["section_name"], "execution_queue_status_reentry_bridge_checklist")
        self.assertEqual(rows[17]["section_name"], "execution_queue_handoff_bridge_checklist")
        self.assertEqual(rows[18]["section_name"], "execution_queue_receipt_open_card")
        self.assertEqual(rows[19]["section_name"], "execution_queue_receipt_readiness_board")
        self.assertEqual(rows[-1]["section_name"], "execution_queue_receipt_readiness_bridge_checklist")


if __name__ == "__main__":
    unittest.main()
