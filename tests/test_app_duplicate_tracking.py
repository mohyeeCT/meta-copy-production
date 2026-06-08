import unittest
from pathlib import Path


class DuplicateKeywordTrackingTests(unittest.TestCase):
    def setUp(self):
        self.source = Path("app.py").read_text(encoding="utf-8")
        self.lines = self.source.splitlines()

    def test_used_keywords_initialised_before_loop(self):
        """used_keywords set must be created before the per-row loop."""
        init_line = next(
            (i for i, l in enumerate(self.lines) if "used_keywords: set = set()" in l), None
        )
        loop_line = next(
            (i for i, l in enumerate(self.lines) if "for i, row in df_work.iterrows()" in l), None
        )
        self.assertIsNotNone(init_line, "used_keywords initialisation not found in app.py")
        self.assertIsNotNone(loop_line, "df_work loop not found in app.py")
        self.assertLess(init_line, loop_line,
                        "used_keywords must be initialised before the row loop")

    def test_duplicate_check_is_below_none_guard(self):
        """Duplicate check must come after the 'if not selected_keyword' guard."""
        guard_line = next(
            (i for i, l in enumerate(self.lines) if "if not selected_keyword:" in l), None
        )
        dup_line = next(
            (i for i, l in enumerate(self.lines) if "duplicate — reused" in l), None
        )
        self.assertIsNotNone(guard_line, "'if not selected_keyword' guard not found")
        self.assertIsNotNone(dup_line, "duplicate tracking line not found in app.py")
        self.assertGreater(dup_line, guard_line,
                           "Duplicate check must be below the None guard to avoid AttributeError")

    def test_duplicate_label_matches_saas(self):
        """Appended label must match the SaaS keyword_source suffix exactly."""
        self.assertIn("(duplicate — reused)", self.source)


if __name__ == "__main__":
    unittest.main()
