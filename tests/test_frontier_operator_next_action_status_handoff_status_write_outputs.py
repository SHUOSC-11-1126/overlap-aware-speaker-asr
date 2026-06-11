from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_operator_next_action_status_handoff_status import (
    STATUS_COLUMNS,
    build_status_row,
    write_outputs,
)


class FrontierOperatorNextActionStatusHandoffStatusWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        status_row = build_status_row(
            {
                "queue_status": "queue_complete",
                "ready_lane_count": "1",
                "blocked_lane_count": "1",
                "primary_frontier": "meeteval_compatibility",
            },
            {"next_milestone": "ready_lane_checkpoint_complete"},
            {"current_first_frontier": "meeteval_compatibility"},
            [{"receipt_target": "results/figures/frontier_operator_next_action_status_handoff_runbook_card.md"}],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_operator_next_action_status_handoff_status.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(status_row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, STATUS_COLUMNS)
                self.assertEqual(list(reader)[0]["combined_status_handoff_state"], "status_handoff_mixed_ready")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["primary_status_target"], "meeteval_compatibility")
            self.assertIn("Status Handoff Status", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
