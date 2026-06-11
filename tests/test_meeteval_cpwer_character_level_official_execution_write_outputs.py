from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_cpwer_character_level_official_execution import (
    EXECUTION_COLUMNS,
    write_outputs,
)
from src.meeteval_cpwer_official_execution import build_execution_row


class MeetEvalCpwerCharacterLevelOfficialExecutionWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_character_level_execution_artifacts(self) -> None:
        row = build_execution_row("NoOverlap", "separated_whisper", 0.11, 2, True, scored_length=20)
        row["tokenization_mode"] = "character_spaced"
        row["official_cpwer_raw"] = "0.18"
        row["execution_status"] = "character_level_cpwer_narrow_dry_run_complete"
        row["execution_note"] = "Character-spaced MeetEval cpWER narrow dry run completed for NoOverlap."

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_cpwer_character_level_official_execution.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs([row])

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, EXECUTION_COLUMNS)
                self.assertEqual(list(reader)[0]["tokenization_mode"], "character_spaced")
            self.assertIn("Character-Level Official Execution", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
