from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_operator_next_action_status_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_rows,
    write_outputs,
)


class FrontierOperatorNextActionStatusHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        rows = build_handoff_rows(
            {"combined_operator_status": "operator_status_mixed_ready"},
            [
                {
                    "action_lane": "ready_lane",
                    "frontier_name": "meeteval_compatibility",
                    "operator_action": "Fill the official receipt with real evidence.",
                    "target_artifact": "results/tables/meeteval_cpwer_execution_receipt.json",
                },
                {
                    "action_lane": "blocked_lane",
                    "frontier_name": "external_validation",
                    "operator_action": "Record the license confirmation decision.",
                    "target_artifact": "results/tables/external_validation_license_confirmation_receipt_bridge.json",
                },
            ],
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_operator_next_action_status_handoff.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(rows)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                parsed = list(reader)
                self.assertEqual(len(parsed), 2)
                self.assertEqual(parsed[0]["action_lane"], "ready_lane")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[1]["frontier_name"], "external_validation")
            self.assertIn("Status Handoff", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
