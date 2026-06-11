from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_execution_receipt_scaffold_bridge_checklist import (
    BRIDGE_CHECKLIST_COLUMNS,
    build_bridge_checklist_rows,
    write_outputs,
)


class MeetEvalCpwerExecutionReceiptScaffoldBridgeChecklistWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_bridge_checklist_rows(
            {"case_id": "NoOverlap", "scaffold_status": "receipt_scaffold_only", "preflight_pass": "True"}
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.meeteval_cpwer_execution_receipt_scaffold_bridge_checklist.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BRIDGE_CHECKLIST_COLUMNS)
                self.assertEqual(list(reader)[0]["preflight_pass"], "True")
            self.assertIn(
                "MeetEval cpWER Execution Receipt Scaffold Bridge Checklist",
                md_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
