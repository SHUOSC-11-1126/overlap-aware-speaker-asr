from __future__ import annotations

import unittest
from unittest.mock import patch

from src.meeteval_cpwer_character_level_official_execution import (
    build_execution_lines,
    build_tokenized_speaker_text_lists,
    extract_speakers,
    resolve_case_ids,
)


class MeetEvalCharacterLevelHelpersTest(unittest.TestCase):
    def test_extract_speakers_returns_sorted_unique_labels(self) -> None:
        speakers = extract_speakers(
            [
                {"speaker": "SPEAKER_2"},
                {"speaker": "SPEAKER_1"},
                {"speaker": "SPEAKER_1"},
            ]
        )
        self.assertEqual(speakers, ["SPEAKER_1", "SPEAKER_2"])

    def test_build_tokenized_speaker_text_lists_aligns_per_speaker(self) -> None:
        reference_segments = [
            {"speaker": "SPEAKER_1", "text": "你好"},
            {"speaker": "SPEAKER_2", "text": "世界"},
        ]
        hypothesis_segments = [
            {"speaker": "SPEAKER_1", "text": "你好"},
            {"speaker": "SPEAKER_2", "text": "世界"},
        ]
        reference_texts, hypothesis_texts = build_tokenized_speaker_text_lists(
            reference_segments,
            hypothesis_segments,
            ["SPEAKER_1", "SPEAKER_2"],
        )
        self.assertEqual(len(reference_texts), 2)
        self.assertEqual(len(hypothesis_texts), 2)
        self.assertIn(" ", reference_texts[0])

    @patch("src.meeteval_cpwer_character_level_official_execution.select_preferred_case", return_value="LightOverlap")
    def test_resolve_case_ids_handles_preferred_scope(self, _mock_select: object) -> None:
        self.assertEqual(resolve_case_ids("preferred", False), ["LightOverlap"])

    def test_resolve_case_ids_returns_all_gold_cases(self) -> None:
        case_ids = resolve_case_ids("all", False)
        self.assertEqual(len(case_ids), 5)
        self.assertIn("NoOverlap", case_ids)

    def test_build_execution_lines_renders_markdown_table(self) -> None:
        lines = build_execution_lines(
            [
                {
                    "case_id": "NoOverlap",
                    "hypothesis_source": "separated_whisper",
                    "execution_status": "character_level_cpwer_narrow_dry_run_complete",
                    "official_cpwer": "0.12",
                    "official_cpwer_raw": "0.15",
                    "cpwer_tool": "meeteval",
                    "speaker_count": "2",
                    "tokenization_mode": "character_spaced",
                    "result_label": "experimental/frontier",
                    "execution_note": "dry run complete",
                }
            ]
        )
        rendered = "\n".join(lines)
        self.assertIn("NoOverlap", rendered)
        self.assertIn("character_spaced", rendered)
        self.assertIn("experimental/frontier", rendered)


if __name__ == "__main__":
    unittest.main()
