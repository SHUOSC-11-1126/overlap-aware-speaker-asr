from __future__ import annotations

import unittest
import unittest.mock

from src.compare_mixed_vs_separated import parse_args


class CompareMixedVsSeparatedMainTest(unittest.TestCase):
    def test_parse_args_requires_case_flag(self) -> None:
        with unittest.mock.patch("sys.argv", ["compare_mixed_vs_separated", "--case", "NoOverlap"]):
            args = parse_args()
        self.assertEqual(args.case, "NoOverlap")


if __name__ == "__main__":
    unittest.main()
