import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsCloseoutLinksTest(unittest.TestCase):
    def test_current_roadmap_is_linked(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/current_roadmap.md", readme)
        self.assertIn("current_roadmap.md", docs_index)

    def test_pr_template_has_guard_fields(self):
        template = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(encoding="utf-8")
        for phrase in ["Risk Level", "Critical Skeleton Change", "GitNexus Impact", "Verification", "Claim Boundary"]:
            self.assertIn(phrase, template)


if __name__ == "__main__":
    unittest.main()
