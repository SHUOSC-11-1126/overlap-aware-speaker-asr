from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.external_validation_license_confirmation_scaffold import SCAFFOLD_COLUMNS, write_outputs


def _sample_scaffold_row() -> dict[str, str]:
    return {
        "dataset_name": "AISHELL-4",
        "label": "external/sanity-check",
        "license_status": "pending_confirmation",
        "confirmation_status": "template_only",
        "confirmation_step": "Record license decision.",
        "expected_writeback": "license gate receipt",
        "scaffold_note": "fixture",
    }


def _sample_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "scaffold_only",
        "confirmation_scope": "license_confirmation",
        "dataset_name": "AISHELL-4",
        "writeback_note": "fixture",
    }


class ExternalValidationLicenseConfirmationScaffoldWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_scaffold_and_receipt_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.external_validation_license_confirmation_scaffold.PROJECT_ROOT", root):
                outputs = write_outputs(_sample_scaffold_row(), [_sample_receipt_row()])

            for path in outputs:
                self.assertTrue(path.exists())

            with outputs[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, SCAFFOLD_COLUMNS)
                self.assertEqual(list(reader)[0]["confirmation_status"], "template_only")

            scaffold_json = json.loads(outputs[1].read_text(encoding="utf-8"))
            self.assertEqual(scaffold_json["dataset_name"], "AISHELL-4")
            receipt_json = json.loads(outputs[3].read_text(encoding="utf-8"))
            self.assertEqual(receipt_json[0]["confirmation_scope"], "license_confirmation")
            self.assertIn("license confirmation scaffold", outputs[2].read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
