from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_tokenization_gain_scorecard_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_row,
    write_outputs,
)


class MeetEvalCpwerTokenizationGainScorecardHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_handoff_artifacts(self) -> None:
        handoff_row = build_handoff_row(
            {
                "recommended_default_mode": "character_spaced",
                "adapted_and_aligned_count": "5",
                "case_count": "5",
            }
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_tokenization_gain_scorecard_handoff.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(handoff_row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                self.assertEqual(list(reader)[0]["handoff_status"], "tokenization_gain_handoff_ready")
            self.assertIn("Tokenization Gain Scorecard Handoff", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
