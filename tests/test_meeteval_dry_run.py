from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.meeteval_dry_run import (
    build_diagnostic_receipt_lines,
    build_diagnostic_receipt_row,
    build_diagnostic_summary_lines,
    extract_speakers,
    load_jsonl_segments,
    run_diagnostic,
    select_preferred_case,
    time_ranges_valid,
)


class MeetEvalDryRunTest(unittest.TestCase):
    def test_extract_speakers_collects_unique_labels(self) -> None:
        speakers = extract_speakers(
            [
                {"speaker": "SPEAKER_1"},
                {"speaker": "SPEAKER_2"},
                {"speaker": "SPEAKER_1"},
            ]
        )
        self.assertEqual(speakers, {"SPEAKER_1", "SPEAKER_2"})

    def test_time_ranges_valid_rejects_inverted_bounds(self) -> None:
        self.assertTrue(time_ranges_valid([{"start_time": 0.0, "end_time": 1.0}]))
        self.assertFalse(time_ranges_valid([{"start_time": 2.0, "end_time": 1.0}]))

    def test_time_ranges_valid_rejects_empty_segment_list(self) -> None:
        self.assertFalse(time_ranges_valid([]))

    def test_load_jsonl_segments_filters_by_session_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            jsonl_path = Path(tmp_dir) / "segments.jsonl"
            jsonl_path.write_text(
                "\n".join(
                    [
                        json.dumps({"session_id": "NoOverlap", "speaker": "SPEAKER_1", "text": "a"}),
                        json.dumps({"session_id": "HeavyOverlap", "speaker": "SPEAKER_1", "text": "b"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            segments = load_jsonl_segments(jsonl_path, "NoOverlap")
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0]["speaker"], "SPEAKER_1")

    def test_select_preferred_case_falls_back_to_no_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing = Path(tmp_dir) / "missing_checklist.csv"
            self.assertEqual(select_preferred_case(missing), "NoOverlap")

    def test_build_diagnostic_receipt_row_marks_diagnostic_complete(self) -> None:
        row = build_diagnostic_receipt_row(
            {
                "case_id": "NoOverlap",
                "hypothesis_source": "separated_whisper",
                "reference_segment_count": 3,
                "hypothesis_segment_count": 3,
                "speaker_set_match": True,
                "time_range_valid": True,
                "export_path_valid": True,
                "diagnostic_pass": True,
                "diagnostic_note": "Export path validated for NoOverlap; cpWER has not been computed.",
            }
        )

        self.assertEqual(row["execution_status"], "diagnostic_complete")
        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["diagnostic_pass"], "True")
        self.assertIn("still pending", row["writeback_note"].lower())

    def test_build_diagnostic_receipt_lines_render_completed_receipt(self) -> None:
        lines = build_diagnostic_receipt_lines(
            [
                {
                    "execution_status": "diagnostic_complete",
                    "run_scope": "single_verified_case",
                    "case_id": "NoOverlap",
                    "hypothesis_source": "separated_whisper",
                    "reference_segment_count": "3",
                    "hypothesis_segment_count": "3",
                    "speaker_set_match": "True",
                    "time_range_valid": "True",
                    "export_path_valid": "True",
                    "diagnostic_pass": "True",
                    "writeback_note": "Diagnostic dry run complete. MeetEval / cpWER evaluation still pending.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("diagnostic_complete", rendered)
        self.assertIn("NoOverlap", rendered)
        self.assertIn("still pending", rendered)

    def test_build_diagnostic_summary_lines_render_note(self) -> None:
        lines = build_diagnostic_summary_lines(
            {
                "case_id": "NoOverlap",
                "hypothesis_source": "separated_whisper",
                "reference_segment_count": 3,
                "hypothesis_segment_count": 3,
                "speaker_set_match": True,
                "time_range_valid": True,
                "export_path_valid": True,
                "diagnostic_pass": True,
                "diagnostic_note": "Export path validated for NoOverlap; cpWER has not been computed.",
            }
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Dry Run Diagnostic", rendered)
        self.assertIn("NoOverlap", rendered)
        self.assertIn("cpWER has not been computed", rendered)

    def test_run_diagnostic_validates_exported_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            tables_dir = root / "results" / "tables"
            tables_dir.mkdir(parents=True)

            reference_path = tables_dir / "meeteval_reference_segments.jsonl"
            hypothesis_path = tables_dir / "meeteval_hypothesis_segments.jsonl"
            reference_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "session_id": "NoOverlap",
                                "speaker": "SPEAKER_1",
                                "start_time": 0.0,
                                "end_time": 1.0,
                                "text": "alpha",
                                "source": "reference",
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "session_id": "NoOverlap",
                                "speaker": "SPEAKER_2",
                                "start_time": 1.0,
                                "end_time": 2.0,
                                "text": "beta",
                                "source": "reference",
                            },
                            ensure_ascii=False,
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            hypothesis_path.write_text(
                json.dumps(
                    {
                        "session_id": "NoOverlap",
                        "speaker": "SPEAKER_1",
                        "start_time": 0.0,
                        "end_time": 1.0,
                        "text": "alpha",
                        "source": "hypothesis",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            from src import meeteval_dry_run as module

            original_root = module.PROJECT_ROOT
            module.PROJECT_ROOT = root
            try:
                diagnostic = run_diagnostic("NoOverlap")
            finally:
                module.PROJECT_ROOT = original_root

        self.assertFalse(diagnostic["speaker_set_match"])
        self.assertTrue(diagnostic["export_path_valid"])
        self.assertFalse(diagnostic["diagnostic_pass"])


if __name__ == "__main__":
    unittest.main()
