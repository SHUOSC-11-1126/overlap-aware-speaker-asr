from __future__ import annotations

import unittest
from unittest.mock import patch

from src.wave132_meeteval_official_narrow_dry_run_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class Wave132MeetevalOfficialNarrowDryRunCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_five_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 5)

    def test_build_fill_row_marks_wave132_official_coordination_complete(self) -> None:
        row = build_fill_row(build_coordination_rows(), "5")
        self.assertEqual(
            row["execution_receipt_status"],
            "wave132_meeteval_official_narrow_dry_run_coordination_complete",
        )

    def test_run_coordination_writeback_requires_wave132_closure(self) -> None:
        with patch(
            "src.wave132_meeteval_official_narrow_dry_run_coordination_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave132_presentation_extension_complete",
                },
                {"execution_status": "wave126_meeteval_official_narrow_dry_run_coordination_complete"},
                {"execution_status": "wave17_meeteval_cpwer_narrow_dry_run_coordination_complete"},
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
