"""Tests for the Harness knowledge-base contract rules.

Python analogue of code-tape's scripts/tests/workflow-rules.test.mjs. These
tests are the TDD safety net for the contract engine itself, and they also
satisfy the ``harness`` critical category's own test pattern (touching
scripts/harness/** requires a changed tests/test_harness* file).
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

# Load scripts/harness/contract_rules.py without requiring it to be importable
# as a package from the tests directory. Register in sys.modules before exec so
# dataclass annotation resolution can find the module namespace.
_RULES_PATH = Path(__file__).resolve().parents[1] / "scripts" / "harness" / "contract_rules.py"
_spec = importlib.util.spec_from_file_location("harness_contract_rules", _RULES_PATH)
cr = importlib.util.module_from_spec(_spec)
sys.modules["harness_contract_rules"] = cr
_spec.loader.exec_module(cr)


def valid_summary(extra: str = "") -> str:
    """A structured impact summary that passes the four base fields."""
    base = (
        "- Risk level: MEDIUM\n"
        "- Critical skeleton change: touched the adaptive router decision path\n"
        "- GitNexus impact: ran detect_changes and impact on the touched symbols\n"
        "- Verification: python -m unittest discover -s tests passed (3212 tests)\n"
    )
    return base + extra


class TestClassification(unittest.TestCase):
    def test_normalize_files_dedupes_and_normalises_separators(self):
        result = cr.normalize_files(["src\\foo.py", "src/foo.py", "", " src/bar.py ", "src/foo.py"])
        self.assertEqual(result, ["src/foo.py", "src/bar.py"])

    def test_combine_changed_files_merges_tracked_and_untracked(self):
        result = cr.combine_changed_files(["a.py"], ["b.py", "a.py"])
        self.assertEqual(result, ["a.py", "b.py"])

    def test_router_module_classified_as_router_core(self):
        c = cr.classify_contract_paths(["src/adaptive_router_v2.py"])
        self.assertEqual([i["category"] for i in c.critical], ["router-core"])

    def test_eval_module_classified_as_evaluation_core(self):
        c = cr.classify_contract_paths(["src/evaluate_speaker_cer.py"])
        self.assertEqual([i["category"] for i in c.critical], ["evaluation-core"])

    def test_non_critical_file_is_not_flagged(self):
        c = cr.classify_contract_paths(["src/some_frontier_receipt.py", "notes.txt"])
        self.assertEqual(c.critical, [])
        self.assertEqual(c.non_critical, ["src/some_frontier_receipt.py", "notes.txt"])

    def test_harness_paths_classified(self):
        c = cr.classify_contract_paths(
            ["scripts/harness/quality.py", ".githooks/pre-commit", ".github/workflows/test.yml", "Makefile"]
        )
        self.assertEqual({i["category"] for i in c.critical}, {"harness"})

    def test_gold_table_and_reference_categories(self):
        c = cr.classify_contract_paths(
            ["results/tables/cer_results.csv", "references/reference_transcripts.json"]
        )
        self.assertEqual({i["category"] for i in c.critical}, {"gold-results", "references"})

    def test_non_gold_result_table_is_not_critical(self):
        c = cr.classify_contract_paths(["results/tables/frontier_receipt_board.csv"])
        self.assertEqual(c.critical, [])


class TestNonCriticalDiff(unittest.TestCase):
    def test_advisory_when_no_critical_surface(self):
        result = cr.evaluate_contract(["docs/experiment_notes.md", "src/frontier_widget.py"])
        self.assertTrue(result["ok"])
        self.assertEqual(result["reasons"], [])
        self.assertTrue(any("advisory" in w for w in result["warnings"]))


class TestPairedTestGate(unittest.TestCase):
    def test_router_without_paired_test_fails(self):
        result = cr.evaluate_contract(["src/adaptive_router.py"], valid_summary())
        self.assertFalse(result["ok"])
        self.assertTrue(any("Missing paired test" in r and "src/adaptive_router.py" in r for r in result["reasons"]))

    def test_router_with_paired_test_and_summary_passes(self):
        result = cr.evaluate_contract(
            ["src/adaptive_router.py", "tests/test_adaptive_router_helpers.py"], valid_summary()
        )
        self.assertTrue(result["ok"], result["reasons"])

    def test_eval_module_requires_its_own_named_test(self):
        # A router test does NOT satisfy an evaluation-core module.
        result = cr.evaluate_contract(
            ["src/evaluate_cpcer_lite.py", "tests/test_adaptive_router_helpers.py"], valid_summary()
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("evaluate_cpcer_lite" in r for r in result["reasons"]))

    def test_eval_module_with_matching_test_passes(self):
        result = cr.evaluate_contract(
            ["src/evaluate_cpcer_lite.py", "tests/test_evaluate_cpcer_lite_build_row.py"], valid_summary()
        )
        self.assertTrue(result["ok"], result["reasons"])


class TestCategoryTestGate(unittest.TestCase):
    def test_harness_change_without_harness_test_fails(self):
        result = cr.evaluate_contract(["scripts/harness/quality.py"], valid_summary())
        self.assertFalse(result["ok"])
        self.assertIn("Missing contract test for critical category: harness", result["reasons"])

    def test_harness_change_with_harness_test_passes(self):
        result = cr.evaluate_contract(
            ["scripts/harness/quality.py", "tests/test_harness_contract_rules.py"], valid_summary()
        )
        self.assertTrue(result["ok"], result["reasons"])

    def test_harness_test_under_scripts_dir_also_satisfies(self):
        result = cr.evaluate_contract(
            ["scripts/harness/quality.py", "scripts/harness/tests/test_quality.py"], valid_summary()
        )
        self.assertTrue(result["ok"], result["reasons"])


class TestResultLabelGate(unittest.TestCase):
    def test_reference_change_requires_result_label(self):
        result = cr.evaluate_contract(["references/reference_transcripts.json"], valid_summary())
        self.assertFalse(result["ok"])
        self.assertTrue(any("result label" in r.lower() for r in result["reasons"]))

    def test_reference_change_with_label_passes(self):
        result = cr.evaluate_contract(
            ["references/reference_transcripts.json"], valid_summary("- Result label: gold\n")
        )
        self.assertTrue(result["ok"], result["reasons"])

    def test_gold_table_with_compound_label_passes(self):
        result = cr.evaluate_contract(
            ["results/tables/cer_results.csv"], valid_summary("- Result label: stable/gold\n")
        )
        self.assertTrue(result["ok"], result["reasons"])

    def test_invalid_result_label_fails(self):
        result = cr.evaluate_contract(
            ["results/tables/cer_results.csv"], valid_summary("- Result label: provisional\n")
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("Invalid result label" in r for r in result["reasons"]))


class TestSummaryEnforcement(unittest.TestCase):
    """Locally (enforce_summary=False) structural gates stay hard, but the
    impact-summary requirement is advisory; CI (enforce_summary=True) makes it
    hard."""

    def test_local_missing_summary_is_warning_not_failure(self):
        result = cr.evaluate_contract(
            ["src/adaptive_router.py", "tests/test_adaptive_router_helpers.py"],
            "",
            enforce_summary=False,
        )
        self.assertTrue(result["ok"], result["reasons"])
        self.assertTrue(any("impact summary" in w.lower() for w in result["warnings"]))

    def test_local_still_fails_on_missing_paired_test(self):
        # The TDD structural gate is hard even locally.
        result = cr.evaluate_contract(["src/adaptive_router.py"], "", enforce_summary=False)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Missing paired test" in r for r in result["reasons"]))

    def test_ci_missing_summary_is_hard_failure(self):
        result = cr.evaluate_contract(
            ["src/adaptive_router.py", "tests/test_adaptive_router_helpers.py"],
            "",
            enforce_summary=True,
        )
        self.assertFalse(result["ok"])


class TestImpactSummaryValidation(unittest.TestCase):
    def test_missing_summary_when_critical(self):
        result = cr.evaluate_contract(["src/adaptive_router.py", "tests/test_adaptive_router_helpers.py"], "")
        self.assertFalse(result["ok"])
        self.assertTrue(any("Missing structured GitNexus impact summary" in r for r in result["reasons"]))

    def test_placeholder_summary_rejected(self):
        for placeholder in ("-", "无", "TODO", "n/a"):
            self.assertTrue(cr.validate_impact_summary(placeholder))

    def test_invalid_risk_level(self):
        bad = (
            "- Risk level: SEVERE\n"
            "- Critical skeleton change: x\n"
            "- GitNexus impact: detect_changes and query\n"
            "- Verification: ran tests\n"
        )
        reasons = cr.validate_impact_summary(bad)
        self.assertTrue(any("Invalid GitNexus risk level" in r for r in reasons))

    def test_gitnexus_field_must_mention_detect_changes_and_a_tool(self):
        missing_tool = (
            "- Risk level: LOW\n"
            "- Critical skeleton change: x\n"
            "- GitNexus impact: ran detect_changes only\n"
            "- Verification: ran tests\n"
        )
        reasons = cr.validate_impact_summary(missing_tool)
        self.assertTrue(any("detect_changes and one of" in r for r in reasons))

    def test_missing_individual_fields(self):
        only_risk = "- Risk level: LOW\n"
        reasons = cr.validate_impact_summary(only_risk)
        self.assertTrue(any("skeleton_change" in r for r in reasons))
        self.assertTrue(any("gitnexus_impact" in r for r in reasons))
        self.assertTrue(any("verification" in r for r in reasons))

    def test_bilingual_chinese_fields_accepted(self):
        zh = (
            "- 风险等级: HIGH\n"
            "- 关键骨架变更: 调整了路由判定\n"
            "- GitNexus 影响面: 运行 detect_changes 与 impact\n"
            "- 验证结果: 全量单测通过\n"
        )
        self.assertEqual(cr.validate_impact_summary(zh), [])

    def test_valid_summary_has_no_reasons(self):
        self.assertEqual(cr.validate_impact_summary(valid_summary()), [])


class TestExtractImpactSummary(unittest.TestCase):
    def test_extracts_english_section(self):
        body = (
            "Some PR preamble.\n\n"
            "## GitNexus Impact Summary\n"
            "- Risk level: LOW\n"
            "- Verification: ran tests\n\n"
            "## Other Section\n"
            "ignored\n"
        )
        section = cr.extract_impact_summary(body)
        self.assertIn("Risk level: LOW", section)
        self.assertNotIn("ignored", section)

    def test_extracts_chinese_section(self):
        body = "前言\n\n### GitNexus 影响分析摘要\n- 风险等级: LOW\n\n## 下一节\n忽略\n"
        section = cr.extract_impact_summary(body)
        self.assertIn("风险等级: LOW", section)
        self.assertNotIn("忽略", section)

    def test_falls_back_to_whole_text_without_heading(self):
        self.assertEqual(cr.extract_impact_summary("just text"), "just text")


if __name__ == "__main__":
    unittest.main()
