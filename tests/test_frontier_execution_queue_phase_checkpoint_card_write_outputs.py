from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_phase_checkpoint_card import (
    PHASE_CHECKPOINT_COLUMNS,
    build_phase_checkpoint_row,
    write_outputs,
)


class FrontierExecutionQueuePhaseCheckpointCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_phase_checkpoint_row(
            {
                "recommended_frontier": "meeteval_compatibility",
                "recommended_action": "Fill the execution receipt.",
                "completion_signal": "receipt ready to open",
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_execution_queue_phase_checkpoint_card.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(row)

            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, PHASE_CHECKPOINT_COLUMNS)
                self.assertEqual(list(reader)[0]["checkpoint_frontier"], "meeteval_compatibility")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["checkpoint_frontier"], "meeteval_compatibility")
            self.assertIn("Frontier Execution Queue Phase Checkpoint Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
