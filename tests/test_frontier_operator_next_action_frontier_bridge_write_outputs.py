from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_operator_next_action_frontier_bridge import (
    FRONTIER_BRIDGE_COLUMNS,
    build_frontier_bridge_row,
    write_outputs,
)


class FrontierOperatorNextActionFrontierBridgeWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_frontier_bridge_row(
            {"recommended_frontier": "meeteval_compatibility"},
            {"highest_priority_ready_frontier": "meeteval_compatibility"},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_operator_next_action_frontier_bridge.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, FRONTIER_BRIDGE_COLUMNS)
                self.assertEqual(list(reader)[0]["runbook_frontier"], "meeteval_compatibility")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["frontier_queue_head"], "meeteval_compatibility")
            self.assertIn("Frontier Bridge", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
