from __future__ import annotations

import importlib
import io
import unittest
from contextlib import redirect_stdout


PLACEHOLDER_MODULES = [
    "src.evaluate_summary",
    "src.transcribe_funasr",
    "src.rag_retrieve",
]


class StagePlaceholderModulesTest(unittest.TestCase):
    def test_placeholder_modules_are_importable_with_docstrings(self) -> None:
        for module_name in PLACEHOLDER_MODULES:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertIsNotNone(module.__doc__)
                self.assertIn("placeholder", module.__doc__.lower())

    def test_placeholder_main_prints_not_implemented_message(self) -> None:
        for module_name in PLACEHOLDER_MODULES:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    module.main()
                self.assertIn("not implemented", buffer.getvalue().lower())


if __name__ == "__main__":
    unittest.main()
