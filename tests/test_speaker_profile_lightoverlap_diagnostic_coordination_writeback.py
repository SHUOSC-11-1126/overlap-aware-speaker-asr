from __future__ import annotations

import unittest
from unittest.mock import patch

from src.speaker_profile_lightoverlap_diagnostic_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class SpeakerProfileLightOverlapDiagnosticCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_four_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 4)

    def test_build_fill_row_records_lightoverlap_scope(self) -> None:
        row = build_fill_row(build_coordination_rows())
        self.assertEqual(row["diagnostic_case_scope"], "LightOverlap")
        self.assertEqual(row["execution_receipt_status"], "speaker_profile_lightoverlap_diagnostic_coordination_complete")

    def test_run_coordination_writeback_requires_wave8_closure(self) -> None:
        with patch(
            "src.speaker_profile_lightoverlap_diagnostic_coordination_writeback.load_json_dict",
            return_value={"execution_status": "pending"},
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
