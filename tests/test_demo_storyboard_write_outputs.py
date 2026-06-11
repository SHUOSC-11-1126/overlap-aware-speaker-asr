from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.demo_storyboard import write_outputs


def _sample_cards() -> list[dict[str, str]]:
    return [
        {"title": "Problem", "body": "Fixture problem framing."},
        {"title": "Frontier", "body": "Fixture frontier note."},
    ]


def _sample_steps() -> list[dict[str, str]]:
    return [
        {
            "step_id": "1",
            "focus": "Problem framing",
            "talk_track": "Fixture talk track.",
            "artifact_anchor": "README.md",
        }
    ]


class DemoStoryboardWriteOutputsTest(unittest.TestCase):
    def test_write_outputs_emits_storyboard_and_walkthrough_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            with patch("src.demo_storyboard.PROJECT_ROOT", root):
                outputs = write_outputs(_sample_cards(), _sample_steps())

            for path in outputs:
                self.assertTrue(path.exists(), msg=str(path))

            json_path, md_path = outputs[0], outputs[1]
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload[0]["title"], "Problem")
            self.assertIn("Demo Storyboard", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
