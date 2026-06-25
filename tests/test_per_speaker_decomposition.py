"""Tests for RQ37 per-speaker cpWER decomposition -- experimental/frontier.

Covers the pure helpers (to_char_level, char_edit_distance, gini_coefficient,
worst_speaker, ranking, hypothesis evaluation) and the MeetEval-dependent
decompose_cpwer_per_speaker against known-small inputs.

MeetEval 0.4.3 is available via /opt/homebrew/bin/python3; the decomposition
tests are skipped automatically when MeetEval cannot be imported (e.g. a
minimal CI runner) so the rest of the suite still passes.
"""
from __future__ import annotations

import unittest

from src.per_speaker_decomposition import (
    UNMATCHED_HYP_KEY,
    build_segments,
    char_edit_distance,
    decompose_cpwer_per_speaker,
    evaluate_hypotheses,
    gini_coefficient,
    rank_windows_by_cpwer,
    to_char_level,
    worst_speaker,
    worst_speaker_consistency,
)

try:  # MeetEval is only on the /opt/homebrew/bin/python3 interpreter.
    import meeteval  # noqa: F401
    MEETEVAL_AVAILABLE = True
except Exception:  # pragma: no cover - exercised on minimal CI runners.
    MEETEVAL_AVAILABLE = False


# ----------------------------------------------------------------- pure helpers

class ToCharLevelTest(unittest.TestCase):
    def test_spaces_each_character(self) -> None:
        self.assertEqual(to_char_level("abc"), "a b c")

    def test_empty_string(self) -> None:
        self.assertEqual(to_char_level(""), "")

    def test_single_char(self) -> None:
        self.assertEqual(to_char_level("x"), "x")

    def test_preserves_punctuation_and_markers(self) -> None:
        # <#> segment-boundary markers are kept as separate chars (matches RQ30).
        self.assertEqual(to_char_level("a<#>b"), "a < # > b")


class CharEditDistanceTest(unittest.TestCase):
    def test_identical_strings(self) -> None:
        self.assertEqual(char_edit_distance("abc", "abc"), 0)

    def test_one_substitution(self) -> None:
        self.assertEqual(char_edit_distance("abc", "axc"), 1)

    def test_one_insertion(self) -> None:
        self.assertEqual(char_edit_distance("abc", "abxc"), 1)

    def test_one_deletion(self) -> None:
        self.assertEqual(char_edit_distance("abc", "ac"), 1)

    def test_all_different(self) -> None:
        self.assertEqual(char_edit_distance("abc", "xyz"), 3)

    def test_empty_ref(self) -> None:
        self.assertEqual(char_edit_distance("", "abc"), 3)

    def test_empty_hyp(self) -> None:
        self.assertEqual(char_edit_distance("abc", ""), 3)

    def test_both_empty(self) -> None:
        self.assertEqual(char_edit_distance("", ""), 0)

    def test_chinese_chars(self) -> None:
        # Each Chinese character is one token at char level.
        self.assertEqual(char_edit_distance("你好", "你坏"), 1)


class GiniCoefficientTest(unittest.TestCase):
    def test_empty_list(self) -> None:
        self.assertEqual(gini_coefficient([]), 0.0)

    def test_single_value(self) -> None:
        self.assertEqual(gini_coefficient([5.0]), 0.0)

    def test_all_equal(self) -> None:
        self.assertAlmostEqual(gini_coefficient([3.0, 3.0, 3.0]), 0.0, places=6)

    def test_all_zero(self) -> None:
        self.assertEqual(gini_coefficient([0.0, 0.0, 0.0]), 0.0)

    def test_max_inequality_two_values(self) -> None:
        # One speaker holds everything -> Gini = 0.5 for n=2.
        self.assertAlmostEqual(gini_coefficient([10.0, 0.0]), 0.5, places=6)

    def test_two_values_partial(self) -> None:
        # |10-2|*2 / (2*2*12) = 16/48 = 1/3.
        self.assertAlmostEqual(gini_coefficient([10.0, 2.0]), 1.0 / 3.0, places=6)

    def test_uniform_below_threshold(self) -> None:
        # Near-equal values -> low Gini (H37c success condition).
        self.assertLess(gini_coefficient([1.0, 1.1, 0.9]), 0.3)

    def test_skewed_above_threshold(self) -> None:
        self.assertGreater(gini_coefficient([10.0, 0.1, 0.1]), 0.3)

    def test_symmetry(self) -> None:
        self.assertAlmostEqual(
            gini_coefficient([1.0, 5.0, 3.0]),
            gini_coefficient([3.0, 1.0, 5.0]),
            places=6,
        )


# ----------------------------------------------------------------- build_segments

class BuildSegmentsTest(unittest.TestCase):
    def test_skips_empty_speakers(self) -> None:
        segs = build_segments({"A": "hi", "B": "", "C": "  "}, char_level=True)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["speaker"], "A")
        self.assertEqual(segs[0]["session_id"], "s1")

    def test_char_level_default(self) -> None:
        segs = build_segments({"A": "abc"}, char_level=True)
        self.assertEqual(segs[0]["words"], "a b c")

    def test_word_level_explicit(self) -> None:
        segs = build_segments({"A": "abc"}, char_level=False)
        self.assertEqual(segs[0]["words"], "abc")


# ---------------------------------------------------------- worst_speaker helpers

class WorstSpeakerTest(unittest.TestCase):
    def test_picks_highest_error_count(self) -> None:
        per_speaker = [
            {"speaker": "A", "errors": 3, "share_of_total_errors": 0.3},
            {"speaker": "B", "errors": 5, "share_of_total_errors": 0.5},
            {"speaker": "C", "errors": 2, "share_of_total_errors": 0.2},
        ]
        spk, share, errs = worst_speaker(per_speaker)
        self.assertEqual(spk, "B")
        self.assertEqual(share, 0.5)
        self.assertEqual(errs, 5)

    def test_empty_list(self) -> None:
        spk, share, errs = worst_speaker([])
        self.assertEqual(spk, "")
        self.assertEqual(share, 0.0)
        self.assertEqual(errs, 0)

    def test_tie_returns_first_max(self) -> None:
        per_speaker = [
            {"speaker": "A", "errors": 4, "share_of_total_errors": 0.4},
            {"speaker": "B", "errors": 4, "share_of_total_errors": 0.4},
        ]
        spk, _, _ = worst_speaker(per_speaker)
        self.assertEqual(spk, "A")


class WorstSpeakerConsistencyTest(unittest.TestCase):
    def test_all_same_speaker(self) -> None:
        windows = [
            {"per_speaker": [{"speaker": "A", "errors": 5, "share_of_total_errors": 0.5}]},
            {"per_speaker": [{"speaker": "A", "errors": 6, "share_of_total_errors": 0.6}]},
            {"per_speaker": [{"speaker": "A", "errors": 4, "share_of_total_errors": 0.4}]},
        ]
        spk, frac = worst_speaker_consistency(windows)
        self.assertEqual(spk, "A")
        self.assertEqual(frac, 1.0)

    def test_split_consistency(self) -> None:
        windows = [
            {"per_speaker": [{"speaker": "A", "errors": 5, "share_of_total_errors": 0.5}]},
            {"per_speaker": [{"speaker": "B", "errors": 6, "share_of_total_errors": 0.6}]},
        ]
        spk, frac = worst_speaker_consistency(windows)
        self.assertEqual(frac, 0.5)
        self.assertIn(spk, {"A", "B"})

    def test_empty_windows(self) -> None:
        spk, frac = worst_speaker_consistency([])
        self.assertEqual(spk, "")
        self.assertEqual(frac, 0.0)


# --------------------------------------------------------------------- ranking

class RankWindowsTest(unittest.TestCase):
    def test_ranks_descending_by_cpwer(self) -> None:
        windows = [
            {"window_id": 0, "cpwer": 0.5},
            {"window_id": 1, "cpwer": 1.5},
            {"window_id": 2, "cpwer": 0.9},
        ]
        top = rank_windows_by_cpwer(windows, top_k=2)
        self.assertEqual([w["window_id"] for w in top], [1, 2])

    def test_top_k_caps_result(self) -> None:
        windows = [{"window_id": i, "cpwer": float(i)} for i in range(5)]
        top = rank_windows_by_cpwer(windows, top_k=3)
        self.assertEqual(len(top), 3)
        self.assertEqual([w["window_id"] for w in top], [4, 3, 2])


# ---------------------------------------------------------- hypothesis evaluation

class EvaluateHypothesesTest(unittest.TestCase):
    def _top_window(self, wid: int, worst_spk: str, share: float) -> dict:
        return {
            "window_id": wid,
            "per_speaker": [
                {"speaker": worst_spk, "errors": 10, "cpwer": 0.6,
                 "share_of_total_errors": share},
                {"speaker": "other", "errors": 2, "cpwer": 0.1,
                 "share_of_total_errors": 1.0 - share},
            ],
        }

    def test_h37a_supported_when_share_above_half(self) -> None:
        tops = [self._top_window(i, "A", 0.6) for i in range(10)]
        verdict = evaluate_hypotheses(tops, [])
        self.assertEqual(verdict["H37a"]["verdict"], "SUPPORTED")
        self.assertGreater(verdict["H37a"]["max_worst_speaker_share"], 0.5)

    def test_h37a_not_supported_when_share_below_half(self) -> None:
        tops = [self._top_window(i, "A", 0.4) for i in range(10)]
        verdict = evaluate_hypotheses(tops, [])
        self.assertEqual(verdict["H37a"]["verdict"], "NOT SUPPORTED")

    def test_h37b_supported_when_same_speaker_majority(self) -> None:
        tops = [self._top_window(i, "A", 0.6) for i in range(6)]
        tops += [self._top_window(i, "B", 0.6) for i in range(6, 10)]
        verdict = evaluate_hypotheses(tops, [])
        self.assertEqual(verdict["H37b"]["verdict"], "SUPPORTED")
        self.assertEqual(verdict["H37b"]["most_common_worst_speaker"], "A")
        self.assertGreater(verdict["H37b"]["consistency_fraction"], 0.5)

    def test_h37b_not_supported_when_split(self) -> None:
        tops = [self._top_window(i, "A", 0.6) for i in range(5)]
        tops += [self._top_window(i, "B", 0.6) for i in range(5, 10)]
        verdict = evaluate_hypotheses(tops, [])
        self.assertEqual(verdict["H37b"]["verdict"], "NOT SUPPORTED")

    def test_h37c_supported_when_all_mode_s_low_gini(self) -> None:
        mode_s = [
            {"window_id": 22, "per_speaker": [
                {"speaker": "A", "cpwer": 0.5},
                {"speaker": "B", "cpwer": 0.55},
            ]},
            {"window_id": 30, "per_speaker": [
                {"speaker": "A", "cpwer": 0.4},
            ]},
        ]
        verdict = evaluate_hypotheses([], mode_s)
        self.assertEqual(verdict["H37c"]["verdict"], "SUPPORTED")
        self.assertLess(verdict["H37c"]["mode_s_ginis"][22], 0.3)

    def test_h37c_not_supported_when_any_mode_s_high_gini(self) -> None:
        mode_s = [
            {"window_id": 22, "per_speaker": [
                {"speaker": "A", "cpwer": 0.9},
                {"speaker": "B", "cpwer": 0.05},
            ]},
            {"window_id": 30, "per_speaker": [
                {"speaker": "A", "cpwer": 0.4},
            ]},
        ]
        verdict = evaluate_hypotheses([], mode_s)
        self.assertEqual(verdict["H37c"]["verdict"], "NOT SUPPORTED")


# --------------------------------------------------------- MeetEval decomposition

@unittest.skipUnless(MEETEVAL_AVAILABLE, "MeetEval 0.4.3 not available in this env")
class DecomposeCpwerPerSpeakerTest(unittest.TestCase):
    def test_perfect_match_zero_errors(self) -> None:
        ref = {"A": "你好", "B": "世界"}
        hyp = {"A": "你好", "B": "世界"}
        d = decompose_cpwer_per_speaker(ref, hyp)
        self.assertFalse(d["skipped"])
        self.assertEqual(d["total_errors"], 0)
        self.assertEqual(d["total_length"], 4)
        self.assertEqual(d["cpwer"], 0.0)
        self.assertEqual(d["meetval_errors"], 0)
        self.assertEqual(len(d["per_speaker"]), 2)
        for p in d["per_speaker"]:
            self.assertEqual(p["errors"], 0)
            self.assertEqual(p["cpwer"], 0.0)

    def test_decomposition_sums_to_meetval_errors(self) -> None:
        # The whole point: per-speaker errors + unmatched must equal MeetEval
        # aggregate errors.
        ref = {"A": "abcdef", "B": "gh"}
        hyp = {"A": "abxdef", "B": "g", "C": "zzz"}  # C is unmatched (insertions)
        d = decompose_cpwer_per_speaker(ref, hyp)
        self.assertFalse(d["skipped"])
        reconstructed = sum(p["errors"] for p in d["per_speaker"]) + d["unmatched_hyp"]["errors"]
        self.assertEqual(reconstructed, d["meetval_errors"])
        self.assertEqual(reconstructed, d["total_errors"])
        # C's "zzz" (3 chars) are all insertions.
        self.assertEqual(d["unmatched_hyp"]["errors"], 3)

    def test_assignment_permutation_detected(self) -> None:
        # Hyp speakers labelled differently from ref but content matches -> 0 errors.
        ref = {"A": "abc", "B": "def"}
        hyp = {"X": "abc", "Y": "def"}
        d = decompose_cpwer_per_speaker(ref, hyp)
        self.assertEqual(d["total_errors"], 0)
        # Assignment maps ref A/B to hyp X/Y (in some order).
        assignments = {a[0]: a[1] for a in d["assignment"]}
        self.assertIn(assignments.get("A"), {"X", "Y"})
        self.assertIn(assignments.get("B"), {"X", "Y"})

    def test_worst_speaker_share_computed(self) -> None:
        # Speaker A has 3 errors, speaker B has 1 error -> A is worst with 75% share.
        ref = {"A": "abcdef", "B": "gh"}
        hyp = {"A": "xxxdef", "B": "g"}  # A: 3 subs; B: 1 deletion
        d = decompose_cpwer_per_speaker(ref, hyp)
        ws_id, ws_share, ws_errs = worst_speaker(d["per_speaker"])
        self.assertEqual(ws_id, "A")
        self.assertEqual(ws_errs, 3)
        self.assertAlmostEqual(ws_share, 0.75, places=6)

    def test_empty_ref_or_hyp_is_skipped(self) -> None:
        d = decompose_cpwer_per_speaker({}, {"A": "hi"})
        self.assertTrue(d["skipped"])
        self.assertEqual(d["total_errors"], 0)
        self.assertEqual(d["cpwer"], 0.0)

    def test_share_sums_to_one_with_unmatched(self) -> None:
        ref = {"A": "abc"}
        hyp = {"A": "axc", "B": "yy"}  # A: 1 sub; B unmatched: 2 insertions
        d = decompose_cpwer_per_speaker(ref, hyp)
        total_share = sum(p["share_of_total_errors"] for p in d["per_speaker"])
        total_share += d["unmatched_hyp"]["share_of_total_errors"]
        self.assertAlmostEqual(total_share, 1.0, places=6)

    def test_internal_whitespace_stripped_to_match_meetval(self) -> None:
        # Hyp text contains an internal space.  MeetEval's str.split() on the
        # char-level-joined words drops that space; the decomposition must do
        # the same so per-speaker errors sum to the MeetVal aggregate.
        ref = {"A": "abcd"}
        hyp = {"A": "ab cd"}  # raw hyp has a space; MeetVal sees ['a','b','c','d']
        d = decompose_cpwer_per_speaker(ref, hyp)
        self.assertEqual(d["total_errors"], 0)
        self.assertEqual(d["meetval_errors"], 0)
        self.assertEqual(d["per_speaker"][0]["ref_length"], 4)
        self.assertEqual(d["per_speaker"][0]["hyp_length"], 4)

    def test_decomposition_matches_meetval_with_multispeaker_whitespace(self) -> None:
        # Two ref speakers, hyp has internal spaces -> must still sum exactly.
        ref = {"A": "你好世界", "B": "测试"}
        hyp = {"A": "你好 世 界", "B": "测  试"}  # internal spaces should be stripped
        d = decompose_cpwer_per_speaker(ref, hyp)
        self.assertFalse(d["skipped"])
        reconstructed = sum(p["errors"] for p in d["per_speaker"]) + d["unmatched_hyp"]["errors"]
        self.assertEqual(reconstructed, d["meetval_errors"])
        self.assertEqual(d["per_speaker"][0]["hyp_length"], 4)

    def test_unmatched_hyp_key_constant(self) -> None:
        # Sanity: the constant is exported and stable.
        self.assertEqual(UNMATCHED_HYP_KEY, "__unmatched_hyp__")


if __name__ == "__main__":
    unittest.main()
