from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.demo_go_no_go_board import BOARD_COLUMNS, SUMMARY_COLUMNS, write_outputs


def _sample_board_row() -> dict[str, str]:
    return {
        "checkpoint_name": "walkthrough_review",
        "scope": "qualitative/demo",
        "current_status": "queue_in_progress",
        "claim_boundary": "no live demo",
        "go_no_go_state": "no_go",
        "next_action": "Finish walkthrough review pass.",
        "evidence_artifact": "results/figures/demo_walkthrough_review_pass.md",
    }


def _sample_summary_row() -> dict[str, str]:
    return {
        "scope": "demo_excellence",
        "checkpoint_count": "1",
        "go_count": "0",
        "no_go_count": "1",
        "overall_state": "no_go",
        "primary_boundary": "no live demo",
        "recommended_next_action": "Finish walkthrough review pass.",
        "observation": "fixture",
    }


class DemoGoNoGoBoardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_board_and_summary_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.demo_go_no_go_board.PROJECT_ROOT", root):
                outputs = write_outputs([_sample_board_row()], _sample_summary_row())

            for path in outputs:
                self.assertTrue(path.exists())

            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BOARD_COLUMNS)
                self.assertEqual(list(reader)[0]["checkpoint_name"], "walkthrough_review")

            with outputs[2].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
                self.assertEqual(list(reader)[0]["overall_state"], "no_go")

            self.assertEqual(json.loads(outputs[1].read_text(encoding="utf-8"))[0]["scope"], "qualitative/demo")
            self.assertIn("Demo Go-No-Go Board", outputs[4].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
