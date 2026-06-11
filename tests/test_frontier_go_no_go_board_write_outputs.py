from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.frontier_go_no_go_board import BOARD_COLUMNS, SUMMARY_COLUMNS, write_outputs


def _sample_board_row() -> dict[str, str]:
    return {
        "frontier_name": "meeteval_compatibility",
        "current_state": "receipt_ready_to_fill",
        "primary_boundary": "official_benchmark_claims_still_blocked_until_receipt_fill",
        "go_no_go_state": "go",
        "recommended_next_action": "Fill the official receipt with real evidence.",
        "evidence_artifact": "results/figures/meeteval_cpwer_tokenization_gain_scorecard_summary.md",
    }


def _sample_summary_row() -> dict[str, str]:
    return {
        "scope": "frontier_go_no_go_board",
        "frontier_count": "1",
        "go_count": "1",
        "no_go_count": "0",
        "highest_priority_ready_frontier": "meeteval_compatibility",
        "highest_priority_blocked_frontier": "",
        "coordination_state": "all_ready",
        "recommended_operator_focus": "meeteval_compatibility",
        "observation": "fixture",
    }


class FrontierGoNoGoBoardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_board_and_summary_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.frontier_go_no_go_board.PROJECT_ROOT", root):
                outputs = write_outputs([_sample_board_row()], _sample_summary_row())

            for path in outputs:
                self.assertTrue(path.exists())

            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BOARD_COLUMNS)
                self.assertEqual(list(reader)[0]["frontier_name"], "meeteval_compatibility")

            with outputs[2].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
                self.assertEqual(list(reader)[0]["coordination_state"], "all_ready")

            self.assertEqual(
                json.loads(outputs[1].read_text(encoding="utf-8"))[0]["go_no_go_state"],
                "go",
            )
            self.assertIn("Frontier Go-No-Go Board", outputs[4].read_text(encoding="utf-8"))
            self.assertIn("Frontier Go-No-Go Summary", outputs[5].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
