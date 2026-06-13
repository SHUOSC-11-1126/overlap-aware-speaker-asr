from __future__ import annotations

import unittest
from unittest.mock import patch

from src.wave142_exploration_baseline_closure_writeback import (
    build_closure_rows,
    build_fill_row,
    run_closure_writeback,
)


class Wave142ExplorationBaselineClosureWritebackTest(unittest.TestCase):
    def test_build_closure_rows_has_five_sections(self) -> None:
        self.assertEqual(len(build_closure_rows()), 5)

    def test_build_fill_row_marks_wave142_closure_complete(self) -> None:
        row = build_fill_row(build_closure_rows())
        self.assertEqual(row["execution_receipt_status"], "wave142_exploration_baseline_closure_complete")

    def test_run_closure_writeback_requires_wave141_chain(self) -> None:
        with patch(
            "src.wave142_exploration_baseline_closure_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {"execution_status": "wave141_speaker_profile_heavyoverlap_diagnostic_coordination_complete"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave141_presentation_extension_complete",
                },
                {"coordination_state": "all_ready"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_closure_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
