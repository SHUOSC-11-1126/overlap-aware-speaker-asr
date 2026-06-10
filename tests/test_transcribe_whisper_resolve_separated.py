from __future__ import annotations

import unittest

from src.config import load_config
from src.transcribe_whisper import find_case, resolve_separated_audio_paths


class TranscribeWhisperResolveSeparatedTest(unittest.TestCase):
    def test_resolve_separated_audio_paths_returns_two_tracks(self) -> None:
        config = load_config()
        case = find_case(config, "NoOverlap")
        paths = resolve_separated_audio_paths(config, case)
        self.assertEqual(len(paths), 2)
        labels = {label for label, _ in paths}
        self.assertEqual(labels, {"separated_spk1", "separated_spk2"})
        for _, path in paths:
            self.assertTrue(path.name.endswith(".wav"))


if __name__ == "__main__":
    unittest.main()
