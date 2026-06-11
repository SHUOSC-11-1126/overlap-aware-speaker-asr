from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_fill_execution_runbook_card import (
    RUNBOOK_COLUMNS,
    build_runbook_card_row,
    write_outputs,
)


class FrontierExecutionReceiptFillExecutionRunbookCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_runbook_card_row(
            {
                "operator_frontier": "meeteval_compatibility",
                "operator_action": "Fill MeetEval execution receipt.",
                "operator_evidence": "results/figures/frontier_execution_receipt_fill_execution_handoff.md",
            },
            {
                "receipt_evidence": "results/tables/meeteval_cpwer_execution_receipt.json",
                "receipt_completion_signal": "execution_status != template_only",
            },
            {
                "awaiting_fill_execution_count": "3",
                "total_frontier_count": "3",
            },
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_fill_execution_runbook_card.PROJECT_ROOT",
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
            self.assertEqual(payload["urgency"], "3/3 frontiers awaiting fill execution")
            self.assertIn("Runbook Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
