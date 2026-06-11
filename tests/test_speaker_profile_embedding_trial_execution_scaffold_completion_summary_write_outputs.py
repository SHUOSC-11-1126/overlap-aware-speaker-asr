from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_scaffold_completion_summary import (
    COMPLETION_COLUMNS,
    build_completion_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionScaffoldCompletionSummaryWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_completion_summary_artifacts(self) -> None:
        completion_row = build_completion_row(
            {
                "readiness_status": "scaffold_ready",
                "case_id": "NoOverlap",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_scaffold_completion_summary.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(completion_row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, COMPLETION_COLUMNS)
                self.assertEqual(list(reader)[0]["queue_status"], "queue_complete")
            self.assertIn(
                "Scaffold Completion Summary",
                md_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
