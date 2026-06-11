from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_embedding_trial_execution_preflight import (
    PREFLIGHT_COLUMNS,
    build_receipt_rows,
    run_preflight,
    write_outputs,
)


class SpeakerProfileEmbeddingTrialExecutionPreflightWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_preflight_and_receipt_artifacts(self) -> None:
        preflight_row = run_preflight(
            "NoOverlap",
            {
                "handoff_status": "execution_handoff_ready",
                "method_direction": "embedding_or_voiceprint_baseline",
            },
            {
                "best_profile_alignment": "swapped",
                "profile_confidence_gap": "0.24",
            },
            {"combined_signal_status": "mixed_signal", "recommended_next_step": "Run embedding baseline."},
        )
        receipt_rows = build_receipt_rows(preflight_row)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.speaker_profile_embedding_trial_execution_preflight.PROJECT_ROOT",
                root,
            ):
                paths = write_outputs(preflight_row, receipt_rows)

            for path in paths:
                self.assertTrue(path.exists())
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PREFLIGHT_COLUMNS)
                self.assertEqual(list(reader)[0]["preflight_pass"], "True")
            payload = json.loads(paths[1].read_text(encoding="utf-8"))
            self.assertTrue(payload["swapped_bias_detected"])
            self.assertIn("Execution Preflight", paths[2].read_text(encoding="utf-8"))
            receipt_payload = json.loads(paths[3].read_text(encoding="utf-8"))
            self.assertEqual(receipt_payload[0]["execution_status"], "preflight_complete")


if __name__ == "__main__":
    unittest.main()
