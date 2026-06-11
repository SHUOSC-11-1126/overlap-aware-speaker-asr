from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge import (
    EXECUTION_RECEIPT_BRIDGE_COLUMNS,
    build_execution_receipt_bridge_row,
    write_outputs,
)


class MeetEvalTokenizationGainFrontierFillExecutionReceiptBridgeWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_execution_receipt_bridge_artifacts(self) -> None:
        row = build_execution_receipt_bridge_row(
            {
                "recommended_frontier": "meeteval_compatibility",
                "runbook_status": "tokenization_gain_frontier_fill_runbook_ready",
                "execution_receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.meeteval_tokenization_gain_frontier_fill_execution_receipt_bridge.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, EXECUTION_RECEIPT_BRIDGE_COLUMNS)
                self.assertEqual(list(reader)[0]["recommended_frontier"], "meeteval_compatibility")
            self.assertIn("Execution Receipt Bridge", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
