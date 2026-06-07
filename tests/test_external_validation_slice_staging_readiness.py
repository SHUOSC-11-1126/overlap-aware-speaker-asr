from __future__ import annotations

import unittest

from src.external_validation_slice_staging_readiness import build_readiness_row


class ExternalValidationSliceStagingReadinessTest(unittest.TestCase):
    def test_build_readiness_row_marks_not_ready_when_license_pending(self) -> None:
        row = build_readiness_row(
            {
                "dataset_name": "AISHELL-4",
                "slice_id": "aishell4_excerpt_001",
                "label": "external/sanity-check",
                "license_status": "pending_confirmation",
                "staging_status": "blocked_by_license_gate",
            }
        )

        self.assertEqual(row["readiness_status"], "not_ready")
        self.assertEqual(row["blocker"], "license_confirmation_pending")


if __name__ == "__main__":
    unittest.main()
