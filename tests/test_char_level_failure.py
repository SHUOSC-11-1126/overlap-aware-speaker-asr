"""Tests for RQ35 char-level cpWER failure-mode characterisation (experimental/frontier).

Pin the PURE helpers used by
``results/frontier/char_level_failure_modes/char_level_failure_analysis.py``:
char-level tokenisation, MeetEval segment construction, the cpWER/orcWER
error-decomposition wrapper, ranking / top-N / set-overlap, Spearman, the
4-mode failure classifier (mirrors RQ12), the Whisper compression-ratio proxy,
and the error-breakdown aggregator. Synthetic data only -- no AISHELL-4 file,
no Whisper, no audio.
"""
from __future__ import annotations

import sys
import unittest
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")  # MeetEval prints "Assuming sort=False" spam

# Make the analysis module importable when running from the repo root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = (
    PROJECT_ROOT
    / "results"
    / "frontier"
    / "char_level_failure_modes"
)
sys.path.insert(0, str(SCRIPT_DIR))

from char_level_failure_analysis import (  # noqa: E402
    build_mixed_segment,
    build_segments,
    classify_failure,
    compression_ratio,
    compute_cpwer_with_decomp,
    compute_orcwer_with_decomp,
    max_cr_separated,
    rank_windows,
    set_overlap,
    spearman_rho,
    to_char_level,
    top_n_window_ids,
    total_error_breakdown,
)


# ----------------------------------------------------------------- tokenisation
class TestToCharLevel(unittest.TestCase):
    def test_inserts_spaces_between_each_character(self) -> None:
        self.assertEqual(to_char_level("你好世界"), "你 好 世 界")

    def test_single_character_no_trailing_space(self) -> None:
        self.assertEqual(to_char_level("你"), "你")

    def test_empty_string_stays_empty(self) -> None:
        self.assertEqual(to_char_level(""), "")

    def test_preserves_character_order(self) -> None:
        self.assertEqual(to_char_level("abc"), "a b c")
        self.assertEqual(to_char_level("中英文"), "中 英 文")


# ------------------------------------------------------------- segment building
class TestBuildSegments(unittest.TestCase):
    def test_char_level_splits_into_chars(self) -> None:
        segs = build_segments({"A": "你好"}, char_level=True)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["words"], "你 好")
        self.assertEqual(segs[0]["speaker"], "A")

    def test_word_level_keeps_whole_string_as_one_token(self) -> None:
        segs = build_segments({"A": "你好"}, char_level=False)
        self.assertEqual(segs[0]["words"], "你好")

    def test_skips_empty_and_whitespace_speakers(self) -> None:
        segs = build_segments({"A": "你好", "B": "", "C": "   "}, char_level=True)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["speaker"], "A")

    def test_empty_dict_returns_empty_list(self) -> None:
        self.assertEqual(build_segments({}, char_level=True), [])


class TestBuildMixedSegment(unittest.TestCase):
    def test_char_level_mixed(self) -> None:
        segs = build_mixed_segment("你好", char_level=True)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["speaker"], "mix")
        self.assertEqual(segs[0]["words"], "你 好")

    def test_empty_mixed_returns_empty(self) -> None:
        self.assertEqual(build_mixed_segment("", char_level=True), [])
        self.assertEqual(build_mixed_segment("   ", char_level=True), [])


# --------------------------------------------------------- cpwer decomposition
class TestComputeCpwerWithDecomp(unittest.TestCase):
    def test_perfect_match_is_zero_error(self) -> None:
        out = compute_cpwer_with_decomp({"A": "你好"}, {"A": "你好"}, char_level=True)
        self.assertEqual(out["error_rate"], 0.0)
        self.assertEqual(out["substitutions"], 0)
        self.assertEqual(out["insertions"], 0)
        self.assertEqual(out["deletions"], 0)
        self.assertEqual(out["length"], 2)
        self.assertFalse(out["empty"])

    def test_all_substitutions_no_ins_no_del(self) -> None:
        # same length, every char different -> all subs
        out = compute_cpwer_with_decomp({"A": "你好"}, {"A": "他们"}, char_level=True)
        self.assertEqual(out["substitutions"], 2)
        self.assertEqual(out["insertions"], 0)
        self.assertEqual(out["deletions"], 0)
        self.assertAlmostEqual(out["error_rate"], 1.0)

    def test_all_insertions(self) -> None:
        # hyp = ref + extra chars -> all insertions
        out = compute_cpwer_with_decomp({"A": "你好"}, {"A": "你好世界"}, char_level=True)
        self.assertEqual(out["insertions"], 2)
        self.assertEqual(out["substitutions"], 0)
        self.assertEqual(out["deletions"], 0)

    def test_all_deletions(self) -> None:
        out = compute_cpwer_with_decomp({"A": "你好世界"}, {"A": "你好"}, char_level=True)
        self.assertEqual(out["deletions"], 2)
        self.assertEqual(out["substitutions"], 0)
        self.assertEqual(out["insertions"], 0)
        self.assertEqual(out["length"], 4)
        self.assertAlmostEqual(out["error_rate"], 0.5)

    def test_empty_hyp_returns_sentinel(self) -> None:
        out = compute_cpwer_with_decomp({"A": "你好"}, {"A": ""}, char_level=True)
        self.assertEqual(out["error_rate"], 1.0)
        self.assertTrue(out["empty"])
        self.assertEqual(out["length"], 0)

    def test_empty_ref_returns_sentinel(self) -> None:
        out = compute_cpwer_with_decomp({"A": ""}, {"A": "你好"}, char_level=True)
        self.assertEqual(out["error_rate"], 1.0)
        self.assertTrue(out["empty"])

    def test_multi_speaker_perfect(self) -> None:
        out = compute_cpwer_with_decomp(
            {"A": "你好", "B": "今天"}, {"A": "你好", "B": "今天"}, char_level=True
        )
        self.assertEqual(out["error_rate"], 0.0)
        self.assertEqual(out["length"], 4)


# --------------------------------------------------------- orcwer decomposition
class TestComputeOrcwerWithDecomp(unittest.TestCase):
    def test_perfect_single_speaker(self) -> None:
        out = compute_orcwer_with_decomp({"A": "你好"}, "你好", char_level=True)
        self.assertEqual(out["error_rate"], 0.0)
        self.assertEqual(out["substitutions"], 0)
        self.assertFalse(out["empty"])

    def test_insertion_in_mixed(self) -> None:
        out = compute_orcwer_with_decomp({"A": "你好"}, "你好世", char_level=True)
        self.assertEqual(out["insertions"], 1)
        self.assertEqual(out["substitutions"], 0)
        self.assertAlmostEqual(out["error_rate"], 0.5)

    def test_empty_mixed_returns_sentinel(self) -> None:
        out = compute_orcwer_with_decomp({"A": "你好"}, "", char_level=True)
        self.assertEqual(out["error_rate"], 1.0)
        self.assertTrue(out["empty"])


# --------------------------------------------------------- compression ratio
class TestCompressionRatio(unittest.TestCase):
    def test_repetitive_text_higher_than_diverse(self) -> None:
        repetitive = "小小小小小小小小小小小小"
        diverse = "今天天气真好我们去公园散步吧"
        self.assertGreater(compression_ratio(repetitive), compression_ratio(diverse))

    def test_empty_is_zero(self) -> None:
        self.assertEqual(compression_ratio(""), 0.0)
        self.assertEqual(compression_ratio("   "), 0.0)

    def test_matches_whisper_formula_positive(self) -> None:
        import zlib
        text = "今天天气真好"
        b = text.encode("utf-8")
        expected = len(b) / len(zlib.compress(b))
        self.assertAlmostEqual(compression_ratio(text), expected, places=6)


class TestMaxCrSeparated(unittest.TestCase):
    def test_returns_max_across_speakers(self) -> None:
        win = {"separated_text_per_speaker": {
            "A": "小" * 50,   # highly repetitive -> high CR
            "B": "今天天气真好我们去公园散步吧",  # diverse -> low CR
        }}
        cr_a = compression_ratio("小" * 50)
        cr_b = compression_ratio("今天天气真好我们去公园散步吧")
        self.assertAlmostEqual(max_cr_separated(win), max(cr_a, cr_b), places=6)

    def test_empty_speakers_returns_zero(self) -> None:
        self.assertEqual(max_cr_separated({"separated_text_per_speaker": {}}), 0.0)
        self.assertEqual(
            max_cr_separated({"separated_text_per_speaker": {"A": "", "B": "  "}}),
            0.0,
        )


# --------------------------------------------------------- ranking helpers
class TestRankWindows(unittest.TestCase):
    def test_descending_sort_with_ranks(self) -> None:
        rows = [
            {"window_id": 0, "v": 0.5},
            {"window_id": 1, "v": 1.5},
            {"window_id": 2, "v": 1.0},
        ]
        ranking = rank_windows(rows, "v", descending=True)
        self.assertEqual([r["window_id"] for r in ranking], [1, 2, 0])
        self.assertEqual([r["rank"] for r in ranking], [1, 2, 3])

    def test_ascending_sort(self) -> None:
        rows = [{"window_id": i, "v": v} for i, v in enumerate([3.0, 1.0, 2.0])]
        ranking = rank_windows(rows, "v", descending=False)
        self.assertEqual([r["window_id"] for r in ranking], [1, 2, 0])

    def test_stable_tie_order(self) -> None:
        rows = [{"window_id": 5, "v": 1.0}, {"window_id": 3, "v": 1.0}]
        ranking = rank_windows(rows, "v", descending=True)
        # ties keep original order
        self.assertEqual([r["window_id"] for r in ranking], [5, 3])


class TestTopNWindowIds(unittest.TestCase):
    def test_top_n_returns_set(self) -> None:
        ranking = [
            {"window_id": 1, "rank": 1, "value": 1.5},
            {"window_id": 2, "rank": 2, "value": 1.0},
            {"window_id": 0, "rank": 3, "value": 0.5},
        ]
        self.assertEqual(top_n_window_ids(ranking, 2), {1, 2})


class TestSetOverlap(unittest.TestCase):
    def test_partial_overlap(self) -> None:
        out = set_overlap({1, 2, 3}, {2, 3, 4})
        self.assertEqual(out["intersection"], [2, 3])
        self.assertEqual(out["intersection_size"], 2)
        self.assertEqual(out["union_size"], 4)
        self.assertAlmostEqual(out["jaccard"], 0.5)

    def test_disjoint_sets(self) -> None:
        out = set_overlap({1, 2}, {3, 4})
        self.assertEqual(out["intersection_size"], 0)
        self.assertAlmostEqual(out["jaccard"], 0.0)


# --------------------------------------------------------- spearman
class TestSpearmanRho(unittest.TestCase):
    def test_perfect_positive(self) -> None:
        rho, _ = spearman_rho([1, 2, 3, 4], [10, 20, 30, 40])
        self.assertAlmostEqual(rho, 1.0, places=6)

    def test_perfect_negative(self) -> None:
        rho, _ = spearman_rho([1, 2, 3, 4], [40, 30, 20, 10])
        self.assertAlmostEqual(rho, -1.0, places=6)

    def test_length_mismatch_returns_nan(self) -> None:
        rho, _ = spearman_rho([1, 2, 3], [1, 2])
        import math
        self.assertTrue(math.isnan(rho))


# --------------------------------------------------------- failure classifier
class TestClassifyFailure(unittest.TestCase):
    def test_not_failure_returns_none(self) -> None:
        # router picked separated, separated is oracle-best -> no regret
        self.assertEqual(
            classify_failure("separated", 0.5, 0.4, 0.4, 0.4, 1.0),
            "none",
        )

    def test_separated_hallucination_cr_caught(self) -> None:
        # router picked separated, separated lost (1.5 > 0.5), sep>1.0, CR>2.4
        self.assertEqual(
            classify_failure("separated", 0.5, 1.5, 1.5, 0.5, 3.0),
            "separated_hallucination_cr_caught",
        )

    def test_separated_hallucination_cr_missed(self) -> None:
        # router picked separated, separated lost, sep>1.0, CR<=2.4
        self.assertEqual(
            classify_failure("separated", 0.5, 1.5, 1.5, 0.5, 1.5),
            "separated_hallucination_cr_missed",
        )

    def test_wrong_route_nonhalluc_separated(self) -> None:
        # router picked separated, separated lost but neither hallucinated (<=1.0)
        self.assertEqual(
            classify_failure("separated", 0.5, 0.8, 0.8, 0.5, 1.0),
            "wrong_route_nonhalluc",
        )

    def test_mixed_hallucination(self) -> None:
        # router picked mixed, mixed lost, mixed>1.0
        self.assertEqual(
            classify_failure("mixed", 1.5, 0.5, 1.5, 0.5, 1.0),
            "mixed_hallucination",
        )

    def test_wrong_route_nonhalluc_mixed(self) -> None:
        # router picked mixed, mixed lost but neither hallucinated
        self.assertEqual(
            classify_failure("mixed", 0.8, 0.5, 0.8, 0.5, 1.0),
            "wrong_route_nonhalluc",
        )


# --------------------------------------------------------- error breakdown
class TestTotalErrorBreakdown(unittest.TestCase):
    def test_sums_across_rows(self) -> None:
        rows = [
            {"char_sep_substitutions": 2, "char_sep_insertions": 1,
             "char_sep_deletions": 0, "char_sep_errors": 3, "char_sep_length": 4},
            {"char_sep_substitutions": 3, "char_sep_insertions": 2,
             "char_sep_deletions": 1, "char_sep_errors": 6, "char_sep_length": 5},
        ]
        out = total_error_breakdown(rows, "char_sep")
        self.assertEqual(out["substitutions"], 5)
        self.assertEqual(out["insertions"], 3)
        self.assertEqual(out["deletions"], 1)
        self.assertEqual(out["errors"], 9)
        self.assertEqual(out["length"], 9)
        self.assertEqual(out["n_windows"], 2)

    def test_predicate_filters(self) -> None:
        rows = [
            {"window_id": 0, "char_sep_substitutions": 2, "char_sep_insertions": 1,
             "char_sep_deletions": 0, "char_sep_errors": 3, "char_sep_length": 4},
            {"window_id": 1, "char_sep_substitutions": 10, "char_sep_insertions": 10,
             "char_sep_deletions": 10, "char_sep_errors": 30, "char_sep_length": 10},
        ]
        out = total_error_breakdown(
            rows, "char_sep", predicate=lambda r: r["window_id"] == 0
        )
        self.assertEqual(out["substitutions"], 2)
        self.assertEqual(out["n_windows"], 1)

    def test_empty_selection_returns_zeros(self) -> None:
        rows = [{"window_id": 0, "char_sep_substitutions": 2, "char_sep_insertions": 1,
                 "char_sep_deletions": 0, "char_sep_errors": 3, "char_sep_length": 4}]
        out = total_error_breakdown(rows, "char_sep", predicate=lambda r: False)
        self.assertEqual(out["substitutions"], 0)
        self.assertEqual(out["n_windows"], 0)


if __name__ == "__main__":
    unittest.main()
