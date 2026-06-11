from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_status import (
    STATUS_COLUMNS,
    build_status_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionStatusWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_status_artifacts(self) -> None:
        status_row = build_status_row(
            {
                "case_id": "NoOverlap",
                "preflight_pass": True,
                "swapped_bias_detected": True,
                "combined_signal_status": "mixed_signal",
            },
            {"case_id": "NoOverlap", "scaffold_status": "receipt_scaffold_only"},
            "template_only",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_status.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(status_row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, STATUS_COLUMNS)
                self.assertEqual(list(reader)[0]["execution_chain_status"], "execution_chain_ready")
            self.assertIn("Execution Status", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
