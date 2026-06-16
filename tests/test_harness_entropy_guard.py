"""Tests for the stdlib-only harness research-entropy guard.

This satisfies the contract's ``harness`` category-test gate and pins the guard's
advisory behaviour: it must classify ceremony names, produce a sensible diff
verdict, and -- crucially -- ALWAYS return 0 so it can never block a commit or
push (it is an advisory hygiene signal, not a gate).

The guard is imported the same way quality.py imports contract_check: by adding
scripts/harness to sys.path. It must remain importable under a bare python3
without the project virtualenv, so this test imports nothing from ``src``.
"""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "harness"
sys.path.insert(0, str(HARNESS_DIR))

import entropy_guard  # noqa: E402


class GuardNameTest(unittest.TestCase):
    def test_ceremony_names(self) -> None:
        self.assertTrue(entropy_guard.is_ceremony_name("src/x_coordination_writeback.py"))
        self.assertTrue(entropy_guard.is_ceremony_name("results/y_handoff_completion_summary.md"))
        self.assertFalse(entropy_guard.is_ceremony_name("src/evaluate_cer.py"))


class GuardVerdictTest(unittest.TestCase):
    def test_pure_ceremony_warns(self) -> None:
        v = entropy_guard.assess_diff(["src/a_writeback.py", "src/b_handoff.py"])
        self.assertEqual(v["verdict"], "warn")
        self.assertEqual(v["delta_ceremony"], 2)
        self.assertEqual(v["delta_substance"], 0)

    def test_substance_ok(self) -> None:
        self.assertEqual(entropy_guard.assess_diff(["src/evaluate_new.py"])["verdict"], "ok")

    def test_empty_ok(self) -> None:
        self.assertEqual(entropy_guard.assess_diff([])["verdict"], "ok")


class GuardAdvisoryTest(unittest.TestCase):
    def test_run_guard_always_returns_zero_even_on_warn(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = entropy_guard.run_guard(
                changed=["src/a_writeback.py", "src/b_handoff.py", "src/c_receipt.py"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("advisory", buf.getvalue().lower())

    def test_run_guard_clean_diff_returns_zero(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = entropy_guard.run_guard(changed=["src/evaluate_new.py"])
        self.assertEqual(rc, 0)
        self.assertIn("ok", buf.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
