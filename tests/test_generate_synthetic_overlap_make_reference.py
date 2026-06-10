from __future__ import annotations

import unittest
from pathlib import Path

from src.config import PROJECT_ROOT
from src.generate_synthetic_overlap import make_reference


class GenerateSyntheticOverlapMakeReferenceTest(unittest.TestCase):
    def test_make_reference_builds_synthetic_placeholder_metadata(self) -> None:
        mixed = PROJECT_ROOT / "results" / "synthetic_audio" / "demo_mixed.wav"
        spk1 = PROJECT_ROOT / "results" / "synthetic_audio" / "demo_spk1.wav"
        spk2 = PROJECT_ROOT / "results" / "synthetic_audio" / "demo_spk2.wav"
        ref = make_reference(
            sample_id="demo_002",
            tier="SyntheticMidOverlap",
            overlap_ratio=0.35,
            con_source="con_a.wav",
            pro_source="pro_b.wav",
            mixed_path=mixed,
            spk1_path=spk1,
            spk2_path=spk2,
        )
        self.assertEqual(ref["tier"], "SyntheticMidOverlap")
        self.assertEqual(ref["status"], "draft")
        self.assertTrue(ref["spk2_audio_path"].endswith("demo_spk2.wav"))


if __name__ == "__main__":
    unittest.main()
