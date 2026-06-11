from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge import (
    BRIDGE_COLUMNS,
    build_bridge_row,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionReceiptOperatorBriefBridgeWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_bridge_artifacts(self) -> None:
        row = build_bridge_row(
            {
                "operator_case": "NoOverlap",
                "operator_status": "receipt_not_ready",
                "operator_target": "results/figures/speaker_profile_embedding_trial_execution_receipt_readiness.md",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_receipt_operator_brief_bridge.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BRIDGE_COLUMNS)
                self.assertEqual(list(reader)[0]["operator_case"], "NoOverlap")
            self.assertIn("Operator Brief Bridge", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
