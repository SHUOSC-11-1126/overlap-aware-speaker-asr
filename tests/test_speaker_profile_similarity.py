from __future__ import annotations

import unittest

from src.speaker_profile_similarity import (
    build_profile_text,
    build_similarity_rows,
    build_speaker_profile_method_handoff_lines,
    build_speaker_profile_method_handoff_rows,
    build_speaker_profile_method_receipt_lines,
    build_speaker_profile_method_receipt_rows,
    build_speaker_profile_summary_lines,
    build_speaker_profile_triage_lines,
    build_speaker_profile_triage_rows,
    text_overlap_ratio,
)


class SpeakerProfileSimilarityTest(unittest.TestCase):
    def test_text_overlap_ratio_counts_shared_characters(self) -> None:
        self.assertEqual(text_overlap_ratio("甲乙丙", "甲乙"), 0.666667)
        self.assertEqual(text_overlap_ratio("完全不同", "甲乙"), 0.0)

    def test_build_profile_text_merges_snippet_texts(self) -> None:
        text = build_profile_text(
            [
                {"text": "我们支持这个观点"},
                {"text": "这个观点很重要"},
            ]
        )
        self.assertEqual(text, "我们支持这个观点这个观点很重要")

    def test_build_similarity_rows_compare_direct_and_swapped_alignment(self) -> None:
        rows = build_similarity_rows(
            case_ids=["DemoCase"],
            profile_texts={
                "con": "支持这个观点",
                "pro": "反对这个观点",
            },
            references={
                "DemoCase": {
                    "speaker_1_text": "支持这个观点",
                    "speaker_2_text": "反对这个观点",
                }
            },
            hypothesis_texts={
                "DemoCase": {
                    "speaker_1_text": "支持这个观点",
                    "speaker_2_text": "反对这个观点",
                    "hypothesis_source": "separated_whisper",
                }
            },
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "DemoCase")
        self.assertEqual(rows[0]["best_profile_alignment"], "direct")
        self.assertEqual(rows[0]["hypothesis_source"], "separated_whisper")
        self.assertGreater(rows[0]["direct_profile_score"], rows[0]["swapped_profile_score"])
        self.assertIn("lightweight risk signal", rows[0]["observation"])

    def test_build_speaker_profile_summary_lines_render_report(self) -> None:
        lines = build_speaker_profile_summary_lines(
            [
                {
                    "case_id": "DemoCase",
                    "best_profile_alignment": "direct",
                    "direct_profile_score": 1.0,
                    "swapped_profile_score": 0.333333,
                    "profile_confidence_gap": 0.666667,
                    "hypothesis_source": "separated_whisper",
                    "observation": "This is a lightweight risk signal, not speaker identification.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Speaker Profile Risk Summary", rendered)
        self.assertIn("DemoCase", rendered)
        self.assertIn("separated_whisper", rendered)
        self.assertIn("lightweight risk signal", rendered)

    def test_build_speaker_profile_triage_rows_summarize_swapped_pattern(self) -> None:
        rows = build_speaker_profile_triage_rows(
            [
                {
                    "case_id": "CaseA",
                    "best_profile_alignment": "swapped",
                    "profile_confidence_gap": 0.4,
                    "hypothesis_source": "separated_whisper_cleaned",
                },
                {
                    "case_id": "CaseB",
                    "best_profile_alignment": "swapped",
                    "profile_confidence_gap": 0.42,
                    "hypothesis_source": "separated_whisper",
                },
                {
                    "case_id": "CaseC",
                    "best_profile_alignment": "direct",
                    "profile_confidence_gap": 0.1,
                    "hypothesis_source": "separated_whisper",
                },
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dominant_pattern"], "swapped_bias")
        self.assertEqual(rows[0]["swapped_count"], "2")
        self.assertEqual(rows[0]["direct_count"], "1")
        self.assertIn("stronger profile method", rows[0]["next_action"].lower())

    def test_build_speaker_profile_triage_lines_render_card(self) -> None:
        lines = build_speaker_profile_triage_lines(
            [
                {
                    "dominant_pattern": "swapped_bias",
                    "case_count": "5",
                    "swapped_count": "5",
                    "direct_count": "0",
                    "average_confidence_gap": "0.413131",
                    "cleaned_source_count": "4",
                    "next_action": "Test a stronger profile method before claiming attribution value.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Speaker Profile Triage", rendered)
        self.assertIn("swapped_bias", rendered)
        self.assertIn("stronger profile method", rendered)

    def test_build_speaker_profile_method_handoff_rows_turn_triage_into_next_method(self) -> None:
        rows = build_speaker_profile_method_handoff_rows(
            [
                {
                    "dominant_pattern": "swapped_bias",
                    "case_count": "5",
                    "swapped_count": "5",
                    "direct_count": "0",
                    "average_confidence_gap": "0.413131",
                    "cleaned_source_count": "4",
                    "next_action": "Test a stronger profile method before claiming attribution value.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dominant_pattern"], "swapped_bias")
        self.assertEqual(rows[0]["first_method_direction"], "embedding_or_voiceprint_baseline")
        self.assertIn("speaker_profile_method_receipt.json", rows[0]["expected_evidence"])
        self.assertIn("not speaker-id success", rows[0]["handoff_note"].lower())

    def test_build_speaker_profile_method_handoff_lines_render_packet(self) -> None:
        lines = build_speaker_profile_method_handoff_lines(
            [
                {
                    "dominant_pattern": "swapped_bias",
                    "first_method_direction": "embedding_or_voiceprint_baseline",
                    "method_goal": "Test a stronger profile method before any attribution claim.",
                    "expected_evidence": "results/tables/speaker_profile_method_receipt.json",
                    "handoff_note": "Current signal is diagnostic only, not speaker-ID success.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Speaker Profile Method Handoff", rendered)
        self.assertIn("embedding_or_voiceprint_baseline", rendered)
        self.assertIn("speaker_profile_method_receipt.json", rendered)
        self.assertIn("diagnostic only", rendered)

    def test_build_speaker_profile_method_receipt_rows_create_template_evidence_target(self) -> None:
        rows = build_speaker_profile_method_receipt_rows(
            [
                {
                    "dominant_pattern": "swapped_bias",
                    "first_method_direction": "embedding_or_voiceprint_baseline",
                    "method_goal": "Test a stronger profile method before any attribution claim.",
                    "expected_evidence": "results/tables/speaker_profile_method_receipt.json",
                    "handoff_note": "Current signal is diagnostic only, not speaker-ID success.",
                }
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["execution_status"], "template_only")
        self.assertEqual(rows[0]["method_scope"], "embedding_or_voiceprint_baseline")
        self.assertIn("triage", rows[0]["expected_inputs"].lower())
        self.assertIn("diagnostic", rows[0]["expected_outputs"].lower())
        self.assertIn("has been executed", rows[0]["writeback_note"].lower())

    def test_build_speaker_profile_method_receipt_lines_render_template(self) -> None:
        lines = build_speaker_profile_method_receipt_lines(
            [
                {
                    "execution_status": "template_only",
                    "method_scope": "embedding_or_voiceprint_baseline",
                    "expected_inputs": "Speaker profile triage plus one stronger-method baseline stub.",
                    "expected_outputs": "Diagnostic stronger-method comparison note and a narrow evidence writeback.",
                    "writeback_note": "No stronger speaker-profile method has been executed yet; fill this receipt only after the first trial.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# Speaker Profile Method Receipt", rendered)
        self.assertIn("template_only", rendered)
        self.assertIn("embedding_or_voiceprint_baseline", rendered)
        self.assertIn("has been executed yet", rendered)


if __name__ == "__main__":
    unittest.main()
