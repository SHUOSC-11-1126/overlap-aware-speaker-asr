import unittest
from pathlib import Path

from scripts.build_asr_effect_demo import build_demo, build_html


ROOT = Path(__file__).resolve().parents[1]


class AsrEffectDemoTest(unittest.TestCase):
    def test_html_contains_direct_transcript_demo(self):
        html = build_html()
        self.assertIn("Play the audio, then compare what ASR actually recognized.", html)
        self.assertIn("LightOverlap", html)
        self.assertIn("HeavyOverlap", html)
        self.assertIn("Reference transcript", html)
        self.assertIn("Mixed Whisper output", html)
        self.assertIn("Separated speaker output", html)
        self.assertIn("Cleaned separated output", html)
        self.assertIn("../resources/mixed_audio/LightOverlap.wav", html)
        self.assertIn("0.211", html)
        self.assertIn("separated route is much closer", html)

    def test_demo_file_can_be_written(self):
        path = build_demo()
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("ASR Transcript Effect Demo", text)
        self.assertIn("local audio + committed transcript JSON + committed CER CSV", text)
        self.assertIn("Raw separated transcript JSON is not present in this checkout", text)

    def test_audio_sources_exist_for_demo_cases(self):
        for case_id in ["LightOverlap", "HeavyOverlap", "NoOverlap", "OppositeOverlap"]:
            self.assertTrue((ROOT / "resources" / "mixed_audio" / f"{case_id}.wav").exists())


if __name__ == "__main__":
    unittest.main()
