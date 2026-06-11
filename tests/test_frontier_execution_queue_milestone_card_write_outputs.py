from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_execution_queue_milestone_card import (
    MILESTONE_COLUMNS,
    build_milestone_card_row,
    write_outputs,
)


class FrontierExecutionQueueMilestoneCardBuildRowTest(unittest.TestCase):
    def test_build_milestone_card_row_returns_empty_without_completion_summary(self) -> None:
        self.assertEqual(build_milestone_card_row({}, [{"frontier_name": "speaker_profile"}]), {})

    def test_build_milestone_card_row_uses_second_handoff_frontier(self) -> None:
        row = build_milestone_card_row(
            {"total_chain_count": "5"},
            [
                {"frontier_name": "meeteval_compatibility"},
                {"frontier_name": "speaker_profile"},
            ],
        )
        self.assertEqual(row["next_milestone"], "first_execution_queue_checkpoint_complete")
        self.assertEqual(row["remaining_frontier_count"], "4")
        self.assertIn("speaker_profile", row["unlocks"])


class FrontierExecutionQueueMilestoneCardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_csv_json_and_markdown(self) -> None:
        row = build_milestone_card_row(
            {"total_chain_count": "3"},
            [{"frontier_name": "meeteval_compatibility"}, {"frontier_name": "external_validation"}],
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_execution_queue_milestone_card.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(row)

            self.assertTrue(csv_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())

            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, MILESTONE_COLUMNS)
                self.assertEqual(list(reader)[0]["remaining_frontier_count"], "2")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["next_milestone"], "first_execution_queue_checkpoint_complete")
            self.assertIn("Frontier Execution Queue Milestone Card", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
