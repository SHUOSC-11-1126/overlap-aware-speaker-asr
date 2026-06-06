from __future__ import annotations

import json
import unittest

from src.export_meeteval_compatibility import (
    build_meeteval_compatibility_lines,
    build_meeteval_compatibility_rows,
    build_meeteval_readiness_lines,
    build_meeteval_readiness_rows,
    build_meeteval_segment_lines,
)


class MeetEvalCompatibilityTest(unittest.TestCase):
    def test_build_meeteval_compatibility_rows_summarize_reference_and_hypothesis(self) -> None:
        rows = build_meeteval_compatibility_rows(
            case_ids=["NoOverlap"],
            reference_payloads={
                "NoOverlap": {
                    "segments": [
                        {"speaker": "SPEAKER_1", "start": 0.0, "end": 1.0, "text": "alpha"},
                        {"speaker": "SPEAKER_2", "start": 1.0, "end": 2.0, "text": "beta"},
                    ]
                }
            },
            hypothesis_payloads={
                "NoOverlap": {
                    "segments": [
                        {"speaker": "SPEAKER_1", "start": 0.0, "end": 1.0, "text": "alpha"},
                        {"speaker": "SPEAKER_2", "start": 1.0, "end": 2.0, "text": "beta"},
                    ]
                }
            },
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["case_id"], "NoOverlap")
        self.assertEqual(rows[0]["reference_segment_count"], 2)
        self.assertEqual(rows[0]["hypothesis_segment_count"], 2)
        self.assertEqual(rows[0]["speaker_count"], 2)
        self.assertIn("compatibility bridge", rows[0]["observation"])

    def test_build_meeteval_segment_lines_render_jsonl_export(self) -> None:
        lines = build_meeteval_segment_lines(
            case_id="NoOverlap",
            source="reference",
            segments=[
                {"speaker": "SPEAKER_1", "start": 0.0, "end": 1.0, "text": "alpha"},
                {"speaker": "SPEAKER_2", "start": 1.0, "end": 2.0, "text": "beta"},
            ],
        )

        payload = [json.loads(line) for line in lines]

        self.assertEqual(len(payload), 2)
        self.assertEqual(payload[0]["session_id"], "NoOverlap")
        self.assertEqual(payload[0]["speaker"], "SPEAKER_1")
        self.assertEqual(payload[0]["source"], "reference")
        self.assertEqual(payload[1]["text"], "beta")

    def test_build_meeteval_compatibility_lines_render_note(self) -> None:
        lines = build_meeteval_compatibility_lines(
            [
                {
                    "case_id": "NoOverlap",
                    "reference_segment_count": 2,
                    "hypothesis_segment_count": 2,
                    "speaker_count": 2,
                    "hypothesis_source": "separated_whisper",
                    "reference_export": "results/tables/meeteval_reference_segments.jsonl",
                    "hypothesis_export": "results/tables/meeteval_hypothesis_segments.jsonl",
                    "observation": "Compatibility bridge only; no cpWER claim yet.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Compatibility Note", rendered)
        self.assertIn("NoOverlap", rendered)
        self.assertIn("meeteval_reference_segments.jsonl", rendered)
        self.assertIn("no cpWER claim yet", rendered)

    def test_build_meeteval_readiness_rows_summarize_fallback_and_next_step(self) -> None:
        rows = build_meeteval_readiness_rows(
            [
                {
                    "case_id": "NoOverlap",
                    "reference_segment_count": 25,
                    "hypothesis_segment_count": 25,
                    "speaker_count": 2,
                    "hypothesis_source": "separated_whisper",
                    "reference_export": "results/tables/meeteval_reference_segments.jsonl",
                    "hypothesis_export": "results/tables/meeteval_hypothesis_segments.jsonl",
                    "observation": "compatibility bridge only; this export does not claim cpWER evaluation yet.",
                },
                {
                    "case_id": "LightOverlap",
                    "reference_segment_count": 25,
                    "hypothesis_segment_count": 26,
                    "speaker_count": 2,
                    "hypothesis_source": "separated_whisper_cleaned",
                    "reference_export": "results/tables/meeteval_reference_segments.jsonl",
                    "hypothesis_export": "results/tables/meeteval_hypothesis_segments.jsonl",
                    "observation": "compatibility bridge only; this export does not claim cpWER evaluation yet.",
                },
            ]
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bridge_status"], "ready_for_dry_run")
        self.assertEqual(rows[0]["raw_source_count"], "1")
        self.assertEqual(rows[0]["cleaned_fallback_count"], "1")
        self.assertIn("cleaned fallback", rows[0]["readiness_note"].lower())
        self.assertIn("dry run", rows[0]["next_action"].lower())

    def test_build_meeteval_readiness_lines_render_summary_card(self) -> None:
        lines = build_meeteval_readiness_lines(
            [
                {
                    "bridge_status": "ready_for_dry_run",
                    "case_count": "5",
                    "raw_source_count": "1",
                    "cleaned_fallback_count": "4",
                    "readiness_note": "The bridge is export-complete, but cleaned fallback is still common.",
                    "next_action": "Use one narrow dry run before claiming any cpWER-style evaluation.",
                }
            ]
        )
        rendered = "\n".join(lines)

        self.assertIn("# MeetEval Readiness", rendered)
        self.assertIn("ready_for_dry_run", rendered)
        self.assertIn("cleaned fallback is still common", rendered)


if __name__ == "__main__":
    unittest.main()
