from __future__ import annotations

import unittest

from src.frontier_execution_queue_status_bridge_checklist import build_bridge_checklist_rows


class FrontierExecutionQueueStatusBridgeChecklistTest(unittest.TestCase):
    def test_build_bridge_checklist_rows_uses_combined_status(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "combined_chain_status": "execution_chain_ready",
                "meeteval_chain_status": "execution_chain_ready",
                "speaker_profile_chain_status": "execution_chain_ready",
                "external_staging_chain_status": "execution_chain_ready",
            }
        )

        self.assertEqual(rows[0]["combined_chain_status"], "execution_chain_ready")
        self.assertIn("combined_chain_status=execution_chain_ready", rows[0]["bridge_note"])

    def test_build_bridge_checklist_rows_defaults_statuses(self) -> None:
        rows = build_bridge_checklist_rows({})

        self.assertEqual(rows[0]["combined_chain_status"], "execution_chain_in_progress")


if __name__ == "__main__":
    unittest.main()
