from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.external_validation_mini_sanity_check import CHECK_COLUMNS, write_outputs


class ExternalValidationMiniSanityCheckWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_artifacts(self) -> None:
        row = {
            "dataset_name": "AISHELL-4",
            "slice_id": "stub",
            "label": "external/sanity-check",
            "license_status": "confirmed_research_cc_by_sa_4_0",
            "license_confirmed": "True",
            "mapping_schema_valid": "True",
            "audio_staged": "False",
            "reference_staged": "False",
            "validation_status": "metadata_only_pass",
            "result_label": "external/sanity-check",
            "observation": "ok",
        }
        summary = [{"metric": "validation_status", "value": "metadata_only_pass", "label": "external/sanity-check"}]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.external_validation_mini_sanity_check.PROJECT_ROOT", root):
                paths = write_outputs(row, summary)
            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CHECK_COLUMNS)


if __name__ == "__main__":
    unittest.main()
