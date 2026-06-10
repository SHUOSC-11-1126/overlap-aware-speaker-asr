from __future__ import annotations

import json
import unittest

from src.config import PROJECT_ROOT
from src.merge_speaker_tracks import merge_case


class MergeSpeakerTracksMergeCaseTest(unittest.TestCase):
    def test_merge_case_sorts_segments_by_start_then_speaker(self) -> None:
        output_path = merge_case("NoOverlap")
        payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["case_id"], "NoOverlap")
        self.assertEqual(payload["method"], "separated_tracks_whisper")
        segments = payload["segments"]
        self.assertGreater(len(segments), 0)

        starts = [(segment["start"], segment["speaker"]) for segment in segments]
        self.assertEqual(starts, sorted(starts))
        self.assertTrue(all(segment["speaker"] in {"SPEAKER_1", "SPEAKER_2"} for segment in segments))

    def test_merge_case_aggregates_runtime_from_both_speakers(self) -> None:
        output_path = merge_case("NoOverlap")
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        spk1 = json.loads(
            (PROJECT_ROOT / "results" / "transcripts_raw" / "NoOverlap_spk1_whisper.json").read_text(
                encoding="utf-8"
            )
        )
        spk2 = json.loads(
            (PROJECT_ROOT / "results" / "transcripts_raw" / "NoOverlap_spk2_whisper.json").read_text(
                encoding="utf-8"
            )
        )
        expected_runtime = round(float(spk1.get("runtime_sec", 0.0)) + float(spk2.get("runtime_sec", 0.0)), 3)
        self.assertEqual(payload["runtime_sec_total"], expected_runtime)


if __name__ == "__main__":
    unittest.main()
