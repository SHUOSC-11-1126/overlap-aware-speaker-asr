from __future__ import annotations

import unittest

from src.hallucination_router import (
    route_by_overlap,
    route_min_degeneracy,
    summarize_routing,
)


class TestRouteMinDegeneracy(unittest.TestCase):
    def test_picks_lowest_score(self) -> None:
        deg = {"fixed_mixed": 3.0, "fixed_sep_trim": 1.2}
        self.assertEqual(route_min_degeneracy(deg, ["fixed_mixed", "fixed_sep_trim"]), "fixed_sep_trim")

    def test_degenerate_candidate_avoided(self) -> None:
        # separated track is hallucinating (very high compression ratio) -> avoid it
        deg = {"fixed_mixed": 1.4, "fixed_sep_trim": 16.0}
        self.assertEqual(route_min_degeneracy(deg, ["fixed_mixed", "fixed_sep_trim"]), "fixed_mixed")

    def test_stable_tiebreak_by_allowed_order(self) -> None:
        deg = {"fixed_mixed": 2.0, "fixed_sep_trim": 2.0}
        self.assertEqual(route_min_degeneracy(deg, ["fixed_sep_trim", "fixed_mixed"]), "fixed_sep_trim")

    def test_three_way(self) -> None:
        deg = {"fixed_mixed": 2.0, "fixed_sep": 9.0, "fixed_sep_trim": 1.1}
        self.assertEqual(
            route_min_degeneracy(deg, ["fixed_mixed", "fixed_sep", "fixed_sep_trim"]), "fixed_sep_trim"
        )


class TestRouteByOverlap(unittest.TestCase):
    def test_below_crossover_uses_mixed(self) -> None:
        self.assertEqual(route_by_overlap(0.10, threshold=0.17), "fixed_mixed")

    def test_at_or_above_crossover_uses_sep_trim(self) -> None:
        self.assertEqual(route_by_overlap(0.17, threshold=0.17), "fixed_sep_trim")
        self.assertEqual(route_by_overlap(0.6, threshold=0.17), "fixed_sep_trim")


class TestSummarizeRouting(unittest.TestCase):
    def _rows(self) -> list[dict]:
        # 2 dev cases + 1 test case; oracle is the per-row min CER
        return [
            {
                "split": "dev", "cer_oracle": 0.2,
                "cer_fixed_mixed": 0.5, "cer_fixed_sep": 0.7, "cer_fixed_sep_trim": 0.2,
                "cer_halluc_2way": 0.2, "cer_halluc_3way": 0.2, "cer_overlap_router": 0.5,
            },
            {
                "split": "dev", "cer_oracle": 0.3,
                "cer_fixed_mixed": 0.4, "cer_fixed_sep": 0.9, "cer_fixed_sep_trim": 0.3,
                "cer_halluc_2way": 0.3, "cer_halluc_3way": 0.3, "cer_overlap_router": 0.3,
            },
            {
                "split": "test", "cer_oracle": 0.1,
                "cer_fixed_mixed": 0.6, "cer_fixed_sep": 0.1, "cer_fixed_sep_trim": 0.15,
                "cer_halluc_2way": 0.15, "cer_halluc_3way": 0.1, "cer_overlap_router": 0.6,
            },
        ]

    def test_split_filtering_and_counts(self) -> None:
        dev = summarize_routing(self._rows(), "dev")
        self.assertEqual(dev["n"], 2)
        test = summarize_routing(self._rows(), "test")
        self.assertEqual(test["n"], 1)
        self.assertEqual(summarize_routing(self._rows(), None)["n"], 3)

    def test_regret_and_best(self) -> None:
        dev = summarize_routing(self._rows(), "dev")
        # oracle mean = (0.2+0.3)/2 = 0.25; halluc_2way mean = (0.2+0.3)/2 = 0.25 -> regret 0
        self.assertAlmostEqual(dev["mean_cer"]["oracle"], 0.25)
        self.assertAlmostEqual(dev["regret_vs_oracle"]["halluc_2way"], 0.0, places=6)
        # fixed_sep is worst on dev
        self.assertGreater(dev["regret_vs_oracle"]["fixed_sep"], dev["regret_vs_oracle"]["halluc_2way"])
        # best_reference_free must not be the overlap_router (which is given true overlap)
        self.assertNotEqual(dev["best_reference_free"], "overlap_router")

    def test_empty_split(self) -> None:
        self.assertEqual(summarize_routing(self._rows(), "missing")["n"], 0)


if __name__ == "__main__":
    unittest.main()
