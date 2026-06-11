from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_handoff import HANDOFF_COLUMNS, build_handoff_rows, write_outputs


class FrontierExecutionQueueHandoffBuildRowsTest(unittest.TestCase):
    def test_build_handoff_rows_emits_five_frontier_chains(self) -> None:
        rows = build_handoff_rows({})
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["frontier_name"], "meeteval_compatibility")
        self.assertEqual(rows[0]["handoff_order"], "1")

    def test_build_handoff_rows_uses_receipt_fill_action_when_chain_ready(self) -> None:
        rows = build_handoff_rows({"meeteval_chain_status": "execution_chain_ready"})
        self.assertIn("Fill the execution receipt", rows[0]["recommended_action"])


if __name__ == "__main__":
    unittest.main()
