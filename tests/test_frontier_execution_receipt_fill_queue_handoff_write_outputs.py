from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_receipt_fill_queue_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_rows,
    write_outputs,
)


class FrontierExecutionReceiptFillQueueHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_handoff_rows(
            [
                {
                    "fill_order": "1",
                    "frontier_name": "meeteval_compatibility",
                    "fill_status": "awaiting_fill",
                    "receipt_path": "results/tables/meeteval_cpwer_execution_receipt.json",
                },
                {
                    "fill_order": "2",
                    "frontier_name": "speaker_profile",
                    "fill_status": "fill_complete",
                    "receipt_path": "results/tables/speaker_profile_embedding_trial_execution_receipt.json",
                },
            ]
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_execution_receipt_fill_queue_handoff.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                parsed = list(reader)
                self.assertEqual(parsed[0]["frontier_name"], "meeteval_compatibility")
                self.assertEqual(parsed[1]["fill_status"], "fill_complete")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload), 2)
            self.assertIn("Fill Queue Handoff", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
