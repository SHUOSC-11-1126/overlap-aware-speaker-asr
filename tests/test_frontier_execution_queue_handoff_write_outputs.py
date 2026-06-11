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


class FrontierExecutionQueueHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_handoff_rows({"meeteval_chain_status": "execution_chain_ready"})
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_execution_queue_handoff.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(rows)

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                self.assertEqual(len(list(reader)), 5)

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["frontier_name"], "meeteval_compatibility")
            self.assertIn("Frontier Execution Queue Handoff", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
