from __future__ import annotations

import unittest
from unittest.mock import patch

from src.llm_critic_narrow_dry_run_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class LlmCriticNarrowDryRunCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_five_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 5)

    def test_build_fill_row_records_llm_critic_blocker(self) -> None:
        row = build_fill_row(build_coordination_rows(), "5")
        self.assertEqual(row["execution_receipt_status"], "llm_critic_narrow_dry_run_coordination_complete")
        self.assertEqual(row["blocker"], "verified_repair_claims_still_blocked")

    def test_run_coordination_writeback_requires_wave12_closure(self) -> None:
        with patch(
            "src.llm_critic_narrow_dry_run_coordination_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {"execution_status": "speaker_profile_heavyoverlap_diagnostic_coordination_complete"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave12_presentation_extension_complete",
                },
                {"overall_state": "qualitative_writeback_ready"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
