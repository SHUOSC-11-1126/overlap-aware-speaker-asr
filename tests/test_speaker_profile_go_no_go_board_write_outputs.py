from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.speaker_profile_go_no_go_board import BOARD_COLUMNS, SUMMARY_COLUMNS, write_outputs


def _sample_board_row() -> dict[str, str]:
    return {
        "checkpoint_name": "embedding_trial_scaffold",
        "case_scope": "FixtureCase",
        "current_status": "scaffold_only",
        "claim_boundary": "no verified voiceprint",
        "go_no_go_state": "no_go",
        "next_action": "Run narrow embedding baseline.",
        "evidence_artifact": "results/figures/speaker_profile_method_receipt.md",
    }


def _sample_summary_row() -> dict[str, str]:
    return {
        "scope": "speaker_profile_frontier",
        "case_scope": "FixtureCase",
        "checkpoint_count": "1",
        "go_count": "0",
        "no_go_count": "1",
        "overall_state": "no_go",
        "primary_boundary": "no verified voiceprint",
        "recommended_next_action": "Run narrow embedding baseline.",
        "observation": "fixture",
    }


class SpeakerProfileGoNoGoBoardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_board_and_summary_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.speaker_profile_go_no_go_board.PROJECT_ROOT", root):
                outputs = write_outputs([_sample_board_row()], _sample_summary_row())

            board_csv, board_json, summary_csv, summary_json, board_md, summary_md = outputs
            for path in outputs:
                self.assertTrue(path.exists(), msg=str(path))

            with board_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, BOARD_COLUMNS)
                self.assertEqual(list(reader)[0]["checkpoint_name"], "embedding_trial_scaffold")

            with summary_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SUMMARY_COLUMNS)
                self.assertEqual(list(reader)[0]["overall_state"], "no_go")

            self.assertEqual(json.loads(board_json.read_text(encoding="utf-8"))[0]["go_no_go_state"], "no_go")
            self.assertIn("Speaker Profile Go-No-Go Board", board_md.read_text(encoding="utf-8"))
            self.assertIn("Speaker Profile Go-No-Go Summary", summary_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
