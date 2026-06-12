from __future__ import annotations

import unittest
from unittest.mock import patch

from src.cascade_benchmark_phase4_gate_coordination_writeback import (
    build_coordination_rows,
    build_fill_row,
    run_coordination_writeback,
)


class CascadeBenchmarkPhase4GateCoordinationWritebackTest(unittest.TestCase):
    def test_build_coordination_rows_has_five_sections(self) -> None:
        self.assertEqual(len(build_coordination_rows()), 5)

    def test_build_fill_row_records_phase4_gate(self) -> None:
        row = build_fill_row(build_coordination_rows())
        self.assertEqual(row["phase4_gate_id"], "phase4_synthetic_surface_refresh")
        self.assertEqual(row["execution_receipt_status"], "cascade_benchmark_phase4_gate_coordination_complete")

    def test_run_coordination_writeback_requires_wave13_closure(self) -> None:
        with patch(
            "src.cascade_benchmark_phase4_gate_coordination_writeback.load_json_dict",
            side_effect=[
                {"execution_status": "pending"},
                {"execution_status": "cascade_benchmark_phase3_gate_coordination_complete"},
                {"execution_status": "speaker_profile_oppositeoverlap_diagnostic_coordination_complete"},
                {
                    "fill_status": "writeback_filled",
                    "storyboard_receipt_status": "wave13_presentation_extension_complete",
                },
            ],
        ):
            with self.assertRaises(RuntimeError):
                run_coordination_writeback(force=True)


if __name__ == "__main__":
    unittest.main()
