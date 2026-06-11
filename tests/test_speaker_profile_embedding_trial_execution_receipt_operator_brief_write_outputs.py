from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_receipt_operator_brief import (
    OPERATOR_BRIEF_COLUMNS,
    build_operator_brief_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptOperatorBriefWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_operator_brief_artifacts(self) -> None:
        row = build_operator_brief_row(
            {
                "case_id": "NoOverlap",
                "readiness_status": "receipt_not_ready",
                "receipt_template_status": "missing",
                "receipt_target": "results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_receipt_operator_brief.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, OPERATOR_BRIEF_COLUMNS)
                self.assertEqual(list(reader)[0]["operator_case"], "NoOverlap")
            self.assertIn("Operator Brief", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
