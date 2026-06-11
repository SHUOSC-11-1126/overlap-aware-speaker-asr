from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_scaffold import (
    SCAFFOLD_COLUMNS,
    build_execution_scaffold_row,
    build_scaffold_receipt_rows,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionScaffoldWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_scaffold_and_receipt_artifacts(self) -> None:
        scaffold_row = build_execution_scaffold_row(
            {
                "case_id": "NoOverlap",
                "method_direction": "embedding_or_voiceprint_baseline",
                "trial_status": "scaffold_only",
                "profile_confidence_gap": "0.24",
            }
        )
        receipt_rows = build_scaffold_receipt_rows(scaffold_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_scaffold.PROJECT_ROOT",
                root,
            ):
                paths = write_outputs(scaffold_row, receipt_rows)

            for path in paths:
                self.assertTrue(path.exists())
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SCAFFOLD_COLUMNS)
                self.assertEqual(list(reader)[0]["scaffold_status"], "execution_scaffold_only")
            payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertEqual(payload["case_id"], "NoOverlap")
            self.assertIn("Execution Scaffold", paths[2].read_text(encoding="utf-8"))
            receipt_payload = json.loads(paths[3].read_text(encoding="utf-8"))
            self.assertEqual(receipt_payload[0]["execution_status"], "execution_scaffold_complete")


if __name__ == "__main__":
    unittest.main()
