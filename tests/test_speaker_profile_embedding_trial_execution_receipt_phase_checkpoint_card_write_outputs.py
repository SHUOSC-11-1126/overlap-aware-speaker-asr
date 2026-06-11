from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_card import (
    PHASE_CHECKPOINT_COLUMNS,
    build_phase_checkpoint_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptPhaseCheckpointCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_phase_checkpoint_card_artifacts(self) -> None:
        row = build_phase_checkpoint_row(
            {
                "recommended_case": "NoOverlap",
                "recommended_action": "Fill execution receipt template.",
                "completion_signal": "receipt_template_ready",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_receipt_phase_checkpoint_card.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PHASE_CHECKPOINT_COLUMNS)
                self.assertEqual(list(reader)[0]["checkpoint_case"], "NoOverlap")
            self.assertIn("Phase Checkpoint Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
