from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_queue_runbook_card import (
    RUNBOOK_COLUMNS,
    build_runbook_card_row,
    write_outputs,
)


class FrontierExecutionReceiptQueueRunbookCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_runbook_card_row(
            {
                "operator_frontier": "meeteval_compatibility",
                "operator_action": "Update execution receipt after real run.",
                "operator_evidence": "results/figures/frontier_execution_receipt_queue_operator_brief.md",
                "operator_urgency": "ready_receipt_count=2",
            },
            [
                {
                    "frontier_name": "meeteval_compatibility",
                    "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
                }
            ],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_queue_runbook_card.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, RUNBOOK_COLUMNS)
                self.assertEqual(list(reader)[0]["recommended_frontier"], "meeteval_compatibility")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("meeteval_cpwer_execution_receipt", payload["completion_signal"])
            self.assertIn("Runbook Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
