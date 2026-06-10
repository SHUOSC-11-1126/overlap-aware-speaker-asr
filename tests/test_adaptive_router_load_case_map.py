from __future__ import annotations

import unittest

from src.adaptive_router import load_case_map
from src.config import load_config


class AdaptiveRouterLoadCaseMapTest(unittest.TestCase):
    def test_load_case_map_indexes_configured_cases(self) -> None:
        case_map = load_case_map(load_config())
        self.assertEqual(len(case_map), 5)
        self.assertIn("LightOverlap", case_map)


if __name__ == "__main__":
    unittest.main()
