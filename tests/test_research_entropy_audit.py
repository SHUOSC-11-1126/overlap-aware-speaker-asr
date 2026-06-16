"""Tests for src/research_entropy_audit.py.

The audit is a meta-analysis tool: it classifies the repository's own source
surface as research *substance* vs agentic *ceremony*, mines the git add-history
for the substance/ceremony dynamics, and produces an advisory diff verdict.

These tests pin the pure, deterministic core (classification, aggregation,
self-reference, timeline, diff verdict, the degeneration index) using injected
fixtures so they never depend on the live git state or filesystem layout. A
single output-writing test uses a tmp dir.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from src import research_entropy_audit as rea

# Representative source bodies ------------------------------------------------

SUBSTANCE_BODY = (
    "import numpy as np\n\n"
    "def separation_gain(mixed, separated):\n"
    "    delta = np.mean(separated) - np.mean(mixed)\n"
    "    return delta / len(mixed) * 100\n"
)

# A real ceremony file: builds hardcoded markdown/CSV status rows and writes
# them out; computes nothing about the research domain.
CEREMONY_BODY = (
    "import csv, json\n"
    "from pathlib import Path\n\n"
    "def build_lines(row):\n"
    "    return ['# Handoff Completion Summary', 'queue_status: ' + row['status']]\n\n"
    "def write_outputs(row):\n"
    "    Path('out.md').write_text('\\n'.join(build_lines(row)))\n"
    "    Path('out.json').write_text(json.dumps(row))\n"
)

SUPPORT_BODY = "from pathlib import Path\nPROJECT_ROOT = Path(__file__).resolve().parents[1]\n"


class ClassifyNameTest(unittest.TestCase):
    def test_ceremony_tokens_match_filenames(self) -> None:
        self.assertTrue(rea.is_ceremony_name("src/foo_coordination_writeback.py"))
        self.assertTrue(rea.is_ceremony_name("src/x_handoff_completion_summary.py"))
        self.assertTrue(rea.is_ceremony_name("src/demo_wave100_presentation_writeback.py"))
        self.assertTrue(rea.is_ceremony_name("src/y_bridge_checklist.py"))
        self.assertFalse(rea.is_ceremony_name("src/evaluate_cer.py"))
        self.assertFalse(rea.is_ceremony_name("src/separation_phase_diagram.py"))
        self.assertFalse(rea.is_ceremony_name("src/adaptive_router.py"))


class ClassifyFileTest(unittest.TestCase):
    def test_substance_file_is_substance(self) -> None:
        r = rea.classify_python_file("src/separation_phase_diagram.py", SUBSTANCE_BODY)
        self.assertEqual(r["klass"], "substance")
        self.assertTrue(r["compute_import"])
        self.assertGreaterEqual(r["arith_ops"], 3)

    def test_ceremony_file_is_ceremony(self) -> None:
        r = rea.classify_python_file(
            "src/frontier_operator_next_action_status_handoff_completion_summary.py",
            CEREMONY_BODY,
        )
        self.assertEqual(r["klass"], "ceremony")
        self.assertFalse(r["compute_import"])
        self.assertTrue(r["writes_doc"])

    def test_support_file_is_support(self) -> None:
        r = rea.classify_python_file("src/config.py", SUPPORT_BODY)
        self.assertEqual(r["klass"], "support")

    def test_ceremony_named_sibling_of_substance_is_ceremony(self) -> None:
        # separation_phase_diagram.py (substance) vs its coordination writeback
        # barnacle (ceremony) -- same stem family, opposite class.
        r = rea.classify_python_file("src/separation_phase_coordination_writeback.py", CEREMONY_BODY)
        self.assertEqual(r["klass"], "ceremony")

    def test_compute_override_flags_disagreement(self) -> None:
        # A ceremony-named file that actually computes is reclassified to
        # substance and flagged as a name/content disagreement (honesty check).
        r = rea.classify_python_file("src/cascade_benchmark_writeback.py", SUBSTANCE_BODY)
        self.assertEqual(r["klass"], "substance")
        self.assertTrue(r["disagreement"])


class AuditFilesTest(unittest.TestCase):
    def _fixture(self):
        return [
            ("src/separation_phase_diagram.py", SUBSTANCE_BODY),
            ("src/a_coordination_writeback.py", CEREMONY_BODY),
            ("src/b_handoff_completion_summary.py", CEREMONY_BODY),
            ("src/config.py", SUPPORT_BODY),
        ]

    def test_counts_and_saturation(self) -> None:
        summary = rea.audit_files(self._fixture())
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["counts"]["substance"], 1)
        self.assertEqual(summary["counts"]["ceremony"], 2)
        self.assertEqual(summary["counts"]["support"], 1)
        # saturation excludes support from the denominator: 2 / (2 + 1)
        self.assertAlmostEqual(summary["ceremony_saturation"], 2 / 3, places=6)

    def test_content_contrast_present(self) -> None:
        summary = rea.audit_files(self._fixture())
        # ceremony files should have a far lower compute-import rate than substance
        self.assertLess(
            summary["content"]["ceremony_compute_import_rate"],
            summary["content"]["substance_compute_import_rate"],
        )


class SelfReferenceTest(unittest.TestCase):
    def test_ratio_counts_ceremony_to_ceremony_refs(self) -> None:
        # A ceremony file that references one other ceremony stem and one
        # substance stem -> self-reference ratio 0.5.
        ceremony_text = (
            "load('frontier_operator_next_action_status_handoff')\n"
            "import evaluate_cer\n"
        )
        items = [
            ("src/a_handoff.py", ceremony_text),
            ("src/frontier_operator_next_action_status_handoff.py", "x=1\n"),
            ("src/evaluate_cer.py", "import numpy\n"),
        ]
        res = rea.self_reference_ratio(items)
        self.assertEqual(res["total_refs"], 2)
        self.assertEqual(res["ceremony_refs"], 1)
        self.assertAlmostEqual(res["ratio"], 0.5, places=6)


class TimelineTest(unittest.TestCase):
    def test_per_day_counts_and_collapse_detection(self) -> None:
        events = [
            ("2026-06-02", "src/evaluate_cer.py"),
            ("2026-06-12", "src/a_writeback.py"),
            ("2026-06-12", "src/b_handoff.py"),
            ("2026-06-12", "src/c_receipt.py"),
            ("2026-06-12", "src/real_module.py"),
        ]
        tl = rea.summarize_timeline(events)
        by_day = {d["date"]: d for d in tl["by_day"]}
        self.assertEqual(by_day["2026-06-02"]["substance"], 1)
        self.assertEqual(by_day["2026-06-02"]["ceremony"], 0)
        self.assertEqual(by_day["2026-06-12"]["ceremony"], 3)
        self.assertEqual(by_day["2026-06-12"]["substance"], 1)
        # cumulative substance after 06-12 = 2
        self.assertEqual(by_day["2026-06-12"]["cum_substance"], 2)
        self.assertEqual(tl["peak_ceremony_day"], "2026-06-12")
        self.assertEqual(tl["first_collapse_day"], "2026-06-12")


class DiffVerdictTest(unittest.TestCase):
    def test_pure_ceremony_addition_warns(self) -> None:
        v = rea.assess_diff(
            ["src/x_writeback.py", "src/y_handoff.py", "src/z_receipt.py"]
        )
        self.assertEqual(v["delta_ceremony"], 3)
        self.assertEqual(v["delta_substance"], 0)
        self.assertEqual(v["verdict"], "warn")

    def test_substance_addition_ok(self) -> None:
        v = rea.assess_diff(["src/evaluate_new_metric.py"])
        self.assertEqual(v["verdict"], "ok")

    def test_empty_diff_ok(self) -> None:
        self.assertEqual(rea.assess_diff([])["verdict"], "ok")

    def test_non_python_ignored(self) -> None:
        v = rea.assess_diff(["docs/notes.md", "results/x.csv"])
        self.assertEqual(v["delta_ceremony"], 0)
        self.assertEqual(v["delta_substance"], 0)
        self.assertEqual(v["verdict"], "ok")

    def test_ratio_threshold_warns(self) -> None:
        v = rea.assess_diff(
            [
                "src/a_writeback.py",
                "src/b_writeback.py",
                "src/c_writeback.py",
                "src/d_writeback.py",
                "src/e_real.py",
            ]
        )
        self.assertEqual(v["verdict"], "warn")


class DegenerationIndexTest(unittest.TestCase):
    def test_bounds(self) -> None:
        self.assertEqual(rea.degeneration_index(0.0, 0.0), 0.0)
        self.assertAlmostEqual(rea.degeneration_index(1.0, 1.0), 1.0, places=6)
        di = rea.degeneration_index(0.89, 0.8)
        self.assertTrue(0.0 <= di <= 1.0)


class ContentCeremonyTest(unittest.TestCase):
    """A name-clean file that computes nothing and only emits documents is a
    content-ceremony candidate -- the audit reports it as a separate, higher
    estimate so the headline (name-based) figure is an auditable lower bound."""

    def test_name_clean_doc_emitter_flagged_by_content(self) -> None:
        # 'review_pass_status' is not in the ceremony token list, so the name
        # signal misses it; the content signal should catch it.
        r = rea.classify_python_file("src/llm_critic_review_pass_status.py", CEREMONY_BODY)
        self.assertFalse(r["name_ceremony"])
        self.assertEqual(r["klass"], "substance")  # name-anchored class
        self.assertTrue(r["content_ceremony"])  # but content says ceremony

    def test_upper_estimate_exceeds_lower_bound(self) -> None:
        items = [
            ("src/separation_phase_diagram.py", SUBSTANCE_BODY),
            ("src/a_coordination_writeback.py", CEREMONY_BODY),
            ("src/llm_critic_review_pass_status.py", CEREMONY_BODY),  # name-clean doc emitter
            ("src/config.py", SUPPORT_BODY),
        ]
        summary = rea.audit_files(items)
        self.assertEqual(summary["content"]["borderline_substance_count"], 1)
        self.assertGreater(
            summary["ceremony_saturation_content_upper"], summary["ceremony_saturation"]
        )


class WriteOutputsTest(unittest.TestCase):
    def test_writes_three_artifacts(self) -> None:
        report = {
            "label": "experimental/frontier (meta-analysis / analysis-only)",
            "summary": {
                "total": 4,
                "counts": {"substance": 1, "ceremony": 2, "support": 1},
                "ceremony_saturation": 0.667,
                "content": {
                    "ceremony_compute_import_rate": 0.0,
                    "substance_compute_import_rate": 1.0,
                    "ceremony_mean_arith": 0.0,
                    "substance_mean_arith": 4.0,
                },
                "files": [
                    {"path": "src/x.py", "klass": "substance", "arith_ops": 4,
                     "compute_import": True, "writes_doc": False, "name_ceremony": False,
                     "str_ratio": 0.1, "loc": 5, "disagreement": False},
                ],
            },
            "self_reference": {"ratio": 0.5, "ceremony_refs": 1, "total_refs": 2},
            "timeline": {
                "by_day": [
                    {"date": "2026-06-02", "ceremony": 0, "substance": 1,
                     "cum_ceremony": 0, "cum_substance": 1},
                ],
                "peak_ceremony_day": "2026-06-12",
                "first_collapse_day": "2026-06-12",
            },
            "degeneration_index": 0.53,
        }
        with tempfile.TemporaryDirectory() as d:
            paths = rea.write_outputs(report, Path(d))
            names = {p.name for p in paths}
            self.assertIn("entropy_summary.json", names)
            self.assertIn("file_classification.csv", names)
            self.assertIn("entropy_timeline.csv", names)
            payload = json.loads((Path(d) / "entropy_summary.json").read_text(encoding="utf-8"))
            self.assertIn("degeneration_index", payload)
            self.assertEqual(payload["summary"]["counts"]["ceremony"], 2)


class HarnessGuardConsistencyTest(unittest.TestCase):
    """The stdlib-only harness guard must share the audit's ceremony vocabulary
    and diff verdict, or the pre-dev advisory drifts from the analysis."""

    def _import_guard(self):
        here = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(here / "scripts" / "harness"))
        import entropy_guard  # noqa: E402

        return entropy_guard

    def test_ceremony_tokens_match(self) -> None:
        guard = self._import_guard()
        self.assertEqual(set(guard.CEREMONY_TOKENS), set(rea.CEREMONY_TOKENS))

    def test_verdict_matches_on_samples(self) -> None:
        guard = self._import_guard()
        for sample in (
            ["src/x_writeback.py", "src/y_handoff.py", "src/z_receipt.py"],
            ["src/evaluate_new.py"],
            [],
        ):
            self.assertEqual(
                guard.assess_diff(sample)["verdict"],
                rea.assess_diff(sample)["verdict"],
                msg=f"verdict mismatch for {sample}",
            )


if __name__ == "__main__":
    unittest.main()
