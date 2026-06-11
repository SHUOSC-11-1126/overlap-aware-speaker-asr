from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.external_validation_candidates import (
    CSV_COLUMNS,
    build_external_validation_candidate_rows,
    write_outputs,
)


class ExternalValidationCandidatesWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_candidate_and_derived_artifacts(self) -> None:
        rows = build_external_validation_candidate_rows()
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.external_validation_candidates.PROJECT_ROOT", root):
                outputs = write_outputs(rows)

            for path in outputs:
                self.assertTrue(path.exists())

            csv_path = outputs[0]
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CSV_COLUMNS)
                loaded = list(reader)
            self.assertGreaterEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["label"], "external/sanity-check")

            payload = json.loads(outputs[1].read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["dataset_name"], loaded[0]["dataset_name"])
            self.assertIn("External Validation Candidates", outputs[2].read_text(encoding="utf-8"))
            self.assertTrue((root / "results" / "tables" / "external_validation_prioritization.csv").exists())
            self.assertTrue((root / "results" / "figures" / "external_validation_checklist.md").exists())


if __name__ == "__main__":
    unittest.main()
