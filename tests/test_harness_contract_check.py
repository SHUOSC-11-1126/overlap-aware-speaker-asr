"""Tests for the GitNexus contract-check CLI helpers.

Covers the pieces that don't shell out: the npx invocation builder, the
GITNEXUS_VERSION override, timeout resolution, and PR-body impact extraction.
This file also satisfies the ``harness`` contract category's test pattern, so
changes to scripts/harness/contract_check.py are allowed to land with it.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path

_HARNESS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "harness"
sys.path.insert(0, str(_HARNESS_DIR))


def _load(mod_name, filename):
    spec = importlib.util.spec_from_file_location(mod_name, _HARNESS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


cc = _load("harness_contract_check", "contract_check.py")


class TestGitnexusInvocation(unittest.TestCase):
    def test_uses_pinned_version_and_index_only(self):
        args = cc.build_gitnexus_args()
        self.assertEqual(args[0], "npx")
        self.assertIn("--yes", args)
        self.assertIn(f"gitnexus@{cc.GITNEXUS_VERSION}", args)
        self.assertEqual(args[-3:], ["analyze", "--force", "--index-only"])

    def test_does_not_use_prefer_offline(self):
        # --prefer-offline breaks on a cold npm cache (ETARGET on transitive deps).
        self.assertNotIn("--prefer-offline", cc.build_gitnexus_args())

    def test_default_version_is_pinned_stable(self):
        # A pinned x.y.z (not a dist-tag) keeps the index build reproducible.
        parts = cc.GITNEXUS_VERSION.split(".")
        self.assertEqual(len(parts), 3, cc.GITNEXUS_VERSION)
        self.assertTrue(all(p.isdigit() for p in parts), cc.GITNEXUS_VERSION)


class TestTimeoutResolution(unittest.TestCase):
    def setUp(self):
        self._saved = os.environ.pop("GITNEXUS_ANALYZE_TIMEOUT_MS", None)

    def tearDown(self):
        if self._saved is not None:
            os.environ["GITNEXUS_ANALYZE_TIMEOUT_MS"] = self._saved
        else:
            os.environ.pop("GITNEXUS_ANALYZE_TIMEOUT_MS", None)

    def test_ci_default_larger_than_local(self):
        self.assertGreater(cc.resolve_timeout_ms("ci"), cc.resolve_timeout_ms("local"))

    def test_env_override(self):
        os.environ["GITNEXUS_ANALYZE_TIMEOUT_MS"] = "12345"
        self.assertEqual(cc.resolve_timeout_ms("local"), 12345)

    def test_invalid_override_rejected(self):
        os.environ["GITNEXUS_ANALYZE_TIMEOUT_MS"] = "-1"
        with self.assertRaises(SystemExit):
            cc.resolve_timeout_ms("local")


class TestChangedFilesAndSummary(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ("CONTRACT_CHANGED_FILES", "GITNEXUS_IMPACT_SUMMARY")}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_changed_files_env_override_splits_on_comma_and_newline(self):
        os.environ["CONTRACT_CHANGED_FILES"] = "a.py, b.py\nc.py"
        self.assertEqual(cc.get_changed_files("local"), ["a.py", "b.py", "c.py"])

    def test_impact_summary_from_env(self):
        os.environ["GITNEXUS_IMPACT_SUMMARY"] = "## GitNexus Impact Summary\n- Risk level: LOW\n"
        self.assertIn("Risk level: LOW", cc.get_impact_summary())


if __name__ == "__main__":
    unittest.main()
