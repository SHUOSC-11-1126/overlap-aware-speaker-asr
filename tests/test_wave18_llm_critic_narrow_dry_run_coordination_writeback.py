from __future__ import annotations

import unittest
from unittest.mock import patch

from src.wave18_llm_critic_narrow_dry_run_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class Wave18LlmCriticNarrowDryRunCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_five_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 5)

    def test_build_fill_row_marks_wave18_llm_critic_coordination_complete(self) -> None:
        row = build_fill_row(build_coordination_rows(), "5")
        self.assertEqual(row["execution_receipt_status"], "wave18_llm_critic_narrow_dry_run_coordination_complete")

    def test_run_coordination_writeback_requires_wave18_closure(self) -> None:
        with patch(
            "src.wave18_llm_critic_narrow_dry_run_coordination_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {"execution_status": "wave18_speaker_profile_heavyoverlap_diagnostic_coordination_complete"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave18_presentation_extension_complete",
                },
                {"overall_state": "qualitative_writeback_ready"},
                {"execution_status": "wave15_llm_critic_narrow_dry_run_coordination_complete"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
