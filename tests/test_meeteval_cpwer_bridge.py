from __future__ import annotations

import unittest

from src.meeteval_cpwer_bridge import (
    build_cpwer_bridge_handoff_lines,
    build_cpwer_bridge_handoff_rows,
    build_cpwer_bridge_lines,
    build_cpwer_bridge_receipt_lines,
    build_cpwer_bridge_receipt_rows,
    build_cpwer_bridge_row,
    build_cpwer_bridge_summary_lines,
    build_cpwer_bridge_summary_row,
    compute_cer,
)


class MeetEvalCpwerBridgeTest(unittest.TestCase):
    def test_compute_cer_matches_normalized_edit_distance(self) -> None:
        self.assertEqual(compute_cer("你好世界", "你好世"), 0.25)

    def test_build_cpwer_bridge_row_prefers_direct_mapping(self) -> None:
        row = build_cpwer_bridge_row(
            case_id="NoOverlap",
            reference_segments=[
                {"speaker": "SPEAKER_1", "text": "alpha"},
                {"speaker": "SPEAKER_2", "text": "beta"},
            ],
            hypothesis_segments=[
                {"speaker": "SPEAKER_1", "text": "alpha"},
                {"speaker": "SPEAKER_2", "text": "beta"},
            ],
            hypothesis_source="separated_whisper",
        )

        self.assertEqual(row["case_id"], "NoOverlap")
        self.assertEqual(row["cpwer_bridge_lite"], 0.0)
        self.assertEqual(row["best_mapping"], "direct")
        self.assertIn("experimental/frontier", row["observation"])

    def test_build_cpwer_bridge_row_detects_swapped_mapping(self) -> None:
        row = build_cpwer_bridge_row(
            case_id="NoOverlap",
            reference_segments=[
                {"speaker": "SPEAKER_1", "text": "alpha"},
                {"speaker": "SPEAKER_2", "text": "beta"},
            ],
            hypothesis_segments=[
                {"speaker": "SPEAKER_1", "text": "beta"},
                {"speaker": "SPEAKER_2", "text": "alpha"},
            ],
            hypothesis_source="separated_whisper",
        )

        self.assertEqual(row["best_mapping"], "swapped")
        self.assertEqual(row["cpwer_bridge_lite"], 0.0)

    def test_build_cpwer_bridge_lines_render_note(self) -> None:
        lines = build_cpwer_bridge_lines(
            [
                {
                    "case_id": "NoOverlap",
                    "hypothesis_source": "separated_whisper",
                    "speaker_count": 2,
                    "direct_macro_cer": 0.1,
                    "swapped_macro_cer": 0.2,
                    "cpwer_bridge_lite": 0.1,
                    "best_mapping": "direct",
                    "observation": "experimental/frontier cpWER bridge-lite from JSONL exports; this is not a full MeetEval cpWER claim.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval cpWER Bridge", rendered)
        self.assertIn("NoOverlap", rendered)
        self.assertIn("not a full MeetEval", rendered)

    def test_build_cpwer_bridge_summary_row_averages_selected_cases(self) -> None:
        summary = build_cpwer_bridge_summary_row(
            [
                {"cpwer_bridge_lite": 0.1, "best_mapping": "direct"},
                {"cpwer_bridge_lite": 0.3, "best_mapping": "swapped"},
            ],
            "all_gold_cases",
        )

        self.assertEqual(summary["scope"], "all_gold_cases")
        self.assertEqual(summary["case_count"], 2)
        self.assertEqual(summary["average_cpwer_bridge_lite"], 0.2)
        self.assertEqual(summary["direct_mapping_count"], 1)
        self.assertEqual(summary["swapped_mapping_count"], 1)

    def test_build_cpwer_bridge_summary_lines_render_summary(self) -> None:
        lines = build_cpwer_bridge_summary_lines(
            {
                "scope": "all_gold_cases",
                "case_count": 5,
                "average_cpwer_bridge_lite": 0.12,
                "direct_mapping_count": 4,
                "swapped_mapping_count": 1,
                "observation": "experimental/frontier all-case cpWER bridge-lite summary; this is not a full MeetEval cpWER benchmark claim.",
            }
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval cpWER Bridge Summary", rendered)
        self.assertIn("all_gold_cases", rendered)

    def test_build_cpwer_bridge_handoff_rows_link_bridge_to_receipt(self) -> None:
        rows = build_cpwer_bridge_handoff_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "cpwer_bridge_lite": 0.054312,
                    "best_mapping": "direct",
                }
            ],
            {
                "scope": "single_verified_case",
                "case_count": 1,
                "average_cpwer_bridge_lite": 0.054312,
                "direct_mapping_count": 1,
                "swapped_mapping_count": 0,
            },
        )

        self.assertEqual(rows[0]["bridge_status"], "cpwer_bridge_complete")
        self.assertEqual(rows[0]["case_id"], "NoOverlap")
        self.assertIn("meeteval_cpwer_bridge_receipt.json", rows[0]["expected_evidence"])

    def test_build_cpwer_bridge_handoff_lines_render_handoff(self) -> None:
        lines = build_cpwer_bridge_handoff_lines(
            [
                {
                    "bridge_status": "cpwer_bridge_complete",
                    "case_id": "NoOverlap",
                    "cpwer_bridge_lite": "0.054312",
                    "best_mapping": "direct",
                    "bridge_goal": "Use the bridge-lite result as a narrow compatibility signal before any broader MeetEval integration.",
                    "primary_limitation": "This uses speaker-aggregated macro CER rather than a full MeetEval cpWER implementation.",
                    "expected_evidence": "results/tables/meeteval_cpwer_bridge_receipt.json",
                    "handoff_note": "MeetEval cpWER bridge-lite has been computed for one case; it is not a finished benchmark claim.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval cpWER Bridge Handoff", rendered)
        self.assertIn("cpwer_bridge_complete", rendered)

    def test_build_cpwer_bridge_receipt_rows_mark_bridge_complete(self) -> None:
        rows = build_cpwer_bridge_receipt_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "cpwer_bridge_lite": "0.054312",
                    "best_mapping": "direct",
                }
            ]
        )

        self.assertEqual(rows[0]["execution_status"], "bridge_complete")
        self.assertEqual(rows[0]["case_id"], "NoOverlap")
        self.assertIn("remains pending", rows[0]["writeback_note"].lower())

    def test_build_cpwer_bridge_receipt_lines_render_receipt(self) -> None:
        lines = build_cpwer_bridge_receipt_lines(
            [
                {
                    "execution_status": "bridge_complete",
                    "run_scope": "single_verified_case",
                    "case_id": "NoOverlap",
                    "cpwer_bridge_lite": "0.054312",
                    "best_mapping": "direct",
                    "expected_inputs": "results/tables/meeteval_reference_segments.jsonl; results/tables/meeteval_hypothesis_segments.jsonl",
                    "writeback_note": "cpWER bridge-lite complete for one case; full MeetEval evaluation remains pending.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval cpWER Bridge Receipt", rendered)
        self.assertIn("bridge_complete", rendered)


if __name__ == "__main__":
    unittest.main()
