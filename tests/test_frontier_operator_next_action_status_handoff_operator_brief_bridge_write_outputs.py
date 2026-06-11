from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_operator_next_action_status_handoff_operator_brief_bridge import (
    BRIDGE_COLUMNS,
    build_bridge_row,
    write_outputs,
)


class FrontierOperatorNextActionStatusHandoffOperatorBriefBridgeWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_bridge_row(
            {
                "ready_frontier": "meeteval_compatibility",
                "operator_urgency": "queue_status=queue_complete; ready_lane_count=1; blocked_lane_count=1",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_operator_next_action_status_handoff_operator_brief_bridge.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BRIDGE_COLUMNS)
                self.assertEqual(list(reader)[0]["reentry_frontier"], "meeteval_compatibility")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("runbook_card", payload["receipt_target"])
            self.assertIn("Operator Brief Bridge", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
