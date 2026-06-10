from __future__ import annotations

import unittest

from src.build_synthetic_references import TIER_TO_LEVEL, snippet_transcript_path
from src.config import PROJECT_ROOT


class BuildSyntheticReferencesHelpersTest(unittest.TestCase):
    def test_tier_to_level_maps_synthetic_tiers(self) -> None:
        self.assertEqual(TIER_TO_LEVEL["SyntheticNoOverlap"], 0)
        self.assertEqual(TIER_TO_LEVEL["SyntheticHeavyOverlap"], 3)

    def test_snippet_transcript_path_under_results(self) -> None:
        path = snippet_transcript_path("demo_snippet")
        self.assertEqual(
            path,
            PROJECT_ROOT / "results" / "snippet_transcripts" / "demo_snippet_whisper.json",
        )


if __name__ == "__main__":
    unittest.main()
