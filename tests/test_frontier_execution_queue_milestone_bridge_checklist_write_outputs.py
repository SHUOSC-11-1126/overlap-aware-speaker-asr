from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_milestone_bridge_checklist import (
    BRIDGE_CHECKLIST_COLUMNS,
    build_bridge_checklist_rows,
    write_outputs,
)


class FrontierExecutionQueueMilestoneBridgeChecklistWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_bridge_checklist_rows(
            {
                "next_milestone": "first_execution_queue_checkpoint_complete",
                "unlocks": "speaker_profile handoff",
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_execution_queue_milestone_bridge_checklist.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(rows)

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BRIDGE_CHECKLIST_COLUMNS)
                self.assertEqual(list(reader)[0]["next_milestone"], "first_execution_queue_checkpoint_complete")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("speaker_profile handoff", payload[0]["bridge_note"])
            self.assertIn("Frontier Execution Queue Milestone Bridge Checklist", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
