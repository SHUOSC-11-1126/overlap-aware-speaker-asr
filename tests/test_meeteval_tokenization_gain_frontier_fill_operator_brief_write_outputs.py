from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_tokenization_gain_frontier_fill_operator_brief import (
    OPERATOR_BRIEF_COLUMNS,
    build_operator_brief_row,
    write_outputs,
)


class MeetEvalTokenizationGainFrontierFillOperatorBriefWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_operator_brief_artifacts(self) -> None:
        row = build_operator_brief_row(
            {
                "recommended_frontier": "meeteval_compatibility",
                "receipt_target": "results/tables/meeteval_cpwer_execution_receipt.json",
                "bridge_note": "checklist verified",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.meeteval_tokenization_gain_frontier_fill_operator_brief.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, OPERATOR_BRIEF_COLUMNS)
                self.assertEqual(list(reader)[0]["operator_frontier"], "meeteval_compatibility")
            self.assertIn("Operator Brief", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
