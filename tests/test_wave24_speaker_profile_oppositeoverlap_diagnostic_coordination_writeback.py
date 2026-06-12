from __future__ import annotations

import unittest
from unittest.mock import patch

from src.wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class Wave24SpeakerProfileOppositeOverlapDiagnosticCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_five_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 5)

    def test_build_fill_row_records_oppositeoverlap_scope(self) -> None:
        row = build_fill_row(build_coordination_rows())
        self.assertEqual(row["diagnostic_case_scope"], "OppositeOverlap")
        self.assertEqual(
            row["execution_receipt_status"],
            "wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_complete",
        )

    def test_run_coordination_writeback_requires_wave24_closure(self) -> None:
        with patch(
            "src.wave24_speaker_profile_oppositeoverlap_diagnostic_coordination_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave24_presentation_extension_complete",
                },
                {"execution_status": "speaker_profile_oppositeoverlap_diagnostic_coordination_complete"},
                {"execution_status": "wave19_speaker_profile_oppositeoverlap_diagnostic_coordination_complete"},
                {"execution_status": "wave23_speaker_profile_heavyoverlap_diagnostic_coordination_complete"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
