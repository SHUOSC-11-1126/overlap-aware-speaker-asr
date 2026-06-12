from __future__ import annotations

import unittest
from unittest.mock import patch

from src.wave107_external_validation_narrow_slice_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class Wave107ExternalValidationNarrowSliceCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_five_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 5)

    def test_build_fill_row_marks_wave107_external_coordination_complete(self) -> None:
        row = build_fill_row(build_coordination_rows(), "aishell4_meeting_excerpt_stub_001")
        self.assertEqual(
            row["execution_receipt_status"],
            "wave107_external_validation_narrow_slice_coordination_complete",
        )

    def test_run_coordination_writeback_requires_wave107_closure(self) -> None:
        with patch(
            "src.wave107_external_validation_narrow_slice_coordination_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {"execution_status": "wave106_speaker_profile_oppositeoverlap_diagnostic_coordination_complete"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave107_presentation_extension_complete",
                },
                {"execution_status": "narrow_asr_complete"},
                {"overall_state": "ready_for_narrow_audio_eval"},
                {"execution_status": "wave101_external_validation_narrow_slice_coordination_complete"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
