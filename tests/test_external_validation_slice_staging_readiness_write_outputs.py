from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.external_validation_slice_staging_readiness import READINESS_COLUMNS, write_outputs


def _sample_readiness_row() -> dict[str, str]:
    return {
        "dataset_name": "FixtureDataset",
        "slice_id": "slice-001",
        "label": "external/sanity-check",
        "license_status": "pending",
        "staging_status": "scaffold_only",
        "readiness_status": "not_ready",
        "blocker": "license_confirmation",
        "readiness_note": "fixture readiness note",
    }


def _sample_receipt_rows() -> list[dict[str, str]]:
    return [
        {
            "execution_status": "scaffold_only",
            "readiness_scope": "external_validation_slice_staging",
            "dataset_name": "FixtureDataset",
            "readiness_status": "not_ready",
            "writeback_note": "fixture receipt",
        }
    ]


class ExternalValidationSliceStagingReadinessWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_readiness_and_receipt_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.external_validation_slice_staging_readiness.PROJECT_ROOT", root):
                outputs = write_outputs(_sample_readiness_row(), _sample_receipt_rows())

            for path in outputs:
                self.assertTrue(path.exists(), msg=str(path))

            csv_path, json_path, md_path, receipt_json, receipt_md = outputs
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, READINESS_COLUMNS)
                self.assertEqual(list(reader)[0]["dataset_name"], "FixtureDataset")

            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["readiness_status"], "not_ready")
            self.assertIn("Staging Readiness", md_path.read_text(encoding="utf-8"))

            receipt_payload = json.loads(receipt_json.read_text(encoding="utf-8"))
            self.assertEqual(receipt_payload[0]["execution_status"], "scaffold_only")
            self.assertEqual(receipt_payload[0]["readiness_scope"], "external_validation_slice_staging")
            self.assertIn("Readiness Receipt", receipt_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
