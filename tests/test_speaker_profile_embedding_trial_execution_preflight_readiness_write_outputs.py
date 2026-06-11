from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_preflight_readiness import (
    PREFLIGHT_READINESS_COLUMNS,
    build_readiness_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionPreflightReadinessWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_readiness_artifacts(self) -> None:
        readiness_row = build_readiness_row(
            {"queue_status": "queue_complete", "case_id": "NoOverlap"},
            {"preflight_pass": "True", "case_id": "NoOverlap"},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_preflight_readiness.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(readiness_row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PREFLIGHT_READINESS_COLUMNS)
                self.assertEqual(list(reader)[0]["readiness_status"], "preflight_ready")
            self.assertIn("Preflight Readiness", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
