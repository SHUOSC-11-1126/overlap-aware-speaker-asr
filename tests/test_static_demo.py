import unittest
from pathlib import Path
import re

from scripts.build_static_demo import build_demo


ROOT = Path(__file__).resolve().parents[1]


class StaticDemoTest(unittest.TestCase):
    def test_demo_html_contains_interactive_sections(self):
        html = build_demo()
        self.assertIn("GitHub-online evidence deck", html)
        self.assertIn("王景宏", html)
        self.assertIn("吴方舟/wfzark", html)
        self.assertIn("谢宇轩", html)
        self.assertIn("邵俊霖", html)
        self.assertIn("梁跃川", html)
        self.assertIn("张浩豪", html)
        self.assertIn("LLM rescoring / repair", html)
        self.assertIn("Emotion separation tax", html)
        self.assertIn("AudioDepth", html)
        self.assertIn("MeetEval / cpWER", html)
        self.assertIn("GitHub raw image", html)
        self.assertIn("CONTRIBUTIONS.md", html)

    def test_demo_file_can_be_written(self):
        path = ROOT / "demo" / "index.html"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")
        self.assertIn("Overlap-Aware Speaker ASR", text)
        self.assertIn("raw.githubusercontent.com", text)
        self.assertIn("github.com/SHUOSC-11-1126/overlap-aware-speaker-asr", text)

    def test_references_online_github_assets(self):
        html = build_demo()
        raw_refs = set(re.findall(r"https://raw\.githubusercontent\.com/[^\"'`<> ]+", html))
        github_refs = set(re.findall(r"https://github\.com/SHUOSC-11-1126/overlap-aware-speaker-asr[^\"'`<> ]*", html))
        self.assertGreaterEqual(len(raw_refs), 5)
        self.assertGreaterEqual(len(github_refs), 10)


if __name__ == "__main__":
    unittest.main()
