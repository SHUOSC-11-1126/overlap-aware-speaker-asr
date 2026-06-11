from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_queue_evidence_receipt_bridge_checklist import (
    RECEIPT_BRIDGE_COLUMNS,
    build_bridge_checklist_rows,
    write_outputs,
)


class FrontierExecutionReceiptQueueEvidenceReceiptBridgeChecklistWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "receipt_frontier": "meeteval_compatibility",
                "receipt_note": "Fill evidence before writeback.",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_queue_evidence_receipt_bridge_checklist.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, RECEIPT_BRIDGE_COLUMNS)
                self.assertEqual(list(reader)[0]["receipt_frontier"], "meeteval_compatibility")
            self.assertIn(
                "Evidence Receipt Bridge Checklist",
                md_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
