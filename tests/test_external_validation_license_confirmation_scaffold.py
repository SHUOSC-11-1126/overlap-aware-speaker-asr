from __future__ import annotations

import unittest

from src.external_validation_license_confirmation_scaffold import build_scaffold_row


class ExternalValidationLicenseConfirmationScaffoldTest(unittest.TestCase):
    def test_build_scaffold_row_stays_template_only(self) -> None:
        row = build_scaffold_row(
            {
                "dataset_name": "AISHELL-4",
                "label": "external/sanity-check",
                "license_status": "pending_confirmation",
            }
        )

        self.assertEqual(row["confirmation_status"], "template_only")
        self.assertEqual(row["license_status"], "pending_confirmation")


if __name__ == "__main__":
    unittest.main()
