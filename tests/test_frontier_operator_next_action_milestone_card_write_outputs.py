from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_operator_next_action_milestone_card import (
    MILESTONE_COLUMNS,
    build_milestone_card_row,
    write_outputs,
)


class FrontierOperatorNextActionMilestoneCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_milestone_card_row(
            {
                "ready_frontier": "meeteval_compatibility",
                "blocked_frontier": "external_validation",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch(
                "src.frontier_operator_next_action_milestone_card.PROJECT_ROOT",
                root,
            ):
                csv_path, json_path, md_path = write_outputs(row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, MILESTONE_COLUMNS)
                self.assertEqual(list(reader)[0]["next_milestone"], "ready_lane_checkpoint_complete")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("external_validation", payload["unlocks"])
            self.assertIn("Milestone Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
