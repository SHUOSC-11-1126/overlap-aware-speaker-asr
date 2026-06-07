from __future__ import annotations

import unittest

from src.frontier_execution_queue_handoff import build_handoff_rows


class FrontierExecutionQueueHandoffTest(unittest.TestCase):
    def test_build_handoff_rows_recommends_receipt_fill_when_chain_ready(self) -> None:
        rows = build_handoff_rows(
            {
                "meeteval_chain_status": "execution_chain_ready",
                "speaker_profile_chain_status": "execution_chain_ready",
                "external_staging_chain_status": "execution_chain_ready",
            }
        )

        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["frontier_name"], "meeteval_compatibility")
        self.assertIn("Fill the execution receipt", rows[0]["recommended_action"])

    def test_build_handoff_rows_recommends_scaffold_when_chain_pending(self) -> None:
        rows = build_handoff_rows({"meeteval_chain_status": "execution_chain_in_progress"})

        self.assertIn("Complete the remaining execution-chain scaffold", rows[0]["recommended_action"])


if __name__ == "__main__":
    unittest.main()
