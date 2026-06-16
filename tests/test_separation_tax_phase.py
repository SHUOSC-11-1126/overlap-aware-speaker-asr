from __future__ import annotations

import unittest

import numpy as np

from src.separation_tax_phase import (
    aggregate_phase,
    bootstrap_ci,
    estimate_crossover,
    insertion_share,
    nonzero_speech_span,
    rank_auc,
    router_choice,
    summarize_router,
    tail_rate,
    trim_silence,
)


class TestSpeechSpanAndTrim(unittest.TestCase):
    def test_nonzero_speech_span_basic(self) -> None:
        track = np.zeros(1000, dtype=np.float32)
        track[200:400] = 0.5
        start, end = nonzero_speech_span(track)
        self.assertEqual(start, 200)
        self.assertEqual(end, 400)

    def test_nonzero_speech_span_silent(self) -> None:
        self.assertEqual(nonzero_speech_span(np.zeros(500, dtype=np.float32)), (0, 0))
        self.assertEqual(nonzero_speech_span(np.array([], dtype=np.float32)), (0, 0))

    def test_trim_silence_crops_with_margin(self) -> None:
        track = np.zeros(20000, dtype=np.float32)
        track[8000:9000] = 0.8  # 1000 speech samples in the middle
        trimmed = trim_silence(track, margin_samples=1600)
        # speech (1000) + 2*margin (3200) = 4200, far smaller than original 20000
        self.assertLess(trimmed.size, track.size)
        self.assertGreaterEqual(trimmed.size, 1000)
        self.assertLessEqual(trimmed.size, 1000 + 2 * 1600 + 2)
        # the loud region must survive the crop
        self.assertGreater(float(np.max(np.abs(trimmed))), 0.5)

    def test_trim_silence_all_silent_returns_original(self) -> None:
        track = np.zeros(500, dtype=np.float32)
        out = trim_silence(track)
        self.assertEqual(out.size, track.size)


class TestCrossover(unittest.TestCase):
    def test_ascending_zero_crossing_interpolated(self) -> None:
        ratios = [0.0, 0.1, 0.2, 0.3]
        deltas = [-0.2, -0.1, 0.1, 0.3]  # crosses between 0.1 and 0.2
        r = estimate_crossover(ratios, deltas)
        assert r is not None
        self.assertAlmostEqual(r, 0.15, places=3)

    def test_positive_everywhere_returns_first_ratio(self) -> None:
        self.assertEqual(estimate_crossover([0.0, 0.5], [0.2, 0.4]), 0.0)

    def test_never_positive_returns_none(self) -> None:
        self.assertIsNone(estimate_crossover([0.0, 0.5, 0.9], [-0.3, -0.2, -0.1]))

    def test_handles_nan_and_unsorted(self) -> None:
        ratios = [0.3, 0.0, 0.2, 0.1]
        deltas = [0.3, -0.2, 0.1, float("nan")]
        r = estimate_crossover(ratios, deltas)
        assert r is not None
        # sorted -> 0.0:-0.2, 0.2:0.1 (0.1 dropped as NaN); crossing between 0.0 and 0.2
        self.assertTrue(0.0 < r < 0.2)


class TestTailRateAndAuc(unittest.TestCase):
    def test_tail_rate(self) -> None:
        self.assertAlmostEqual(tail_rate([0.1, 0.5, 1.5, 2.0]), 0.5)
        self.assertEqual(tail_rate([]), 0.0)
        self.assertEqual(tail_rate([1.0, 0.9]), 0.0)  # strictly greater than 1.0

    def test_rank_auc_perfect_separation(self) -> None:
        scores = [0.1, 0.2, 0.9, 1.0]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(rank_auc(scores, labels), 1.0)

    def test_rank_auc_reversed(self) -> None:
        scores = [0.9, 1.0, 0.1, 0.2]
        labels = [0, 0, 1, 1]
        self.assertAlmostEqual(rank_auc(scores, labels), 0.0)

    def test_rank_auc_ties_and_empty(self) -> None:
        self.assertAlmostEqual(rank_auc([0.5, 0.5], [0, 1]), 0.5)
        self.assertEqual(rank_auc([0.1, 0.2], [0, 0]), 0.5)  # one class empty


class TestBootstrapAndInsertion(unittest.TestCase):
    def test_bootstrap_ci_deterministic_and_ordered(self) -> None:
        vals = [0.0, 0.1, 0.2, 0.3, 0.4]
        lo1, hi1 = bootstrap_ci(vals, n_boot=200, seed=42)
        lo2, hi2 = bootstrap_ci(vals, n_boot=200, seed=42)
        self.assertEqual((lo1, hi1), (lo2, hi2))  # seeded => reproducible
        self.assertLessEqual(lo1, hi1)
        self.assertTrue(lo1 <= float(np.mean(vals)) <= hi1)

    def test_bootstrap_ci_single_value(self) -> None:
        self.assertEqual(bootstrap_ci([0.7]), (0.7, 0.7))

    def test_insertion_share(self) -> None:
        # hypothesis is reference + extra inserted chars => insertion-dominated
        share = insertion_share("ABCDEF", "ABCDEFGGGG")
        self.assertGreater(share, 0.9)
        # identical strings => no errors => 0.0
        self.assertEqual(insertion_share("ABC", "ABC"), 0.0)


class TestAggregatePhase(unittest.TestCase):
    def _rows(self) -> list[dict]:
        # two ratios, two pairs each; greedy config
        return [
            {"config": "greedy", "overlap_ratio": 0.0, "delta_cer": -0.5, "cer_mixed": 0.2, "cer_sep": 0.7},
            {"config": "greedy", "overlap_ratio": 0.0, "delta_cer": 0.1, "cer_mixed": 0.3, "cer_sep": 0.2},
            {"config": "greedy", "overlap_ratio": 0.5, "delta_cer": 0.4, "cer_mixed": 0.6, "cer_sep": 0.2},
            {"config": "greedy", "overlap_ratio": 0.5, "delta_cer": 0.2, "cer_mixed": 0.5, "cer_sep": 0.3},
            {"config": "fallback", "overlap_ratio": 0.0, "delta_cer": 0.9, "cer_mixed": 0.2, "cer_sep": 0.1},
        ]

    def test_aggregate_groups_by_ratio_for_config(self) -> None:
        agg = aggregate_phase(self._rows(), "greedy")
        self.assertEqual(len(agg), 2)  # two ratios
        r0 = next(a for a in agg if a["overlap_ratio"] == 0.0)
        self.assertEqual(r0["n"], 2)
        self.assertAlmostEqual(r0["mean_delta_cer"], -0.2, places=6)
        self.assertAlmostEqual(r0["sep_helps_frac"], 0.5, places=6)
        # tail rate counts cer_sep > 1.0; none here
        self.assertEqual(r0["tail_rate_sep"], 0.0)

    def test_aggregate_isolates_config(self) -> None:
        agg = aggregate_phase(self._rows(), "fallback")
        self.assertEqual(len(agg), 1)
        self.assertAlmostEqual(agg[0]["mean_delta_cer"], 0.9, places=6)

    def test_aggregate_tail_rate_detects_catastrophic(self) -> None:
        rows = [
            {"config": "greedy", "overlap_ratio": 0.0, "delta_cer": -4.0, "cer_mixed": 0.2, "cer_sep": 4.2},
            {"config": "greedy", "overlap_ratio": 0.0, "delta_cer": 0.1, "cer_mixed": 0.3, "cer_sep": 0.2},
        ]
        agg = aggregate_phase(rows, "greedy")
        self.assertAlmostEqual(agg[0]["tail_rate_sep"], 0.5, places=6)


class TestRouter(unittest.TestCase):
    def test_router_choice_guard(self) -> None:
        # both compression ratios below threshold -> trust separation (True)
        self.assertTrue(router_choice(1.0, 1.2, threshold=2.4))
        # one degenerate track -> distrust separation (False)
        self.assertFalse(router_choice(1.0, 16.3, threshold=2.4))
        # boundary is inclusive (<= threshold is non-degenerate)
        self.assertTrue(router_choice(2.4, 2.4, threshold=2.4))

    def test_summarize_router_policies_and_oracle(self) -> None:
        rows = [
            # healthy condition: sep+trim best, guard does not fire
            {"config": "greedy", "cer_mixed": 0.5, "cer_sep": 0.3, "cer_sep_trim": 0.2,
             "cr_sep1": 1.0, "cr_sep2": 1.1},
            # catastrophic sep: huge cr -> guard fires; trim rescues it
            {"config": "greedy", "cer_mixed": 0.6, "cer_sep": 9.0, "cer_sep_trim": 0.4,
             "cr_sep1": 1.0, "cr_sep2": 16.0},
            # fallback rows must be ignored
            {"config": "fallback", "cer_mixed": 0.9, "cer_sep": 0.9, "cer_sep_trim": 0.9,
             "cr_sep1": 1.0, "cr_sep2": 1.0},
        ]
        res = summarize_router(rows, threshold=2.4)
        self.assertEqual(res["n"], 2)  # only greedy rows
        self.assertAlmostEqual(res["guard_fired_frac"], 0.5)  # 1 of 2 flagged
        m = res["mean_cer"]
        # fixed_sep is dragged by the 9.0 catastrophic case
        self.assertAlmostEqual(m["fixed_sep"], (0.3 + 9.0) / 2)
        # always_trim avoids the blowup
        self.assertAlmostEqual(m["always_trim"], (0.2 + 0.4) / 2)
        # oracle picks min per row: min(.5,.3,.2)=.2 and min(.6,9,.4)=.4
        self.assertAlmostEqual(m["oracle"], (0.2 + 0.4) / 2)
        # guard_retry_trim: healthy row uses sep(.3), flagged row retries trim(.4)
        self.assertAlmostEqual(m["guard_retry_trim"], (0.3 + 0.4) / 2)
        # a sane policy should not be worse than fixed_sep here
        self.assertLessEqual(m["always_trim"], m["fixed_sep"])
        self.assertIn(res["best_deployable_policy"], m)
        self.assertNotEqual(res["best_deployable_policy"], "oracle")


if __name__ == "__main__":
    unittest.main()
