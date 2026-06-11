from __future__ import annotations

import unittest

from src.external_validation_license_confirmation import (
    CONFIRMED_LICENSE_STATUS,
    apply_confirmation_to_mapping,
    build_confirmation_row,
)


class ExternalValidationLicenseConfirmationTest(unittest.TestCase):
    def test_build_confirmation_row_records_cc_by_sa(self) -> None:
        row = build_confirmation_row({"dataset_name": "AISHELL-4", "label": "external/sanity-check"})
        self.assertEqual(row["license_status"], CONFIRMED_LICENSE_STATUS)
        self.assertEqual(row["confirmation_status"], "confirmed")
        self.assertIn("CC BY-SA", row["license_id"])

    def test_apply_confirmation_to_mapping_updates_status(self) -> None:
        updated = apply_confirmation_to_mapping(
            {"dataset_name": "AISHELL-4", "license_status": "pending_confirmation"}
        )
        self.assertEqual(updated["license_status"], CONFIRMED_LICENSE_STATUS)
        self.assertEqual(updated["license_confirmation_status"], "confirmed")


if __name__ == "__main__":
    unittest.main()
