from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.external_validation_slice_scaffold import MAPPING_COLUMNS, write_outputs


def _sample_stub() -> dict[str, object]:
    return {
        "dataset_name": "AISHELL-4",
        "label": "external/sanity-check",
        "slice_id": "aishell4_stub_001",
        "license_status": "pending_confirmation",
        "mapping_status": "scaffold_only",
    }


def _sample_mapping_row() -> dict[str, str]:
    return {
        "dataset_name": "AISHELL-4",
        "label": "external/sanity-check",
        "slice_id": "aishell4_stub_001",
        "license_status": "pending_confirmation",
        "audio_path": "",
        "reference_path": "",
        "speaker_schema": "speaker",
        "mapping_status": "scaffold_only",
        "scaffold_note": "fixture",
    }


def _sample_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "scaffold_only",
        "slice_scope": "tiny sanity-check",
        "dataset_name": "AISHELL-4",
        "mapping_artifact": "results/tables/external_validation_slice_mapping.json",
        "license_status": "pending_confirmation",
        "expected_outputs": "mapping json",
        "writeback_note": "fixture",
    }


class ExternalValidationSliceScaffoldWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_mapping_scaffold_and_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.external_validation_slice_scaffold.PROJECT_ROOT", root):
                outputs = write_outputs(_sample_stub(), _sample_mapping_row(), [_sample_receipt_row()])

            for path in outputs:
                self.assertTrue(path.exists())

            mapping_csv = outputs[1]
            with mapping_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, MAPPING_COLUMNS)
                self.assertEqual(list(reader)[0]["slice_id"], "aishell4_stub_001")

            mapping_json = json.loads(outputs[0].read_text(encoding="utf-8"))
            self.assertEqual(mapping_json["dataset_name"], "AISHELL-4")
            self.assertIn("External Validation Slice Scaffold", outputs[2].read_text(encoding="utf-8"))
            self.assertTrue(outputs[5].name == ".gitkeep")


if __name__ == "__main__":
    unittest.main()
