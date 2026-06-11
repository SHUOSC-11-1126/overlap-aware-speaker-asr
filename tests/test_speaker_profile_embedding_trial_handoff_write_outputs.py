from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_receipt_rows,
    build_handoff_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_handoff_and_receipt_artifacts(self) -> None:
        handoff_row = build_handoff_row(
            {
                "dominant_pattern": "swapped_bias",
                "method_direction": "embedding_or_voiceprint_baseline",
            }
        )
        receipt_rows = build_handoff_receipt_rows(handoff_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.speaker_profile_embedding_trial_handoff.PROJECT_ROOT", root):
                paths = write_outputs(handoff_row, receipt_rows)

            for path in paths:
                self.assertTrue(path.exists())
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                self.assertEqual(list(reader)[0]["handoff_status"], "embedding_trial_handoff_ready")
            payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertEqual(payload["trial_case_target"], "NoOverlap")
            self.assertIn("Trial Handoff", paths[2].read_text(encoding="utf-8"))
            receipt_payload = json.loads(paths[3].read_text(encoding="utf-8"))
            self.assertEqual(receipt_payload[0]["execution_status"], "handoff_documented")


if __name__ == "__main__":
    unittest.main()
