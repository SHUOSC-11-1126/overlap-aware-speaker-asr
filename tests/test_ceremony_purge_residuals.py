"""Guards the ceremony helpers deliberately retained by the ceremony purge.

The purge (docs/cleanup/ceremony-purge-manifest.md) deleted ceremony-named
modules that compute nothing, but kept three because kept modules/tests still
import them (import-closure safety). This test documents and enforces that
retention rationale: each helper must remain importable, and each declared
importer must actually import it. If a future change removes the last importer,
this test flags that the helper can now be deleted too.
"""

from __future__ import annotations

import importlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# retained ceremony helper -> kept file(s) that import it (its load-bearing reason)
RETAINED = {
    "external_validation_go_no_go_board": [
        "src/external_validation_narrow_audio_eval.py",
    ],
    "external_validation_slice_scaffold": [
        "src/external_validation_license_confirmation.py",
        "src/external_validation_audio_excerpt_staging_plan.py",
    ],
    "meeteval_cpwer_official_execution_completion_summary": [
        "tests/test_meeteval_cpwer_official_execution.py",
    ],
}


class RetainedCeremonyHelpersTest(unittest.TestCase):
    def test_helpers_remain_importable(self) -> None:
        for module in RETAINED:
            importlib.import_module(f"src.{module}")  # must not raise

    def test_helpers_are_load_bearing(self) -> None:
        for module, importers in RETAINED.items():
            self.assertTrue(importers, f"{module} has no recorded importer")
            for rel in importers:
                path = ROOT / rel
                self.assertTrue(path.exists(), f"recorded importer missing: {rel}")
                self.assertIn(
                    module,
                    path.read_text(encoding="utf-8"),
                    f"{rel} should import {module} (purge-retention justification)",
                )


if __name__ == "__main__":
    unittest.main()
