from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_queue_status_reentry_card import (
    REENTRY_COLUMNS,
    build_reentry_card_row,
    write_outputs,
)


class FrontierExecutionReceiptQueueStatusReentryCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_reentry_card_row(
            [
                {
                    "current_first_frontier": "meeteval_compatibility",
                    "receipt_target": "results/figures/frontier_execution_receipt_queue_status.md",
                }
            ],
            {"combined_readiness_status": "receipt_not_ready"},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_queue_status_reentry_card.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, REENTRY_COLUMNS)
                self.assertEqual(list(reader)[0]["current_first_frontier"], "meeteval_compatibility")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["combined_readiness_status"], "receipt_not_ready")
            self.assertIn("Status Reentry Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
