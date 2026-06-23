import unittest
from pathlib import Path
import re

from scripts.build_static_demo import build_demo


ROOT = Path(__file__).resolve().parents[1]


class StaticDemoTest(unittest.TestCase):
    def test_demo_html_contains_interactive_sections(self):
        html = build_demo()
        self.assertIn("10 minute demo", html)
        self.assertIn("route challenge", html.lower())
        self.assertIn("Everybody's work fits into one pipeline", html)
        self.assertIn("AudioDepth", html)
        self.assertIn("MeetEval / cpWER", html)
        self.assertIn("LLM critic / RAG", html)
        self.assertIn("Source-disjoint", html)
        self.assertIn("oracle_for_abstained", html)

    def test_demo_file_can_be_written(self):
        path = ROOT / "demo" / "index.html"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("Overlap-aware Speaker ASR", text)
        self.assertIn("resources/mixed_audio/LightOverlap.wav", text)

    def test_referenced_local_assets_exist(self):
        html = build_demo()
        refs = set(re.findall(r"\.\./[^\"'`<> ]+", html))
        self.assertGreaterEqual(len(refs), 10)
        missing = []
        for ref in refs:
            target = (ROOT / "demo" / ref.rstrip("),.;")).resolve()
            if not target.exists():
                missing.append(ref)
        self.assertEqual([], sorted(missing))


if __name__ == "__main__":
    unittest.main()
