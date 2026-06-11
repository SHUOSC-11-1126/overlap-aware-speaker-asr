from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.external_validation_license_gate import GATE_COLUMNS, write_outputs


def _sample_gate_row() -> dict[str, str]:
    return {
        "dataset_name": "AISHELL-4",
        "label": "external/sanity-check",
        "license_status": "pending_confirmation",
        "gate_step": "Confirm license terms.",
        "gate_order": "1",
        "gate_note": "Read the official release page.",
        "next_gate": "Document the license decision.",
    }


def _sample_receipt_row() -> dict[str, str]:
    return {
        "execution_status": "scaffold_only",
        "slice_scope": "tiny sanity-check",
        "dataset_name": "AISHELL-4",
        "license_status": "pending_confirmation",
        "expected_inputs": "license confirmation note",
        "writeback_note": "fixture",
    }


class ExternalValidationLicenseGateWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_gate_and_receipt_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.external_validation_license_gate.PROJECT_ROOT", root):
                outputs = write_outputs([_sample_gate_row()], [_sample_receipt_row()])

            gate_csv, gate_json, gate_md, receipt_json, receipt_md = outputs
            for path in outputs:
                self.assertTrue(path.exists())

            with gate_csv.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, GATE_COLUMNS)
                self.assertEqual(list(reader)[0]["license_status"], "pending_confirmation")

            gate_payload = json.loads(gate_json.read_text(encoding="utf-8"))
            self.assertEqual(gate_payload[0]["dataset_name"], "AISHELL-4")
            receipt_payload = json.loads(receipt_json.read_text(encoding="utf-8"))
            self.assertEqual(receipt_payload[0]["execution_status"], "scaffold_only")

            self.assertIn("External Validation License Gate", gate_md.read_text(encoding="utf-8"))
            self.assertIn("license gate receipt", receipt_md.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
