from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.external_validation_license_confirmation import CONFIRMATION_COLUMNS, write_outputs


class ExternalValidationLicenseConfirmationWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_artifacts(self) -> None:
        row = {
            "dataset_name": "AISHELL-4",
            "label": "external/sanity-check",
            "license_id": "CC BY-SA 4.0",
            "license_status": "confirmed_research_cc_by_sa_4_0",
            "confirmation_status": "confirmed",
            "usage_scope": "research_only_sanity_check_slice",
            "source_url": "https://www.openslr.org/111/",
            "paper_url": "https://arxiv.org/abs/2104.03603",
            "attribution_note": "research only",
            "result_label": "external/sanity-check",
        }
        receipt = [{"execution_status": "license_confirmed", "confirmation_scope": "x", "dataset_name": "AISHELL-4", "license_status": row["license_status"], "writeback_note": "ok"}]
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.external_validation_license_confirmation.PROJECT_ROOT", root):
                paths = write_outputs(row, receipt)
            for path in paths:
                self.assertTrue(path.exists(), msg=str(path))
            with paths[0].open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, CONFIRMATION_COLUMNS)


if __name__ == "__main__":
    unittest.main()
