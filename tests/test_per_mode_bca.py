"""Tests for RQ70: per-mode BCa CI decomposition (experimental/frontier).

Pin the PURE helpers used by
``results/frontier/per_mode_bca_decomposition/analysis.py``: detector primitives
(script_category, language_id_entropy, max_across_speakers,
corrected_router_decision), Mode S classification primitives (compression_ratio,
max_cr_across_speakers, separated_total_length, mixed_text_length, length_ratio,
is_hallucinated, is_mode_s, classify_mode), char-level MeetEval helpers
(to_char_level, build_segments, build_mixed_segment, safe_cpwer, safe_orcwer),
bootstrap helpers (bootstrap_indices, bootstrap_distribution, percentile_ci,
_jackknife_means, bca_ci), CI helpers (ci_includes, ci_excludes, _round6,
_ci_pair), and the subset BCa driver (_subset_bca, _compute_window_cpwer).

MeetEval-dependent tests (safe_cpwer/safe_orcwer on real Chinese text, and the
full integration test) are guarded by ``HAS_MEETEVAL``. Synthetic data only for
the pure helpers — no AISHELL-4 file, no Whisper, no audio.
"""
from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

import numpy as np

# Load the analysis module from the results/frontier path (standalone script).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = (
    _PROJECT_ROOT
    / "results"
    / "frontier"
    / "per_mode_bca_decomposition"
    / "analysis.py"
)
_spec = importlib.util.spec_from_file_location("per_mode_bca_analysis", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

# MeetEval availability guards the integration + char-level cpWER tests.
try:
    import meeteval  # noqa: F401
    HAS_MEETEVAL = True
except ImportError:
    HAS_MEETEVAL = False


def _make_window(
    separated: dict[str, str] | None = None,
    mixed: str = "",
    sep_cpwer: float = 1.0,
    mixed_cpwer: float = 1.0,
    oracle_cpwer: float = 1.0,
    window_id: int = 0,
) -> dict:
    """Build a synthetic AISHELL-4-style window dict for testing."""
    return {
        "window_id": window_id,
        "overlap_label": "NoOverlap",
        "num_speakers": len(separated) if separated else 0,
        "separated_text_per_speaker": separated or {},
        "ref_text_per_speaker": separated or {},
        "mixed_text": mixed,
        "always_separated_cpwer": sep_cpwer,
        "always_mixed_cpwer": mixed_cpwer,
        "oracle_best_cpwer": oracle_cpwer,
    }


# =================================================================== script_category
class ScriptCategoryTest(unittest.TestCase):
    """RQ13 detector primitive — must classify Unicode scripts correctly."""

    def test_chinese_character_is_han(self) -> None:
        self.assertEqual(mod.script_category("商"), "Han")
        self.assertEqual(mod.script_category("场"), "Han")

    def test_latin_character_is_latin(self) -> None:
        self.assertEqual(mod.script_category("A"), "Latin")
        self.assertEqual(mod.script_category("z"), "Latin")

    def test_digit_is_digit(self) -> None:
        self.assertEqual(mod.script_category("3"), "Digit")

    def test_whitespace_is_space(self) -> None:
        self.assertEqual(mod.script_category(" "), "Space")
        self.assertEqual(mod.script_category("\t"), "Space")
        self.assertEqual(mod.script_category("\n"), "Space")

    def test_hangul_is_hangul(self) -> None:
        self.assertEqual(mod.script_category("카"), "Hangul")

    def test_katakana_is_katakana(self) -> None:
        self.assertEqual(mod.script_category("カ"), "Katakana")

    def test_hiragana_is_hiragana(self) -> None:
        self.assertEqual(mod.script_category("あ"), "Hiragana")

    def test_punctuation_is_punct(self) -> None:
        self.assertEqual(mod.script_category(","), "Punct")
        self.assertEqual(mod.script_category("。"), "Punct")


# ============================================================ language_id_entropy
class LanguageIdEntropyTest(unittest.TestCase):
    """RQ13 lang-id entropy detector — clean Chinese ~ 0, diverse > threshold."""

    def test_clean_chinese_has_near_zero_entropy(self) -> None:
        ent = mod.language_id_entropy("零零幺商场经理这次把大家伙儿叫过来")
        self.assertLess(ent, 0.05)

    def test_diverse_multilingual_has_high_entropy(self) -> None:
        ent = mod.language_id_entropy("美國生活差幾個 카메 mad將會")
        self.assertGreater(ent, 0.5)

    def test_empty_string_has_zero_entropy(self) -> None:
        self.assertEqual(mod.language_id_entropy(""), 0.0)

    def test_whitespace_only_has_zero_entropy(self) -> None:
        self.assertEqual(mod.language_id_entropy("   \t\n  "), 0.0)

    def test_single_script_has_zero_entropy(self) -> None:
        self.assertEqual(mod.language_id_entropy("AAAA"), 0.0)

    def test_two_scripts_have_positive_entropy(self) -> None:
        # Non-uniform mix (3 Latin + 2 Han) -> entropy strictly between 0 and 1.
        ent = mod.language_id_entropy("ABC商场")
        self.assertGreater(ent, 0.0)
        self.assertLess(ent, 1.0)

    def test_uniform_two_scripts_have_entropy_one(self) -> None:
        # Equal mix of two scripts -> entropy = log2(2) = 1.0
        ent = mod.language_id_entropy("AB商场")
        self.assertAlmostEqual(ent, 1.0, places=5)


# ============================================================ max_across_speakers
class MaxAcrossSpeakersTest(unittest.TestCase):
    """RQ12/RQ13 worst-case-across-speakers convention."""

    def test_max_of_single_speaker(self) -> None:
        w = _make_window(separated={"spk1": "商"})
        self.assertAlmostEqual(
            mod.max_across_speakers(w, mod.language_id_entropy),
            mod.language_id_entropy("商"),
        )

    def test_max_of_multiple_speakers(self) -> None:
        w = _make_window(separated={"spk1": "商", "spk2": "AB商场"})
        self.assertAlmostEqual(
            mod.max_across_speakers(w, mod.language_id_entropy),
            mod.language_id_entropy("AB商场"),
        )

    def test_empty_speakers_returns_zero(self) -> None:
        w = _make_window(separated={})
        self.assertEqual(mod.max_across_speakers(w, mod.language_id_entropy), 0.0)

    def test_whitespace_speakers_ignored(self) -> None:
        w = _make_window(separated={"spk1": "  ", "spk2": "商"})
        self.assertAlmostEqual(
            mod.max_across_speakers(w, mod.language_id_entropy),
            mod.language_id_entropy("商"),
        )


# ===================================================== corrected_router_decision
class CorrectedRouterDecisionTest(unittest.TestCase):
    """RQ55 router: lang-id entropy > 0.38 -> MIXED, else SEPARATED."""

    def test_low_entropy_routes_to_separated(self) -> None:
        w = _make_window(separated={"spk1": "商场经理这次"})
        self.assertEqual(mod.corrected_router_decision(w), "separated")

    def test_high_entropy_routes_to_mixed(self) -> None:
        w = _make_window(separated={"spk1": "美國生活差幾個 카메 mad將會"})
        self.assertEqual(mod.corrected_router_decision(w), "mixed")

    def test_empty_routes_to_separated(self) -> None:
        w = _make_window(separated={})
        self.assertEqual(mod.corrected_router_decision(w), "separated")

    def test_threshold_is_0_38(self) -> None:
        self.assertEqual(mod.LANG_ID_ENTROPY_THRESHOLD, 0.38)


# ============================================================ compression_ratio
class CompressionRatioTest(unittest.TestCase):
    """RQ12/RQ14 Whisper-style CR primitive."""

    def test_empty_text_has_zero_cr(self) -> None:
        self.assertEqual(mod.compression_ratio(""), 0.0)

    def test_whitespace_text_has_zero_cr(self) -> None:
        self.assertEqual(mod.compression_ratio("   "), 0.0)

    def test_non_repetitive_text_cr_near_one(self) -> None:
        # Short Chinese text has CR < 1 because zlib adds overhead; just verify
        # it's positive and well below the hallucination threshold.
        cr = mod.compression_ratio("商场经理这次把大家伙儿叫过来开个会")
        self.assertGreater(cr, 0.7)
        self.assertLess(cr, 2.0)

    def test_repetitive_text_has_high_cr(self) -> None:
        cr = mod.compression_ratio("你能化的你能化的你能化的你能化的你能化的")
        self.assertGreater(cr, 2.0)

    def test_cr_returns_positive_for_normal_text(self) -> None:
        self.assertGreater(mod.compression_ratio("hello world"), 0.0)


# =================================================== Mode S classification primitives
class ModeSClassificationTest(unittest.TestCase):
    """RQ19 Mode S definition: hallucinated AND ent<0.409 AND lr<2.0 AND cr<2.4."""

    def test_non_hallucinated_is_not_mode_s(self) -> None:
        w = _make_window(sep_cpwer=0.5, separated={"spk1": "商"})
        self.assertFalse(mod.is_mode_s(w))

    def test_hallucinated_low_entropy_is_mode_s_candidate(self) -> None:
        # Hallucinated (sep>1.0), low entropy (clean Chinese), low lr, low cr
        w = _make_window(
            sep_cpwer=2.0,
            separated={"spk1": "商场经理这次把大家伙儿叫过来"},
            mixed="商场经理这次把大家伙儿叫过来开个会",
        )
        self.assertTrue(mod.is_hallucinated(w))
        self.assertTrue(mod.is_mode_s(w))

    def test_hallucinated_high_entropy_is_not_mode_s(self) -> None:
        w = _make_window(
            sep_cpwer=2.0,
            separated={"spk1": "美國生活差幾個 카메 mad將會"},
            mixed="",
        )
        self.assertTrue(mod.is_hallucinated(w))
        self.assertFalse(mod.is_mode_s(w))

    def test_hallucinated_high_length_ratio_is_not_mode_s(self) -> None:
        # length ratio huge (empty mixed, long separated)
        w = _make_window(
            sep_cpwer=2.0,
            separated={"spk1": "商场" * 100},
            mixed="",
        )
        self.assertTrue(mod.is_hallucinated(w))
        self.assertFalse(mod.is_mode_s(w))

    def test_is_hallucinated_threshold(self) -> None:
        self.assertTrue(mod.is_hallucinated(_make_window(sep_cpwer=1.5)))
        self.assertFalse(mod.is_hallucinated(_make_window(sep_cpwer=1.0)))
        self.assertFalse(mod.is_hallucinated(_make_window(sep_cpwer=0.5)))


class ClassifyModeTest(unittest.TestCase):
    """Three-way mutually-exclusive classification."""

    def test_mode_s_classification(self) -> None:
        w = _make_window(
            sep_cpwer=2.0,
            separated={"spk1": "商场经理这次把大家伙儿叫过来"},
            mixed="商场经理这次把大家伙儿叫过来开个会",
        )
        self.assertEqual(mod.classify_mode(w), "mode_s")

    def test_diverse_hallucination_classification(self) -> None:
        w = _make_window(
            sep_cpwer=2.0,
            separated={"spk1": "美國生活差幾個 카메 mad將會"},
            mixed="",
        )
        self.assertEqual(mod.classify_mode(w), "diverse_hallucination")

    def test_non_hallucinated_classification(self) -> None:
        w = _make_window(sep_cpwer=0.5, separated={"spk1": "商"})
        self.assertEqual(mod.classify_mode(w), "non_hallucinated")

    def test_classification_is_mutually_exclusive(self) -> None:
        # Every window maps to exactly one mode
        cases = [
            _make_window(sep_cpwer=0.5, separated={"spk1": "商"}),
            _make_window(sep_cpwer=2.0, separated={"spk1": "美國 카메"}),
            _make_window(sep_cpwer=2.0, separated={"spk1": "商场"},
                         mixed="商场经理"),
        ]
        for w in cases:
            mode = mod.classify_mode(w)
            self.assertIn(mode, {"mode_s", "diverse_hallucination", "non_hallucinated"})


# =================================================== length / mixed text helpers
class LengthHelpersTest(unittest.TestCase):
    """separated_total_length / mixed_text_length / length_ratio."""

    def test_separated_total_length_strips_whitespace(self) -> None:
        w = _make_window(separated={"spk1": "商 场", "spk2": "经 理"})
        self.assertEqual(mod.separated_total_length(w), 4)

    def test_separated_total_length_empty(self) -> None:
        self.assertEqual(mod.separated_total_length(_make_window(separated={})), 0)

    def test_mixed_text_length_strips_whitespace(self) -> None:
        w = _make_window(mixed="商 场 经 理")
        self.assertEqual(mod.mixed_text_length(w), 4)

    def test_mixed_text_length_empty(self) -> None:
        self.assertEqual(mod.mixed_text_length(_make_window(mixed="")), 0)

    def test_length_ratio_empty_mixed(self) -> None:
        w = _make_window(separated={"spk1": "商场"}, mixed="")
        self.assertEqual(mod.length_ratio(w), 2.0)  # 2 / max(0,1) = 2

    def test_length_ratio_normal(self) -> None:
        w = _make_window(separated={"spk1": "商场"}, mixed="商场经理")
        self.assertAlmostEqual(mod.length_ratio(w), 0.5)

    def test_max_cr_across_speakers(self) -> None:
        # Need a long-enough repetition so zlib actually compresses (CR > 1.0);
        # 8 chars of UTF-8 Chinese only break even at CR=1.0.
        w = _make_window(separated={"spk1": "商", "spk2": "你能化的你能化的你能化的"})
        cr = mod.max_cr_across_speakers(w)
        self.assertGreater(cr, 1.0)

    def test_max_cr_empty_returns_zero(self) -> None:
        self.assertEqual(mod.max_cr_across_speakers(_make_window(separated={})), 0.0)


# ============================================================ char-level helpers
class CharLevelHelpersTest(unittest.TestCase):
    """RQ31 char-level MeetEval tokenisation helpers."""

    def test_to_char_level_splits_characters(self) -> None:
        self.assertEqual(mod.to_char_level("你好"), "你 好")

    def test_to_char_level_empty(self) -> None:
        self.assertEqual(mod.to_char_level(""), "")

    def test_build_segments_skips_empty(self) -> None:
        segs = mod.build_segments({"spk1": "你好", "spk2": ""})
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["speaker"], "spk1")

    def test_build_segments_session_id(self) -> None:
        segs = mod.build_segments({"spk1": "你好"})
        self.assertEqual(segs[0]["session_id"], mod.SESSION_ID)

    def test_build_mixed_segment_empty(self) -> None:
        self.assertEqual(mod.build_mixed_segment(""), [])

    def test_build_mixed_segment_nonempty(self) -> None:
        segs = mod.build_mixed_segment("你好")
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["speaker"], "mix")


# ============================================================ bootstrap helpers
class BootstrapHelpersTest(unittest.TestCase):
    """RQ39/RQ55 bootstrap + BCa helpers (pure numpy)."""

    def test_bootstrap_indices_shape(self) -> None:
        idx = mod.bootstrap_indices(10, 500, 42)
        self.assertEqual(idx.shape, (500, 10))

    def test_bootstrap_indices_in_range(self) -> None:
        idx = mod.bootstrap_indices(10, 500, 42)
        self.assertTrue(np.all(idx >= 0))
        self.assertTrue(np.all(idx < 10))

    def test_bootstrap_indices_deterministic(self) -> None:
        a = mod.bootstrap_indices(10, 100, 42)
        b = mod.bootstrap_indices(10, 100, 42)
        np.testing.assert_array_equal(a, b)

    def test_bootstrap_distribution_mean(self) -> None:
        vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        dist = mod.bootstrap_distribution(vals, 10000, 42)
        self.assertAlmostEqual(dist.mean(), 3.0, places=1)

    def test_percentile_ci_bounds(self) -> None:
        dist = np.array([1.0, 2.0, 3.0, 4.0, 5.0] * 1000)
        lo, hi = mod.percentile_ci(dist)
        self.assertLessEqual(lo, hi)

    def test_percentile_ci_contains_mean(self) -> None:
        rng = np.random.default_rng(0)
        dist = rng.normal(5.0, 1.0, size=10000)
        lo, hi = mod.percentile_ci(dist)
        self.assertLessEqual(lo, 5.0)
        self.assertGreaterEqual(hi, 5.0)

    def test_jackknife_means_length(self) -> None:
        vals = np.array([1.0, 2.0, 3.0, 4.0])
        jack = mod._jackknife_means(vals)
        self.assertEqual(len(jack), 4)

    def test_jackknife_mean_identity(self) -> None:
        # leave-one-out mean of [1,2,3,4] dropping 1 = (2+3+4)/3 = 3.0
        vals = np.array([1.0, 2.0, 3.0, 4.0])
        jack = mod._jackknife_means(vals)
        self.assertAlmostEqual(jack[0], 3.0)

    def test_jackknife_single_element(self) -> None:
        vals = np.array([5.0])
        jack = mod._jackknife_means(vals)
        self.assertAlmostEqual(jack[0], 5.0)

    def test_bca_ci_contains_mean(self) -> None:
        rng = np.random.default_rng(1)
        vals = rng.normal(10.0, 2.0, size=100)
        boot = mod.bootstrap_distribution(vals, 5000, 42)
        lo, hi = mod.bca_ci(vals, boot)
        self.assertLessEqual(lo, 10.0)
        self.assertGreaterEqual(hi, 10.0)

    def test_bca_ci_constant_data_falls_back(self) -> None:
        # Constant data: BCa should fall back to percentile CI (no variance)
        vals = np.array([5.0] * 10)
        boot = mod.bootstrap_distribution(vals, 1000, 42)
        lo, hi = mod.bca_ci(vals, boot)
        self.assertAlmostEqual(lo, 5.0)
        self.assertAlmostEqual(hi, 5.0)

    def test_bca_ci_n_less_than_2(self) -> None:
        vals = np.array([5.0])
        boot = np.array([5.0])
        lo, hi = mod.bca_ci(vals, boot)
        self.assertAlmostEqual(lo, 5.0)
        self.assertAlmostEqual(hi, 5.0)

    def test_bca_ci_lo_le_hi(self) -> None:
        rng = np.random.default_rng(2)
        vals = rng.normal(0.0, 1.0, size=50)
        boot = mod.bootstrap_distribution(vals, 2000, 42)
        lo, hi = mod.bca_ci(vals, boot)
        self.assertLessEqual(lo, hi)


# ============================================================ CI helpers
class CIHelpersTest(unittest.TestCase):
    """ci_includes / ci_excludes / _round6 / _ci_pair."""

    def test_ci_includes_inside(self) -> None:
        self.assertTrue(mod.ci_includes((1.0, 2.0), 1.5))

    def test_ci_includes_boundary(self) -> None:
        self.assertTrue(mod.ci_includes((1.0, 2.0), 1.0))
        self.assertTrue(mod.ci_includes((1.0, 2.0), 2.0))

    def test_ci_includes_outside(self) -> None:
        self.assertFalse(mod.ci_includes((1.0, 2.0), 0.5))
        self.assertFalse(mod.ci_includes((1.0, 2.0), 2.5))

    def test_ci_excludes_inside(self) -> None:
        self.assertFalse(mod.ci_excludes((1.0, 2.0), 1.5))

    def test_ci_excludes_outside(self) -> None:
        self.assertTrue(mod.ci_excludes((1.0, 2.0), 0.5))

    def test_round6(self) -> None:
        self.assertEqual(mod._round6(1.23456789), 1.234568)

    def test_ci_pair_returns_list(self) -> None:
        result = mod._ci_pair((1.23456789, 2.3456789))
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)


# ============================================================ _subset_bca
class SubsetBcaTest(unittest.TestCase):
    """_subset_bca driver: handles n=0, n=1, n<5 stability flag, normal case."""

    def test_subset_bca_empty(self) -> None:
        result = mod._subset_bca(np.array([]), "empty")
        self.assertEqual(result["n"], 0)
        self.assertFalse(result["stable"])
        self.assertTrue(math.isnan(result["mean"]))

    def test_subset_bca_single(self) -> None:
        result = mod._subset_bca(np.array([5.0]), "single")
        self.assertEqual(result["n"], 1)
        self.assertFalse(result["stable"])
        self.assertEqual(result["mean"], 5.0)
        self.assertEqual(result["bca_width"], 0.0)

    def test_subset_bca_small_n_unstable(self) -> None:
        result = mod._subset_bca(np.array([1.0, 2.0]), "small")
        self.assertEqual(result["n"], 2)
        self.assertFalse(result["stable"])
        self.assertIn("n=2", result["stability_note"])

    def test_subset_bca_normal_stable(self) -> None:
        rng = np.random.default_rng(0)
        vals = rng.normal(1.0, 0.1, size=20)
        result = mod._subset_bca(vals, "normal")
        self.assertEqual(result["n"], 20)
        self.assertTrue(result["stable"])
        self.assertLessEqual(result["bca_ci"][0], result["bca_ci"][1])


# ============================================================ _compute_window_cpwer
@unittest.skipUnless(HAS_MEETEVAL, "MeetEval not installed")
class ComputeWindowCpwerTest(unittest.TestCase):
    """_compute_window_cpwer: word-level fields + mode classification.

    Guarded because _compute_window_cpwer calls safe_cpwer/safe_orcwer for the
    char-level fields, which require MeetEval.
    """

    def test_compute_window_word_level_fields(self) -> None:
        w = _make_window(
            sep_cpwer=2.0, mixed_cpwer=1.0, oracle_cpwer=1.0,
            separated={"spk1": "美國 카메"}, mixed="", window_id=42,
        )
        row = mod._compute_window_cpwer(w)
        self.assertEqual(row["window_id"], 42)
        self.assertEqual(row["word_separated_cpwer"], 2.0)
        self.assertEqual(row["word_mixed_cpwer"], 1.0)
        self.assertEqual(row["word_oracle_cpwer"], 1.0)
        self.assertTrue(row["hallucinated"])

    def test_compute_window_corrected_picks_mixed(self) -> None:
        w = _make_window(
            sep_cpwer=2.0, mixed_cpwer=1.0, oracle_cpwer=1.0,
            separated={"spk1": "美國生活差幾個 카메 mad將會"}, mixed="",
        )
        row = mod._compute_window_cpwer(w)
        self.assertEqual(row["corrected_decision"], "mixed")
        self.assertEqual(row["word_corrected_cpwer"], 1.0)

    def test_compute_window_corrected_picks_separated(self) -> None:
        w = _make_window(
            sep_cpwer=0.5, mixed_cpwer=2.0, oracle_cpwer=0.5,
            separated={"spk1": "商场经理"}, mixed="商场经理",
        )
        row = mod._compute_window_cpwer(w)
        self.assertEqual(row["corrected_decision"], "separated")
        self.assertEqual(row["word_corrected_cpwer"], 0.5)

    def test_compute_window_mode_classification(self) -> None:
        w = _make_window(
            sep_cpwer=2.0,
            separated={"spk1": "美國生活差幾個 카메 mad將會"}, mixed="",
        )
        row = mod._compute_window_cpwer(w)
        self.assertEqual(row["mode"], "diverse_hallucination")

    def test_compute_window_has_char_level_fields(self) -> None:
        w = _make_window(sep_cpwer=1.0, separated={"spk1": "商"}, mixed="商")
        row = mod._compute_window_cpwer(w)
        self.assertIn("char_corrected_cpwer", row)
        self.assertIn("char_oracle_cpwer", row)
        self.assertIn("char_mixed_cpwer", row)
        self.assertIn("char_separated_cpwer", row)


# ============================================================ MeetEval integration
@unittest.skipUnless(HAS_MEETEVAL, "MeetEval not installed")
class MeetEvalCharLevelTest(unittest.TestCase):
    """safe_cpwer / safe_orcwer on real Chinese text (MeetEval-guarded)."""

    def test_safe_cpwer_empty_returns_sentinel(self) -> None:
        er, err, length = mod.safe_cpwer([], [])
        self.assertEqual(er, 1.0)
        self.assertEqual(err, -1)
        self.assertEqual(length, -1)

    def test_safe_orcwer_empty_returns_sentinel(self) -> None:
        er, err, length = mod.safe_orcwer([], [])
        self.assertEqual(er, 1.0)
        self.assertEqual(err, -1)
        self.assertEqual(length, -1)

    def test_safe_cpwer_perfect_match(self) -> None:
        ref = mod.build_segments({"spk1": "你好"})
        hyp = mod.build_segments({"spk1": "你好"})
        er, _, _ = mod.safe_cpwer(ref, hyp)
        self.assertAlmostEqual(er, 0.0, places=4)

    def test_safe_orcwer_perfect_match(self) -> None:
        ref = mod.build_segments({"spk1": "你好"})
        hyp = mod.build_mixed_segment("你好")
        er, _, _ = mod.safe_orcwer(ref, hyp)
        self.assertAlmostEqual(er, 0.0, places=4)


# ============================================================ full integration
@unittest.skipUnless(HAS_MEETEVAL, "MeetEval not installed")
class FullIntegrationTest(unittest.TestCase):
    """End-to-end: run main() and verify the output JSON reproduces RQ55 + RQ19."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.out_json = mod.OUT_DIR / "per_mode_bca_results.json"
        cls.out_csv = mod.OUT_DIR / "per_mode_bca_results.csv"
        # The analysis is run by the developer before tests; verify outputs exist.
        if not cls.out_json.exists():
            mod.main()

    def test_output_json_exists(self) -> None:
        self.assertTrue(self.out_json.exists())

    def test_output_csv_exists(self) -> None:
        self.assertTrue(self.out_csv.exists())

    def test_label_is_experimental_frontier(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        self.assertEqual(d["label"], "experimental/frontier")

    def test_closes_issue_998(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        self.assertEqual(d["closes_issue"], 998)

    def test_n_windows_is_77(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        self.assertEqual(d["n_windows"], 77)

    def test_mode_counts_match_data(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        mc = d["mode_counts"]
        self.assertEqual(mc["mode_s"], 2)
        self.assertEqual(mc["diverse_hallucination"], 35)
        self.assertEqual(mc["non_hallucinated"], 40)
        self.assertEqual(mc["non_mode_s"], 75)
        self.assertEqual(mc["all"], 77)

    def test_mode_s_window_ids_are_22_and_30(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        self.assertEqual(sorted(d["mode_s_window_ids"]), [22, 30])

    def test_word_bca_reproduces_rq55(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        rc = d["reproducibility_check"]
        self.assertTrue(rc["word_reproduces"])
        self.assertAlmostEqual(rc["all_word_bca_ci"][0], mod.RQ55_WORD_BCA_CI[0], places=5)
        self.assertAlmostEqual(rc["all_word_bca_ci"][1], mod.RQ55_WORD_BCA_CI[1], places=5)

    def test_char_bca_reproduces_rq55(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        rc = d["reproducibility_check"]
        self.assertTrue(rc["char_reproduces"])
        self.assertAlmostEqual(rc["all_char_bca_ci"][0], mod.RQ55_CHAR_BCA_CI[0], places=5)
        self.assertAlmostEqual(rc["all_char_bca_ci"][1], mod.RQ55_CHAR_BCA_CI[1], places=5)

    def test_all_77_corrected_word_reproduces_rq55(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        s = d["per_subset"]["all"]
        self.assertAlmostEqual(s["word_corrected_mean"], mod.RQ55_WORD_CORRECTED, places=4)

    def test_all_77_corrected_char_reproduces_rq55(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        s = d["per_subset"]["all"]
        self.assertAlmostEqual(s["char_corrected_mean"], mod.RQ55_CHAR_CORRECTED, places=4)

    def test_h70a_verdict_present(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        self.assertIn("H70a", d["hypothesis_verdicts"])
        self.assertIn("supported", d["hypothesis_verdicts"]["H70a"])

    def test_h70b_verdict_present(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        self.assertIn("H70b", d["hypothesis_verdicts"])
        self.assertIn("stable", d["hypothesis_verdicts"]["H70b"])

    def test_h70c_verdict_present(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        self.assertIn("H70c", d["hypothesis_verdicts"])
        self.assertIn("char_width_ratio", d["hypothesis_verdicts"]["H70c"])

    def test_mode_s_subset_flagged_unstable(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        s = d["per_subset"]["mode_s"]
        self.assertFalse(s["stable"])

    def test_diverse_and_nonhall_subsets_stable(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        self.assertTrue(d["per_subset"]["diverse_hallucination"]["stable"])
        self.assertTrue(d["per_subset"]["non_hallucinated"]["stable"])
        self.assertTrue(d["per_subset"]["non_mode_s"]["stable"])

    def test_per_window_csv_has_77_rows(self) -> None:
        with self.out_csv.open(encoding="utf-8") as f:
            rows = list(mod.csv.DictReader(f))
        self.assertEqual(len(rows), 77)

    def test_per_window_csv_has_mode_column(self) -> None:
        with self.out_csv.open(encoding="utf-8") as f:
            reader = mod.csv.DictReader(f)
            self.assertIn("mode", reader.fieldnames)

    def test_global_oracle_matches_rq55(self) -> None:
        d = json.loads(self.out_json.read_text(encoding="utf-8"))
        go = d["global_oracle"]
        self.assertAlmostEqual(go["word_level"], mod.RQ55_WORD_ORACLE, places=4)
        self.assertAlmostEqual(go["char_level"], mod.RQ55_CHAR_ORACLE, places=3)


if __name__ == "__main__":
    unittest.main()
