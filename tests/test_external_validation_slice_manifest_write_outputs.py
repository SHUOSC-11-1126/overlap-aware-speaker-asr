from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.external_validation_slice_manifest import MANIFEST_COLUMNS, write_outputs


def _sample_manifest_row() -> dict[str, str]:
    return {
        "dataset_name": "AISHELL-4",
        "slice_id": "tiny-001",
        "label": "external/sanity-check",
        "license_status": "pending_confirmation",
        "mapping_status": "scaffold_only",
        "audio_path": "",
        "reference_path": "",
        "staging_status": "blocked_by_license_gate",
        "manifest_note": "fixture",
    }


def _sample_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "scaffold_only",
        "slice_scope": "tiny sanity-check",
        "dataset_name": "AISHELL-4",
        "staging_status": "blocked_by_license_gate",
        "writeback_note": "fixture",
    }


class ExternalValidationSliceManifestWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_manifest_and_receipt_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.external_validation_slice_manifest.PROJECT_ROOT", root):
                outputs = write_outputs(_sample_manifest_row(), [_sample_receipt_row()])

            for path in outputs:
                self.assertTrue(path.exists())

            manifest_csv = outputs[0]
            with manifest_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, MANIFEST_COLUMNS)
                self.assertEqual(list(reader)[0]["slice_id"], "tiny-001")

            manifest_json = json.loads(outputs[1].read_text(encoding="utf-8"))
            self.assertEqual(manifest_json["dataset_name"], "AISHELL-4")
            receipt_json = json.loads(outputs[3].read_text(encoding="utf-8"))
            self.assertEqual(receipt_json[0]["execution_status"], "scaffold_only")
            self.assertIn("External Validation Slice Manifest", outputs[2].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
