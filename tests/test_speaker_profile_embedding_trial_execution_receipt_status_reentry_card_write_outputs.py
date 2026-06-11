from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_receipt_status_reentry_card import (
    REENTRY_COLUMNS,
    build_reentry_card_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptStatusReentryCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_reentry_card_artifacts(self) -> None:
        row = build_reentry_card_row(
            [
                {
                    "current_case": "NoOverlap",
                    "receipt_target": "results/figures/speaker_profile_embedding_trial_execution_status.md",
                }
            ],
            {"execution_chain_status": "execution_chain_ready"},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_receipt_status_reentry_card.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, REENTRY_COLUMNS)
                self.assertEqual(list(reader)[0]["current_case"], "NoOverlap")
            self.assertIn("Status Reentry Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
