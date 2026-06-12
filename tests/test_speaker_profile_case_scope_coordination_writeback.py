from __future__ import annotations

import unittest
from unittest.mock import patch

from src.speaker_profile_case_scope_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class SpeakerProfileCaseScopeCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_four_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 4)

    def test_build_fill_row_records_candidate_cases(self) -> None:
        row = build_fill_row(build_coordination_rows())
        self.assertEqual(row["completed_case_scope"], "NoOverlap")
        self.assertIn("LightOverlap", row["candidate_case_scope"])

    def test_run_coordination_writeback_requires_embedding_fill(self) -> None:
        with patch(
            "src.speaker_profile_case_scope_coordination_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "wave7_exploration_baseline_closure_complete"},
                {"execution_receipt_status": "pending"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
