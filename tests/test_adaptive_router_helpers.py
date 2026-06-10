from __future__ import annotations

import unittest

from src.adaptive_router import select_method, to_float, to_int


class AdaptiveRouterHelpersTest(unittest.TestCase):
    def test_select_method_uses_overlap_level_rules(self) -> None:
        self.assertEqual(select_method(0)[0], "separated_whisper")
        self.assertEqual(select_method(1)[0], "mixed_whisper")
        self.assertEqual(select_method(3)[0], "separated_whisper")

    def test_to_int_and_to_float_parse_numeric_strings(self) -> None:
        self.assertEqual(to_int("12"), 12)
        self.assertEqual(to_float("0.5"), 0.5)

    def test_to_int_and_to_float_return_defaults_for_invalid_input(self) -> None:
        self.assertEqual(to_int("bad"), 0)
        self.assertEqual(to_float("bad"), 0.0)


if __name__ == "__main__":
    unittest.main()
