from __future__ import annotations

import unittest
from unittest.mock import patch

from src.frontier_execution_receipt_fill_queue_status import (
    build_fill_status_rows,
    build_status_summary,
    derive_fill_status,
)


class FrontierExecutionReceiptFillQueueStatusTest(unittest.TestCase):
    def test_derive_fill_status_awaiting_when_template_only(self) -> None:
        status = derive_fill_status("template_only", "receipt_ready_to_fill")

        self.assertEqual(status, "awaiting_fill")

    def test_build_fill_status_rows_maps_handoff_and_receipt(self) -> None:
        with patch(
            "src.frontier_execution_receipt_fill_queue_status.load_receipt_execution_status",
            return_value="template_only",
        ):
            rows = build_fill_status_rows(
                [
                    {
                        "handoff_order": "1",
                        "frontier_name": "meeteval_compatibility",
                        "readiness_status": "receipt_ready_to_fill",
                        "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
                    }
                ]
            )

        self.assertEqual(rows[0]["frontier_name"], "meeteval_compatibility")
        self.assertEqual(rows[0]["execution_status"], "template_only")
        self.assertEqual(rows[0]["fill_status"], "awaiting_fill")

    def test_build_status_summary_reports_fill_queue_ready(self) -> None:
        with patch(
            "src.frontier_execution_receipt_fill_queue_status.load_receipt_execution_status",
            return_value="template_only",
        ):
            rows = build_fill_status_rows(
                [
                    {
                        "handoff_order": "1",
                        "frontier_name": "meeteval_compatibility",
                        "readiness_status": "receipt_ready_to_fill",
                        "expected_outputs": "results/tables/meeteval_cpwer_execution_receipt.json",
                    },
                    {
                        "handoff_order": "2",
                        "frontier_name": "speaker_profile",
                        "readiness_status": "receipt_ready_to_fill",
                        "expected_outputs": "results/tables/speaker_profile_embedding_trial_execution_receipt.json",
                    },
                    {
                        "handoff_order": "3",
                        "frontier_name": "external_validation",
                        "readiness_status": "receipt_ready_to_fill",
                        "expected_outputs": "results/tables/external_validation_slice_staging_handoff_receipt.json",
                    },
                ]
            )
        summary = build_status_summary(rows)

        self.assertEqual(summary["combined_fill_status"], "fill_queue_ready")
        self.assertEqual(summary["awaiting_fill_count"], "3")


if __name__ == "__main__":
    unittest.main()
