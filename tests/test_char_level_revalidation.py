"""Paired tests for RQ31: char-level cpWER re-validation of the corrected router.

Tests the pure-Python helper functions (detectors, decision rule, recovery
fraction, Mode S share) directly, plus a guarded integration test that runs
the full analysis when MeetEval is installed and asserts the output JSON/CSV
are well-formed and consistent with RQ30's char-level baselines.
"""
from __future__ import annotations

import importlib.util
import json
import math
import unittest
from pathlib import Path

import numpy as np

# Load the analysis module from the results/frontier path (it is a standalone
# script, not under src/).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_MODULE_PATH = (
    _PROJECT_ROOT
    / "results"
    / "frontier"
    / "char_level_cpwer_revalidation"
    / "char_level_revalidation_analysis.py"
)
_spec = importlib.util.spec_from_file_location(
    "char_level_revalidation_analysis", _MODULE_PATH
)
assert _spec is not None and _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


# MeetEval availability guards the integration test.
HAS_MEETEVAL = importlib.util.find_spec("meeteval") is not None


class ScriptCategoryTest(unittest.TestCase):
    """RQ13 detector primitive — copied verbatim from RQ16; must classify scripts."""

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

    def test_hangul_is_hangul(self) -> None:
        self.assertEqual(mod.script_category("카"), "Hangul")

    def test_katakana_is_katakana(self) -> None:
        self.assertEqual(mod.script_category("カ"), "Katakana")


class LanguageIdEntropyTest(unittest.TestCase):
    """RQ13 lang-id entropy detector — clean Chinese ~ 0, diverse > 0.409."""

    def test_clean_chinese_has_near_zero_entropy(self) -> None:
        # Near-monoscript Han => entropy ~ 0.
        ent = mod.language_id_entropy("零零幺商场经理这次把大家伙儿叫过来")
        self.assertLess(ent, 0.05)

    def test_diverse_multilingual_has_high_entropy(self) -> None:
        # Mix Han + Latin + Hangul + Katakana => high entropy.
        ent = mod.language_id_entropy("商 abc 카 メ")
        self.assertGreater(ent, mod.LANG_ID_ENTROPY_THRESHOLD)

    def test_empty_text_returns_zero(self) -> None:
        self.assertEqual(mod.language_id_entropy(""), 0.0)
        self.assertEqual(mod.language_id_entropy("   "), 0.0)

    def test_pure_single_script_has_near_zero_entropy(self) -> None:
        # A single-script string with no spaces/punct => entropy ~ 0.
        # "hello" is pure Latin with no whitespace, so 1 category => entropy 0.
        ent = mod.language_id_entropy("hello")
        self.assertLess(ent, 0.05)


class ToCharLevelTest(unittest.TestCase):
    """Character-level tokenisation helper (RQ30 verbatim)."""

    def test_chinese_string_split_into_spaced_chars(self) -> None:
        self.assertEqual(mod.to_char_level("商场"), "商 场")

    def test_empty_string_stays_empty(self) -> None:
        self.assertEqual(mod.to_char_level(""), "")

    def test_single_char_no_trailing_space(self) -> None:
        self.assertEqual(mod.to_char_level("商"), "商")


class CorrectedRouterDecisionTest(unittest.TestCase):
    """Decision rule: lang_id_entropy > 0.409 => mixed, else separated."""

    def test_low_entropy_routes_to_separated(self) -> None:
        self.assertEqual(mod.corrected_router_decision(0.0), "separated")
        self.assertEqual(mod.corrected_router_decision(0.408), "separated")

    def test_high_entropy_routes_to_mixed(self) -> None:
        self.assertEqual(mod.corrected_router_decision(0.41), "mixed")
        self.assertEqual(mod.corrected_router_decision(1.5), "mixed")

    def test_threshold_is_strict_inequality(self) -> None:
        # 0.409 exactly should route to separated (strict >).
        self.assertEqual(mod.corrected_router_decision(0.409), "separated")

    def test_mode_s_windows_route_to_separated(self) -> None:
        # RQ16: window 22 ent=0.14, window 30 ent=0.32 => separated.
        self.assertEqual(mod.corrected_router_decision(0.144), "separated")
        self.assertEqual(mod.corrected_router_decision(0.323), "separated")


class CpwerForRouteTest(unittest.TestCase):
    def test_mixed_choice_returns_mixed_value(self) -> None:
        self.assertEqual(mod.cpwer_for_route(0.5, 0.9, "mixed"), 0.5)

    def test_separated_choice_returns_separated_value(self) -> None:
        self.assertEqual(mod.cpwer_for_route(0.5, 0.9, "separated"), 0.9)


class MaxAcrossSpeakersTest(unittest.TestCase):
    def test_max_across_speakers_picks_worst_case(self) -> None:
        window = {
            "separated_text_per_speaker": {
                "001-M": "商",        # clean Chinese, ent ~ 0
                "002-M": "abc 카 メ",  # diverse, high entropy
            }
        }
        ent = mod.max_across_speakers(window, mod.language_id_entropy)
        self.assertGreater(ent, mod.LANG_ID_ENTROPY_THRESHOLD)

    def test_max_across_speakers_skips_empty(self) -> None:
        window = {
            "separated_text_per_speaker": {
                "001-M": "",
                "002-M": "  ",
                "003-F": "商",
            }
        }
        ent = mod.max_across_speakers(window, mod.language_id_entropy)
        self.assertLess(ent, 0.05)

    def test_max_across_speakers_empty_dict_returns_zero(self) -> None:
        self.assertEqual(mod.max_across_speakers({}, mod.language_id_entropy), 0.0)


class BootstrapHelpersTest(unittest.TestCase):
    def test_bootstrap_mean_ci_brackets_mean(self) -> None:
        vals = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        lo, hi = mod.bootstrap_mean_ci(vals, n_boot=500, seed=42)
        mean = float(vals.mean())
        self.assertLessEqual(lo, mean)
        self.assertGreaterEqual(hi, mean)
        self.assertLess(lo, hi)

    def test_bootstrap_diff_ci_sign_matches(self) -> None:
        a = np.array([2.0, 3.0, 4.0])
        b = np.array([1.0, 1.0, 1.0])
        lo, hi = mod.bootstrap_diff_ci(a, b, n_boot=500, seed=42)
        self.assertGreater(lo, 0.0)
        self.assertGreater(hi, 0.0)

    def test_bootstrap_recovery_ci_in_unit_interval_when_sensible(self) -> None:
        # corrected exactly halfway between mixed and oracle => recovery ~ 0.5.
        mixed = np.array([0.9, 0.9, 0.9])
        corrected = np.array([0.85, 0.85, 0.85])
        oracle = np.array([0.8, 0.8, 0.8])
        lo, hi = mod.bootstrap_recovery_ci(mixed, corrected, oracle, n_boot=500, seed=42)
        self.assertGreater(hi, 0.0)
        self.assertLessEqual(lo, 1.0)

    def test_bootstrap_mode_s_share_ci_zero_when_no_residual(self) -> None:
        # If Mode S windows have zero residual, share must be 0.
        corrected = np.array([0.9, 0.8, 0.7])
        oracle = np.array([0.9, 0.8, 0.7])  # corrected == oracle everywhere
        lo, hi = mod.bootstrap_mode_s_share_ci(corrected, oracle, [0], n_boot=500, seed=42)
        self.assertEqual(lo, 0.0)
        self.assertEqual(hi, 0.0)


class BuildSegmentsTest(unittest.TestCase):
    def test_build_segments_skips_empty_speakers(self) -> None:
        segs = mod.build_segments({"001-M": "商场", "002-M": "", "003-F": "  "})
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["speaker"], "001-M")
        self.assertIn(" ", segs[0]["words"])

    def test_build_segments_char_level_tokenises(self) -> None:
        segs = mod.build_segments({"001-M": "商场"})
        self.assertEqual(segs[0]["words"], "商 场")

    def test_build_mixed_segment_skips_empty(self) -> None:
        self.assertEqual(mod.build_mixed_segment(""), [])
        self.assertEqual(mod.build_mixed_segment("  "), [])

    def test_build_mixed_segment_char_level(self) -> None:
        segs = mod.build_mixed_segment("商场")
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0]["speaker"], "mix")
        self.assertEqual(segs[0]["words"], "商 场")


@unittest.skipUnless(HAS_MEETEVAL, "MeetEval not installed")
class IntegrationTest(unittest.TestCase):
    """End-to-end: run the analysis and check outputs are well-formed.

    Requires MeetEval 0.4.3 (only available under /opt/homebrew/bin/python3).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.out_dir = mod.OUT_DIR
        cls.json_path = mod.OUT_JSON
        cls.csv_path = mod.OUT_CSV
        # Run the analysis once.
        mod.main()

    def test_json_exists_and_is_valid(self) -> None:
        self.assertTrue(self.json_path.exists())
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        self.assertEqual(data["label"], "experimental/frontier")
        self.assertEqual(data["rq"], "RQ31: Char-level cpWER re-validation of the corrected router")
        self.assertEqual(data["closes_issue"], 938)
        self.assertEqual(data["n_windows"], 77)

    def test_csv_exists_and_has_77_rows(self) -> None:
        self.assertTrue(self.csv_path.exists())
        lines = self.csv_path.read_text(encoding="utf-8").strip().split("\n")
        self.assertEqual(len(lines), 78)  # 1 header + 77 data

    def test_char_baselines_match_rq30_cross_reference(self) -> None:
        # RQ30 (PR #934) established these char-level aggregate values.
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        b = data["char_level_baselines"]
        self.assertAlmostEqual(b["always_mixed_char"], 0.910577, places=5)
        self.assertAlmostEqual(b["always_separated_char"], 0.915831, places=5)
        self.assertAlmostEqual(b["oracle_char"], 0.876847, places=5)
        self.assertAlmostEqual(b["router_v2_char"], 0.922196, places=5)

    def test_corrected_router_beats_mixed_pointwise(self) -> None:
        # H31a point estimate.
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        b = data["char_level_baselines"]
        self.assertLess(b["corrected_router_char"], b["always_mixed_char"])

    def test_oracle_is_lower_bound(self) -> None:
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        b = data["char_level_baselines"]
        self.assertLessEqual(b["oracle_char"], b["always_mixed_char"])
        self.assertLessEqual(b["oracle_char"], b["always_separated_char"])
        self.assertLessEqual(b["oracle_char"], b["corrected_router_char"])

    def test_hypothesis_verdicts_present(self) -> None:
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        hv = data["hypothesis_verdicts"]
        for h in ("H31a", "H31b", "H31c"):
            self.assertIn(h, hv)
            self.assertIn("supported", hv[h])
            self.assertIn("statement", hv[h])
            self.assertIn("success_criterion", hv[h])
            self.assertIn("kill_criterion", hv[h])

    def test_mode_s_windows_have_zero_residual_at_char_level(self) -> None:
        # The central RQ31 finding: Mode S disappears at char level.
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        for d in data["mode_s_analysis"]["mode_s_per_window"]:
            self.assertEqual(d["residual"], 0.0)

    def test_recovery_fraction_is_well_defined(self) -> None:
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        ra = data["regret_analysis"]
        self.assertGreater(ra["mixed_regret_gap_to_oracle_char"], 0.0)
        recovery = ra["corrected_recovery_fraction"]
        self.assertGreater(recovery, -1.0)
        self.assertLess(recovery, 2.0)

    def test_per_window_rows_count(self) -> None:
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        self.assertEqual(len(data["per_window"]), 77)

    def test_corrected_decision_counts_sum_to_77(self) -> None:
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        counts = data["corrected_router_decision_counts"]
        self.assertEqual(counts["mixed"] + counts["separated"], 77)

    def test_separation_tax_ratio_near_80x(self) -> None:
        # RQ30: word-level separation tax is ~80x the char-level tax.
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        st = data["separation_tax"]
        self.assertAlmostEqual(st["ratio_word_over_char"], 79.5, places=1)


if __name__ == "__main__":
    unittest.main()
