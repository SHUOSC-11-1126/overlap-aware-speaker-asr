from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.meeteval_tokenization_adaptation_handoff import (
    HANDOFF_COLUMNS,
    build_handoff_row,
    write_outputs,
)


class MeetEvalTokenizationAdaptationHandoffWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_handoff_artifacts(self) -> None:
        handoff_row = build_handoff_row(
            {"aligned_count": "5", "total_count": "5", "queue_status": "queue_complete"}
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.meeteval_tokenization_adaptation_handoff.PROJECT_ROOT", root):
                csv_path, json_path, md_path = write_outputs(handoff_row)

            for path in (csv_path, json_path, md_path):
                self.assertTrue(path.exists())
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, HANDOFF_COLUMNS)
                self.assertEqual(list(reader)[0]["handoff_status"], "tokenization_adaptation_handoff_ready")
            self.assertIn("Tokenization Adaptation Handoff", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
